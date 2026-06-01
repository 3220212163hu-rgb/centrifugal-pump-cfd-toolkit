# -*- coding: utf-8 -*-
"""
PDF → Markdown + 图片提取 + Qdrant向量化 一体化脚本
功能：
  1. 将PDF转换为Markdown（保留结构）
  2. 提取PDF中的图片并保存
  3. 生成图片索引JSON
  4. 分块导入Qdrant向量库

运行环境：Windows PowerShell, Python 3.14
用法：python pdf_to_markdown_qdrant.py
"""

import os
import re
import json
import glob
import hashlib
import fitz  # PyMuPDF
from pathlib import Path
from datetime import datetime
from markitdown import MarkItDown
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

# 国内镜像源配置
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# ========== 配置 ==========
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
from common.path_config import PROJECT_DIR

PROJECT_ROOT = PROJECT_DIR

# PDF文献目录
PDF_DIRS = [
    os.path.join(PROJECT_ROOT, "01-参考文献", "01-核心文献"),
    os.path.join(PROJECT_ROOT, "01-参考文献", "02-辅助文献"),
    os.path.join(PROJECT_ROOT, "参考文献", "03-英文文献"),
]

# 输出目录
VAULT_ROOT = os.path.join(PROJECT_ROOT, "ObsidianVault", "本科毕业论文知识库")
PAPERS_DIR = os.path.join(VAULT_ROOT, "raw", "papers")
IMAGES_INDEX_FILE = os.path.join(PAPERS_DIR, "图片索引.json")

# Qdrant配置
QDRANT_PATH = os.path.join(PROJECT_ROOT, "qdrant_data")
COLLECTION_NAME = "thesis_literature"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2
MODEL_NAME = "all-MiniLM-L6-v2"

# 分块参数
CHUNK_SIZE = 600      # 每块字符数
CHUNK_OVERLAP = 100   # 重叠字符

# 图片过滤参数
MIN_IMAGE_WIDTH = 100   # 最小宽度（像素）
MIN_IMAGE_HEIGHT = 100  # 最小高度（像素）
MIN_IMAGE_SIZE = 5000   # 最小文件大小（字节），过滤太小的图标


def get_pdf_files():
    """获取所有PDF文件列表"""
    all_files = []
    for pdf_dir in PDF_DIRS:
        if not os.path.exists(pdf_dir):
            print(f"  [警告] 目录不存在: {pdf_dir}")
            continue
        files = glob.glob(os.path.join(pdf_dir, "**", "*.pdf"), recursive=True)
        category = "核心文献" if "01-核心" in pdf_dir else ("辅助文献" if "02-辅助" in pdf_dir else "英文文献")
        for f in files:
            # 排除已处理批次目录和metadata文件
            if "已处理" in f or "Metadata" in f:
                continue
            all_files.append({"path": f, "category": category})
    return all_files


def sanitize_name(filename):
    """清理文件名，用于创建目录"""
    # 移除扩展名
    name = os.path.splitext(filename)[0]
    # 只保留中文、英文、数字、下划线、横线
    name = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9_\-]', '_', name)
    # 去除连续下划线
    name = re.sub(r'_+', '_', name)
    # 去除首尾下划线
    name = name.strip('_')
    return name


def extract_images_from_pdf(pdf_path, output_dir, paper_name):
    """从PDF提取图片"""
    images_info = []
    image_hashes = set()  # 用于去重
    
    try:
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # 过滤太小的图片
                    if len(image_bytes) < MIN_IMAGE_SIZE:
                        continue
                    
                    # 计算hash去重
                    img_hash = hashlib.md5(image_bytes).hexdigest()
                    if img_hash in image_hashes:
                        continue
                    image_hashes.add(img_hash)
                    
                    # 保存图片
                    img_filename = f"fig_p{page_num+1}_{img_index+1}.{image_ext}"
                    img_path = os.path.join(output_dir, img_filename)
                    
                    with open(img_path, "wb") as f:
                        f.write(image_bytes)
                    
                    images_info.append({
                        "filename": img_filename,
                        "page": page_num + 1,
                        "index": img_index + 1,
                        "size": len(image_bytes),
                        "paper": paper_name,
                    })
                    
                except Exception as e:
                    continue
        
        doc.close()
        
    except Exception as e:
        print(f"    [图片提取错误] {e}")
    
    return images_info


def pdf_to_markdown(pdf_path):
    """使用markitdown将PDF转为Markdown"""
    try:
        md = MarkItDown()
        result = md.convert(pdf_path)
        return result.text_content
    except Exception as e:
        print(f"    [markitdown失败，回退到PyMuPDF] {e}")
        # 回退到PyMuPDF
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text("text") + "\n\n"
            doc.close()
            return text
        except Exception as e2:
            print(f"    [PyMuPDF也失败] {e2}")
            return ""


def clean_markdown(text):
    """清理Markdown文本"""
    # 去除过多空行
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    # 去除行首行尾空白
    lines = [line.rstrip() for line in text.split('\n')]
    text = '\n'.join(lines)
    return text


def split_markdown_by_sections(text, paper_name, images_info):
    """按章节分割Markdown，并插入图片引用"""
    chunks = []
    
    # 尝试识别章节标题（## 或 ### 或数字编号）
    section_pattern = r'^(#{1,3}\s+.+|\d+[\.\、]\s*.+)$'
    lines = text.split('\n')
    
    current_section = "摘要"  # 默认第一节
    current_content = []
    
    # 构建页码到图片的映射
    page_images = {}
    for img in images_info:
        p = img["page"]
        if p not in page_images:
            page_images[p] = []
        page_images[p].append(img["filename"])
    
    for i, line in enumerate(lines):
        # 检测新章节
        if re.match(section_pattern, line):
            # 保存上一节
            if current_content:
                content = '\n'.join(current_content).strip()
                if len(content) > 50:
                    chunks.append({
                        "text": content,
                        "section": current_section,
                        "paper": paper_name,
                    })
            current_section = line.strip('#').strip()
            current_content = [line]
        else:
            current_content.append(line)
    
    # 最后一节
    if current_content:
        content = '\n'.join(current_content).strip()
        if len(content) > 50:
            chunks.append({
                "text": content,
                "section": current_section,
                "paper": paper_name,
            })
    
    # 如果章节分割失败（没有识别到章节），按长度切分
    if len(chunks) <= 1:
        chunks = []
        # 按段落+长度切分
        paragraphs = text.split('\n\n')
        current_chunk = ""
        current_section = "正文"
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current_chunk) + len(para) < CHUNK_SIZE:
                current_chunk += para + "\n\n"
            else:
                if current_chunk.strip():
                    chunks.append({
                        "text": current_chunk.strip(),
                        "section": current_section,
                        "paper": paper_name,
                    })
                current_chunk = para + "\n\n"
        
        if current_chunk.strip():
            chunks.append({
                "text": current_chunk.strip(),
                "section": current_section,
                "paper": paper_name,
            })
    
    return chunks, page_images


def process_single_pdf(pdf_info, model):
    """处理单个PDF文件"""
    pdf_path = pdf_info["path"]
    category = pdf_info["category"]
    
    filename = os.path.basename(pdf_path)
    paper_name = sanitize_name(filename)
    
    print(f"\n  处理: {filename[:50]}...")
    
    # 创建输出目录
    paper_dir = os.path.join(PAPERS_DIR, paper_name)
    images_dir = os.path.join(paper_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    # 1. 提取图片
    print(f"    [1/4] 提取图片...")
    images_info = extract_images_from_pdf(pdf_path, images_dir, paper_name)
    print(f"    提取到 {len(images_info)} 张图片")
    
    # 2. 转换为Markdown
    print(f"    [2/4] 转换Markdown...")
    markdown_text = pdf_to_markdown(pdf_path)
    if not markdown_text.strip():
        print(f"    [跳过] 无法提取文本")
        return None, []
    
    markdown_text = clean_markdown(markdown_text)
    print(f"    提取到 {len(markdown_text)} 字符")
    
    # 3. 分块
    print(f"    [3/4] 分块处理...")
    chunks, page_images = split_markdown_by_sections(markdown_text, paper_name, images_info)
    print(f"    分成 {len(chunks)} 个文本块")
    
    # 4. 保存Markdown文件
    print(f"    [4/4] 保存文件...")
    md_path = os.path.join(paper_dir, f"{paper_name}.md")
    
    # 在Markdown开头添加元信息
    header = f"""---
title: {paper_name}
source: {filename}
category: {category}
processed: {datetime.now().strftime('%Y-%m-%d %H:%M')}
images: {len(images_info)}
---

# {paper_name}

> 来源: {category} / {filename}
> 图片数: {len(images_info)}

"""
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(header + markdown_text)
    
    return {
        "paper_name": paper_name,
        "filename": filename,
        "category": category,
        "char_count": len(markdown_text),
        "chunk_count": len(chunks),
        "image_count": len(images_info),
        "md_path": md_path,
        "images_dir": images_dir,
    }, images_info


def import_to_qdrant(all_chunks, model):
    """导入Qdrant向量库"""
    print(f"\n{'='*60}")
    print("导入Qdrant向量库")
    print(f"{'='*60}")
    
    client = QdrantClient(path=QDRANT_PATH)
    
    # 删除旧集合
    try:
        client.delete_collection(COLLECTION_NAME)
        print("已删除旧集合")
    except:
        pass
    
    # 创建新集合
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    print(f"已创建集合: {COLLECTION_NAME}")
    
    # 批量导入
    batch_size = 32
    total = len(all_chunks)
    
    for i in range(0, total, batch_size):
        batch = all_chunks[i:i+batch_size]
        texts = [c["text"] for c in batch]
        
        # 生成向量
        vectors = model.encode(texts, show_progress_bar=False)
        
        # 构建点
        points = []
        for j, chunk in enumerate(batch):
            points.append(PointStruct(
                id=i + j,
                vector=vectors[j].tolist(),
                payload={
                    "text": chunk["text"],
                    "paper": chunk["paper"],
                    "section": chunk["section"],
                },
            ))
        
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        
        done = min(i + batch_size, total)
        pct = done * 100 // total
        print(f"  进度: {done}/{total} ({pct}%)")
    
    print(f"\n导入完成！共 {total} 个文本块")
    
    # 验证
    info = client.get_collection(COLLECTION_NAME)
    print(f"集合状态: {info.points_count} 个向量点")
    
    return client


def test_query(model):
    """测试查询"""
    print(f"\n{'='*60}")
    print("测试语义搜索")
    print(f"{'='*60}")
    
    client = QdrantClient(path=QDRANT_PATH)
    
    queries = [
        "进口导叶对离心泵效率的影响",
        "SST湍流模型设置",
        "压力脉动频域分析",
    ]
    
    for q in queries:
        print(f"\n查询: {q}")
        vector = model.encode(q).tolist()
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=3,
        )
        
        for i, point in enumerate(results.points):
            paper = point.payload.get('paper', '未知')[:25]
            section = point.payload.get('section', '未知')[:20]
            text_preview = point.payload['text'][:80].replace('\n', ' ')
            print(f"  [{i+1}] 相似度={point.score:.3f}")
            print(f"      论文: {paper} | 章节: {section}")
            print(f"      内容: {text_preview}...")


def main():
    print("=" * 60)
    print("PDF → Markdown + 图片 + Qdrant 一体化处理")
    print("=" * 60)
    
    # 确保输出目录存在
    os.makedirs(PAPERS_DIR, exist_ok=True)
    
    # 1. 加载嵌入模型
    print("\n[步骤1] 加载嵌入模型...")
    print(f"  模型: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    print("  模型加载完成！")
    
    # 2. 获取PDF列表
    print("\n[步骤2] 扫描PDF文件...")
    pdf_files = get_pdf_files()
    print(f"  找到 {len(pdf_files)} 个PDF文件")
    
    if not pdf_files:
        print("没有找到PDF文件！")
        return
    
    # 3. 处理每个PDF
    print("\n[步骤3] 处理PDF文件...")
    all_chunks = []
    all_images_index = []
    all_papers_info = []
    
    for i, pdf_info in enumerate(pdf_files):
        print(f"\n--- [{i+1}/{len(pdf_files)}] ---")
        result, images = process_single_pdf(pdf_info, model)
        
        if result:
            all_papers_info.append(result)
            all_images_index.extend(images)
            
            # 获取分块
            pdf_path = pdf_info["path"]
            filename = os.path.basename(pdf_path)
            paper_name = result["paper_name"]
            
            # 重新读取md分块
            md_path = result["md_path"]
            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            
            # 跳过frontmatter
            if md_content.startswith("---"):
                parts = md_content.split("---", 2)
                if len(parts) >= 3:
                    md_content = parts[2]
            
            chunks, _ = split_markdown_by_sections(md_content, paper_name, [])
            all_chunks.extend(chunks)
    
    # 4. 保存图片索引
    print(f"\n[步骤4] 保存图片索引...")
    with open(IMAGES_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(all_images_index, f, ensure_ascii=False, indent=2)
    print(f"  图片索引已保存: {IMAGES_INDEX_FILE}")
    print(f"  共 {len(all_images_index)} 张图片")
    
    # 5. 导入Qdrant
    print(f"\n[步骤5] 导入Qdrant向量库...")
    if all_chunks:
        import_to_qdrant(all_chunks, model)
    else:
        print("没有文本块可导入！")
    
    # 6. 测试查询
    test_query(model)
    
    # 7. 输出汇总
    print(f"\n{'='*60}")
    print("处理完成汇总")
    print(f"{'='*60}")
    print(f"处理论文数: {len(all_papers_info)}")
    print(f"文本块总数: {len(all_chunks)}")
    print(f"图片总数: {len(all_images_index)}")
    print(f"\n输出目录:")
    print(f"  Markdown+图片: {PAPERS_DIR}")
    print(f"  图片索引: {IMAGES_INDEX_FILE}")
    print(f"  Qdrant数据: {QDRANT_PATH}")
    
    # 生成论文清单
    print(f"\n论文清单:")
    for p in all_papers_info:
        print(f"  - {p['paper_name'][:40]} ({p['image_count']}图, {p['chunk_count']}块)")


if __name__ == "__main__":
    main()
