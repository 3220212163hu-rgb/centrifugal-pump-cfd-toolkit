#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本科毕业论文检索闭环工具：SQLite 精确检索 + Qdrant 语义检索 + 原文回查建议。

目标：
1) 先用 vault_search.py 同款 SQLite 全文检索做精确命中；
2) 再用 Qdrant 做语义召回；
3) 将结果映射回文献实体页、原文 Markdown、PDF 原文；
4) 为后续人工阅读提供清晰的下一跳路径。

当前支持的语义集合：
- thesis_literature_zh
- thesis_literature

未来可继续接入：
- thesis_paper_chunks
- thesis_simulation_results
- thesis_figures
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# 国内镜像源，避免首次下载模型时超时
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from common.path_config import PROJECT_DIR, QDRANT_PATH, REF_DIR, NOTES_DIR  # type: ignore
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

PROJECT_DIR = Path(PROJECT_DIR)
QDRANT_PATH = Path(QDRANT_PATH)
REF_DIR = Path(REF_DIR)
NOTES_DIR = Path(NOTES_DIR)

VAULT_DIR = PROJECT_DIR / "ObsidianVault" / "本科毕业论文知识库"
VAULT_DB = Path(os.environ.get(
    "VAULT_DB_PATH",
    str(PROJECT_DIR / "thesis_vault_index.sqlite")
))
REFERENCE_JSON = PROJECT_DIR / "03-论文正文" / "references.json"

ZH_MODEL = "BAAI/bge-large-zh-v1.5"
EN_MODEL = "all-MiniLM-L6-v2"

# 未来扩展：脚本会自动跳过不存在的集合。
COLLECTION_SPECS = [
    {"name": "thesis_literature_zh", "model": ZH_MODEL, "purpose": "文献语义检索"},
    {"name": "thesis_literature", "model": EN_MODEL, "purpose": "文献语义检索"},
    {"name": "thesis_paper_chunks", "model": ZH_MODEL, "purpose": "文献语义检索"},
    {"name": "thesis_simulation_results", "model": ZH_MODEL, "purpose": "仿真结果说明"},
    {"name": "thesis_figures", "model": ZH_MODEL, "purpose": "图片说明"},
]


def detect_language(text: str) -> str:
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    total = len(re.sub(r"\s", "", text))
    if total == 0:
        return "en"
    return "zh" if chinese / total > 0.3 else "en"


def make_snippet(text: str, query: str, width: int = 180) -> str:
    query_tokens = [q for q in re.split(r"\s+", query.strip()) if q]
    idx = -1
    low = text.lower()
    for token in query_tokens:
        idx = low.find(token.lower())
        if idx >= 0:
            break
    if idx < 0:
        idx = 0
    start = max(0, idx - width // 2)
    end = min(len(text), idx + width // 2)
    snip = text[start:end].replace("\n", " ")
    return re.sub(r"\s+", " ", snip).strip()


def normalize_path(path_str: str) -> Path:
    if not path_str:
        return Path()
    path_str = str(path_str)
    m = re.match(r"^([A-Za-z]):\\(.*)$", path_str)
    if m:
        drive = m.group(1).lower()
        rest = m.group(2).replace("\\", "/")
        return Path(f"/mnt/{drive}") / rest
    return Path(path_str)


@lru_cache(maxsize=1)
def load_references() -> Tuple[Dict[str, dict], Dict[str, dict]]:
    by_card: Dict[str, dict] = {}
    by_pdf: Dict[str, dict] = {}
    if not REFERENCE_JSON.exists():
        return by_card, by_pdf
    try:
        data = json.loads(REFERENCE_JSON.read_text(encoding="utf-8"))
    except Exception:
        return by_card, by_pdf

    for row in data:
        card = row.get("vault_card")
        if card:
            by_card[str(card)] = row
        pdf_path = row.get("pdf_path")
        if pdf_path:
            by_pdf[Path(str(pdf_path)).name.lower()] = row
    return by_card, by_pdf


def find_first_match(root: Path, target_name: str) -> Optional[Path]:
    if not root.exists() or not target_name:
        return None
    target_name = Path(target_name).name
    direct = root / target_name
    if direct.exists():
        return direct
    for p in root.rglob(target_name):
        if p.name == target_name:
            return p
    return None


def find_entity_page(vault_card: Optional[str]) -> Optional[Path]:
    if not vault_card:
        return None
    return find_first_match(VAULT_DIR / "实体" / "文献", f"{vault_card}.md")


def find_raw_md(pdf_name: Optional[str]) -> Optional[Path]:
    if not pdf_name:
        return None
    stem = Path(pdf_name).stem
    root = VAULT_DIR / "raw" / "papers"
    direct = find_first_match(root, f"{stem}.md")
    if direct:
        return direct
    for p in root.rglob("*.md"):
        if stem.lower() in p.stem.lower():
            return p
    return None


def find_pdf_file(pdf_name: Optional[str]) -> Optional[Path]:
    if not pdf_name:
        return None
    root = VAULT_DIR / "原始素材" / "pdfs"
    direct = find_first_match(root, pdf_name)
    if direct:
        return direct
    stem = Path(pdf_name).stem.lower()
    for p in root.rglob("*.pdf"):
        if p.name.lower() == pdf_name.lower() or stem in p.stem.lower():
            return p
    return None


def sqlite_search(query: str, limit: int = 8, kind: Optional[str] = None) -> List[dict]:
    if not VAULT_DB.exists():
        raise FileNotFoundError(f"SQLite 索引不存在：{VAULT_DB}")

    con = sqlite3.connect(VAULT_DB)
    con.row_factory = sqlite3.Row
    rows: List[dict] = []
    try:
        where = ""
        params: List[Any] = [query]
        if kind:
            where = "AND docs.kind = ?"
            params.append(kind)
        sql = f"""
        SELECT docs.*, bm25(docs_fts) AS score
        FROM docs_fts JOIN docs ON docs_fts.rowid = docs.id
        WHERE docs_fts MATCH ? {where}
        ORDER BY score
        LIMIT ?
        """
        params.append(limit)
        try:
            fetched = con.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            like = f"%{query}%"
            if kind:
                fetched = con.execute(
                    "SELECT *, 0.0 as score FROM docs WHERE content LIKE ? AND kind = ? ORDER BY relpath LIMIT ?",
                    (like, kind, limit),
                ).fetchall()
            else:
                fetched = con.execute(
                    "SELECT *, 0.0 as score FROM docs WHERE content LIKE ? ORDER BY relpath LIMIT ?",
                    (like, limit),
                ).fetchall()
        for r in fetched:
            rows.append(dict(r))
    finally:
        con.close()
    return rows


@lru_cache(maxsize=4)
def load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def collection_exists(client: QdrantClient, collection_name: str) -> bool:
    try:
        client.get_collection(collection_name)
        return True
    except Exception:
        return False


def semantic_search(
    query: str,
    limit: int = 5,
    collection: Optional[str] = None,
    search_all_existing: bool = False,
) -> List[dict]:
    client = QdrantClient(path=str(QDRANT_PATH))
    lang = detect_language(query)

    if collection:
        specs = [s for s in COLLECTION_SPECS if s["name"] == collection]
    elif search_all_existing:
        specs = [s for s in COLLECTION_SPECS if collection_exists(client, s["name"])]
    else:
        # 默认先按语言只打当前最合适的集合，避免跨模型分数不可比。
        preferred = ["thesis_literature_zh", "thesis_literature"] if lang == "zh" else ["thesis_literature"]
        specs = [s for s in COLLECTION_SPECS if s["name"] in preferred and collection_exists(client, s["name"])]
        if not specs:
            specs = [s for s in COLLECTION_SPECS if collection_exists(client, s["name"])]

    results: List[dict] = []
    for spec in specs:
        model = load_model(spec["model"])
        vector = model.encode(query).tolist()
        hits = client.query_points(
            collection_name=spec["name"],
            query=vector,
            limit=limit,
        )
        for point in hits.points:
            payload = dict(point.payload or {})
            payload.update(
                {
                    "score": float(point.score),
                    "collection": spec["name"],
                    "model": spec["model"],
                    "purpose": spec["purpose"],
                }
            )
            results.append(payload)

    results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return results[:limit]


def resolve_paths_from_payload(payload: dict) -> dict:
    by_card, by_pdf = load_references()
    pdf_name = payload.get("pdf_name") or Path(payload.get("pdf_path", "")).name
    pdf_name = str(pdf_name) if pdf_name else ""
    ref = by_pdf.get(pdf_name.lower()) if pdf_name else None
    vault_card = ref.get("vault_card") if ref else None

    entity_page = find_entity_page(vault_card)
    raw_md = find_raw_md(pdf_name)
    pdf_file = find_pdf_file(pdf_name)

    return {
        "vault_card": vault_card,
        "reference": ref,
        "entity_page": entity_page,
        "raw_markdown": raw_md,
        "pdf_file": pdf_file,
    }


def print_exact_results(query: str, rows: List[dict]) -> None:
    print("\n=== 1) SQLite 精确检索 ===")
    print(f"查询：{query}")
    print(f"命中：{len(rows)} 条")
    if not rows:
        print("  无直接命中。可尝试更短的关键词组合，如：β2 / 叶片出口角 / SST k-ω / efficiency")
        return
    for i, row in enumerate(rows, 1):
        print(f"\n[{i}] {row.get('title', '未命名')}")
        print(f"    类型：{row.get('kind', '未知')}")
        print(f"    路径：{row.get('path', '未知')}")
        print(f"    相对路径：{row.get('relpath', '未知')}")
        print(f"    片段：{make_snippet(row.get('content', ''), query)}")


def print_semantic_results(query: str, rows: List[dict]) -> None:
    print("\n=== 2) Qdrant 语义检索 ===")
    print(f"查询：{query}")
    print(f"命中：{len(rows)} 条")
    if not rows:
        print("  当前语义集合没有返回结果。")
        return

    for i, row in enumerate(rows, 1):
        text = str(row.get("text", ""))
        pdf_name = row.get("pdf_name") or Path(row.get("pdf_path", "")).name
        print(f"\n[{i}] 分数：{row.get('score', 0.0):.4f} | 集合：{row.get('collection', '未知')} | 论文：{pdf_name}")
        print(f"    类别：{row.get('category', '未知')} | 页码：{row.get('page', '?')}")
        preview = text[:220].replace("\n", " ").strip()
        print(f"    预览：{preview}..." if preview else "    预览：无")


def print_recall_chain(rows: List[dict]) -> None:
    print("\n=== 3) 原文回查链 ===")
    if not rows:
        print("  无语义结果可回查。")
        return

    for i, row in enumerate(rows, 1):
        resolved = resolve_paths_from_payload(row)
        print(f"\n[{i}] 语义结果：{row.get('pdf_name', '未知')}")
        print(f"    文献实体页：{resolved['entity_page'] if resolved['entity_page'] else '未找到'}")
        print(f"    原文 Markdown：{resolved['raw_markdown'] if resolved['raw_markdown'] else '未找到'}")
        print(f"    PDF 原文：{resolved['pdf_file'] if resolved['pdf_file'] else '未找到'}")
        if resolved["vault_card"]:
            print(f"    实体卡片：{resolved['vault_card']}")
        ref = resolved["reference"]
        if ref:
            print(f"    参考文献编号：{ref.get('citation_number', '未知')}")
            print(f"    GB/T 7714：{ref.get('gbt_7714', '未知')}")


def run_hybrid(query: str, exact_limit: int, semantic_limit: int, kind: Optional[str], collection: Optional[str], all_semantic: bool) -> None:
    exact_rows = sqlite_search(query, limit=exact_limit, kind=kind)
    semantic_rows = semantic_search(query, limit=semantic_limit, collection=collection, search_all_existing=all_semantic)

    print_exact_results(query, exact_rows)
    print_semantic_results(query, semantic_rows)
    print_recall_chain(semantic_rows)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="本科毕业论文检索闭环工具")
    parser.add_argument("query", nargs="?", help="检索关键词或问题")
    parser.add_argument("--exact-limit", type=int, default=8, help="SQLite 精确检索返回条数")
    parser.add_argument("--semantic-limit", type=int, default=5, help="Qdrant 语义检索返回条数")
    parser.add_argument("--kind", default=None, help="SQLite 文档类型过滤：文献实体/原文提取/概念页/专题页/对比分析/索引/其他笔记")
    parser.add_argument("--collection", default=None, help="仅查询指定 Qdrant 集合")
    parser.add_argument("--all-semantic", action="store_true", help="查询当前已存在的全部语义集合")
    parser.add_argument("--json", action="store_true", help="输出 JSON（便于后续自动化）")
    parser.add_argument("--mode", choices=["hybrid", "exact", "semantic"], default="hybrid")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    if not args.query:
        print(__doc__)
        return

    if args.mode == "exact":
        rows = sqlite_search(args.query, limit=args.exact_limit, kind=args.kind)
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
        else:
            print_exact_results(args.query, rows)
        return

    if args.mode == "semantic":
        rows = semantic_search(
            args.query,
            limit=args.semantic_limit,
            collection=args.collection,
            search_all_existing=args.all_semantic,
        )
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
        else:
            print_semantic_results(args.query, rows)
            print_recall_chain(rows)
        return

    exact_rows = sqlite_search(args.query, limit=args.exact_limit, kind=args.kind)
    semantic_rows = semantic_search(
        args.query,
        limit=args.semantic_limit,
        collection=args.collection,
        search_all_existing=args.all_semantic,
    )

    if args.json:
        print(
            json.dumps(
                {
                    "query": args.query,
                    "exact": exact_rows,
                    "semantic": semantic_rows,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        return

    print(f"检索闭环：SQLite → Qdrant → 实体页 → 原文 Markdown → PDF")
    print(f"Vault：{VAULT_DIR}")
    print(f"SQLite：{VAULT_DB}")
    print(f"Qdrant：{QDRANT_PATH}")
    print(f"检测语言：{detect_language(args.query)}")
    print_exact_results(args.query, exact_rows)
    print_semantic_results(args.query, semantic_rows)
    print_recall_chain(semantic_rows)


if __name__ == "__main__":
    main()
