#!/usr/bin/env python3
"""Extract OMML formulas → clean LaTeX for MathType - FINAL version."""
import zipfile
import xml.etree.ElementTree as ET
import re

docx_path = '/mnt/d/AI/SJK/biyesheji/03-论文正文/03-最终稿/thesis.docx'

with zipfile.ZipFile(docx_path, 'r') as z:
    with z.open('word/document.xml') as f:
        tree = ET.parse(f)
        root = tree.getroot()

M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

def qn(ns, tag):
    return f'{{{ns}}}{tag}'

def tag_of(elem):
    return elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

def omml_to_latex(elem):
    tag = tag_of(elem)
    if tag == 'oMath':
        return ''.join(omml_to_latex(c) for c in elem)
    if tag == 'oMathPara':
        return ''.join(omml_to_latex(c) for c in elem)
    if tag == 'r':
        text = ''
        for child in elem:
            if tag_of(child) == 't':
                text += child.text or ''
        return text
    if tag == 't':
        return elem.text or ''
    if tag == 'f':
        num = den = ''
        for child in elem:
            ct = tag_of(child)
            if ct == 'num': num = ''.join(omml_to_latex(c) for c in child)
            elif ct == 'den': den = ''.join(omml_to_latex(c) for c in child)
        return f'\\frac{{{num}}}{{{den}}}'
    if tag == 'sSub':
        base = sub = ''
        for child in elem:
            ct = tag_of(child)
            if ct == 'e': base = ''.join(omml_to_latex(c) for c in child)
            elif ct == 'sub': sub = ''.join(omml_to_latex(c) for c in child)
        return f'{base}_{{{sub}}}'
    if tag == 'sSup':
        base = sup = ''
        for child in elem:
            ct = tag_of(child)
            if ct == 'e': base = ''.join(omml_to_latex(c) for c in child)
            elif ct == 'sup': sup = ''.join(omml_to_latex(c) for c in child)
        return f'{base}^{{{sup}}}'
    if tag == 'sSubSup':
        base = sub = sup = ''
        for child in elem:
            ct = tag_of(child)
            if ct == 'e': base = ''.join(omml_to_latex(c) for c in child)
            elif ct == 'sub': sub = ''.join(omml_to_latex(c) for c in child)
            elif ct == 'sup': sup = ''.join(omml_to_latex(c) for c in child)
        return f'{base}_{{{sub}}}^{{{sup}}}'
    if tag == 'rad':
        deg = ''
        base = ''
        for child in elem:
            ct = tag_of(child)
            if ct == 'deg': deg = ''.join(omml_to_latex(c) for c in child)
            elif ct == 'e': base = ''.join(omml_to_latex(c) for c in child)
        if deg: return f'\\sqrt[{deg}]{{{base}}}'
        return f'\\sqrt{{{base}}}'
    if tag == 'd':
        beg, end, sep_ch = '(', ')', '|'
        for child in elem:
            ct = tag_of(child)
            if ct == 'dPr':
                for prop in child:
                    pt = tag_of(prop)
                    if pt == 'begChr': beg = prop.get(qn(M, 'val'), '(')
                    elif pt == 'endChr': end = prop.get(qn(M, 'val'), ')')
                    elif pt == 'sepChr': sep_ch = prop.get(qn(M, 'val'), '|')
        parts = []
        for child in elem:
            if tag_of(child) == 'e':
                parts.append(''.join(omml_to_latex(c) for c in child))
        return f'{beg}{sep_ch.join(parts)}{end}'
    if tag == 'nary':
        op = '\\int'
        sub = sup = base = ''
        for child in elem:
            ct = tag_of(child)
            if ct == 'naryPr':
                for prop in child:
                    if tag_of(prop) == 'chr':
                        cv = prop.get(qn(M, 'val'), '')
                        op_map = {'∑': '\\sum', '∏': '\\prod', '∫': '\\int', '∬': '\\iint'}
                        op = op_map.get(cv, cv)
            elif ct == 'sub': sub = ''.join(omml_to_latex(c) for c in child)
            elif ct == 'sup': sup = ''.join(omml_to_latex(c) for c in child)
            elif ct == 'e': base = ''.join(omml_to_latex(c) for c in child)
        result = op
        if sub or sup: result += f'_{{{sub}}}^{{{sup}}}'
        return result + base
    if tag == 'bar':
        for child in elem:
            if tag_of(child) == 'e':
                return f'\\overline{{{" ".join(omml_to_latex(c) for c in child)}}}'
        return ''
    if tag == 'acc':
        base = ''
        chr_val = '\\hat'
        for child in elem:
            ct = tag_of(child)
            if ct == 'accPr':
                for prop in child:
                    if tag_of(prop) == 'chr':
                        v = prop.get(qn(M, 'val'), '')
                        acc_map = {'\u0302': '\\hat', '\u0303': '\\tilde', '\u0305': '\\overline',
                                   '\u0307': '\\dot', '\u0308': '\\ddot', '\u20D7': '\\vec'}
                        chr_val = acc_map.get(v, '\\hat')
            elif ct == 'e': base = ''.join(omml_to_latex(c) for c in child)
        return f'{chr_val}{{{base}}}'
    if tag == 'func':
        fname = base = ''
        for child in elem:
            ct = tag_of(child)
            if ct == 'fName': fname = ''.join(omml_to_latex(c) for c in child).strip()
            elif ct == 'e': base = ''.join(omml_to_latex(c) for c in child)
        func_map = {'sin': '\\sin', 'cos': '\\cos', 'tan': '\\tan', 'log': '\\log', 'ln': '\\ln', 'lim': '\\lim'}
        return f'{func_map.get(fname, fname)}{{{base}}}'
    if tag == 'eqArr':
        rows = []
        for child in elem:
            if tag_of(child) == 'e':
                rows.append(''.join(omml_to_latex(c) for c in child))
        return '\\begin{aligned} ' + ' \\\\ '.join(rows) + ' \\end{aligned}'
    if tag.endswith('Pr') or tag in ('ctrlPr',): return ''
    return ''.join(omml_to_latex(c) for c in elem)


# Unicode → LaTeX mapping for post-processing
UNICODE_TO_LATEX = [
    ('∂', r'\partial '), ('∇', r'\nabla '), ('·', r'\cdot '),
    ('×', r'\times '), ('²', r'^{2}'), ('³', r'^{3}'),
    ('ρ', r'\rho '), ('μ', r'\mu '), ('α', r'\alpha '),
    ('β', r'\beta '), ('σ', r'\sigma '), ('ω', r'\omega '),
    ('ν', r'\nu '), ('δ', r'\delta '), ('η', r'\eta '),
    ('θ', r'\theta '), ('τ', r'\tau '), ('ε', r'\varepsilon '),
    ('ζ', r'\zeta '), ('λ', r'\lambda '), ('κ', r'\kappa '),
    ('γ', r'\gamma '), ('φ', r'\phi '), ('ψ', r'\psi '),
    ('χ', r'\chi '), ('ξ', r'\xi '), ('π', r'\pi '),
    ('∞', r'\infty '), ('≈', r'\approx '), ('≠', r'\neq '),
    ('≤', r'\leq '), ('≥', r'\geq '), ('±', r'\pm '),
    ('→', r'\to '), ('←', r'\leftarrow '), ('…', r'\ldots '),
    ('̄', ''),  # combining macron - handled by \bar
    ('̂', ''),  # combining circumflex
    # Overline/accents on specific chars
    ('ū', r'\bar{u} '), ('ū', r'\bar{u} '), ('ū', r'\bar{u} '),
    ('p̄', r'\bar{p} '), ('p̄', r'\bar{p} '),
    ('ṁ', r'\dot{m} '), ('ṁ', r'\dot{m} '),
    ('P̃', r'\tilde{P} '), ('P̃', r'\tilde{P} '),
    ('ẑ', r'\hat{z} '), ('ẑ', r'\hat{z} '),
    # Superscript/subscript digits in Unicode
    ('⁺', r'^{+}'), ('⁻', r'^{-}'),
    ('₁', '_{1}'), ('₂', '_{2}'), ('₃', '_{3}'), ('₄', '_{4}'), ('₅', '_{5}'),
    ('₆', '_{6}'), ('₇', '_{7}'), ('₈', '_{8}'), ('₉', '_{9}'), ('₀', '_{0}'),
    # Special chars
    ('𝑎', 'a'), ('𝑎', 'a'),
    ('−', '-'), ('–', '-'), ('—', '-'),
    (''', "'"), (''', "'"), ('"', '"'), ('"', '"'),
]

def unicode_to_latex(text):
    """Replace Unicode math chars with LaTeX commands."""
    for u, l in UNICODE_TO_LATEX:
        text = text.replace(u, l)
    # Clean up multiple spaces
    text = re.sub(r'  +', ' ', text)
    return text.strip()

def clean_latex(tex):
    """Final cleanup of LaTeX string."""
    tex = unicode_to_latex(tex)
    # Fix \cdot followed by spaces
    tex = re.sub(r'\\cdot\s+', r'\\cdot ', tex)
    # Fix spacing around operators
    tex = re.sub(r'\s+', ' ', tex)
    return tex.strip()


# Extract formulas
paragraphs = root.findall(f'.//{qn(W, "p")}')
formulas = []

for i, para in enumerate(paragraphs):
    math_elems = para.findall(f'.//{qn(M, "oMath")}')
    if not math_elems:
        continue

    text_parts = []
    for run in para.findall(f'.//{qn(W, "r")}/{qn(W, "t")}'):
        if run.text:
            text_parts.append(run.text)
    context = ''.join(text_parts).strip()

    for j, math_elem in enumerate(math_elems):
        raw_latex = omml_to_latex(math_elem)
        clean = clean_latex(raw_latex)
        formulas.append({
            'para_idx': i,
            'formula_idx': j,
            'context': context[:120],
            'latex': clean,
            'raw': raw_latex
        })

print(f"Total formulas extracted: {len(formulas)}")
print("=" * 80)

for idx, f in enumerate(formulas):
    print(f"\n=== [{idx+1}] Para {f['para_idx']} ===")
    print(f"Context: {f['context']}")
    print(f"LaTeX:   {f['latex']}")

# Also save to file for easy copy
output_path = '/mnt/d/AI/SJK/biyesheji/scripts/formulas_for_mathtype.txt'
with open(output_path, 'w', encoding='utf-8') as out:
    out.write("=" * 80 + "\n")
    out.write("毕业论文公式提取 → MathType TeX格式\n")
    out.write("使用方法：在MathType中开启 TeX输入模式（参数→转换→勾选TeX输入），\n")
    out.write("然后复制下方LaTeX代码粘贴即可自动渲染为公式。\n")
    out.write("粘贴后在MathType中全选公式，右键→格式→字体→设为斜体（Italic）。\n")
    out.write("=" * 80 + "\n\n")
    
    for idx, f in enumerate(formulas):
        out.write(f"{'='*60}\n")
        out.write(f"[{idx+1}] 段落 {f['para_idx']} | {f['context']}\n")
        out.write(f"{'='*60}\n")
        out.write(f"{f['latex']}\n\n")
    
    out.write("\n" + "=" * 80 + "\n")
    out.write("END\n")

print(f"\n\nSaved to: {output_path}")
