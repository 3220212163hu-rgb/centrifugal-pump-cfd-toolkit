# -*- coding: utf-8 -*-
"""
Qdrant PDF文献导入脚本 - 改进版
功能：将毕业论文PDF原文提取文本后分块导入Qdrant向量数据库
改进：添加完整PDF路径，支持精准定位到原文
运行环境：Windows PowerShell, Python 3.14
用法：python import_to_qdrant_v2.py
"""

import os
import re
import glob
import fitz  # PyMuPDF
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

# ========== 配置 ==========
COLLECTION_NAME = "thesis_literature"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 的向量维度
MODEL_NAME = "all-MiniLM-L6-v2"

# PDF文献目录（统一放在01-参考文献下）
PDF_DIRS = [
    os.path.join(REF_DIR, "01-核心文献"),
    os.path.join(REF_DIR, "02-辅助文献"),
    os.path.join(REF_DIR, "03-英文文献"),
]

# Qdrant数据存储路径
from path_config import QDRANT_PATH, REF_DIR

# 分块参数
CHUNK_SIZE = 500    # 每块最多500字符
CHUNK_OVERLAP = 80  # 块之间重叠80字符


def extract_pdf_text(pdf_path):
    """从PDF提取文本，返回文本和页码映射"""
    try:
        doc = fitz.open(pdf_path)
        pages_content = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            pages_content.append({
                "page": page_num + 1,  # 页码从1开始
                "text": text
            })
        doc.close()
        return pages_content
    except Exception as e:
        print(f"  [错误] 无法读取 {os.path.basename(pdf_path)}: {e}")
        return []


def clean_text(text):
    """清理提取的文本"""
    # 去除过多空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 去除行首行尾空白
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    # 去除特殊字符（保留中文、英文、数字、常见标点）
    text = re.sub(r'[^\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\w\s\-.,;:!?()（）、。，；：！？\[\]{}=/+\-×÷·∂∇ρφεωΩαβγδλμσθπ<>≤≥≠≈∞]', '', text)
    return text


def split_text_with_page(text, page_num, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """将长文本分块，记录页码"""
    if len(text) <= chunk_size:
        return [{"text": text, "page": page_num}] if text.strip() else []

    # 先按段落分割
    paragraphs = re.split(r'\n\n+', text)
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # 如果当前块+新段落不超过限制，合并
        if len(current_chunk) + len(para) + 1 <= chunk_size:
            if current_chunk:
                current_chunk += "\n" + para
            else:
                current_chunk = para
        else:
            # 保存当前块
            if current_chunk:
                chunks.append({"text": current_chunk, "page": page_num})
            
            # 如果单个段落超过chunk_size，强制切分
            if len(para) > chunk_size:
                start = 0
                while start < len(para):
                    end = start + chunk_size
                    chunk = para[start:end]
                    if chunk.strip():
                        chunks.append({"text": chunk.strip(), "page": page_num})
                    start += chunk_size - overlap
                current_chunk = ""
            else:
                current_chunk = para
    
    # 最后一块
    if current_chunk:
        chunks.append({"text": current_chunk, "page": page_num})
    
    return chunks


def get_category_from_path(pdf_path):
    """从路径判断文献类别"""
    if "01-核心文献" in pdf_path:
        return "核心文献"
    elif "02-辅助文献" in pdf_path:
        return "辅助文献"
    elif "03-英文文献" in pdf_path:
        return "英文文献"
    else:
        return "其他"


def process_pdfs():
    """读取所有PDF并分块"""
    all_chunks = []
    point_id = 0
    
    for pdf_dir in PDF_DIRS:
        if not os.path.exists(pdf_dir):
            print(f"  跳过（目录不存在）: {pdf_dir}")
            continue
        
        category = get_category_from_path(pdf_dir)
        pdf_files = glob.glob(os.path.join(pdf_dir, "**", "*.pdf"), recursive=True)
        
        # 过滤掉metadata和已处理的非正文文件
        pdf_files = [f for f in pdf_files if "Metadata" not in f and "已处理" not in f]
        
        print(f"\n  [{category}] 找到 {len(pdf_files)} 个PDF文件")
        
        for i, pdf_path in enumerate(pdf_files):
            filename = os.path.basename(pdf_path)
            print(f"    ({i+1}/{len(pdf_files)}) 正在提取: {filename[:50]}...", end="")
            
            # 提取文本（带页码）
            pages_content = extract_pdf_text(pdf_path)
            if not pages_content:
                print(" [空文件，跳过]")
                continue
            
            # 处理每一页
            total_chunks = 0
            for page_info in pages_content:
                page_num = page_info["page"]
                raw_text = page_info["text"]
                
                if not raw_text.strip():
                    continue
                
                # 清理文本
                text = clean_text(raw_text)
                
                if len(text) < 20:  # 页面内容太少也跳过
                    continue
                
                # 分块（带页码）
                chunks = split_text_with_page(text, page_num)
                
                for chunk in chunks:
                    all_chunks.append({
                        "id": point_id,
                        "text": chunk["text"],
                        "pdf_path": pdf_path,  # 完整PDF路径
                        "pdf_name": filename,
                        "page": chunk["page"],  # 页码
                        "category": category,
                    })
                    point_id += 1
                    total_chunks += 1
            
            print(f" → {total_chunks} 块")
    
    return all_chunks


def import_to_qdrant(all_chunks, model):
    """将文本块导入Qdrant"""
    client = QdrantClient(path=QDRANT_PATH)
    
    # 删除已有集合
    try:
        client.delete_collection(COLLECTION_NAME)
        print("已删除旧集合")
    except:
        pass
    
    # 创建集合
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
                id=chunk["id"],
                vector=vectors[j].tolist(),
                payload={
                    "text": chunk["text"],
                    "pdf_path": chunk["pdf_path"],      # 完整路径
                    "pdf_name": chunk["pdf_name"],      # 文件名
                    "page": chunk["page"],              # 页码
                    "category": chunk["category"],      # 类别
                },
            ))
        
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        
        done = min(i+batch_size, total)
        pct = done * 100 // total
        print(f"  导入进度: {done}/{total} ({pct}%)")
    
    print(f"\n导入完成！共 {total} 个文本块")
    print(f"数据存储在: {QDRANT_PATH}")
    
    # 验证
    info = client.get_collection(COLLECTION_NAME)
    print(f"集合状态: {info.points_count} 个点")
    
    return client


def test_query(model):
    """快速测试查询"""
    client = QdrantClient(path=QDRANT_PATH)
    
    queries = [
        "叶轮出口角对离心泵性能的影响",
        "离心泵数值模拟网格",
        "进口导叶角度优化",
    ]
    
    for q in queries:
        print(f"\n{'='*60}")
        print(f"查询: {q}")
        print('='*60)
        vector = model.encode(q).tolist()
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=3,
        )
        for i, point in enumerate(results.points):
            payload = point.payload
            print(f"\n[{i+1}] 相似度={point.score:.3f}")
            print(f"    文献: {payload['pdf_name']}")
            print(f"    类别: {payload['category']}")
            print(f"    页码: {payload['page']}")
            print(f"    路径: {payload['pdf_path']}")
            text_preview = payload['text'][:100].replace('\n', ' ')
            print(f"    内容: {text_preview}...")


def main():
    print("=" * 60)
    print("Qdrant PDF文献导入工具 v2 - 支持精准定位")
    print("=" * 60)
    
    # 1. 加载模型
    print("\n[1/3] 加载嵌入模型...")
    print(f"  模型: {MODEL_NAME}")
    print("  （首次运行需下载约90MB，请耐心等待）")
    model = SentenceTransformer(MODEL_NAME)
    print("  模型加载完成！")
    
    # 2. 处理PDF
    print("\n[2/3] 提取PDF文本并分块...")
    all_chunks = process_pdfs()
    print(f"\n  总计: {len(all_chunks)} 个文本块")
    
    if not all_chunks:
        print("没有数据可导入！请检查文件路径。")
        return
    
    # 3. 导入Qdrant
    print("\n[3/3] 导入向量数据库...")
    import_to_qdrant(all_chunks, model)
    
    # 4. 测试
    print("\n" + "=" * 60)
    print("测试查询")
    test_query(model)
    
    print("\n" + "=" * 60)
    print("全部完成！")
    print("\nPayload结构:")
    print("  - text: 文本内容")
    print("  - pdf_path: PDF完整路径（可直接打开）")
    print("  - pdf_name: PDF文件名")
    print("  - page: 页码")
    print("  - category: 类别（核心文献/辅助文献/英文文献）")


if __name__ == "__main__":
    main()
