# metasequoia-skin

水杉输入法候选窗皮肤的 AI 技能：**你描述想要的样子 → 生成一个皮肤包 → 离线校验 → 装进皮肤目录 → 设置页点开关**。

你不需要懂代码，也不用读代码。回答几个关于观感的问题，最后在设置页点两下就行。

```text
skin.toml          # 皮肤清单：唯一的必需文件
assets/            # 可选，背景图 / 装饰图放这里
  paper.png
  mountain.png
```

## 安装

分两步：先把**技能**装到你的 agent（装一次），再用它生成并安装**皮肤包**（每个皮肤一次）。

### A. 装技能

把 `skills/metasequoia-skin/` 整个目录放进 agent 的技能目录，**目录名别改**：

| 作用范围 | opencode | Claude Code / Agent Skills 通用 |
|---|---|---|
| 全局（推荐） | `~/.config/opencode/skills/metasequoia-skin/` | `~/.claude/skills/metasequoia-skin/`、`~/.agents/skills/metasequoia-skin/` |
| 当前项目 | `.opencode/skills/metasequoia-skin/` | `.claude/skills/metasequoia-skin/`、`.agents/skills/metasequoia-skin/` |

目录名必须与 `SKILL.md` frontmatter 里的 `name` 一字不差，否则宿主不会加载。

<details>
<summary><b>方式 1 · git clone（推荐，以后好更新）</b></summary>

```powershell
# Windows PowerShell —— 装到 opencode 全局目录
git clone --depth 1 https://github.com/jsfaint/metasequoia-skin.git "$env:TEMP\metasequoia-skin"
Copy-Item -Recurse "$env:TEMP\metasequoia-skin\skills\metasequoia-skin" "$env:USERPROFILE\.config\opencode\skills\metasequoia-skin"
```

```bash
# macOS / Linux —— 装到 Claude Code 全局目录
git clone --depth 1 https://github.com/jsfaint/metasequoia-skin.git ~/.claude/skills/metasequoia-skin
```

想省掉仓库、只留技能目录，用 sparse-checkout：

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/jsfaint/metasequoia-skin.git ~/.claude/skills/metasequoia-skin
git -C ~/.claude/skills/metasequoia-skin sparse-checkout set skills/metasequoia-skin
```
</details>

<details>
<summary><b>方式 2 · 已经有本地仓库，直接复制</b></summary>

```powershell
Copy-Item -Recurse .\skills\metasequoia-skin "$env:USERPROFILE\.config\opencode\skills\metasequoia-skin"
```

```bash
cp -r ./skills/metasequoia-skin ~/.config/opencode/skills/metasequoia-skin
```
</details>

<details>
<summary><b>方式 3 · 下载 zip 手动解压</b></summary>

在仓库页面点 **Code → Download ZIP**，解压后把里面的 `skills\metasequoia-skin` 文件夹拖到上表的目录。
</details>

**装完确认**：新开一个会话（技能在启动时扫描），让 agent 报一下可用技能，看得到 `metasequoia-skin` 就成了。

opencode 里如果技能被权限拦住，在 `opencode.json` 放行：

```json
{ "permission": { "skill": { "metasequoia-skin": "allow" } } }
```

**更新**：重新 clone 覆盖旧目录。**卸载**：删掉那个目录。

### B. 装皮肤包

1. 设置 → 皮肤 → 外部皮肤，**记下那行灰色路径**——那才是真实位置。默认是 `%LOCALAPPDATA%\metasequoiaime\skins`，数据目录装在别的盘时路径会变；旁边的「打开目录」按钮能直接打开它。
2. 把整个 `my-skin/` 文件夹复制进去。**不要**把 `skin.toml` 直接丢进 `skins\`，也不要套一层 zip。最终结构必须是 `skins\my-skin\skin.toml`。
3. 回到 设置 → 皮肤 → 点 **刷新皮肤** → 找到你的皮肤 → 打开开关。列表里能实时预览（横排 / 竖排 / 工具栏三张，另有「预览浅色」按钮）。

改完 `skin.toml` 或图片后，点一次「刷新皮肤」就全量重载，**不需要重启输入法服务**。

**只想改内置皮肤的翻页箭头**：不走外部皮肤这套流程。编辑 `<skins 目录>\default\<内置名>\skin.toml` 里的 `[candidate_window] page_arrows`，然后点「刷新皮肤」。只有 `id`、`name`、`schema_version`、`page_arrows` 会被读，其余字段写了不生效。

**设置页根本不显示这个皮肤**：对照 [SKILL.md 的故障排查表](skills/metasequoia-skin/SKILL.md)。最常见的是目录层级错了、`id` 与目录名不一致、目录名带了大写或中文。

## 快速上手

### 1. 跟 AI 说你要什么

```
帮我做一个水杉输入法的皮肤：深蓝底、琥珀色高亮、圆角大一点，
横排竖排都要，深浅两套都做
```

AI 会问几个问题（明暗、要不要图、要不要改工具栏、翻页箭头），然后生成 `skin.toml`。

### 2. 校验

```powershell
uv run skills\metasequoia-skin\scripts\check_skin.py path\to\my-skin
```

- 退出码 **0** = 通过，可以装
- **错误** = Server 会直接拒收这个包
- **警告** = 能装但可能不符合预期（配色没写全、颜色格式不认识、写了已废弃字段）

传 `skins` 根目录则一次校验所有子目录（自动跳过 `default` 和 `*.bak`）。需要 Python 3.11+，只用标准库 `tomllib`，无第三方依赖。

校验过了就按上面 [B. 装皮肤包](#b-装皮肤包) 装上，在设置页点开开关。

## 皮肤能改什么

| 能改 | 参数 |
|---|---|
| 候选窗配色：基础 8 色 + 细分配色 9 项 + 选中竖条开关 | `[candidate.dark]` / `[candidate.light]` 的 17 个颜色键 + `show_selected_bar` |
| 候选窗右键菜单配色 | `[candidate.dark.menu]` / `[candidate.light.menu]` |
| 外框圆角 / 线宽 / 高亮圆角 / 阴影 / 最小宽度 | `candidate_window.corner_radius_dip`、`border_width_dip`、`item_corner_radius_dip`、`shadow`、`min_width_dip` |
| 候选字体族（**不是字号**） | `candidate_window.font_family` |
| 卡片内背景图 / 卡片上方装饰图 | `candidate_window.background` / `candidate_window.decoration` |
| 翻页箭头 | `candidate_window.page_arrows` |
| 悬浮工具栏配色与圆角 | `[toolbar]` / `[toolbar.dark]` / `[toolbar.light]` |

| 做不到 | 说明 |
|---|---|
| 自定义 CSS / HTML / JavaScript | 外部皮肤**不接受任何 CSS 或脚本**，塞进去不会有任何效果 |
| 字号、行距、内边距、候选框留白 | 不属于皮肤参数，跟 `base` 走；字号由设置页的「候选字号」决定 |
| 工具栏尺寸、加按钮、改图标字形 | `[toolbar]` 只能改 6 个颜色 + 圆角 |
| 菜单里加自定义条目 | 菜单条目是输入法内置的，皮肤只改配色 |
| 动画、毛玻璃、透明窗口、全屏背景 | 不在参数里 |
| 改内置皮肤本身的外观 | 那是水杉仓库的源码，不是皮肤包 |

### `base` 选哪个

`base` 决定几何形态和没写到的键的默认值，选了它之后你仍然可以覆写所有配色和圆角。

| base | 观感 | 圆角 / 线宽 / 高亮圆角 | 选中形态 | accent（dark / light） |
|---|---|---|---|---|
| `fluent` | 默认，Windows 11 味 | 6 / 1.5 / 4 | 左侧竖色条 | `#6B69D6` / `#6B69D6` |
| `wechat` | 微信绿 `#07C160` | 5 / 1 / 4 | 整行绿底白字，无竖条 | `#07C160` |
| `graphite` | 石墨灰，紧凑平直 | 3 / 1 / 2 | 灰底无竖条 | `#8993A0` / `#5F6B7A` |
| `willow_green` | 杨柳青，无边框、高亮铺满 | 9 / 0 / 0 | 整行整列铺满，无竖条 | `#65C98D` / `#58B980` |
| `autumn_osmanthus` | 秋桂，无边框、橙色高亮内缩 | 10 / 0 / 6 | 内缩橙块，无竖条 | `#F97D0A` / `#E6A817` |
| `microsoft` | 仿微软拼音，紧凑、三角翻页箭头 | 8 / 1 / 4 | 灰块 + 竖条在块内 | `#E183D9` / `#E183D9` |

`microsoft` 唯一自带 `page_arrows = true`，其余五个都是关的。选它做 `base` 又不写 `page_arrows`，用户会莫名多出翻页箭头。

## 最短的 skin.toml

```toml
schema_version = 1
id = "midnight-ink"                 # 必须等于目录名
name = "深夜墨水 Midnight Ink"
version = "1.0.0"
author = "你的名字"
base = "fluent"

[supports]
layouts = ["horizontal", "vertical"]
themes = ["dark", "light"]

[candidate_window]                 # 这张表必须存在（哪怕只有 min_width_dip = 0）
corner_radius_dip = 8
border_width_dip = 1.5
item_corner_radius_dip = 6
shadow = "soft"
page_arrows = false

[candidate.dark]                   # 建议 dark / light 两组配色键都写全
accent = "#6B69D6"
selected = "#3e3e3eb9"
hover = "#414141"
surface = "#202020"
border = "#9b9b9b2e"
text = "#e9e8e8"
number = "#e9e8e89d"
translation = "#e6a817"
show_selected_bar = true
candidate_text = "#e9e8e8"
preedit_text = "#e9e8e8"
preedit_caret = "#6B69D6"
selected_text = "#ffffff"
selected_number = "#ffffff"
selected_translation = "#ffd479"
selected_bar = "#6B69D6"
preedit_background = "#ffffff10"
preedit_divider = "#6B69D6"

[candidate.light]
# ... 同上，换一套浅色值
```

完整模板、全部字段的取值范围和每个硬性约束见 [`skills/metasequoia-skin/SKILL.md`](skills/metasequoia-skin/SKILL.md)。

### 三条容易踩的规则

1. **十六进制必须带 `#`**，不透明度在末尾（`#RRGGBBAA`，不是 `#AARRGGBB`）。`绿色`、`lightblue`、`hsl(...)` 会被 Server 拒收整个包。
2. **`dark` 和 `light` 都要写全**。同一个键没写时，原生 Direct2D 后端走 `base` 的 D2D 令牌，WebView2 后端走 `base` 的 CSS，两边历史遗留有细微差别。
3. **设置页的「候选文字颜色」压过** `text` / `candidate_text` / `preedit_text`，别靠这三个键定候选文字主色。

## 目录结构

```text
.
├─ LICENSE                     # MIT
├─ README.md
└─ skills/
   └─ metasequoia-skin/
      ├─ SKILL.md              # 技能正文：完整字段规范、流程、故障排查表
      └─ scripts/
         └─ check_skin.py      # 离线校验器，无第三方依赖
```

## 与水杉源码的关系

这个仓库**不包含水杉输入法本体**，只包含生成外部皮肤包的知识和校验器。

`SKILL.md` 的字段、范围、报错文案逐条对齐 Server 的解析器 `server/src/skin/candidate_skin_catalog.cpp`（`CandidateSkinCatalog::Load`），`check_skin.py` 是它的 Python 等价实现，错误文案也沿用同一套中文，方便和设置页「皮肤 → 外部皮肤」底部的诊断信息对照。

**水杉源码变了之后，请回来同步修改 `SKILL.md` 和 `scripts/check_skin.py`**，别让两套规则分叉。校验器的每个函数注释里都标了对应的 C++ 函数名。

## 许可

本仓库的代码与文档以 [MIT](LICENSE) 授权发布。

**生成的皮肤包归你自己**，MIT 不要求你把皮肤公开。但分享出去之前请在 `skin.toml` 的 `[license]` 表里声明授权（输入法不读这张表，只是分享时该有的礼节）：

```toml
[license]
code = "MIT"                          # skin.toml 本身的授权
assets = "CC-BY-4.0 / 自绘"           # 图片素材的授权
source = "素材出处与授权说明"
```

用别人的图之前先写清 `assets` 的出处与授权；来源说不清就写 `UNVERIFIED` 并说明仅供演示。
