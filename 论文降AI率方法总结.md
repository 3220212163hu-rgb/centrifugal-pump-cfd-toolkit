# 论文降AI率方法总结

## 项目信息

- **论文标题**：基于节能优化的离心泵叶轮参数设计与仿真
- **原版文件**：`thesis.docx`
- **最终文件**：`thesis_rewrite.docx`
- **备份文件**：`thesis_backup.docx`

---

## 一、原始需求

### 1.1 目标
降低毕业论文的AI检测率，重点优化以下章节：
- 第1章 绪论：AI率 65%
- 第5章 参数优化：AI率 49%
- 第6章 结论与展望：AI率 62%

### 1.2 工具要求
- 使用 `D:\AI\GxGj\19-humanize-chinese去痕` 目录中的工具
- 工具路径：`scripts\academic_cn.py`

### 1.3 硬约束（不可违反）

| 序号 | 约束内容 |
|------|----------|
| 1 | 不重建 docx |
| 2 | 不转 markdown |
| 3 | 不修改 Word 公式对象（OMML/MathType） |
| 4 | 不修改图表编号、公式编号、参考文献编号 |
| 5 | 不修改占位符 |

---

## 二、工作流程

### 2.1 整体流程

```
备份原版 → 提取章节文本 → 占位符保护 → AI改写 → 回填文档
```

### 2.2 详细步骤

#### 步骤1：备份原版
```bash
# 备份原版论文
cp "thesis.docx" "thesis_backup.docx"
```

#### 步骤2：提取章节文本
```bash
# 运行提取脚本
python scripts/extract_thesis_text_v2.py
```

**输出文件**：
- `04-论文降重项目/extracted/chapter_1_original.txt`
- `04-论文降重项目/extracted/chapter_5_original.txt`
- `04-论文降重项目/extracted/chapter_6_original.txt`
- `04-论文降重项目/extracted/placeholder_map.json`

#### 步骤3：AI改写
```bash
# 使用 humanize-chinese 工具改写
python "D:\AI\GxGj\19-humanize-chinese去痕\scripts\academic_cn.py" \
  --input "04-论文降重项目/extracted/chapter_1_original.txt" \
  --output "04-论文降重项目/extracted/chapter_1_rewritten.txt"
```

#### 步骤4：回填文档
```bash
# 运行回填脚本
python scripts/rewrite_backfill_v4.py
```

**输出文件**：`thesis_rewrite.docx`

---

## 三、格式规范

### 3.1 物理量格式规则

| 类别 | 格式 | 示例 |
|------|------|------|
| 希腊字母 | 斜体 | β、α、γ、η、ε、ω、μ、ν、ξ、ρ、σ、φ、θ |
| 物理量变量 | 斜体 | Q、H、n、P、R、D、b、Z、k |
| 专业名词 | 不斜体 | Computational Fluid Dynamics、CFD、ANSYS、Fluent |
| 版本号 | 不斜体 | R2、R1、v1.0 |

### 3.2 下标格式规则

| 类型 | 格式 | 示例 |
|------|------|------|
| 数字下标 | 下角标 | β₂ 中的 2、D₂ 中的 2、b₂ 中的 2 |
| 字母下标 | 下角标 | Qd 中的 d、Hd 中的 d、ns 中的 s |

### 3.3 参考文献格式规则

| 类型 | 格式 | 示例 |
|------|------|------|
| 单篇引用 | 上角标 | [1]、[2]、[3] |
| 多篇引用 | 上角标 | [2,3]、[4,5]、[7,8] |
| 范围引用 | 上角标 | [4-6]、[9-11] |

### 3.4 格式判断逻辑

**物理量识别条件**：
1. 前面是空格、标点或行首（不是英文字母）
2. 后面是数字下标、空格、标点或行尾（不是英文字母）
3. 不是单词的一部分（如 CFD、ANSYS）
4. 不是版本号（如 R2）

**正则表达式**：
```python
# 物理量变量 + 数字下标
var_match = re.match(r'([QHnPRDbZk])([0-9]+)?', text[i:])

# 物理量变量 + 小写字母下标
var_with_sub_match = re.match(r'([QHnPRDbZk])([ds])', text[i:])

# 希腊字母 + 数字下标
greek_match = re.match(r'([αβγδεζηθικλμνξοπρστυφχψω])([0-9]+)?', text[i:])

# 参考文献引用
ref_match = re.match(r'\[\d+(?:[,，]\d+)*(?:-\d+)?\]', text[i:])
```

---

## 四、占位符保护系统

### 4.1 需要保护的内容

| 类型 | 占位符格式 | 示例 |
|------|------------|------|
| 行内公式 | `[FORMULA_INLINE_XXX]` | [FORMULA_INLINE_001] |
| 独立公式 | `[FORMULA_DISPLAY_XXX]` | [FORMULA_DISPLAY_001] |
| 图片引用 | `[FIGURE_XXX]` | [FIGURE_001] |
| 表格引用 | `[TABLE_XXX]` | [TABLE_001] |
| 参考文献 | `[REF_XXX]` | [REF_001] |
| 物理量符号 | `[SYMBOL_XXX]` | [SYMBOL_001] |

### 4.2 占位符映射文件

```json
{
  "[FORMULA_INLINE_001]": "Q = \\frac{π D_2 b_2 v_{u2}}{60}",
  "[FIGURE_001]": "图3-1 叶轮几何模型",
  "[REF_001]": "[1] 张三. 离心泵设计[M]. 北京: 机械工业出版社, 2020."
}
```

---

## 五、脚本说明

### 5.1 提取脚本

**文件**：`scripts/extract_thesis_text_v2.py`

**功能**：
- 从Word文档中提取指定章节的文本
- 识别并保护公式、图表、参考文献等特殊内容
- 生成占位符映射文件

**关键逻辑**：
- 使用 Heading 1 样式检测章节标题
- 正则表达式匹配公式、图表、参考文献
- 独立 'n' 替换为占位符（转速符号）

### 5.2 回填脚本

**文件**：`scripts/rewrite_backfill_v4.py`

**功能**：
- 将改写后的文本回填到Word文档
- 保留物理量斜体格式
- 保留下标下角标格式
- 保留参考文献上角标格式

**关键函数**：
```python
def is_english_letter(char):
    """检查字符是否是英文字母"""
    return 'a' <= char <= 'z' or 'A' <= char <= 'Z'

def parse_text_with_format(text):
    """解析文本，识别需要特殊格式的部分"""
    # 1. 匹配参考文献引用 [数字]
    # 2. 匹配希腊字母 + 下标
    # 3. 匹配物理量变量 + 数字下标
    # 4. 匹配物理量变量 + 小写字母下标
    # 5. 排除版本号（如 R2）

def rewrite_paragraph_with_format(para, new_text):
    """重写段落，保留格式"""
    # 1. 获取模板字体
    # 2. 解析文本为格式化部分
    # 3. 清空所有 run
    # 4. 创建新的 run 并设置格式
```

---

## 六、常见问题与解决方案

### 6.1 章节检测失败

**问题**：提取脚本无法识别章节标题

**原因**：章节标题格式不一致

**解决方案**：检查文档中的 Heading 1 样式，修改正则表达式

### 6.2 'n' 替换错误

**问题**：单词中的 'n' 被替换为占位符（如 "Computational" → "Computatio[n]al"）

**原因**：正则表达式 `r'n'` 匹配了所有 'n'

**解决方案**：使用 `r'(?<![a-zA-Z])n(?![a-zA-Z])'` 只匹配独立的 'n'

### 6.3 编码错误

**问题**：Python 脚本输出 GBK 编码错误

**原因**：Windows 默认编码为 GBK

**解决方案**：
```bash
# 方法1：设置环境变量
export PYTHONIOENCODING=utf-8

# 方法2：在脚本中设置
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

### 6.4 物理量格式丢失

**问题**：回填后物理量斜体、下标、上标格式丢失

**原因**：回填脚本直接替换文本，没有保留 run 级别格式

**解决方案**：解析文本为格式化部分，创建多个 run 并分别设置格式

### 6.5 专业名词被错误斜体

**问题**：CFD、ANSYS 等专业名词被设置为斜体

**原因**：正则表达式把所有大写字母识别为物理量

**解决方案**：
1. 使用 `is_english_letter()` 函数检查英文字母
2. 检查前后字符是否是英文字母
3. 排除版本号（如 R2）

### 6.6 下标识别错误

**问题**：小写字母下标（如 Qd 中的 d）没有被识别

**原因**：正则表达式只匹配数字下标

**解决方案**：添加单独的匹配模式
```python
var_with_sub_match = re.match(r'([QHnPRDbZk])([ds])', text[i:])
```

---

## 七、验证方法

### 7.1 格式验证脚本

```python
from docx import Document

doc = Document('thesis_rewrite.docx')

# 验证段落格式
para = doc.paragraphs[107]
for j, run in enumerate(para.runs):
    print(f'Run {j}: "{run.text}" - 斜体: {run.italic}, 下标: {run.font.subscript}, 上标: {run.font.superscript}')
```

### 7.2 验证要点

1. **物理量斜体**：β、Z、D、b 等应该是斜体
2. **下标下角标**：β₂ 中的 2、D₂ 中的 2 应该是下角标
3. **参考文献上角标**：[3]、[4,5] 应该是上角标
4. **专业名词不斜体**：CFD、ANSYS、Fluent 不应该是斜体

---

## 八、文件结构

```
D:\AI\SJK\biyesheji\
├── 定稿修改\
│   ├── thesis.docx          # 原版论文
│   ├── thesis_backup.docx        # 备份文件
│   └── thesis_rewrite.docx   # 最终文件
├── 04-论文降重项目\
│   ├── extracted\
│   │   ├── chapter_1_original.txt             # 第1章原文
│   │   ├── chapter_5_original.txt             # 第5章原文
│   │   ├── chapter_6_original.txt             # 第6章原文
│   │   ├── chapter_1_rewritten.txt            # 第1章改写版
│   │   └── placeholder_map.json               # 占位符映射
│   └── 需人工确认的问题.md                    # 待处理问题
├── scripts\
│   ├── extract_thesis_text_v2.py              # 提取脚本
│   ├── rewrite_backfill_v4.py                 # 回填脚本
│   └── debug_paragraph.py                     # 调试脚本
└── 论文降AI率方法总结.md                      # 本文档
```

---

## 九、下一步工作

### 9.1 人工审核

1. 删除不必要的修饰词（如"在多数情况下"、"公正地看"、"此点存疑"等）
2. 检查改写后的文本是否通顺
3. 确认物理量格式正确

### 9.2 AI率检测

使用学校指定的AI检测工具重新检测AI率，验证降重效果。

### 9.3 待处理问题

参考 `04-论文降重项目/需人工确认的问题.md` 中的问题列表。

---

## 十、版本历史

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| v1 | 2026-05-30 | 初始版本，基本功能实现 |
| v2 | 2026-05-30 | 修复 'n' 替换错误 |
| v3 | 2026-05-30 | 修复格式丢失问题 |
| v4 | 2026-05-30 | 修复物理量识别错误，区分专业名词 |

---

*文档生成时间：2026-05-30*
