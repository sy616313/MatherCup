# -*- coding: utf-8 -*-
"""5.csv / 6.csv 差异量化。

在仓库根目录运行：python 建模/产出/_work/diff56.py
路径可用环境变量覆盖（缺省值按仓库根目录解析，不写死本机盘符路径）：
  DESKTOP_ATTACH  原始附件目录，缺省 ../题目/_extracted/A/附件
  REPO_DATA       仓库数据目录，缺省 数据/A
"""
import os
import pathlib

import numpy as np
import pandas as pd

A = pathlib.Path(os.environ.get("DESKTOP_ATTACH", "../题目/_extracted/A/附件"))
B = pathlib.Path(os.environ.get("REPO_DATA", "数据/A"))

for name in ["5.csv", "6.csv"]:
    a = pd.read_csv(A / name, encoding="utf-8-sig", index_col=0)
    b = pd.read_csv(B / name, encoding="utf-8-sig", index_col=0)
    print(name, "shape", a.shape, b.shape)
    print("  index same:", list(a.index) == list(b.index))
    print("  columns same:", list(a.columns) == list(b.columns))
    na = a.to_numpy(float)
    nb = b.to_numpy(float)
    diff = np.abs(na - nb)
    print("  max|diff| = %.6g   mean|diff| = %.6g   不同元素数 = %d / %d" % (diff.max(), np.nanmean(diff), int((diff > 1e-12).sum()), diff.size))
    idx = np.unravel_index(np.nanargmax(diff), diff.shape)
    print("  最大差异位置:", a.index[idx[0]], "×", a.columns[idx[1]], "desktop=", na[idx], "repo=", nb[idx])
    if name == "5.csv":
        print("  对称性 desktop:", np.allclose(na, na.T), " repo:", np.allclose(nb, nb.T))
        print("  对角 desktop:", np.diag(na)[:5], " repo:", np.diag(nb)[:5])
