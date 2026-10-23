# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""修复后重新定位 自检-M1.md 要引用的行号。"""
import pathlib

files = {
    "口径规范-M1.md": ["## 2.", "## 3.", "### 3.2", "## 4.", "## 5.", "## 6.", "## 7.", "## 8.", "## 9.", "## 10.",
                        "0.126%", "S1 |", "4+1=5"],
    "维度映射-M1.md": ["## 一、", "## 二、", "## 三、", "AG90", "body(AF)"],
    "Q1标定规则-M1.md": ["## 2.", "## 3.", "## 4.", "## 5.", "## 6.", "T1", "T4", "gen_q1.py"],
    "缺陷阈值缺口-M1.md": ["G1", "G2", "G3", "## 三、"],
}
for f, keys in files.items():
    lines = pathlib.Path("建模/产出/" + f).read_text(encoding="utf-8").splitlines()
    print("==", f, len(lines))
    for k in keys:
        hits = [i for i, l in enumerate(lines, 1) if l.startswith(k) or k in l]
        print(f"   {k!r}: {hits[:4]}")
