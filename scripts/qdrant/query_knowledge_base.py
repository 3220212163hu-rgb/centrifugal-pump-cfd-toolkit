# -*- coding: utf-8 -*-
"""
论文知识库查询工具
功能：
  1. 语义搜索文本（Qdrant）
  2. 图片检索（关键词匹配）
  3. 按论文浏览

运行环境：Windows PowerShell
用法：
  python query_knowledge_base.py search "进口导叶效率"
  python query_knowledge_base.py image "速度分布"
  python query_knowledge_base.py list
  python query_knowledge_base.py interactive
"""

import os
import sys
import json
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# 国内镜像源配置
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 配置
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
from common.path_config import PROJECT_DIR

PROJECT_ROOT = PROJECT_DIR
QDRANT_PATH = os.path.join(PROJECT_ROOT, "qdrant_data")
COLLECTION_NAME = "thesis_literature"
PAPERS_DIR = os.path.join(PROJECT_ROOT, "ObsidianVault", "本科毕业论文知识库", "raw", "papers")
IMAGES_INDEX_FILE = os.path.join(PAPERS_DIR, "图片索引.json")

MODEL_NAME = "all-MiniLM-L6-v2"


def load_model():
    """加载嵌入模型"""
    print("加载模型中...")
    model = SentenceTransformer(MODEL_NAME)
    print("模型加载完成！\n")
    return model


def search_text(query, model, top_k=5):
    """语义搜索文本"""
    client = QdrantClient(path=QDRANT_PATH)
    
    vector = model.encode(query).tolist()
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=top_k,
    )
    
    print(f"\n{'='*60}")
    print(f"搜索: {query}")
    print(f"{'='*60}")
    
    if not results.points:
        print("没有找到相关内容")
        return
    
    for i, point in enumerate(results.points):
        paper = point.payload.get('paper', '未知')
        section = point.payload.get('section', '未知')
        text = point.payload['text']
        
        print(f"\n[{i+1}] 相似度: {point.score:.3f}")
        print(f"    论文: {paper}")
        print(f"    章节: {section}")
        print(f"    内容预览:")
        # 显示前200字
        preview = text[:200].replace('\n', ' ').strip()
        print(f"    {preview}...")
        print(f"    {'-'*50}")


def search_image(keyword):
    """搜索图片"""
    if not os.path.exists(IMAGES_INDEX_FILE):
        print("图片索引不存在，请先运行 pdf_to_markdown_qdrant.py")
        return
    
    with open(IMAGES_INDEX_FILE, "r", encoding="utf-8") as f:
        images = json.load(f)
    
    # 关键词匹配（在论文名中搜索）
    matches = []
    keyword_lower = keyword.lower()
    for img in images:
        paper_lower = img["paper"].lower()
        if keyword_lower in paper_lower:
            matches.append(img)
    
    print(f"\n{'='*60}")
    print(f"图片搜索: {keyword}")
    print(f"{'='*60}")
    
    if not matches:
        print("没有找到匹配的图片")
        print(f"提示: 当前索引中有 {len(images)} 张图片")
        print("可用的论文列表:")
        papers = set(img["paper"] for img in images)
        for p in sorted(papers)[:10]:
            print(f"  - {p}")
        return
    
    # 按论文分组显示
    from collections import defaultdict
    by_paper = defaultdict(list)
    for img in matches:
        by_paper[img["paper"]].append(img)
    
    for paper, imgs in by_paper.items():
        print(f"\n论文: {paper}")
        for img in imgs:
            print(f"  - 第{img['page']}页: {img['filename']} ({img['size']//1024}KB)")
            print(f"    路径: raw/papers/{paper}/images/{img['filename']}")


def list_papers():
    """列出所有论文"""
    if not os.path.exists(PAPERS_DIR):
        print("论文目录不存在")
        return
    
    # 读取图片索引统计
    image_count = {}
    if os.path.exists(IMAGES_INDEX_FILE):
        with open(IMAGES_INDEX_FILE, "r", encoding="utf-8") as f:
            images = json.load(f)
        for img in images:
            p = img["paper"]
            image_count[p] = image_count.get(p, 0) + 1
    
    print(f"\n{'='*60}")
    print("论文清单")
    print(f"{'='*60}")
    
    # 遍历论文目录
    papers = [d for d in os.listdir(PAPERS_DIR) 
              if os.path.isdir(os.path.join(PAPERS_DIR, d))]
    
    if not papers:
        print("没有找到论文")
        return
    
    for i, paper in enumerate(sorted(papers), 1):
        md_file = os.path.join(PAPERS_DIR, paper, f"{paper}.md")
        img_dir = os.path.join(PAPERS_DIR, paper, "images")
        
        has_md = os.path.exists(md_file)
        img_count = image_count.get(paper, 0)
        
        status = "✓" if has_md else "✗"
        print(f"{i:2}. [{status}] {paper}")
        print(f"      Markdown: {'有' if has_md else '无'}, 图片: {img_count}张")


def interactive_mode(model):
    """交互模式"""
    print("\n" + "=" * 60)
    print("论文知识库交互查询")
    print("=" * 60)
    print("命令:")
    print("  s 关键词  - 语义搜索文本")
    print("  i 关键词  - 搜索图片")
    print("  l         - 列出所有论文")
    print("  q         - 退出")
    print("=" * 60)
    
    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break
        
        if not user_input:
            continue
        
        if user_input.lower() == 'q':
            print("再见！")
            break
        elif user_input.lower() == 'l':
            list_papers()
        elif user_input.startswith('s '):
            query = user_input[2:].strip()
            if query:
                search_text(query, model)
        elif user_input.startswith('i '):
            keyword = user_input[2:].strip()
            if keyword:
                search_image(keyword)
        else:
            # 默认当作语义搜索
            search_text(user_input, model)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1].lower()
    
    if command == "interactive":
        model = load_model()
        interactive_mode(model)
    
    elif command == "search":
        if len(sys.argv) < 3:
            print("用法: python query_knowledge_base.py search \"查询内容\"")
            return
        query = sys.argv[2]
        model = load_model()
        search_text(query, model)
    
    elif command in ["image", "img", "i"]:
        if len(sys.argv) < 3:
            print("用法: python query_knowledge_base.py image \"关键词\"")
            return
        keyword = sys.argv[2]
        search_image(keyword)
    
    elif command in ["list", "ls", "l"]:
        list_papers()
    
    else:
        print(f"未知命令: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
