#!/usr/bin/env python3
"""Extract OMML formulas from docx and convert to LaTeX for MathType - v2."""
import zipfile
import xml.etree.ElementTree as ET

import os
docx_path = os.environ.get('THESIS_PATH', './thesis.docx')

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

def get_text(elem):
    """Recursively get all text from an element."""
    parts = []
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        parts.extend(get_text(child))
        if child.tail:
            parts.append(child.tail)
    return ''.join(parts)

def omml_to_latex(elem):
    """Convert OMML element to LaTeX string."""
    tag = tag_of(elem)

    if tag == 'oMath':
        return ''.join(omml_to_latex(c) for c in elem)

    if tag == 'oMathPara':
        return ''.join(omml_to_latex(c) for c in elem)

    if tag == 'r':
        # Math run - extract text
        text = ''
        for child in elem:
            if tag_of(child) == 't':
                text += child.text or ''
        return text

    if tag == 't':
        return elem.text or ''

    if tag == 'f':  # fraction
        num = den = ''
        for child in elem:
            ct = tag_of(child)
            if ct == 'num':
                num = ''.join(omml_to_latex(c) for c in child)
            elif ct == 'den':
                den = ''.join(omml_to_latex(c) for c in child)
        return f'\\frac{{{num}}}{{{den}}}'

    if tag == 'sSub':  # subscript: e=base, sub=subscript
        base = sub = ''
        for child in elem:
            ct = tag_of(child)
            if ct == 'e':
                base = ''.join(omml_to_latex(c) for c in child)
            elif ct == 'sub':
                sub = ''.join(omml_to_latex(c) for c in child)
        return f'{base}_{{{sub}}}'

    if tag == 'sSup':  # superscript: e=base, sup=superscript
        base = sup = ''
        for child in elem:
            ct = tag_of(child)
            if ct == 'e':
                base = ''.join(omml_to_latex(c) for c in child)
            elif ct == 'sup':
                sup = ''.join(omml_to_latex(c) for c in child)
        return f'{base}^{{{sup}}}'

    if tag == 'sSubSup':  # sub-superscript: e=base, sub=sub, sup=sup
        base = sub = sup = ''
        for child in elem:
            ct = tag_of(child)
            if ct == 'e':
                base = ''.join(omml_to_latex(c) for c in child)
            elif ct == 'sub':
                sub = ''.join(omml_to_latex(c) for c in child)
            elif ct == 'sup':
                sup = ''.join(omml_to_latex(c) for c in child)
        return f'{base}_{{{sub}}}^{{{sup}}}'

    if tag == 'rad':  # radical
        deg = ''
        base = ''
        for child in elem:
            ct = tag_of(child)
            if ct == 'deg':
                deg = ''.join(omml_to_latex(c) for c in child)
            elif ct == 'e':
                base = ''.join(omml_to_latex(c) for c in child)
        if deg:
            return f'\\sqrt[{deg}]{{{base}}}'
        return f'\\sqrt{{{base}}}'

    if tag == 'd':  # delimiter
        beg, end, sep_ch = '(', ')', '|'
        for child in elem:
            ct = tag_of(child)
            if ct == 'dPr':
                for prop in child:
                    pt = tag_of(prop)
                    if pt == 'begChr':
                        beg = prop.get(qn(M, 'val'), '(')
                    elif pt == 'endChr':
                        end = prop.get(qn(M, 'val'), ')')
                    elif pt == 'sepChr':
                        sep_ch = prop.get(qn(M, 'val'), '|')
        parts = []
        for child in elem:
            if tag_of(child) == 'e':
                parts.append(''.join(omml_to_latex(c) for c in child))
        return f'{beg}{sep_ch.join(parts)}{end}'

    if tag == 'nary':  # n-ary operator
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
            elif ct == 'sub':
                sub = ''.join(omml_to_latex(c) for c in child)
            elif ct == 'sup':
                sup = ''.join(omml_to_latex(c) for c in child)
            elif ct == 'e':
                base = ''.join(omml_to_latex(c) for c in child)
        result = op
        if sub or sup:
            result += f'_{{{sub}}}^{{{sup}}}'
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
            elif ct == 'e':
                base = ''.join(omml_to_latex(c) for c in child)
        return f'{chr_val}{{{base}}}'

    if tag == 'func':
        fname = base = ''
        for child in elem:
            ct = tag_of(child)
            if ct == 'fName':
                fname = get_text(child).strip()
            elif ct == 'e':
                base = ''.join(omml_to_latex(c) for c in child)
        func_map = {'sin': '\\sin', 'cos': '\\cos', 'tan': '\\tan', 'log': '\\log', 'ln': '\\ln', 'lim': '\\lim'}
        fname_tex = func_map.get(fname, fname)
        return f'{fname_tex}{{{base}}}'

    if tag == 'eqArr':
        rows = []
        for child in elem:
            if tag_of(child) == 'e':
                rows.append(''.join(omml_to_latex(c) for c in child))
        return '\\begin{aligned} ' + ' \\\\ '.join(rows) + ' \\end{aligned}'

    if tag == 'limLow':
        base = lim = ''
        count = 0
        for child in elem:
            if tag_of(child) == 'e':
                if count == 0:
                    base = ''.join(omml_to_latex(c) for c in child)
                else:
                    lim = ''.join(omml_to_latex(c) for c in child)
                count += 1
        return f'\\mathop{{{base}}}\\limits_{{{lim}}}'

    if tag == 'limUpp':
        base = lim = ''
        count = 0
        for child in elem:
            if tag_of(child) == 'e':
                if count == 0:
                    base = ''.join(omml_to_latex(c) for c in child)
                else:
                    lim = ''.join(omml_to_latex(c) for c in child)
                count += 1
        return f'\\mathop{{{base}}}\\limits^{{{lim}}}'

    if tag == 'm':  # matrix
        rows = []
        for child in elem:
            if tag_of(child) == 'mr':
                cells = []
                for cell in child:
                    if tag_of(cell) == 'e':
                        cells.append(''.join(omml_to_latex(c) for c in cell))
                rows.append(' & '.join(cells))
        return '\\begin{bmatrix} ' + ' \\\\ '.join(rows) + ' \\end{bmatrix}'

    # Skip property elements
    if tag.endswith('Pr') or tag in ('ctrlPr',):
        return ''

    # Recursively process unknown elements
    return ''.join(omml_to_latex(c) for c in elem)


# Extract formulas
paragraphs = root.findall(f'.//{qn(W, "p")}')
formulas = []

for i, para in enumerate(paragraphs):
    math_elems = para.findall(f'.//{qn(M, "oMath")}')
    if not math_elems:
        continue

    # Get surrounding text
    text_parts = []
    for run in para.findall(f'.//{qn(W, "r")}/{qn(W, "t")}'):
        if run.text:
            text_parts.append(run.text)
    context = ''.join(text_parts).strip()

    for j, math_elem in enumerate(math_elems):
        latex = omml_to_latex(math_elem)
        formulas.append({
            'para_idx': i,
            'formula_idx': j,
            'context': context[:120],
            'latex': latex
        })

print(f"Total formulas extracted: {len(formulas)}")
print("=" * 80)
for idx, f in enumerate(formulas):
    print(f"\n--- [{idx+1}] Para {f['para_idx']} ---")
    print(f"Context: {f['context']}")
    print(f"LaTeX: {f['latex']}")
