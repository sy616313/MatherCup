#!/usr/bin/env python3
"""仓库结构检查：绝对路径、断链、缺失引用、编码/换行。"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
SKIP_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules", ".idea", ".vscode",
    # 本机目录联结的外部资料库：几 GB、非仓库内容，整棵剪掉
    "外部资料",
}
TEXT_SUFFIXES = {".md", ".py", ".txt", ".yml", ".yaml", ".json", ".tex", ".csv", ".tsv"}
PATH_PREFIXES = (
    "资料/", "建模/", "编程/", "论文/", "审阅/", "模板/",
    "图集/", "数据/", "工具/", "规范/", "任务书/",
)
ROLE_RELATIVE = {"任务书/", "产出/", "快照/"}
IGNORE_MARKERS = (
    "____", "Mx", "<", ">", "*", "…", "xxx",
    "外部资料/", "http://", "https://", "mailto:",
)
ABSOLUTE_PATTERNS = (
    re.compile(r"[A-Za-z]:[\\/]"),
    re.compile(r"/(?:Users|home)/"),
    re.compile(r"file://"),
    # UNC 形如 \\server\share：要求反斜杠后紧跟主机名，避免把 LaTeX 换行符 \\ 误判
    re.compile(r"\\\\[A-Za-z0-9_.$-]+\\"),
)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
CODE_RE = re.compile(r"`([^`\n]+)`")


def iter_files():
    """按目录剪枝遍历；SKIP_DIRS 内的目录整棵不进入。"""
    for current, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = Path(current) / name
            if path.resolve() == SELF:
                continue
            yield path


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for path in iter_files():
        rel = path.relative_to(ROOT)
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            raw = path.read_bytes()
        except OSError as exc:
            errors.append(f"{rel}: 读取失败: {exc}")
            continue

        if raw.startswith(b"\xef\xbb\xbf"):
            errors.append(f"{rel}: 含 UTF-8 BOM")
        if b"\r\n" in raw:
            warnings.append(f"{rel}: 含 CRLF（建议 LF）")

        text = raw.decode("utf-8", errors="replace")
        if "\ufffd" in text:
            errors.append(f"{rel}: 不是有效 UTF-8")

        for pattern in ABSOLUTE_PATTERNS:
            for match in pattern.finditer(text):
                errors.append(f"{rel}:{line_of(text, match.start())}: 绝对路径 `{match.group(0)}`")

        if path.suffix.lower() == ".md":
            for match in LINK_RE.finditer(text):
                target = match.group(1).strip()
                if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                    continue
                target = target.split("#", 1)[0].split("?", 1)[0]
                if not target:
                    continue
                if target.startswith("/"):
                    errors.append(f"{rel}:{line_of(text, match.start())}: 站内绝对链接 `{target}`")
                    continue
                dest = (path.parent / target).resolve()
                try:
                    dest.relative_to(ROOT)
                except ValueError:
                    errors.append(f"{rel}:{line_of(text, match.start())}: 链接越出仓库 `{target}`")
                    continue
                if not dest.exists():
                    errors.append(f"{rel}:{line_of(text, match.start())}: 断链 `{target}`")

        for match in CODE_RE.finditer(text):
            value = match.group(1).strip()
            if not value.startswith(PATH_PREFIXES):
                continue
            if value in ROLE_RELATIVE:
                continue
            if any(marker in value for marker in IGNORE_MARKERS):
                continue
            value = value.split()[0].rstrip("，。；;、")
            if not value:
                continue
            dest = (ROOT / value).resolve()
            if not dest.exists():
                errors.append(f"{rel}:{line_of(text, match.start())}: 引用不存在 `{value}`")

    if warnings:
        print("警告：")
        for item in warnings:
            print("  -", item)

    if errors:
        print("错误：")
        for item in errors:
            print("  -", item)
        print(f"\n共 {len(errors)} 个错误。")
        return 1

    print("检查通过：没有绝对路径、断链或缺失引用。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
