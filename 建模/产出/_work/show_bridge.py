# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""打印桥接得到的 97 对映射供人工复核。"""
import pandas as pd

d = pd.read_csv("建模/产出/化合物名称对齐-M1.csv", encoding="utf-8")
b = d[d["匹配方式"] == "桥接"]
print(len(b))
for _, r in b.iterrows():
    print(f"{r['1csv字段']:34s} -> {r['2csv节点名']}")
