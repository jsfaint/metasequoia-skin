---
name: metasequoia-skin
description: 生成、校验、安装水杉输入法（metasequoia ime）的候选窗皮肤包。用户描述想要的观感（配色、圆角、阴影、背景图、装饰图、九宫格贴图面板、卡片外立绘挂件、翻页箭头、工具栏配色），或需要手写/排查 skin.toml，或皮肤装上没反应、设置页报「缺少 candidate_window」「candidate 配色无效」「找不到 image 文件」时使用。产出 skin.toml + assets，并用 check_skin.py 离线校验（支持 schema_version 1 与 2）。
license: MIT
compatibility: opencode
metadata:
  product: metasequoia-ime
  language: zh-CN
---

# 水杉输入法皮肤（metasequoia-skin）

给非开发者用的皮肤生成流程：**用户描述想要的样子 → 你生成一个皮肤包 → 校验 → 装进皮肤目录 → 用户在设置页点开关**。

用户不需要懂代码，你也不该让他读代码。整个过程他只需要回答几个关于观感的问题，最后在设置页点两下。

> 本 skill 的字段、范围、报错文案逐条对齐 Server 的解析器
> `server/src/skin/candidate_skin_catalog.cpp`（`CandidateSkinCatalog::Load`），配色回落见
> `server/src/window/candidate_presenter.cpp`。
> 字段清单另见 `examples/skin-examples/schema/README.md`，带注释的完整样例见
> `examples/skin-examples/skins/niya-demo/skin.toml`，官方全贴图样板见 `skins/green_leaf/skin.toml`。
> **源码变了就回来改这份文档和 `scripts/check_skin.py`**，别让两套规则分叉。
>
> `schema_version` 支持 **1 与 2**：v1 是通用卡片皮肤（配色 + 圆角 + 图片，模板见 §3）；
> v2 是**以 `canvas` 为地基的全贴图皮肤**，追加九宫格贴图面板、面板内安全内边距、行距、
> 卡片外立绘挂件与窗口外留白（见 §3 的 v2 小节）。
> **v2 字段只在 `schema_version = 2` 且 `base = "canvas"` 时被解析**（见 §0 规则 6）。

## 0. 先确定边界：能改什么，不能改什么

外部皮肤**只有 `skin.toml` 一个文件是活的**，没有别的。**开工前先看这张表**，用户要的东西不在里面就直接说做不到，别生成一个装上没反应的包。

| 能改 | 怎么改 |
|---|---|
| 候选窗配色：基础 8 色 + 细分配色 9 项 + 翻译细分 4 项 + 选中竖条开关 | `[candidate.dark]` / `[candidate.light]` 的 21 个颜色键 + `show_selected_bar` |
| 候选窗右键菜单配色（底色、边框、文字、悬停） | `[candidate.dark.menu]` / `[candidate.light.menu]` 的 4 个键 |
| 候选框外框圆角 / 线宽 | `candidate_window.corner_radius_dip`（0~32）、`border_width_dip`（0~4） |
| 候选项高亮圆角 | `candidate_window.item_corner_radius_dip`（0~16） |
| 候选框卡片阴影 | `candidate_window.shadow`（`none` / `soft` / `strong`） |
| 卡片背后的系统材质（亚克力 / 云母） | `candidate_window.backdrop`（`none` / `acrylic` / `mica`） |
| 候选字体**族**（不是字号） | `candidate_window.font_family`（≤64 字节） |
| 候选框最小宽度 | `candidate_window.min_width_dip`（0~1000） |
| 卡片严格按文字宽度收紧 | `candidate_window.fit_content`（`true` / `false`） |
| 候选框卡片内的背景图 | `candidate_window.background`（`image` / `fit` / `opacity`） |
| 候选框卡片上方的装饰图 | `candidate_window.decoration`（`image` / `top_inset_dip` / `width_dip` / `align`） |
| 候选框里的翻页箭头 | `candidate_window.page_arrows`（`true` / `false`） |
| 悬浮工具栏配色（底色、边框、拖动条、分隔线、图标、悬停）与圆角 | `[toolbar]` / `[toolbar.dark]` / `[toolbar.light]` |
| 整块面板贴图（九宫格拉伸，**v2**） | `[candidate_window.border_image]`，其中 `light_source` 能给浅色主题单独换一张面板图 |
| 面板内的四边安全内边距（**v2**） | `[candidate_window.content_insets_dip]` |
| 预编辑行与候选行之间的行距（**v2**） | `line_gap_dip` |
| 挂到卡片外沿的立绘/挂件，多层（**v2**） | `[[candidate_window.decorations]]` |
| 卡片四边之外要预留的透明空白（**v2**） | `[candidate_window.outer_insets_dip]` |
| 动图（APNG / GIF / 动画 WebP，**v2**） | 把 v2 的图片路径指向动图就行，原生播放，不用额外开关 |
| 底子用哪套基底 | `base` |

| 做不到 | 说明 |
|---|---|
| 自定义 CSS 或 HTML / JavaScript | 外部皮肤**不能**提供任何 CSS 或脚本。写 `.css`、`.js` 放进包里不会有任何效果 |
| 字号、行内边距、候选框留白 | 字号由设置页的「候选字号」决定；行内边距与留白跟 `base` 走（v2 的 `content_insets_dip` 只能改四边的**安全内边距**） |
| 工具栏尺寸、加按钮、改图标字形 | `[toolbar]` 只能改 6 个颜色 + 圆角 |
| 菜单里加自定义条目 | 右键菜单的条目是输入法内置的，皮肤只能改配色 |
| 全屏背景、窗口本身的其它透明特效 | 不在参数里。卡片背后的材质只有 `backdrop` 这一种 |
| 改内置皮肤（fluent/wechat/…）本身的外观 | 那是水杉仓库的源码，不是皮肤包。内置皮肤只有 `page_arrows`、`fit_content` 两个开关可改，改法见 §5 末尾 |

**毛玻璃是可以做的**，走 `candidate_window.backdrop`：`acrylic`（亚克力）模糊卡片后面的窗口，`mica`（云母）取样桌面壁纸、只透出壁纸色调。限制要说清：需要系统开着「透明效果」（设置 → 个性化 → 颜色），关掉或系统太老（低于 Windows 10 1903；云母还要 Windows 11，更早的系统按亚克力画）时会退回不透明底色；同一张皮肤写了 `border_image` 时不生效（有面板贴图就不垫材质）。

**实现只有 Direct2D 一套**：候选窗、悬浮工具栏都由 `msimeui` 用 Direct2D 绘制。皮肤只能声明颜色与图片，没有第二个后端可选；这些声明在渲染时解析成 D2D 令牌（`window/candidate_presenter.cpp`、`window/candidate_skin_palette.cpp`），没写的键由 `base` 补齐。

### 六条容易踩的一致性规则

1. **没写的键会走 `base` 的 D2D 令牌**：`base` 的配色与几何先铺底，你的键再逐项覆盖。**所以 `[candidate.dark]` 和 `[candidate.light]` 都要把配色键写全**，这样任何 `base` 下都只听你的。共享基底（§1）没写的键走的也是 fluent 的令牌。

2. **设置页的「候选文字颜色」压过 `text` / `candidate_text` / `preedit_text`**：用户在设置里动过候选文字颜色时，这三个键不生效——所以别靠它们定候选文字的主色。

3. **十六进制必须带 `#`**。这是清单格式的约定。渲染器对不带 `#` 的写法有容错（`e8a` 也会被当成 `#ee88aa`），但别依赖它：`check_skin.py` 会警告，而 `lightblue` 这种不是十六进制的写法会直接退回默认色。

4. **写了 `candidate_text` 就要配 `selected_text`**。`candidate_text` 只管普通候选行；选中行的文字仍取 `base` 的选中行配色——微信、杨柳青、秋桂是实色高亮上的白字，fluent、石墨这类竖条式选中不另设颜色、跟着普通文字色。想让选中行也听你的，就一并写 `selected_text`（和 `selected_number`）。

5. **写 `translation` 会连带重置词性与分隔符**：解析器给 `translation` 上色的同时，会把 `translation_pos` / `translation_separator` 一起拉成同色；写了 `selected_translation` 则把选中行的词性/分隔符也拉成它。要保留那几处独立颜色，得显式写 `translation_pos` / `translation_separator`（选中行另有 `selected_translation_pos` / `selected_translation_separator`）。

6. **v2 必须 `base = "canvas"`**。`schema_version = 2` 只是声明，真正的地基是 `canvas`——透明面板、无描边、直角、默认没有阴影，外观全部来自九宫格面板图与挂件。写了 `2` 但 `base` 是别的基底时，这个包仍能装也能用，但**按 v1 加载**：`border_image`、`content_insets_dip`、`line_gap_dip`、`outer_insets_dip`、`decorations` 全部被忽略（连同其中的错误），设置页诊断里会多一条说明。反过来，`schema_version = 1` 配 `canvas` 会被直接拒——没有面板贴图它只是一张透明卡片。

**已经被移除的老字段**（写了不报错，但**完全无效**，别再生成）：

| 老字段 | 现状 |
|---|---|
| 根级 `preview = "preview.png"` | 已移除。装饰图改由 `candidate_window.decoration.image` 指定 |
| 根级 `toolbar_stylesheet = "toolbar.css"` | 已移除。工具栏改由 `[toolbar]` 系列表配置，不做任何兼容 |
| `[candidate_window.decoration]` 里两个尺寸都填 0 | 现在是**非法**，会被拒（见 §4） |

**另一个同类陷阱**：五个 v2 字段写在没配 `canvas` 的皮肤里同样是「不报错也不生效」——见上面的规则 6。

## 1. 先问用户什么

一轮问完，别挤牙膏：

1. **想要什么观感**——给几个具体的：参考色、参考图、"像微信"、"性冷淡灰"、"赛博霓虹"、"像微软拼音"。用户说不出就给选项让他挑。
2. **明暗**：默认两套都做（推荐），除非用户明确只要一套。
3. **要不要图片**：候选框**里面**铺一张底图（`background`），还是卡片**上方**放一张装饰图（`decoration`），还是都要。要的话让他给图。
4. **要不要改悬浮工具栏**：`[toolbar]` 能改配色和圆角，不改尺寸、不加按钮。
5. **要不要翻页箭头**：写了 `page_arrows`，候选框里会出现一小列/一小行「‹ ›」。不说就跟着 `base` 走。
6. **横排还是竖排**：默认 `supports` 全选，两个布局都支持。
7. **要不要 v2 能力**（整块贴图面板 / 卡片外立绘挂件）：只有这两类需求才需要 `schema_version = 2`，而且 `base` 必须跟着改成 `canvas`（见 §0 规则 6）。
   要卡外立绘就必须 v2 且写 `outer_insets_dip`，否则立绘会被窗口边界裁掉。
   同时要提醒用户：v2 的地基是**透明的 `canvas`**，面板长什么样完全靠 `[candidate_window.border_image]`——只声明 v2 不给面板图，候选框里就只剩悬空的文字。

`base` 不用问用户，按观感你来定：

| base | 观感 | 圆角 / 线宽 / 高亮圆角 | 选中形态 | accent（dark / light） |
|---|---|---|---|---|
| `fluent` | 默认，Windows 11 味 | 6 / 1.5 / 4 | 左侧竖色条 | `#6B69D6` / `#6B69D6` |
| `wechat` | 微信绿 `#07C160` | 5 / 1 / 4 | 整行绿底白字，无竖条 | `#07C160` |
| `graphite` | 石墨灰，紧凑平直 | 3 / 1 / 2 | 灰底无竖条 | `#8993A0` / `#5F6B7A` |
| `willow_green` | 杨柳青，无边框、高亮铺满 | 9 / 0 / 0 | 整行整列铺满，无竖条 | `#65C98D` / `#58B980` |
| `autumn_osmanthus` | 秋桂，无边框、橙色高亮内缩 | 10 / 0 / 6 | 内缩橙块，无竖条 | `#F97D0A` / `#E6A817` |
| `microsoft` | 仿微软拼音，紧凑、三角翻页箭头 | 8 / 1 / 4 | 灰块 + 竖条在块内 | `#E183D9` / `#E183D9` |

`base` 决定的是**几何**和**没写到的键的默认值**。你自己写了 `corner_radius_dip`、`item_corner_radius_dip` 和全部配色键之后，`base` 还剩下不在参数里的排版（行内边距、候选项间距）以及「高亮是铺满还是内缩」这类形态（v2 的 `line_gap_dip` / `content_insets_dip` 只能覆盖行距和四边安全内边距）。

**microsoft 唯一自带 `page_arrows = true`**（出厂清单如此），其余五个内置皮肤都是关的。选它做 base 却不写 `page_arrows`，用户就会莫名多出翻页箭头——要么明确写 `page_arrows = false`，要么跟用户确认要这个箭头。

### 共享基底与全贴图地基

`base` 除了六个内置皮肤，还能写水杉与 msime 共用的**共享基底**，以及只给 v2 用的**全贴图地基**：

| base | 观感 | 明暗 |
|---|---|---|
| `system` | 跟随宿主，没有自己的调色板 | 跟随系统 |
| `shuishan` | 水杉绿：深色底 + 浅绿强调 | 固定深色 |
| `light` | Windows 浅色：白底 + 蓝强调 | 固定浅色 |
| `paper` | 纸白：暖白底 + 绿强调 | 固定浅色 |
| `night` | 夜蓝：深蓝底 + 青绿强调 | 固定深色 |
| `ink` | 墨黑：黑底 + 白强调 | 固定深色 |
| `canvas` | 全贴图地基，**只给 v2 用**，面板外观全交给贴图 | 看你写哪套 |

三条行为要记住，不然会做出「配色写了却没反应」的包：

- **共享基底加载后一律被当作 `fluent`**：绘制结构、几何和设置页预览都按 fluent 走，基底只补上表里的基础配色（`surface` / `text` / `accent` / `number`，以及由它们派生出来的选中、悬停、翻译、菜单、工具栏色）。**你没写的键走的是 fluent 的 D2D 令牌**，不是别的，也不是宿主系统那套。
- **固定明暗的基底会把 `[supports] themes` 收窄**成它自己那一侧（`shuishan` / `night` / `ink` 收成 `dark`，`light` / `paper` 收成 `light`）：声明里没有对应明暗时收窄成空，两种明暗都回退 fluent；声明了另一侧也只是摆设，那一侧的配色不会生效。`system` 不收窄。
- **`canvas` 不能单独在设置页选用**：它只是 v2 皮肤的地基，没有九宫格面板图与挂件时什么也看不见，所以 `schema_version = 1` 用它会直接被拒。

**🔴 CHECKPOINT · 生成前**：问完第 1 节后，把方案一行列给用户确认——「皮肤 ID / 显示名 / base / 明暗两套 / 背景图 / 装饰图 / 翻页箭头 / 工具栏配色」，用户点头再生成文件。用户明确说「直接做」时可跳过这一步。

## 2. 皮肤包长什么样

```text
my-skin/                 ← 目录名 = 皮肤 ID，规则见下
├─ skin.toml             ← 必需，唯一必须的文件
└─ assets/               ← 可选，图片放这里，路径写进 skin.toml
   ├─ paper.png
   └─ mountain.png
```

**ID 规则**（目录名，同时也是 `skin.toml` 里的 `id`，两者必须一字不差）：

- 首字符是小写字母或数字，之后只能是小写字母、数字、`.`、`_`、`-`，总长 ≤ 64 字节
- 纯 ASCII，不能是内置名（`fluent`、`wechat`、`graphite`、`willow_green`、`autumn_osmanthus`、`microsoft`），也不能是保留名 `default`
- 例：`midnight-ink`、`sakura_2`、`gloss.v2` ✅　`Midnight`、`my skin`、`深夜`、`default` ❌

图片路径同样是纯 ASCII，只能含字母数字和 `./_-`，用 `/` 分层（如 `assets/paper.png`），不能有 `..`、不能以 `/` 开头、不能用 `\`、单段不能是 `.`。

## 3. skin.toml 模板

直接照抄改值。两组配色键已写全（规则见 §0），注释掉的部分是可选表：

```toml
schema_version = 1                 # 固定 1，必须是数字不能是字符串

id = "midnight-ink"                # 必须等于目录名
name = "深夜墨水 Midnight Ink"       # 设置页显示的名字，≤80 字节
version = "1.0.0"                  # ≤32 字节
author = "你的名字"                  # 可选，≤120 字节
description = "深蓝底 + 琥珀色高亮"  # 可选，≤500 字节
base = "fluent"                    # 必填，取六个内置皮肤之一；共享基底见 §1

[supports]                         # 必填，建议四项全选
layouts = ["horizontal", "vertical"]
themes = ["dark", "light"]

[candidate_window]                 # 表必须存在（哪怕是空表）
min_width_dip = 320                # 可选，0~1000，0 = 不设
corner_radius_dip = 8              # 可选，0~32；0 = 直角
border_width_dip = 1.5             # 可选，0~4，可小数；0 = 无外框
item_corner_radius_dip = 6         # 可选，0~16；高亮块圆角
shadow = "soft"                    # 可选 none / soft / strong
backdrop = "none"                  # 可选 none / acrylic(亚克力) / mica(云母)；要系统透明效果，写了面板贴图就不生效
font_family = "Segoe UI"           # 可选，≤64 字节，只能一个字体名
page_arrows = false                # 可选 true / false；不写则跟 base 的出厂设置
fit_content = false                # 可选 true / false；true = 卡片严格按文字宽度收紧

# 卡片内的背景图。整段注释掉就没有背景图——
# 【注意】表一旦出现，image 和文件必须存在，写半截会被 Server 拒收。
# [candidate_window.background]
# image = "assets/paper.png"       # 必填
# fit = "cover"                    # 可选 cover(默认) / contain / stretch
# opacity = 0.35                   # 可选 0~1，1 = 原样

# 卡片上方的装饰图。同样是「表和内容一起出现或一起消失」。
# [candidate_window.decoration]
# image = "assets/mountain.png"   # 必填
# top_inset_dip = 88               # 必填，0~500 且必须 > 0
# width_dip = 136                  # 必填，0~1000 且必须 > 0
# align = "right"                  # 可选 left / center / right，默认 right

[candidate.dark]                   # 21 个颜色键 + show_selected_bar，建议写全
# ── 基础 8 色 ──
accent = "#6B69D6"                 # 强调色：预编辑光标；选中竖条的默认颜色
selected = "#3e3e3eb9"             # 选中行背景
hover = "#414141"                  # 悬停行背景；翻页箭头悬停也用它
surface = "#202020"                # 候选窗背景；也是亚克力/云母材质的色调
border = "#9b9b9b2e"               # 候选窗外框
text = "#e9e8e8"                   # 候选文字（会被设置页「候选文字颜色」覆盖）
number = "#e9e8e89d"               # 序号 1. 2. 3.；翻页箭头也用它
translation = "#e6a817"            # 候选后面的翻译；不写则取文字色降到 62% 不透明。写了会连带把下面两个翻译细分键重置成同色
show_selected_bar = true           # 选中行左侧竖色条；false = 关掉

# ── 细分 9 色，不写时按注释回落 ──
candidate_text = "#e9e8e8"         # 普通候选文字 → text；写了就一定要写 selected_text（见 §0 规则 4）
preedit_text = "#e9e8e8"           # 预编辑拼音文字 → text
preedit_caret = "#6B69D6"          # 预编辑光标 → accent
selected_text = "#ffffff"          # 选中候选文字 → base 的选中文字色
selected_number = "#ffffff"        # 选中候选序号 → base 的选中序号色
selected_translation = "#ffd479"   # 选中候选翻译 → translation，再退到选中文字色的 62%
selected_bar = "#6B69D6"           # 选中项左侧竖条 → accent
preedit_background = "#ffffff10"   # 预编辑行底色，圆角同高亮圆角；不写则透明
preedit_divider = "#6B69D6"        # 预编辑行下方 1px 分隔线；不写则没有

# ── 翻译细分 4 色，对应翻译里的词性标记与义项分隔符 ──
# 不写则与 translation 同色；写了 translation 会把它们一起拉成同色，想保住就得显式写
# translation_pos = "#e6a817"             # 翻译里的词性标记（名/动/形…）
# translation_separator = "#e6a817"       # 翻译里义项之间的分隔符
# selected_translation_pos = "#ffd479"    # 选中行的词性标记 → translation_pos
# selected_translation_separator = "#ffd479"  # 选中行的分隔符 → translation_separator

# 只有 backdrop 不是 none 时才用得上，0~1 的数
# backdrop_opacity = 0.15           # surface 色调盖在材质上的不透明度；不写取 surface 自带的 alpha
# backdrop_luminosity = 0.96        # 亮度层不透明度；不写时亚克力 0.85、云母 1

# 候选窗右键菜单，可省略
# [candidate.dark.menu]
# background = "#202020"
# border = "#9b9b9b2e"
# text = "#e9e8e8"
# hover = "#414141"

[candidate.light]
accent = "#6B69D6"
selected = "#E8E8E8"
hover = "#ECECEC"
surface = "#FFFFFF"
border = "rgba(0,0,0,.12)"
text = "#1A1A1A"
number = "#1A1A1A8C"
translation = "#B8860B"
show_selected_bar = true
candidate_text = "#1A1A1A"
preedit_text = "#1A1A1A"
preedit_caret = "#6B69D6"
selected_text = "#1A1A1A"
selected_number = "#1A1A1A8C"
selected_translation = "#B8860B"
selected_bar = "#6B69D6"
preedit_background = "#00000008"
preedit_divider = "rgba(0,0,0,.12)"

# translation_pos = "#B8860B"
# translation_separator = "#B8860B"
# selected_translation_pos = "#B8860B"
# selected_translation_separator = "#B8860B"

# backdrop_opacity = 0
# backdrop_luminosity = 0.85

# [candidate.light.menu]
# background = "#FFFFFF"
# border = "rgba(0,0,0,.12)"
# text = "#1A1A1A"
# hover = "rgba(0,0,0,.06)"

# 悬浮工具栏。整段注释掉就完全跟 base 走。
# [toolbar]
# corner_radius_dip = 8            # 可选 0~32
#
# [toolbar.dark]
# background = "#1A1A1A"           # 工具栏底色
# border = "rgba(255,255,255,.15)"  # 外框
# handle = "#8E8CD8"               # 左侧拖动条；不写时取同主题的 accent
# divider = "rgba(255,255,255,.15)" # 分隔线
# icon = "#FFFFFF"                 # 图标字形
# hover = "rgba(255,255,255,.10)"   # 图标悬停底色
#
# [toolbar.light]
# background = "#FFFFFF"
# border = "rgba(0,0,0,.12)"
# handle = "#6B69D6"
# divider = "rgba(0,0,0,.12)"
# icon = "#1A1A1A"
# hover = "rgba(0,0,0,.06)"

# 授权声明，输入法不读，但分享出去前该写。
# [license]
# code = "MIT"                     # skin.toml 本身的授权
# assets = "CC-BY-4.0 / 自绘"       # 图片素材的授权；来源未核实就写 UNVERIFIED
# source = "素材出处与授权说明"
```

**TOML 顺序陷阱**：子表必须写在父表键之后。`[candidate_window]` 里先写 `min_width_dip`、`corner_radius_dip`，再写 `[candidate_window.background]`；一旦写了 `[candidate_window.background]`，后面再出现 `[candidate_window]` 就是语法错误。同理 `[candidate.dark]` 的键写完才能开 `[candidate.dark.menu]`。

### v2 追加字段（`schema_version = 2`，且 `base = "canvas"`）

先决定要不要 v2。只有这几种需求需要它：**整块贴图面板**（九宫格拉伸）、**面板内的四边安全内边距**、**行距**、**挂到卡片外沿的立绘 / 挂件**（可多层、可动图）、**卡片外的留白**。其余情况停在 v1，v1 的包不用改。

**v2 请和 `base = "canvas"` 一起写**：`canvas` 是透明面板、无描边、直角、默认没有阴影的地基，卡片长什么样完全由上表里的贴图与挂件决定。写了 `2` 而 `base` 是别的基底，整段 v2 字段会被忽略（按 v1 加载，见 §0 规则 6）。

v2 字段全部写在 `[candidate_window]` 里（`line_gap_dip` 是直接的键，其余是子表 / 数组表）：

```toml
schema_version = 2
base = "canvas"                       # v2 必须是 canvas

[candidate_window]
line_gap_dip = 6                     # 可选，0~100；预编辑行与候选行之间的距离

[candidate_window.border_image]      # 面板整体贴图：整块卡片背景换成这张图
source = "assets/panel.png"          # 必填，包内相对路径，只能是 .png / .apng / .gif / .webp
# light_source = "assets/panel-light.png"  # 可选，浅色主题换这张；切片、边宽、fill 与 source 共用
slice_dip = [16, 44, 16, 44]         # 必填，1 / 2 / 4 个数值，各 0~500，顺序是「上 右 下 左」
# stretch_dip = [16, 90, 16, 90]     # 可选，同规则；给出时它才是可拉伸区（语义比 slice 直白）
# width_dip = [16, 44, 16, 44]       # 可选，边框绘制宽度，各 0~500；缺省用 slice/stretch 的值
# fill = true                        # 可选，默认 true；false = 中心区也不画，露出卡片底色

[candidate_window.content_insets_dip]  # 文字与内容的安全内边距，从面板外缘量起
# top = 4                            # 可选，缺省 0；top / bottom ≤ 200，left / right ≤ 500
# right = 130                         # 整段不写时按「边宽 + 5 DIP」排
# bottom = 14
# left = 55

[candidate_window.outer_insets_dip]  # 卡片四边之外要预留的透明空白（给卡片外的挂件用）
# top = 87                           # 可选，缺省 0；四边都 ≤ 500
# right = 16
# bottom = 4
# left = 0

[[candidate_window.decorations]]     # 卡片外的自由挂件，数组表：想要几个就写几段，最多 32 层
image = "assets/char.png"            # 必填，包内相对路径，只能是 .png / .apng / .gif / .webp
anchor = "right"                     # 可选，默认 right；九个锚点见下
width_dip = 149                      # 必填，> 0 且 ≤ 2000
height_dip = 161                     # 必填，> 0 且 ≤ 2000
# offset_x_dip = 10                  # 可选，默认 0；正数向右，范围 -2000~2000
# offset_y_dip = -15                 # 可选，默认 0；正数向下，范围 -2000~2000
# z_index = 3                        # 可选，默认 2；面板自身相当于 1，小于 1 画在面板之下
```

几条语义：

- **九宫格切片**：`slice_dip` 的四条线把图切成九块，四角原样、四边单向拉伸、中心双向拉伸。顺序是「上 右 下 左」，给 1 个值表示四边同值，给 2 个值表示「纵向（上/下）与横向（右/左）」。单位是**源图像素**（96 DPI 下 1 源像素 = 1 DIP）。
- **图里画死的装饰要落在可拉伸区之外**：`stretch_dip` 比 `slice_dip` 直白——它是「可以随意拉伸的区域」。右下角画了一条帆船，就把右侧切片放到船身左边，否则船会被横着拉长。
- **`fill = false` 会连中心区一起不画**（露出 `surface` 底色）；`fill = true`（默认）时中心区也按九宫格绘制。
- **`width_dip` 决定内容盒内缩量**，也是贴在屏上的边框厚度：切得越宽，内容盒收得越多（所以它要和贴图里的边框厚度对齐）。`width_dip` 不写就取切片的值当 DIP，给 2 倍图时写成切片的一半，200% 缩放下逐像素清晰、100% 下是缩小一半的同一张图。
- **有面板图时，卡片自己的底色、描边、圆角和阴影都让给贴图**（写了 `shadow` 也不画、`background` 背景图也不画），真正做成「面板即贴图」。
- **`light_source` 给浅色主题换一张面板图**：切片、边宽、`fill` 与 `source` 共用，所以两张图要按同一套几何画；不写时深浅主题都用 `source`。
- **`content_insets_dip` 从面板外缘量起**：某一边小于九宫格该边的边宽（`width_dip`）时按边宽算，文字不会压在边框上；整段不写时是「边宽 + 5 DIP」。
- **挂件的锚点**：`top-left` / `top-right` / `bottom-left` / `bottom-right` / `left` / `right` / `top` / `bottom` / `center`，默认 `right`（卡片右侧垂直居中）。`offset_x_dip` / `offset_y_dip` 永远正数向右、向下，范围 -2000~2000。
- **挂件必须配 `outer_insets_dip`**：窗口按卡片大小开，不声明外留白，挂到卡片外面的立绘会被窗口边界裁掉；挂在卡片内的挂件不需要它。
- **挂件不吃点击**，只作装饰，也不参与布局。`z_index` 是 -1000~1000 的整数，默认 2；**面板自身相当于 1，所以 `z_index` 小于 1 的挂件画在面板之下**（只有伸出面板的部分看得见），其余画在面板与文字之上；同层按 `z_index` 从小到大、相同时按书写顺序叠放。
- v1 的 `[candidate_window.decoration]`（单数、顶部装饰图）与 v2 的 `[[candidate_window.decorations]]`（复数、卡片外挂件）是两套东西，可以同时用。
- **`background.image` 和 `border_image` 是二选一**：写了面板图就不再画背景图（两者在同一处绘制），卡片底色、描边、圆角也一并让给贴图。要卡内底图就别写面板图。

**`canvas` 已经帮你做好了透明面板、无描边、直角、默认没有阴影**：想额外保险，可以在 `[candidate.dark]` / `[candidate.light]` 把 `surface` 给透明色、`corner_radius_dip = 0`、`border_width_dip = 0`；不想要预览里的投影，整段不写 `shadow` 即可（`canvas` 只在写了 `soft` / `strong` 时才画阴影）。

## 4. 字段硬性规则（Server 会逐条拒绝，写错直接被忽略）

| 规则 | 违反后的报错 |
|---|---|
| `schema_version` 必须是**数字** `1` 或 `2`（字符串 `"1"` 和浮点 `1.0` 都不行） | 仅支持 schema_version 1 或 2 |
| `id` / `name` / `version` / `base` 必填且是字符串且非空，`id` 必须等于目录名 | manifest 的基本信息无效 |
| `base` 必须是六个内置名、六个共享基底（`system` / `shuishan` / `light` / `paper` / `night` / `ink`）或 `canvas` 之一 | manifest 的基本信息无效 |
| `schema_version = 1` 却写 `base = "canvas"` | base = "canvas" 只能用于 schema_version = 2 的皮肤 |
| `author` / `description` 给了就必须是不超长的字符串 | manifest 的基本信息无效 |
| `[supports]` 必须存在，`layouts` ⊆ {horizontal, vertical}、`themes` ⊆ {dark, light}，非空、无重复 | supports.layouts 或 supports.themes 无效 |
| `[candidate_window]` 必须存在（可以只有 `min_width_dip = 0`） | 缺少 candidate_window |
| `min_width_dip` ∈ 0~1000，数字类型 | candidate_window.min_width_dip 超出范围 |
| `corner_radius_dip` 写了就必须是 0~32 的数字 | candidate_window.corner_radius_dip 超出范围 |
| `border_width_dip` 写了就必须是 0~4 的数字 | candidate_window.border_width_dip 超出范围 |
| `item_corner_radius_dip` 写了就必须是 0~16 的数字 | candidate_window.item_corner_radius_dip 超出范围 |
| `shadow` 写了只能是 none / soft / strong | candidate_window.shadow 只能是 none、soft 或 strong |
| `backdrop` 写了只能是 none / acrylic / mica | candidate_window.backdrop 只能是 none、acrylic 或 mica |
| `font_family` 写了就必须是 ≤64 字节的非空字符串，且不含引号、反斜杠、逗号、分号、尖括号、花括号、反引号和控制字符（**可以含汉字**） | candidate_window.font_family 无效 |
| `page_arrows` 写了就必须是布尔（`1`、`"yes"` 都非法） | candidate_window.page_arrows 必须是 true 或 false |
| `fit_content` 写了就必须是布尔 | candidate_window.fit_content 必须是 true 或 false |
| `[candidate_window.decoration]` **可选**；一旦出现就**必须**同时有 `image` 和 `top_inset_dip`、`width_dip`，且 `align` 只能是 left / center / right | candidate_window.decoration 无效 |
| `top_inset_dip` ∈ (0, 500]、`width_dip` ∈ (0, 1000]，**两个都必须 > 0** | candidate_window.decoration 尺寸无效 |
| `decoration.image` 指向的文件必须真实存在 | 找不到 candidate_window.decoration.image 文件 |
| `[candidate_window.background]` **可选**；一旦出现就**必须**有 `image`，`fit` 只能是 cover / contain / stretch，`opacity` 只能是 0~1 的数字 | candidate_window.background 无效 / candidate_window.background.opacity 超出范围 |
| `background.image` 指向的文件必须真实存在 | 找不到 candidate_window.background.image 文件 |
| 21 个配色键给了必须是 ≤80 字节的字符串，且字符集只放行字母数字与 `# ( ) , . %` 空格 `-` `/` | candidate 配色无效 |
| `show_selected_bar` 给了就必须是布尔 | candidate 配色无效 |
| `translation_pos` / `translation_separator` / `selected_translation_pos` / `selected_translation_separator` 给了同样要过颜色白名单；不写则与 `translation` 同色 | candidate 配色无效 |
| `backdrop_opacity` / `backdrop_luminosity` 给了必须是 0~1 的**数字**（不是颜色） | candidate 配色无效 |
| `[candidate.dark.menu]` / `[candidate.light.menu]` 给了必须是表，里面的 4 个键同配色规则 | candidate 配色无效 |
| `[toolbar]` 给了必须是表，`[toolbar.dark]` / `[toolbar.light]` 给了必须是表，键集同配色规则 | toolbar 配色无效 |
| `[toolbar] corner_radius_dip` 写了必须是 0~32 | toolbar.corner_radius_dip 超出范围 |
| 目录名不合法 / 与内置名或 `default` 同名 | 目录名不是有效的外部皮肤 ID |
| 未知字段（含已废弃的 `preview` / `toolbar_stylesheet`、以及 `[license]`） | 静默忽略，不报错也不生效 |
| **v2**：`schema_version = 2` 而 `base` 不是 `canvas` | 不报错：按 v1 加载，v2 字段全部忽略，设置页诊断里多一条说明 |
| **v2**：`[candidate_window.border_image]` 一旦出现就必须有 `source`（文件要存在、扩展名只能是 .png / .apng / .gif / .webp） | candidate_window.border_image.source 无效（需为 .png、.apng、.gif 或 .webp） |
| **v2**：`light_source` 同规则，格式不对或不在白名单同样拒 | candidate_window.border_image.light_source 无效（需为 .png、.apng、.gif 或 .webp） |
| **v2**：`slice_dip` 必填，只能是 1 / 2 / 4 个 0~500 的数值 | candidate_window.border_image.slice_dip 必须是 1、2 或 4 个 0–500 的数值 |
| **v2**：`stretch_dip` / `width_dip` 写了就必须是 1 / 2 / 4 个 0~500 的数值（不是数组、长度不对、越界都报错） | candidate_window.border_image.stretch_dip 必须是 1、2 或 4 个 0–500 的数值 / candidate_window.border_image.width_dip 必须是 1、2 或 4 个 0–500 的数值 |
| **v2**：`fill` 写了必须是布尔 | candidate_window.border_image.fill 必须是 true 或 false |
| **v2**：`border_image.source` / `light_source` 指向的文件必须真实存在 | 找不到 candidate_window.border_image.source 文件 / 找不到 candidate_window.border_image.light_source 文件 |
| **v2**：`[candidate_window.content_insets_dip]` 必须是表，四边各自 0~上限（top / bottom ≤ 200，left / right ≤ 500），缺的边按 0 | candidate_window.content_insets_dip 必须是表 / candidate_window.content_insets_dip 数值超出范围 |
| **v2**：`line_gap_dip` 必须是 0~100 的数字 | candidate_window.line_gap_dip 超出范围 |
| **v2**：`[candidate_window.outer_insets_dip]` 必须是表，四边各自 ≤ 500 | candidate_window.outer_insets_dip 必须是表 / candidate_window.outer_insets_dip 数值超出范围 |
| **v2**：`[[candidate_window.decorations]]` 必须是数组，最多 32 层 | candidate_window.decorations 必须是数组 / candidate_window.decorations 最多 32 层 |
| **v2**：每项要有 `image`（文件要存在、扩展名只能在白名单里） | candidate_window.decorations.image 无效（需为 .png、.apng、.gif 或 .webp） |
| **v2**：`anchor` 只能是九个锚点之一 | candidate_window.decorations.anchor 无效 |
| **v2**：`width_dip` 与 `height_dip` 都要 > 0 且 ≤ 2000 | candidate_window.decorations 的 width_dip 与 height_dip 必须大于 0 |
| **v2**：`offset_x_dip` / `offset_y_dip` 写了必须在 -2000~2000 之间 | candidate_window.decorations 的 offset_x_dip / offset_y_dip 必须在 -2000–2000 之间 |
| **v2**：`z_index` 写了必须是 -1000~1000 的整数 | candidate_window.decorations.z_index 必须是 -1000–1000 的整数 |
| **v2**：`decorations[].image` 指向的文件必须真实存在 | 找不到 candidate_window.decorations.image 文件 |
| **v2 字段写在没配 `canvas` 的皮肤里** | 静默忽略，不报错也不生效 |

长度上限是 **UTF-8 字节数**（中文一个字 3 字节），不是字符数。

**颜色格式**：`#rgb`、`#rgba`、`#rrggbb`、`#rrggbbaa`、`rgb(1,2,3)`、`rgba(1,2,3,.5)`、`transparent`。不透明度在**末尾**（`#RRGGBBAA`），不是 Windows 常见的 `#AARRGGBB`。十六进制大小写均可但**必须带 `#`**。

非标准写法分两种。含**非 ASCII 字符**（`绿色`）或白名单外符号（`;`、`{}`、引号）的**会被 Server 直接拒收整个包**——颜色值的字符集是纯 ASCII 白名单。`lightblue`、`hsl(...)` 这类纯 ASCII 写法能过解析、包也能装，但渲染认不出来，会静默退回默认色（`check_skin.py` 会为此报警告）。想画得出来，就老老实实写十六进制。

## 5. 图片

| | 装饰图 `decoration` | 背景图 `background` |
|---|---|---|
| 位置 | 卡片**上方**一条独立区域，底边贴卡片顶边、不重叠 | 铺在卡片**里面**，底色之上、候选文字之下，按外框圆角裁剪 |
| 贴哪边 | `align`：left / center / right（默认 right） | 永远居中，靠 `fit` 决定怎么缩放 |
| 尺寸 | `top_inset_dip` × `width_dip` 的盒子，图片在盒内 `contain` 等比居中 | 由卡片大小决定，`fit` 取 cover（填满裁切）/ contain（完整显示）/ stretch（拉变形） |
| 压暗 | — | `opacity`：0.35 = 图叠在底色上留 35% 强度。它是往**当前主题的 `surface`** 混，不是往黑混；图自身带 alpha 时保持 1.0 才对，调小只会把它压掉 |

共同规则：

- **两张图都只有一份，不分明暗主题**（它们挂在 `[candidate_window]` 下，不在 `[candidate.dark]` / `[candidate.light]` 里）。所以一张图必须在两套主题下都成立，最稳的做法是只放「中性纹理 / 高光」——图自身带 alpha，颜色交给各主题的 `surface`；想深色下更亮、浅色下更淡只能靠 `opacity` 折中。
- 尺寸单位是 **DIP**（逻辑像素，随 DPI 缩放）。
- **格式优先 PNG**（含透明）。图片靠系统图片解码器加载，PNG / JPEG / BMP / GIF / WebP 一般都能用，SVG 不支持；装了不认识的解码器或文件损坏就会画不出来。v2 的面板图与挂件另有扩展名白名单（见下）。
- 装饰图的**宽高比要和 `width_dip` / `top_inset_dip` 对得上**，否则盒内留白。
- 有装饰图时，候选框最小宽度会自动取 `max(160, min_width_dip, width_dip)`；`fit_content = true` 时那个 160 不再垫（按 0 算）。装饰图不会跑出卡片。

### v2 的图片

- **九宫格面板图**（`border_image.source` / `light_source`）：切成九块拉伸，所以四条切片线要画在纯纹理处；一般是一张大图（如 400×300），四角是完整的花纹/圆角。扩展名只能是 `.png` / `.apng` / `.gif` / `.webp`。
- **卡片外挂件**（`decorations[].image`）：扩展名同上，盒子由 `width_dip` / `height_dip` 给出。图片在框内 **contain 等比缩放、居中**，所以**盒子最好与图片宽高比一致**，比例差得多时四周会留白。
- **动图**：v2 皮肤里的图片可以是动图——APNG、GIF，以及系统解码器能逐帧读出的动画 WebP，**原生播放，不用额外开关**。帧时长按浏览器规则取（分母为 0 按 100 算，10 ms 及以下按 100 ms），循环次数按文件里的设置，播完停在最后一帧。动画从候选窗出现时开始，同一次显示里打字不会让它重头开始；候选窗隐藏或换皮肤后，下一次显示从第一帧开始。
- **动图的边界**：系统关掉「动画效果」（设置 → 辅助功能 → 视觉效果 → 动画效果）时只显示静态图（APNG 的默认图、GIF 首帧）；一张动图超过 **1024 帧**或解码后超过 **64 MB**、文件损坏或不合规范时也只显示第一帧；所有动图的帧合计受 **64 MB 显存预算**约束。
- **v1 皮肤里的图片始终是静态首帧**，动图只在 `schema_version = 2` 且 `base = "canvas"` 的皮肤里播放。
- 面板图也能放动图，但一般建议用静态图，把动画留给挂件。

## 6. 生成 → 校验 → 安装

### 校验

用随本 skill 提供的校验脚本 `scripts/check_skin.py`（路径相对本 skill 根目录），规则与 Server 的解析器逐条一致，错误文案也一样，方便和设置页对照。v1 与 v2 都校验：格式错误报错，其它问题以警告给出。

```powershell
python scripts/check_skin.py <皮肤包目录>   # 单个包
python scripts/check_skin.py <skins 根目录>  # 一次校验多个子目录（自动跳过 default 与 *.bak）
```

需要 Python 3.11+（只用标准库 `tomllib`）。没有 python 就 `uv run`。**退出码 0 才算通过**；脚本里的「错误」= Server 会拒绝这个包，「警告」= 能装但可能不符合预期（比如配色没写全、颜色格式不认识、写了已废弃的字段、base 无外框却只改线宽、写了 `schema_version = 2` 却没配 `base = "canvas"`、固定明暗的基底把 `themes` 收窄、动图超过 64 MB）。

### 安装

**🛑 STOP · 安装前**：复制进 `skins` 是改用户本机目录，动手前把「皮肤 ID + 显示名 + 目标路径」展示给用户，用户说装再装。

1. 皮肤目录**以设置页显示的为准**：设置 → 皮肤 → 外部皮肤区域，那行灰色路径写着真实位置（数据目录安装时可以改到别的盘）。默认是 `%LOCALAPPDATA%\metasequoiaime\skins`。
2. 把整个 `my-skin/` 文件夹复制进去，**不要**把 `skin.toml` 直接丢进 `skins\`，也不要套一层 zip。「打开目录」按钮能直接打开这个目录，省得用户手敲路径。
3. 让用户：设置 → 皮肤 → **刷新皮肤** → 找到自己的皮肤 → 打开开关。列表里能实时预览（横排 / 竖排 / 工具栏三张，另有「预览浅色」按钮）。

**内置皮肤的开关**（翻页箭头、`fit_content`）也能改，但不走这套流程：它是 `<skins 目录>\default\<内置名>\skin.toml` 里的 `[candidate_window] page_arrows` 与 `fit_content`，改完在设置页点「刷新皮肤」。只有 `id`、`name`、`schema_version`、`page_arrows`、`fit_content` 会被读，其余字段写了不生效。同理，外部皮肤不写这两个开关时沿用它 `base` 对应的这份清单（`canvas` 与共享基底取 fluent 的）。

### 改完没效果？

- **点「刷新皮肤」就是全量重载**：它会让 Server 重新读取 `skin.toml` 和皮肤目录里的图片、让候选窗按新清单重载，**不需要重启输入法服务**。改了图片、改了圆角、改了工具栏配色、改了 `font_family`、改了 `backdrop`，点一次就生效。
- 设置页底部出现「已忽略 N 个无效皮肤目录」展开就能看到被拒原因，和 `check_skin.py` 的错误文案一致。

## 7. 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| 设置页根本不显示这个皮肤 | 目录放错层级 / 目录里没有 `skin.toml` / `id` 与目录名不一致 / 目录名是 `default` 或 `.bak` 结尾 | 目录名 = `id`，`skin.toml` 在目录第一层 |
| 显示「缺少 candidate_window」 | manifest 没写 `[candidate_window]` 表 | 哪怕只写 `min_width_dip = 0` 也要有这张表 |
| 显示「目录名不是有效的外部皮肤 ID」 | 目录名含大写、空格、中文，或与内置皮肤/`default` 同名 | 改成 `小写字母数字.-_` |
| 显示「candidate 配色无效」，但看着没写错 | 颜色值里有中文等非 ASCII 字符，或 `;`、`{}`、引号之类白名单外符号 | 全改成 `#rrggbb` / `#rrggbbaa` / `rgb()` / `rgba()` |
| 显示「candidate_window.backdrop 只能是 none、acrylic 或 mica」 | 写了别的材质名，或写成了布尔 | 三选一；不想要材质就把这行删掉 |
| 装饰图/背景图整段被拒 | 写了 `[candidate_window.decoration]` 却漏了 `image`，或两个尺寸没都给 | 表要么完整给，要么整段删掉；两个尺寸必须都 > 0 |
| 显示「candidate_window.page_arrows 必须是 true 或 false」/「fit_content 必须是 true 或 false」 | 写了 `1`、`"yes"` 之类 | 只能是 TOML 的 `true` / `false` |
| 显示「找不到 …image 文件」 | 路径写错、图片没跟着复制、或用了中文/大写以外的非法字符 | 用 `assets/xxx.png` 这种纯 ASCII 相对路径 |
| 显示「candidate_window.border_image.source 无效（需为 .png、.apng、.gif 或 .webp）」 | v2 的面板图与挂件只认这四种扩展名，SVG、JPG 会被直接拒 | 换成 PNG；要动图就用 `.apng` / `.gif` / 动画 `.webp` |
| 列表里有，但标了「当前布局或明暗模式不受支持」 | `supports` 没覆盖当前布局或明暗；或 `base` 是固定明暗的共享基底，声明里没有那一侧（被收窄掉了） | `layouts` 和 `themes` 四项全选；固定明暗基底的收窄规则见 §1 |
| 切过去了但颜色还是老样子 | 键名拼错、颜色不是合法 CSS 颜色、或只改了 `dark` 而系统是浅色 | 用 `check_skin.py`；两组配色都写；确认系统/候选窗主题 |
| 候选文字颜色怎么改都不变 | 设置页的「候选文字颜色」压过了 `text` / `candidate_text` / `preedit_text` | 让用户在设置页改，或提示这层优先级 |
| 翻译的词性/分隔符颜色改了没反应 | 写了 `translation`，解析时会先把词性/分隔符拉成同色，再轮到你的细分键 | 显式写 `translation_pos` / `translation_separator` |
| 选中行文字和普通候选一个色了 | 只写了 `candidate_text`，没写 `selected_text`（见 §0 规则 4） | 补 `selected_text` / `selected_number` |
| 高亮色和设置页预览不一样 | 没写全配色键，没写的走 `base` 的 D2D 令牌，而 `base` 自己还有一套 | 配色键全写 |
| 圆角改了没反应 | `corner_radius_dip` 超过 32，或写成了字符串 | 只接受 0~32 的数字 |
| `border_width_dip` 写了但看不到框 | `border_width_dip` 只管线宽，颜色取 `border`；`base = willow_green` / `autumn_osmanthus` 的边框色是全透明 | 同时在 `[candidate.*]` 给 `border` 一个非透明色，或换 base |
| 字体写了没变化 | `font_family` 只排在用户字体前面，缺字时回落用户字体；**字号不由皮肤决定** | 换个含目标汉字的字体名；字号去设置页调 |
| 莫名其妙多了翻页箭头 | `base = microsoft`，而 `microsoft` 出厂 `page_arrows = true` | 显式写 `page_arrows = false` |
| 翻页箭头不出现 | 写了 `page_arrows` 但 base 的默认清单/出厂值是关的且你的键没生效 | 确认写的是 `[candidate_window]` 里的 `page_arrows = true` |
| 卡片总是被最长那行撑宽 | `fit_content` 没写（出厂默认关，还垫 160 DIP 的出厂最小宽度） | 在 `[candidate_window]` 写 `fit_content = true`；嫌太窄再用 `min_width_dip` 兜底 |
| 背景图看不见 | `opacity` 太小，或图比 `surface` 还暗 | 先把 `opacity` 提到 0.5 以上看效果 |
| 装饰图和卡片挤在一起 | 装饰图 `width_dip` 太宽，卡片被迫撑宽 | 减小 `width_dip`，或提高 `min_width_dip` 让卡片稳定 |
| 写了 `toolbar.css` 没反应 | 外部皮肤已经不支持任何 CSS，工具栏只认 `[toolbar]` 表 | 把样式翻译成 `[toolbar.dark]` / `[toolbar.light]` 的颜色键 |
| 工具栏悬停色预览不出来 | 设置页预览不模拟悬停（预览宿主不吃指针事件） | 属正常，值本身是生效的 |
| 颜色写了 `rgba(0,0,0,0)` 之类看不见 | 透明度 0 | 脚本会警告 |
| 写了 `border_image` / `decorations` 之类完全没反应 | `schema_version` 不是 `2`，或者写了 `2` 但 `base` 不是 `canvas`（见 §0 规则 6） | `schema_version = 2` 和 `base = "canvas"` 一起写 |
| 显示「base = "canvas" 只能用于 schema_version = 2 的皮肤」 | v1 皮肤用了 `canvas` | 要么改成 `schema_version = 2` 并补上面板图，要么换回内置基底 |
| 设置页诊断里多一条「schema_version = 2 需要 base = "canvas"」 | v2 字段被整段忽略，皮肤是按 v1 加载的 | 把 `base` 改成 `canvas` |
| v2 候选框里只有悬空文字、没有面板 | `canvas` 只是透明地基，没写 `[candidate_window.border_image]` | 补一张九宫格面板图 |
| 亚克力 / 云母没生效，卡片仍是不透明 | 系统关了「透明效果」（设置 → 个性化 → 颜色）；系统太老（低于 Windows 10 1903，云母还要 Windows 11）；或同时写了 `border_image`（有面板图就不垫材质） | 让用户打开透明效果 / 升级系统；只能留一种时只留一个 |
| 面板贴图被横着拉长 | 图里画死的装饰落进了可拉伸区 | 用 `stretch_dip` 把可拉伸区收窄到纯纹理处 |
| 候选文字压在贴图花纹上 / 离边框太近 | 没写 `content_insets_dip`，内容按「边宽 + 5 DIP」排 | 按面板外缘给四边 `content_insets_dip` |
| 浅色主题面板还是深色的 | 只写了 `source`，没写 `light_source`；或两张图的切片/边宽不一致 | 补 `light_source`，并让它和 `source` 用同一套几何 |
| 挂件被窗口边界切掉 | 没写 `outer_insets_dip`，或数值小于挂件超出卡片的距离 | 给超出那几边补 `outer_insets_dip` |
| 挂件盖住了候选文字 | 默认 `z_index = 2` 在面板与文字之上 | 调 `offset_x_dip` / `offset_y_dip` 挪开，或把 `z_index` 写到 1 以下让它落到面板后面（只有伸出面板的部分看得见） |
| 挂件图和框对不上、四周留白 | 图片在框内 `contain` 等比缩放、居中，`width_dip` / `height_dip` 与图片比例不一致就会留白 | 按图片宽高比给两个尺寸 |
| 挂件动图不动 | v1 皮肤里的图片从不播动画；系统关了「动画效果」（设置 → 辅助功能 → 视觉效果）；或这张图超过 1024 帧 / 解码后超过 64 MB / 文件损坏 | 确认是 `schema_version = 2` + `base = "canvas"` 的皮肤；其余属于系统设置或文件本身的问题 |
| 写了 `[[decorations]]` 却没有挂件效果 | 挂件不参与布局：伸到卡片外的部分没留白就被裁掉，`z_index < 1` 的只在面板外露出来；图片路径也可能写错 | 补 `outer_insets_dip`；用 `check_skin.py` 确认图片存在 |

## 8. 交付与分享

**🔴 CHECKPOINT · 交付前**：核对三件必说项已写进回复——**放几级目录**、**设置页怎么启用**、**改完点「刷新皮肤」而不是重启服务**。

- 交付物是一个文件夹，`zip` 打包即可分享；对方解压进自己的 `skins` 目录、点「刷新皮肤」就能用。
- 附上 `check_skin.py` 的输出，省得对方装上才发现被拒。
- 告诉对方三件事：**要放几级目录**（`skins\皮肤名\skin.toml`）、**怎么在设置页启用**（设置 → 皮肤 → 刷新皮肤 → 打开开关）、**改完点刷新**。
- 提醒对方：**别把 `.css` 塞进包里**，那套机制已经没了。
- v2 皮肤（贴图面板 / 卡外挂件）要额外说清：`schema_version = 2` **必须配 `base = "canvas"`**（见 §0 规则 6），面板长什么样全靠 `border_image` 与挂件；写了 `2` 却用别的基底会按 v1 加载、v2 字段全部忽略。
- 用了 `backdrop` 就说清它依赖系统的透明效果与 Windows 版本，关掉透明效果或不支持时会退回不透明底色；皮肤同时写了 `border_image` 时也不生效。
- 用别人的图之前先在 `[license]` 里写清 `assets` 的出处与授权；来源说不清就写 `UNVERIFIED` 并说明仅供演示。
