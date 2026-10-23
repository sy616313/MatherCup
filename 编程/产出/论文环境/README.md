# 论文 LaTeX 环境（编程维护的自检记录）

## 一、结论

**能用。** 已在本机跑通：MiKTeX 便携版 + VS Code 的 LaTeX Workshop 10.20.0，中文、公式、三线表、插图、参考文献全部正常，样张 3 页、编译约 6 秒。

## 一·补　图集 → 论文 的引用链路（已实测）

链路四步，谁写谁的文件：

1. **编程出图** → `图集/M1/图M1-01-收敛曲线.png`（图内不烧编号、不烧长标题）。
2. **编程写索引** → `图集/M1/索引.md`：稳定编号 / 标题 / 一句话内容 / 数据来源 / 绘制脚本 / 建议章节 / 建议图注。
3. **论文学会登记** → 按 `模板/图表映射模板.md` 建一张映射表：论文编号（图1）↔ 稳定编号（图M1-01）↔ 来源 png。
4. **论文正文插图**：

```latex
如图\ref{fig:conv}所示，粒子群算法在迭代 120 次后趋于稳定……

\begin{figure}[H]
    \centering
    \includegraphics[width=0.78\linewidth]{M1/图M1-01-收敛曲线.png}
    \caption{三种智能算法的收敛过程对比}
    \label{fig:conv}
\end{figure}
```

`\graphicspath` 已指向 `图集/`，所以只写 `M1/文件名`，不用写 `图集/`。

**实测结论**：中文文件名、中文图注、`\ref` 交叉引用全部正常，效果见 `图集引用效果.png`。两个坑记一下：

- 文件名里的 `M1-01` 是**稳定编号**，不是论文编号；论文里的"图1"由 LaTeX 自动生成，章节调整时自动重排，**不用改图片名**，这也是"图片只增不改名"的原因。
- 图片必须放在 `图集/Mx/` 下，不要复制到 `论文/产出/` 再插——复制会让两份副本各改各的。

## 二、装了什么

| 组件 | 版本 | 说明 |
|---|---|---|
| MiKTeX | 25.12 Portable | 便携模式，整套装在 **D 盘的 MiKTeX 文件夹**里，不占 C 盘、不需要管理员权限 |
| TeX 引擎 | xelatex（MiKTeX-XeTeX 4.16） | 中文必须用 xelatex，`ctex` 宏包已随首次编译自动装上 |
| VS Code | 1.142.0 | `code` 已在 PATH |
| LaTeX Workshop | 10.20.0 | 已安装 |
| PATH | 已把 MiKTeX 的 bin 目录加入**当前用户** PATH | 新开终端/VS Code 生效 |

VS Code 用户设置里已写入三条 recipe，默认用第一条：

1. `xelatex x2`（默认，绝大多数情况够用）
2. `xelatex x3`（交叉引用多、图表多时）
3. `xelatex -> biber -> xelatex x2`（只在用 biblatex 时）

## 三、怎么用

1. 把 `论文骨架.tex` 复制到 `论文/产出/` 下并改名（骨架里的 `\graphicspath{{../../图集/}}` 正是按 `论文/产出/` 的位置写的）。
2. VS Code 打开 `.tex` 文件：`Ctrl+Alt+B` 编译，`Ctrl+Alt+V` 看 PDF，保存时也会自动编译。
3. 命令行等价写法：`xelatex -synctex=1 -interaction=nonstopmode 文件名.tex`，跑两遍。

## 四、踩过的坑（照抄结论即可）

1. **默认 recipe 是 `latexmk` + `pdflatex`**，中文直接报错。已改成 xelatex。
2. **MiKTeX 自带的 `latexmk` 是 Perl 脚本，本机没有 Perl**，调用会失败。所以不用 latexmk，直接 xelatex 两遍；要装 Perl（Strawberry Perl）也可以，但没必要。
3. **首次编译会联网装包**。常用包（ctex/amsmath/booktabs/graphicx/hyperref 等）已在本机装好；换新宏包仍需要网络，镜像已设成清华 CTAN，速度快。
4. 每次编译 stderr 会有一条 `you have not checked for MiKTeX updates`，**不影响出 PDF**，忽略。
5. 图片只能插 `图集/Mx/` 里的 PNG，不要重画（论文角色卡 §3）。

## 五、表题位置（已裁决）

`AGENTS.md` §8 专家十条第 4 条原写"编号置图表下方"，未说清表题在上还是在下。**人类 2026-10-23 裁决：一律置于下方**——图题在图下，表题在表下（台账 R9）。

骨架已按此排版：`\caption{}` 写在 `tabular` 之后。注意 `caption` 宏包按源码位置决定"表题在上/在下"，所以**不要把 `\caption` 写回 `tabular` 之前**，否则会变回表上方。

## 六、重装/换机怎么办

1. 下载 `basic-miktex-25.12-x64.exe`（CTAN 清华镜像，约 142 MB）。
2. 以 `--unattended --portable=<D盘目标目录> --auto-install=yes` 参数运行，等待完成。
3. 把 `<目标目录>\texmfs\install\miktex\bin\x64` 加入用户 PATH。
4. VS Code 装 LaTeX Workshop，把本文 §二 列的三条 recipe 写进设置。
5. 编译 `论文骨架.tex` 验证。

## 七、体积与清理

便携安装本体约 700 MB（含首次编译自动装的宏包）。中间文件（`.aux/.log/.out/.synctex.gz/.fls`）已被 `.gitignore` 排除，不会进仓库；`.pdf` 需要交付时再单独提交。
