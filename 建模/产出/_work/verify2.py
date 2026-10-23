# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""核对 自检-M1.md 修复后引用行号。"""
import pathlib

checks = {
    "维度映射-M1.md": [55, 60, 68, 69, 70, 72, 75, 79, 82, 89, 91],
    "Q1标定规则-M1.md": [16, 29, 30, 44, 46, 59, 65, 68],
    "缺陷阈值缺口-M1.md": [11, 13, 26, 38],
    "口径规范-M1.md": [16, 36, 223, 259, 266, 270],
}
for f, nums in checks.items():
    lines = pathlib.Path("建模/产出/" + f).read_text(encoding="utf-8").splitlines()
    print("==", f, "total", len(lines))
    for n in nums:
        print(f"  L{n}: {lines[n-1][:96]}" if n <= len(lines) else f"  L{n}: <超界>")
