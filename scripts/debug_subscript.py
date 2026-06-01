# -*- coding: utf-8 -*-
"""
调试下标匹配问题
"""

import re

def parse_text_with_format(text):
    """解析文本，识别需要特殊格式的部分"""
    parts = []
    i = 0

    while i < len(text):
        # 匹配参考文献引用 [数字] 或 [数字,数字] 或 [数字-数字]
        ref_match = re.match(r'\[\d+(?:[,，]\d+)*(?:-\d+)?\]', text[i:])
        if ref_match:
            parts.append(('ref', ref_match.group()))
            i += ref_match.end()
            continue

        # 匹配希腊字母+下标模式（如 β2、ε、ω）
        greek_match = re.match(r'([αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ])([0-9]+)?', text[i:])
        if greek_match:
            parts.append(('greek', greek_match.group(1)))
            if greek_match.group(2):
                parts.append(('subscript', greek_match.group(2)))
            i += greek_match.end()
            continue

        # 匹配物理量变量+下标模式（如 Qd、Hd、D2、b2、ns）
        var_match = re.match(r'([A-Za-z])([0-9a-zA-Z]+)?', text[i:])
        if var_match:
            letter = var_match.group(1)
            # 判断是否是物理量变量
            if letter.lower() not in ['a', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'with']:
                parts.append(('var', letter))
                if var_match.group(2):
                    parts.append(('subscript', var_match.group(2)))
                i += var_match.end()
                continue

        # 匹配普通字符
        parts.append(('normal', text[i]))
        i += 1

    return parts

# 测试文本
test_text = "离心泵的核心过流部件是叶轮，其几何参数直接决定泵的水力性能与能量转换效率[3]。其中，β2决定了叶轮出口环量和理论扬程；Z影响流动引导能力和叶片对流体的排挤效应；D2和b2通过比转速和流量-速度关系决定整体流道尺度[4,5]。"

print("测试文本：")
print(test_text)
print("\n解析结果：")

parts = parse_text_with_format(test_text)
for i, (part_type, part_text) in enumerate(parts):
    print(f"{i:3d}: {part_type:12s} | '{part_text}'")
