# 离心泵 CFD 仿真工具链

本科毕业论文项目 —— 基于节能优化的离心泵叶轮 β₂–Z 双参数设计与仿真的 Python 工具集。

## 目录结构

```
scripts/
├── automation/       # ANSYS Workbench + PyFluent 自动化脚本
├── pyfluent/         # PyFluent 求解器主脚本（仿真数据过大，不上传）
├── crawler/          # 论文爬虫（百度学术 + arXiv）
├── qdrant/           # Qdrant 向量知识库导入/检索
├── thesis/           # 论文 docx 生成器
├── common/           # 共用模块（路径配置）
└── *.py              # 论文格式分析/验证/改写工具
```

## 各模块说明

### automation/ — ANSYS 自动化
- `03_fluent_solve.py` — PyFluent 端到端求解：单流道周期性 RANS (k-ω SST)
- `*.wbjn` — Workbench Journal 脚本（几何导出、TurboGrid 网格）
- `*.bat` — Windows 启动器

### crawler/ — 文献检索
- `paper_crawler.py` — 论文爬虫，支持百度学术 + arXiv
- `pdf_to_markdown_qdrant.py` — PDF→Markdown+图片提取+Qdrant 向量化

### qdrant/ — 知识库
- `hybrid_search.py` — SQLite 精确 + Qdrant 语义混合检索闭环
- `import_to_qdrant_v2.py` — PDF 文献导入 Qdrant（带页码精准定位）
- `query_knowledge_base.py` — 交互式论文知识库查询

### thesis/ — 文档生成
- `generate_thesis.py` — 按学校格式生成毕业论文 Word 文档
- `generate_journal.py` — 生成 Fluent Journal 文件

## 快速开始

```bash
# 1. 配置环境
cp .env.example .env
# 编辑 .env 填写本地路径

# 2. 安装依赖
pip install python-docx qdrant-client sentence-transformers pymupdf

# 3. 文献爬虫
python crawler/paper_crawler.py "离心泵 进口导叶" --source both

# 4. 知识库检索
python qdrant/hybrid_search.py "叶片出口角对效率的影响"

# 5. 生成论文框架
python thesis/generate_thesis.py
```

## 依赖

- Python ≥ 3.10
- python-docx — Word 文档生成
- qdrant-client — 向量数据库
- sentence-transformers — 文本嵌入
- PyMuPDF (fitz) — PDF 解析
- requests + BeautifulSoup4 — 爬虫
- ANSYS Fluent + PyFluent（仅 automation/ 需要）

## 注意事项

- `pyfluent/` 目录包含仿真数据（~6.5GB），不上传到 GitHub，需自行配置
- 所有路径通过 `.env` 或环境变量配置，参考 `.env.example`
- ANSYS 版本要求：2024 R2

## License

MIT
