"""M1 作图脚本：生成 图集/M1/ 下的两张示例图。

用法：python 编程/产出/脚本/M1作图.py
数据：示例合成数据（仅为验证出图→论文引用的链路，非赛题结果）
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["savefig.dpi"] = 300
plt.rcParams["figure.dpi"] = 120

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "图集" / "M1"
OUT.mkdir(parents=True, exist_ok=True)


def convergence() -> Path:
    """图M1-01：三种智能算法的收敛曲线。"""
    rng = np.random.default_rng(42)
    it = np.arange(1, 201)

    ga = 1520 * np.exp(-it / 38) + 812 + rng.normal(0, 4, it.size)
    sa = 1495 * np.exp(-it / 26) + 806 + rng.normal(0, 5, it.size)
    pso = 1540 * np.exp(-it / 55) + 798 + rng.normal(0, 3, it.size)

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.plot(it, ga, label="遗传算法", lw=1.6)
    ax.plot(it, sa, label="模拟退火", lw=1.6, ls="--")
    ax.plot(it, pso, label="粒子群算法", lw=1.6, ls="-.")
    ax.set_xlabel("迭代次数")
    ax.set_ylabel("目标函数值")
    ax.set_xlim(1, 200)
    ax.grid(alpha=0.3, ls=":")
    ax.legend(frameon=False, fontsize=10)
    fig.tight_layout()
    path = OUT / "图M1-01-收敛曲线.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def sensitivity() -> Path:
    """图M1-02：关键参数灵敏度。"""
    theta = np.array([0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4])
    base = np.array([0.0, 0.35, 0.62, 0.85, 1.00, 0.88, 0.66, 0.40, 0.12])
    upper = base + 0.06
    lower = np.clip(base - 0.06, 0, None)

    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.plot(theta, base, marker="o", ms=4, lw=1.6, label="目标值（相对）")
    ax.fill_between(theta, lower, upper, alpha=0.18, label="±5% 扰动区间")
    ax.axvline(1.0, color="gray", lw=0.9, ls=":")
    ax.set_xlabel("参数 θ（归一化）")
    ax.set_ylabel("目标值（相对基准）")
    ax.grid(alpha=0.3, ls=":")
    ax.legend(frameon=False, fontsize=10)
    fig.tight_layout()
    path = OUT / "图M1-02-参数灵敏度.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


if __name__ == "__main__":
    for p in (convergence(), sensitivity()):
        print(p.relative_to(ROOT), f"{p.stat().st_size / 1024:.0f} KB")
