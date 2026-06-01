#!/usr/bin/env python3
"""
论文爬虫脚本 - 支持百度学术和 arXiv
用法: python paper_crawler.py "关键词" --source baidu --pages 3
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import argparse
from urllib.parse import quote
import re

# 请求头，模拟浏览器
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

def search_baidu_xueshu(keyword, pages=1):
    """百度学术搜索"""
    results = []
    base_url = "https://xueshu.baidu.com/s"
    
    for page in range(pages):
        params = {
            'wd': keyword,
            'pn': page * 10,
            'tn': 'SE_baiduxueshu_c1gjeupa',
            'ie': 'utf-8',
        }
        
        try:
            print(f"[百度学术] 正在搜索第 {page+1} 页: {keyword}")
            resp = requests.get(base_url, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            
            soup = BeautifulSoup(resp.text, 'lxml')
            items = soup.select('.result')
            
            if not items:
                items = soup.select('div[class*="result"]')
            
            for item in items:
                try:
                    paper = {}
                    
                    # 标题
                    title_tag = item.select_one('a[href*="xueshu.baidu.com"]')
                    if title_tag:
                        paper['title'] = title_tag.get_text(strip=True)
                        paper['link'] = title_tag.get('href', '')
                    
                    # 作者
                    author_tag = item.select_one('.author_text')
                    if not author_tag:
                        author_tag = item.select_one('span[class*="author"]')
                    if author_tag:
                        paper['authors'] = author_tag.get_text(strip=True)
                    
                    # 来源/期刊
                    source_tag = item.select_one('.source_text')
                    if not source_tag:
                        source_tag = item.select_one('span[class*="source"]')
                    if source_tag:
                        paper['source'] = source_tag.get_text(strip=True)
                    
                    # 摘要
                    abstract_tag = item.select_one('.c_abstract')
                    if not abstract_tag:
                        abstract_tag = item.select_one('p[class*="abstract"]')
                    if abstract_tag:
                        paper['abstract'] = abstract_tag.get_text(strip=True)
                    
                    # 年份
                    year_match = re.search(r'(\d{4})', item.get_text())
                    if year_match:
                        paper['year'] = year_match.group(1)
                    
                    if paper.get('title'):
                        results.append(paper)
                        
                except Exception as e:
                    continue
                    
            time.sleep(1)  # 避免请求过快
            
        except Exception as e:
            print(f"[百度学术] 搜索出错: {e}")
            break
    
    return results


def search_arxiv(keyword, max_results=20):
    """arXiv API 搜索"""
    results = []
    base_url = "http://export.arxiv.org/api/query"
    
    params = {
        'search_query': f'all:{keyword}',
        'start': 0,
        'max_results': max_results,
    }
    
    try:
        print(f"[arXiv] 正在搜索: {keyword}")
        resp = requests.get(base_url, params=params, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'xml')
        entries = soup.find_all('entry')
        
        for entry in entries:
            paper = {}
            
            title = entry.find('title')
            if title:
                paper['title'] = title.get_text(strip=True)
            
            authors = entry.find_all('author')
            if authors:
                author_names = [a.find('name').get_text(strip=True) for a in authors if a.find('name')]
                paper['authors'] = ', '.join(author_names)
            
            summary = entry.find('summary')
            if summary:
                paper['abstract'] = summary.get_text(strip=True)
            
            link = entry.find('link', {'type': 'text/html'})
            if link:
                paper['link'] = link.get('href', '')
            
            pdf_link = entry.find('link', {'type': 'application/pdf'})
            if pdf_link:
                paper['pdf_link'] = pdf_link.get('href', '')
            
            published = entry.find('published')
            if published:
                paper['year'] = published.get_text(strip=True)[:4]
            
            if paper.get('title'):
                results.append(paper)
        
    except Exception as e:
        print(f"[arXiv] 搜索出错: {e}")
    
    return results


PROJECT_ROOT = os.environ.get(
    "PROJECT_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)
DEFAULT_OUTPUT_DIR = f"{PROJECT_ROOT}/爬虫结果"


def save_results(results, keyword, output_dir=DEFAULT_OUTPUT_DIR):
    """保存搜索结果"""
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存为 JSON
    json_path = os.path.join(output_dir, f'{keyword}_论文搜索结果.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"已保存 JSON: {json_path}")
    
    # 保存为 Markdown
    md_path = os.path.join(output_dir, f'{keyword}_论文搜索结果.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f'# 论文搜索结果: {keyword}\n\n')
        f.write(f'共找到 {len(results)} 篇论文\n\n')
        f.write('---\n\n')
        
        for i, paper in enumerate(results, 1):
            f.write(f'## {i}. {paper.get("title", "无标题")}\n\n')
            if paper.get('authors'):
                f.write(f'**作者**: {paper["authors"]}\n\n')
            if paper.get('source'):
                f.write(f'**来源**: {paper["source"]}\n\n')
            if paper.get('year'):
                f.write(f'**年份**: {paper["year"]}\n\n')
            if paper.get('abstract'):
                abstract = paper["abstract"][:500] + '...' if len(paper["abstract"]) > 500 else paper["abstract"]
                f.write(f'**摘要**: {abstract}\n\n')
            if paper.get('link'):
                f.write(f'**链接**: [{paper["link"]}]({paper["link"]})\n\n')
            if paper.get('pdf_link'):
                f.write(f'**PDF**: [{paper["pdf_link"]}]({paper["pdf_link"]})\n\n')
            f.write('---\n\n')
    
    print(f"已保存 Markdown: {md_path}")
    return json_path, md_path


def main():
    parser = argparse.ArgumentParser(description='论文爬虫 - 搜索百度学术和 arXiv')
    parser.add_argument('keyword', help='搜索关键词')
    parser.add_argument('--source', choices=['baidu', 'arxiv', 'both'], default='both',
                        help='搜索来源: baidu(百度学术), arxiv, both(默认)')
    parser.add_argument('--pages', type=int, default=2, help='百度学术搜索页数(默认2)')
    parser.add_argument('--max', type=int, default=20, help='arXiv 最大结果数(默认20)')
    
    args = parser.parse_args()
    
    all_results = []
    
    if args.source in ['baidu', 'both']:
        print("\n=== 百度学术搜索 ===")
        baidu_results = search_baidu_xueshu(args.keyword, args.pages)
        for r in baidu_results:
            r['source_platform'] = '百度学术'
        all_results.extend(baidu_results)
        print(f"百度学术找到 {len(baidu_results)} 篇")
    
    if args.source in ['arxiv', 'both']:
        print("\n=== arXiv 搜索 ===")
        arxiv_results = search_arxiv(args.keyword, args.max)
        for r in arxiv_results:
            r['source_platform'] = 'arXiv'
        all_results.extend(arxiv_results)
        print(f"arXiv 找到 {len(arxiv_results)} 篇")
    
    print(f"\n总计: {len(all_results)} 篇论文")
    
    if all_results:
        save_results(all_results, args.keyword.replace(' ', '_'))
    
    return all_results


if __name__ == '__main__':
    main()
