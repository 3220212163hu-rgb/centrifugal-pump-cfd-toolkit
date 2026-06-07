# 🌀 离心泵 CFD 仿真工具链

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/NMKmono/centrifugal-pump-cfd-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/NMKmono/centrifugal-pump-cfd-toolkit/actions/workflows/ci.yml)

本科毕业论文项目的 Python 工具集。

涵盖从文献检索、CFD 自动化求解、知识库管理到论文文档生成的完整研究工具链。

## 📁 项目结构

```
scripts/
├── automation/          # ANSYS Workbench + PyFluent 自动化
│   ├── 03_fluent_solve.py   # PyFluent 端到端 RANS 求解器
│   ├── *.wbjn               # Workbench Journal（几何/网格）
│   ├── *.tse                # TurboGrid 会话文件
│   └── *.bat                # Windows 启动器
├── crawler/             # 文献检索与处理
│   ├── paper_crawler.py     # 百度学术 + arXiv 爬虫
│   └── pdf_to_markdown_qdrant.py  # PDF→Markdown+Qdrant 一体化
├── qdrant/              # 向量知识库
│   ├── hybrid_search.py     # SQLite 精确 + Qdrant 语义混合检索
│   ├── import_to_qdrant_v2.py   # 文献导入（页码精准定位）
│   └── query_knowledge_base.py  # 交互式知识库查询
├── thesis/              # 论文文档生成
│   ├── generate_thesis.py   # python-docx 论文生成器
│   └── generate_journal.py  # Fluent Journal 文件生成
├── common/              # 共用模块
│   └── path_config.py       # 跨平台路径配置（WSL/Windows）
└── *.py                 # 论文格式分析 / 验证 / 降重工具
```

## 🚀 快速开始

### 环境要求

- Python ≥ 3.10
- ANSYS 2024 R2（仅 `automation/` 需要 PyFluent）

### 安装

```bash
git clone https://github.com/NMKmono/centrifugal-pump-cfd-toolkit.git
cd centrifugal-pump-cfd-toolkit

# 复制环境配置
cp .env.example .env
# 编辑 .env 填写你的本地路径

# 安装 Python 依赖
pip install python-docx qdrant-client sentence-transformers pymupdf requests beautifulsoup4
```

### 使用示例

```bash
# 1. 文献检索
python scripts/crawler/paper_crawler.py "离心泵 进口导叶" --source both

# 2. 知识库混合检索
python scripts/qdrant/hybrid_search.py "叶片出口角对效率的影响"

# 3. 生成 Fluent Journal 文件
python scripts/thesis/generate_journal.py --output pump_sim.jou --iterations 500

# 4. 生成论文框架
python scripts/thesis/generate_thesis.py
```

## 🧩 核心功能

### PyFluent 自动化求解

`automation/03_fluent_solve.py` 实现了完整的 CFD 仿真自动化：

- 单流道周期性 RANS 求解（k-ω SST 湍流模型）
- MRF 旋转域设置
- 自动后处理：扬程计算、效率计算、扭矩提取
- 支持命令行参数批量运行

### 混合检索闭环

`qdrant/hybrid_search.py` 提供三层检索：

```
SQLite 精确检索 → Qdrant 语义检索 → 原文回查（实体页/Markdown/PDF）
```

### 论文工具链

- **格式分析**：自动检测 docx 中物理量斜体、下标、参考文献上角标格式
- **降重工具**：占位符保护 + 文本提取 + AI 改写 + 格式回填
- **公式提取**：OMML → LaTeX 转换，可直接粘贴到 MathType

## 📦 依赖项

| 包名 | 用途 |
|------|------|
| `python-docx` | Word 文档生成与格式处理 |
| `qdrant-client` | 向量数据库客户端 |
| `sentence-transformers` | 文本嵌入模型（BGE/MiniLM） |
| `PyMuPDF (fitz)` | PDF 文本提取和图片导出 |
| `markitdown` | PDF → Markdown 转换 |
| `requests` + `beautifulsoup4` | 文献爬虫 |
| `ansys-fluent-core` | PyFluent API（仅 ANSYS 用户） |

## ⚙️ 配置

所有路径通过 `.env` 文件或环境变量配置：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `PROJECT_ROOT` | 自动检测 | 项目根目录 |
| `THESIS_PATH` | `./thesis.docx` | 论文 docx 路径 |
| `OUTPUT_DIR` | `./output` | 输出目录 |
| `QDRANT_PATH` | `$PROJECT_ROOT/qdrant_data` | Qdrant 数据目录 |
| `VAULT_DB_PATH` | `$PROJECT_ROOT/thesis_vault_index.sqlite` | SQLite 索引 |

## 📄 许可证

MIT License — 详见 [LICENSE](LICENSE)

## ⚠️ 注意事项

- `pyfluent/` 目录含仿真数据（~6.5GB），不上传 Git，需自行配置
- `automation/` 脚本需要 ANSYS 2024 R2 + PyFluent 环境
- 路径中不含中文字符时 ANSYS 兼容性更好
- 所有脚本已做脱敏处理：真实姓名和硬编码路径已替换为环境变量
