# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""按内容定位行号，修正 自检-M1.md 的引用。"""
import pathlib

targets = {
    "口径规范-M1.md": ["mean 1.015", "1.015~73.404", "中位数 ≤1.5", "70 可比列", "70 / 70"],
    "维度映射-M1.md": ["A_esters_fruity", "F_esters_fruity", "X4vg", "barnyard", "AG90"],
    "Q1标定规则-M1.md": ["ALR", "def calibrate", "B1 超界", "B2 缺失", "B3 并列", "## 6. 锚点表"],
}
for f, keys in targets.items():
    lines = pathlib.Path("建模/产出/" + f).read_text(encoding="utf-8").splitlines()
    print("==", f, "lines", len(lines))
    for k in keys:
        hits = [i for i, l in enumerate(lines, 1) if k in l]
        print(f"  {k!r}: {hits[:5]}")
