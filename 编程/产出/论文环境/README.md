# 论文 LaTeX 环境（编程维护的自检记录）

## 一、结论

**能用。** 已在本机跑通：MiKTeX 便携版 + VS Code 的 LaTeX Workshop 10.20.0，中文、公式、三线表、插图、参考文献全部正常，样张 3 页、编译约 6 秒。

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

## 五、待裁决（给大脑和论文）

`AGENTS.md` §8 专家十条第 4 条写"图表编号置图表**下方**"，但中文排版惯例是**图题在图下、表题在表上**（GB/T 格式，也是往届获奖论文的通行做法）。骨架目前按惯例（表题在上、图题在下）。

两种改法：① 维持惯例，把章程那句改成"图题在下、表题在上"；② 严格照章程，全部放下方。建议 ①，但这属于章程范围，等大脑裁决后我改骨架。

## 六、重装/换机怎么办

1. 下载 `basic-miktex-25.12-x64.exe`（CTAN 清华镜像，约 142 MB）。
2. 以 `--unattended --portable=<D盘目标目录> --auto-install=yes` 参数运行，等待完成。
3. 把 `<目标目录>\texmfs\install\miktex\bin\x64` 加入用户 PATH。
4. VS Code 装 LaTeX Workshop，把本文 §二 列的三条 recipe 写进设置。
5. 编译 `论文骨架.tex` 验证。

## 七、体积与清理

便携安装本体约 700 MB（含首次编译自动装的宏包）。中间文件（`.aux/.log/.out/.synctex.gz/.fls`）已被 `.gitignore` 排除，不会进仓库；`.pdf` 需要交付时再单独提交。
