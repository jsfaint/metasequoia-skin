# metasequoia-skin

水杉输入法候选窗皮肤的 AI 技能：**你描述想要的样子 → 生成一个皮肤包 → 离线校验 → 装进皮肤目录 → 设置页点开关**。

你不需要懂代码，也不用读代码。回答几个关于观感的问题，最后在设置页点两下就行。

```text
skin.toml          # 皮肤清单：唯一的必需文件
assets/            # 可选，背景图 / 装饰图放这里
  paper.png
  mountain.png
```

## 快速上手

### 1. 装上这个技能

把 `skills/metasequoia-skin/` 整个目录复制到你的 agent 的技能目录：

| 作用范围 | opencode | Claude Code / Agent Skills 通用 |
|---|---|---|
| 全局 | `~/.config/opencode/skills/metasequoia-skin/` | `~/.claude/skills/metasequoia-skin/`、`~/.agents/skills/metasequoia-skin/` |
| 当前项目 | `.opencode/skills/metasequoia-skin/` | `.claude/skills/metasequoia-skin/`、`.agents/skills/metasequoia-skin/` |

Windows PowerShell 示例：

```powershell
Copy-Item -Recurse skills\metasequoia-skin "$env:USERPROFILE\.config\opencode\skills\metasequoia-skin"
```

### 2. 跟 AI 说你要什么

```
帮我做一个水杉输入法的皮肤：深蓝底、琥珀色高亮、圆角大一点，
横排竖排都要，深浅两套都做
```

AI 会问几个问题（明暗、要不要图、要不要改工具栏、翻页箭头），然后生成 `skin.toml`。

### 3. 校验

```powershell
uv run skills\metasequoia-skin\scripts\check_skin.py path\to\my-skin
```

- 退出码 **0** = 通过，可以装
- **错误** = Server 会直接拒收这个包
- **警告** = 能装但可能不符合预期（配色没写全、颜色格式不认识、写了已废弃字段）

传 `skins` 根目录则一次校验所有子目录（自动跳过 `default` 和 `*.bak`）。需要 Python 3.11+，只用标准库 `tomllib`，无第三方依赖。

### 4. 安装启用

1. 设置 → 皮肤 → 外部皮肤区域，记下那行灰色路径（默认 `%LOCALAPPDATA%\metasequoiaime\skins`）
2. 把整个 `my-skin/` 文件夹复制进去 —— **不要**把 `skin.toml` 直接丢进 `skins\`，也不要套一层 zip
3. 设置 → 皮肤 → **刷新皮肤** → 找到你的皮肤 → 打开开关

改完 `skin.toml` 或图片后，点一次「刷新皮肤」就全量重载，**不需要重启输入法服务**。

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
├─ README.md
└─ skills/
   └─ metasequoia-skin/
      ├─ SKILL.md                 # 技能正文：完整字段规范、流程、故障排查表
      └─ scripts/
         └─ check_skin.py         # 离线校验器，无第三方依赖
```

## 与水杉源码的关系

这个仓库**不包含水杉输入法本体**，只包含生成外部皮肤包的知识和校验器。

`SKILL.md` 的字段、范围、报错文案逐条对齐 Server 的解析器 `server/src/skin/candidate_skin_catalog.cpp`（`CandidateSkinCatalog::Load`），`check_skin.py` 是它的 Python 等价实现，错误文案也沿用同一套中文，方便和设置页「皮肤 → 外部皮肤」底部的诊断信息对照。

**水杉源码变了之后，请回来同步修改 `SKILL.md` 和 `scripts/check_skin.py`**，别让两套规则分叉。校验器的每个函数注释里都标了对应的 C++ 函数名。

## 许可

仓库尚未添加 LICENSE 文件，即默认保留所有权利。皮肤包里建议自己声明授权（`skin.toml` 的 `[license]` 表，输入法不读，但分享前该写）：

```toml
[license]
code = "MIT"
assets = "CC-BY-4.0 / 自绘"
source = "素材出处与授权说明"
```

用别人的图之前先写清 `assets` 的出处与授权；来源说不清就写 `UNVERIFIED` 并说明仅供演示。
