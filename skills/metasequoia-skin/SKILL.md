---
name: metasequoia-skin
description: 生成、校验、安装水杉输入法（metasequoia ime）的候选窗皮肤包。用户描述想要的观感（配色、圆角、阴影、背景图、装饰图、翻页箭头、工具栏配色），或需要手写/排查 skin.toml，或皮肤装上没反应、设置页报「缺少 candidate_window」「candidate 配色无效」「找不到 image 文件」时使用。产出 skin.toml + assets，并用 check_skin.py 离线校验。
compatibility: opencode
metadata:
  product: metasequoia-ime
  language: zh-CN
---

# 水杉输入法皮肤（metasequoia-skin）

给非开发者用的皮肤生成流程：**用户描述想要的样子 → 你生成一个皮肤包 → 校验 → 装进皮肤目录 → 用户在设置页点开关**。

用户不需要懂代码，你也不该让他读代码。整个过程他只需要回答几个关于观感的问题，最后在设置页点两下。

> 本 skill 的字段、范围、报错文案逐条对齐 Server 的解析器
> `server/src/skin/candidate_skin_catalog.cpp`（`CandidateSkinCatalog::Load`）。
> 字段清单另见 `examples/skin-examples/schema/README.md`，带注释的完整样例见
> `examples/skin-examples/skins/niya-demo/skin.toml`。
> **源码变了就回来改这份文档和 `scripts/check_skin.py`**，别让两套规则分叉。

## 0. 先确定边界：能改什么，不能改什么

外部皮肤**只有 `skin.toml` 一个文件是活的**，没有别的。**开工前先看这张表**，用户要的东西不在里面就直接说做不到，别生成一个装上没反应的包。

| 能改 | 怎么改 | 两个后端 |
|---|---|---|
| 候选窗配色：基础 8 色 + 细分配色 9 项 + 选中竖条开关 | `[candidate.dark]` / `[candidate.light]` 的 17 个颜色键 + `show_selected_bar` | 都生效 |
| 候选窗右键菜单配色（底色、边框、文字、悬停） | `[candidate.dark.menu]` / `[candidate.light.menu]` 的 4 个键 | 都生效 |
| 候选框外框圆角 / 线宽 | `candidate_window.corner_radius_dip`（0~32）、`border_width_dip`（0~4） | 都生效 |
| 候选项高亮圆角 | `candidate_window.item_corner_radius_dip`（0~16） | 都生效 |
| 候选框卡片阴影 | `candidate_window.shadow`（`none` / `soft` / `strong`） | 都生效 |
| 候选字体**族**（不是字号） | `candidate_window.font_family`（≤64 字节） | 都生效 |
| 候选框最小宽度 | `candidate_window.min_width_dip`（0~1000） | 都生效 |
| 候选框卡片内的背景图 | `candidate_window.background`（`image` / `fit` / `opacity`） | 都生效 |
| 候选框卡片上方的装饰图 | `candidate_window.decoration`（`image` / `top_inset_dip` / `width_dip` / `align`） | 都生效 |
| 候选框里的翻页箭头 | `candidate_window.page_arrows`（`true` / `false`） | 都生效 |
| 悬浮工具栏配色（底色、边框、拖动条、分隔线、图标、悬停）与圆角 | `[toolbar]` / `[toolbar.dark]` / `[toolbar.light]` | 都生效 |
| 底子用哪套内置皮肤 | `base` | — |

| 做不到 | 说明 |
|---|---|
| 自定义 CSS 或 HTML / JavaScript | 外部皮肤**不能**提供任何 CSS 或脚本。写 `.css`、`.js` 放进包里不会有任何效果 |
| 字号、行内边距、行距、候选框留白 | 这些不是皮肤参数，跟 `base` 走；字号由设置页的「候选字号」决定 |
| 工具栏尺寸、加按钮、改图标字形 | `[toolbar]` 只能改 6 个颜色 + 圆角 |
| 菜单里加自定义条目 | 右键菜单的条目是输入法内置的，皮肤只能改配色 |
| 动画、毛玻璃、透明窗口、全屏背景 | 不在参数里 |
| 改内置皮肤（fluent/wechat/…）本身的外观 | 那是水杉仓库的源码，不是皮肤包。内置皮肤只有 `page_arrows` 一个开关可改，改法见 §5 末尾 |

**两个后端**：默认是原生 Direct2D 后端，`appearance.ui_backend=webview2` 才走 WebView。表里写「都生效」的项两边都实现；配色是同一份 manifest 生成的 D2D 令牌（`window/candidate_presenter.cpp`）和 CSS（`webview2/windows_webview2_skin.cpp`），设置页预览又抄了一遍同样的规则。

### 三条容易踩的一致性规则

1. **同一个键没写时，两个后端的取值来源不同**：原生后端走 `base` 皮肤的 D2D 令牌，WebView2 后端走 `base` 皮肤的 CSS。两边对同一个 `base` 大体对齐，但历史遗留仍有细微差别。**所以 `[candidate.dark]` 和 `[candidate.light]` 都要把配色键写全**，这样任何后端、任何 `base` 下都只听你的。

2. **设置页的「候选文字颜色」压过 `text` / `candidate_text` / `preedit_text`**（两个后端都是）。用户在设置里动过候选文字颜色时，这三个键不生效——所以别靠它们定候选文字的主色。

3. **十六进制必须带 `#`**。原生后端不带也能认，WebView2 按 CSS 解析会把 `e8a` 当无效值，两边就画出不同结果。

**已经被移除的老字段**（写了不报错，但**完全无效**，别再生成）：

| 老字段 | 现状 |
|---|---|
| 根级 `preview = "preview.png"` | 已移除。装饰图改由 `candidate_window.decoration.image` 指定 |
| 根级 `toolbar_stylesheet = "toolbar.css"` | 已移除。工具栏改由 `[toolbar]` 系列表配置，不做任何兼容 |
| `[candidate_window.decoration]` 里两个尺寸都填 0 | 现在是**非法**，会被拒（见 §4） |

## 1. 先问用户什么

一轮问完，别挤牙膏：

1. **想要什么观感**——给几个具体的：参考色、参考图、"像微信"、"性冷淡灰"、"赛博霓虹"、"像微软拼音"。用户说不出就给选项让他挑。
2. **明暗**：默认两套都做（推荐），除非用户明确只要一套。
3. **要不要图片**：候选框**里面**铺一张底图（`background`），还是卡片**上方**放一张装饰图（`decoration`），还是都要。要的话让他给图。
4. **要不要改悬浮工具栏**：`[toolbar]` 能改配色和圆角，不改尺寸、不加按钮。
5. **要不要翻页箭头**：写了 `page_arrows`，候选框里会出现一小列/一小行「‹ ›」。不说就跟着 `base` 走。
6. **横排还是竖排**：默认 `supports` 全选，两个布局都支持。

`base` 不用问用户，按观感你来定：

| base | 观感 | 圆角 / 线宽 / 高亮圆角 | 选中形态 | accent（dark / light） |
|---|---|---|---|---|
| `fluent` | 默认，Windows 11 味 | 6 / 1.5 / 4 | 左侧竖色条 | `#6B69D6` / `#6B69D6` |
| `wechat` | 微信绿 `#07C160` | 5 / 1 / 4 | 整行绿底白字，无竖条 | `#07C160` |
| `graphite` | 石墨灰，紧凑平直 | 3 / 1 / 2 | 灰底无竖条 | `#8993A0` / `#5F6B7A` |
| `willow_green` | 杨柳青，无边框、高亮铺满 | 9 / 0 / 0 | 整行整列铺满，无竖条 | `#65C98D` / `#58B980` |
| `autumn_osmanthus` | 秋桂，无边框、橙色高亮内缩 | 10 / 0 / 6 | 内缩橙块，无竖条 | `#F97D0A` / `#E6A817` |
| `microsoft` | 仿微软拼音，紧凑、三角翻页箭头 | 8 / 1 / 4 | 灰块 + 竖条在块内 | `#E183D9` / `#E183D9` |

`base` 决定的是**几何**和**没写到的键的默认值**。你自己写了 `corner_radius_dip`、`item_corner_radius_dip` 和全部配色键之后，`base` 还剩下行距、内边距这类改不了的排版，以及「高亮是铺满还是内缩」这类形态。

**microsoft 唯一自带 `page_arrows = true`**（出厂清单如此），其余五个内置皮肤都是关的。选它做 base 却不写 `page_arrows`，用户就会莫名多出翻页箭头——要么明确写 `page_arrows = false`，要么跟用户确认要这个箭头。

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
base = "fluent"                    # 必填，取上面六个之一

[supports]                         # 必填，建议四项全选
layouts = ["horizontal", "vertical"]
themes = ["dark", "light"]

[candidate_window]                 # 表必须存在（哪怕是空表）
min_width_dip = 320                # 可选，0~1000，0 = 不设
corner_radius_dip = 8              # 可选，0~32；0 = 直角
border_width_dip = 1.5             # 可选，0~4，可小数；0 = 无外框
item_corner_radius_dip = 6         # 可选，0~16；高亮块圆角
shadow = "soft"                    # 可选 none / soft / strong
font_family = "Segoe UI"           # 可选，≤64 字节，只能一个字体名
page_arrows = false                # 可选 true / false；不写则跟 base 的出厂设置

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

[candidate.dark]                   # 17 个颜色键 + show_selected_bar，建议写全
# ── 基础 8 色 ──
accent = "#6B69D6"                 # 强调色：预编辑光标；选中竖条的默认颜色
selected = "#3e3e3eb9"             # 选中行背景
hover = "#414141"                  # 悬停行背景；翻页箭头悬停也用它
surface = "#202020"                # 候选窗背景
border = "#9b9b9b2e"               # 候选窗外框
text = "#e9e8e8"                   # 候选文字（会被设置页「候选文字颜色」覆盖）
number = "#e9e8e89d"               # 序号 1. 2. 3.；翻页箭头也用它
translation = "#e6a817"            # 候选后面的翻译；不写则取文字色降到 62% 不透明
show_selected_bar = true           # 选中行左侧竖色条；false = 关掉

# ── 细分 9 色，不写时按注释回落 ──
candidate_text = "#e9e8e8"         # 普通候选文字 → text
preedit_text = "#e9e8e8"           # 预编辑拼音文字 → text
preedit_caret = "#6B69D6"          # 预编辑光标 → accent
selected_text = "#ffffff"          # 选中候选文字 → base 的选中文字色
selected_number = "#ffffff"        # 选中候选序号 → base 的选中序号色
selected_translation = "#ffd479"   # 选中候选翻译 → translation，再退到选中文字色的 62%
selected_bar = "#6B69D6"           # 选中项左侧竖条 → accent
preedit_background = "#ffffff10"   # 预编辑行底色，圆角同高亮圆角；不写则透明
preedit_divider = "#6B69D6"        # 预编辑行下方 1px 分隔线；不写则没有

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
# handle = "#8E8CD8"               # 左侧拖动条
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

## 4. 字段硬性规则（Server 会逐条拒绝，写错直接被忽略）

| 规则 | 违反后的报错 |
|---|---|
| `schema_version` 必须是**数字** `1`（字符串 `"1"` 和浮点 `1.0` 都不行） | 仅支持 schema_version 1 |
| `id` / `name` / `version` / `base` 必填且是字符串且非空，`id` 必须等于目录名，`base` 必须是六个内置名之一 | manifest 的基本信息无效 |
| `author` / `description` 给了就必须是不超长的字符串 | manifest 的基本信息无效 |
| `[supports]` 必须存在，`layouts` ⊆ {horizontal, vertical}、`themes` ⊆ {dark, light}，非空、无重复 | supports.layouts 或 supports.themes 无效 |
| `[candidate_window]` 必须存在（可以只有 `min_width_dip = 0`） | 缺少 candidate_window |
| `min_width_dip` ∈ 0~1000，数字类型 | candidate_window.min_width_dip 超出范围 |
| `corner_radius_dip` 写了就必须是 0~32 的数字 | candidate_window.corner_radius_dip 超出范围 |
| `border_width_dip` 写了就必须是 0~4 的数字 | candidate_window.border_width_dip 超出范围 |
| `item_corner_radius_dip` 写了就必须是 0~16 的数字 | candidate_window.item_corner_radius_dip 超出范围 |
| `shadow` 写了只能是 none / soft / strong | candidate_window.shadow 只能是 none、soft 或 strong |
| `font_family` 写了就必须是 ≤64 字节的非空字符串，且不含引号、反斜杠、逗号、分号、尖括号、花括号、反引号和控制字符（**可以含汉字**） | candidate_window.font_family 无效 |
| `page_arrows` 写了就必须是布尔（`1`、`"yes"` 都非法） | candidate_window.page_arrows 必须是 true 或 false |
| `[candidate_window.decoration]` **可选**；一旦出现就**必须**同时有 `image` 和 `top_inset_dip`、`width_dip`，且 `align` 只能是 left / center / right | candidate_window.decoration 无效 / 尺寸无效 |
| `top_inset_dip` ∈ (0, 500]、`width_dip` ∈ (0, 1000]，**两个都必须 > 0** | candidate_window.decoration 尺寸无效 |
| `decoration.image` / `background.image` 指向的文件必须真实存在 | 找不到 …image 文件 |
| `[candidate_window.background]` **可选**；一旦出现就**必须**有 `image`，`fit` 只能是 cover / contain / stretch，`opacity` 只能是 0~1 的数字 | candidate_window.background 无效 / opacity 超出范围 |
| 17 个配色键给了必须是 ≤80 字节的字符串，且字符集只放行字母数字与 `# ( ) , . %` 空格 `-` `/` | candidate 配色无效 |
| `show_selected_bar` 给了就必须是布尔 | candidate 配色无效 |
| `[candidate.dark.menu]` / `[candidate.light.menu]` 给了必须是表，里面的 4 个键同配色规则 | candidate 配色无效 |
| `[toolbar]` 给了必须是表，`[toolbar.dark]` / `[toolbar.light]` 给了必须是表，键集同配色规则 | toolbar 配色无效 |
| `[toolbar] corner_radius_dip` 写了必须是 0~32 | toolbar.corner_radius_dip 超出范围 |
| 目录名不合法 / 与内置名或 `default` 同名 | 目录名不是有效的外部皮肤 ID |
| 未知字段（含已废弃的 `preview` / `toolbar_stylesheet`、以及 `[license]`） | 静默忽略，不报错也不生效 |

长度上限是 **UTF-8 字节数**（中文一个字 3 字节），不是字符数。

**颜色格式**：`#rgb`、`#rgba`、`#rrggbb`、`#rrggbbaa`、`rgb(1,2,3)`、`rgba(1,2,3,.5)`、`transparent`。不透明度在**末尾**（`#RRGGBBAA`），不是 Windows 常见的 `#AARRGGBB`。十六进制大小写均可但**必须带 `#`**。

非标准写法（`绿色`、`lightblue`、`hsl(...)`）**会被 Server 直接拒收整个包**——颜色值的字符集是纯 ASCII 白名单，中文和字母单词都过不去。想让原生后端认，就老老实实写十六进制。

## 5. 图片

| | 装饰图 `decoration` | 背景图 `background` |
|---|---|---|
| 位置 | 卡片**上方**一条独立区域，底边贴卡片顶边、不重叠 | 铺在卡片**里面**，底色之上、候选文字之下，按外框圆角裁剪 |
| 贴哪边 | `align`：left / center / right（默认 right） | 永远居中，靠 `fit` 决定怎么缩放 |
| 尺寸 | `top_inset_dip` × `width_dip` 的盒子，图片在盒内 `contain` 等比居中 | 由卡片大小决定，`fit` 取 cover（填满裁切）/ contain（完整显示）/ stretch（拉变形） |
| 压暗 | — | `opacity`：0.35 = 图叠在底色上留 35% 强度 |

共同规则：

- 尺寸单位是 **DIP**（逻辑像素，随 DPI 缩放）。
- **格式优先 PNG**（含透明）。原生后端靠 Windows 图片解码器加载，webp/svg 在部分 Windows 版本上不支持；WebView2 端支持 png/jpg/webp/gif/svg。
- 单文件 **≤ 1500KB** 才会被内联打包，超过就改走虚拟主机加载（能用，但慢且在个别环境下可能被拦），建议压到 1500KB 以内。原生后端没有这个限制。
- 装饰图的**宽高比要和 `width_dip` / `top_inset_dip` 对得上**，否则盒内留白。
- 有装饰图时，候选框最小宽度会自动取 `max(160, min_width_dip, width_dip)`（WebView2 端按 `max(7em, …)`），装饰图不会跑出卡片。

## 6. 生成 → 校验 → 安装

### 校验

用随本 skill 提供的校验脚本 `scripts/check_skin.py`（路径相对本 skill 根目录），规则与 Server 的解析器逐条一致，错误文案也一样，方便和设置页对照：

```powershell
python scripts/check_skin.py <皮肤包目录>   # 单个包
python scripts/check_skin.py <skins 根目录>  # 一次校验多个子目录（自动跳过 default 与 *.bak）
```

需要 Python 3.11+（只用标准库 `tomllib`）。没有 python 就 `uv run`。**退出码 0 才算通过**；脚本里的「错误」= Server 会拒绝这个包，「警告」= 能装但可能不符合预期（比如配色没写全、颜色格式不认识、写了已废弃的字段、base 无外框却只改线宽）。

### 安装

**🛑 STOP · 安装前**：复制进 `skins` 是改用户本机目录，动手前把「皮肤 ID + 显示名 + 目标路径」展示给用户，用户说装再装。

1. 皮肤目录**以设置页显示的为准**：设置 → 皮肤 → 外部皮肤区域，那行灰色路径写着真实位置（数据目录安装时可以改到别的盘）。默认是 `%LOCALAPPDATA%\metasequoiaime\skins`。
2. 把整个 `my-skin/` 文件夹复制进去，**不要**把 `skin.toml` 直接丢进 `skins\`，也不要套一层 zip。「打开目录」按钮能直接打开这个目录，省得用户手敲路径。
3. 让用户：设置 → 皮肤 → **刷新皮肤** → 找到自己的皮肤 → 打开开关。列表里能实时预览（横排 / 竖排 / 工具栏三张，另有「预览浅色」按钮）。

**内置皮肤的翻页箭头开关**也能改，但不走这套流程：它是 `<skins 目录>\default\<内置名>\skin.toml` 里的 `[candidate_window] page_arrows`，改完在设置页点「刷新皮肤」。只有 `id`、`name`、`schema_version`、`page_arrows` 会被读，其余字段写了不生效。同理，外部皮肤不写 `page_arrows` 时沿用它 `base` 对应的这份清单。

### 改完没效果？

- **点「刷新皮肤」就是全量重载**：它会让 Server 重新读一遍 `skin.toml`、重新生成 CSS、让原生后端重读 manifest，**不需要重启输入法服务**。改了图片、改了圆角、改了工具栏配色、改了 `font_family`，点一次就生效。
- 设置页底部出现「已忽略 N 个无效皮肤目录」展开就能看到被拒原因，和 `check_skin.py` 的错误文案一致。

## 7. 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| 设置页根本不显示这个皮肤 | 目录放错层级 / 目录里没有 `skin.toml` / `id` 与目录名不一致 / 目录名是 `default` 或 `.bak` 结尾 | 目录名 = `id`，`skin.toml` 在目录第一层 |
| 显示「缺少 candidate_window」 | manifest 没写 `[candidate_window]` 表 | 哪怕只写 `min_width_dip = 0` 也要有这张表 |
| 显示「目录名不是有效的外部皮肤 ID」 | 目录名含大写、空格、中文，或与内置皮肤/`default` 同名 | 改成 `小写字母数字.-_` |
| 显示「candidate 配色无效」，但看着没写错 | 颜色值里有中文、`lightblue`、`;` 之类过不了 ASCII 白名单的字符 | 全改成 `#rrggbb` / `#rrggbbaa` / `rgb()` / `rgba()` |
| 装饰图/背景图整段被拒 | 写了 `[candidate_window.decoration]` 却漏了 `image`，或两个尺寸没都给 | 表要么完整给，要么整段删掉；两个尺寸必须都 > 0 |
| 显示「candidate_window.page_arrows 必须是 true 或 false」 | 写了 `1`、`"yes"` 之类 | 只能是 TOML 的 `true` / `false` |
| 显示「找不到 …image 文件」 | 路径写错、图片没跟着复制、或用了中文/大写以外的非法字符 | 用 `assets/xxx.png` 这种纯 ASCII 相对路径 |
| 列表里有，但标了「不兼容」 | `supports` 没覆盖当前布局或明暗 | `layouts` 和 `themes` 四项全选 |
| 切过去了但颜色还是老样子 | 键名拼错、颜色不是合法 CSS 颜色、或只改了 `dark` 而系统是浅色 | 用 `check_skin.py`；两组配色都写；确认系统/候选窗主题 |
| 候选文字颜色怎么改都不变 | 设置页的「候选文字颜色」压过了 `text` / `candidate_text` / `preedit_text` | 让用户在设置页改，或提示这层优先级 |
| 高亮色和设置页预览不一样 | 没写全配色键，原生后端走 base 的 D2D 令牌、WebView2 走 base 的 CSS | 配色键全写 |
| 圆角改了没反应 | `corner_radius_dip` 超过 32，或写成了字符串 | 只接受 0~32 的数字 |
| `border_width_dip` 写了但看不到框 | `border_width_dip` 只管线宽，颜色取 `border`；`base = willow_green` / `autumn_osmanthus` 的边框色是全透明 | 同时在 `[candidate.*]` 给 `border` 一个非透明色，或换 base |
| 字体写了没变化 | `font_family` 只排在用户字体前面，缺字时回落用户字体；**字号不由皮肤决定** | 换个含目标汉字的字体名；字号去设置页调 |
| 莫名其妙多了翻页箭头 | `base = microsoft`，而 `microsoft` 出厂 `page_arrows = true` | 显式写 `page_arrows = false` |
| 翻页箭头不出现 | 写了 `page_arrows` 但 base 的默认清单/出厂值是关的且你的键没生效 | 确认写的是 `[candidate_window]` 里的 `page_arrows = true` |
| 背景图看不见 | `opacity` 太小 / 图比 `surface` 还暗 / 图超过 1500KB 走了慢路径 | 先把 `opacity` 提到 0.5 以上看效果 |
| 装饰图和卡片挤在一起 | 装饰图 `width_dip` 太宽，卡片被迫撑宽 | 减小 `width_dip`，或提高 `min_width_dip` 让卡片稳定 |
| 写了 `toolbar.css` 没反应 | 外部皮肤已经不支持任何 CSS，工具栏只认 `[toolbar]` 表 | 把样式翻译成 `[toolbar.dark]` / `[toolbar.light]` 的颜色键 |
| 工具栏悬停色预览不出来 | 设置页预览不模拟悬停（预览宿主不吃指针事件） | 属正常，值本身是生效的 |
| 颜色写了 `rgba(0,0,0,0)` 之类看不见 | 透明度 0 | 脚本会警告 |

## 8. 交付与分享

**🔴 CHECKPOINT · 交付前**：核对三件必说项已写进回复——**放几级目录**、**设置页怎么启用**、**改完点「刷新皮肤」而不是重启服务**。

- 交付物是一个文件夹，`zip` 打包即可分享；对方解压进自己的 `skins` 目录、点「刷新皮肤」就能用。
- 附上 `check_skin.py` 的输出，省得对方装上才发现被拒。
- 告诉对方三件事：**要放几级目录**（`skins\皮肤名\skin.toml`）、**怎么在设置页启用**（设置 → 皮肤 → 刷新皮肤 → 打开开关）、**改完点刷新**。
- 提醒对方：**别把 `.css` 塞进包里**，那套机制已经没了。
- 用别人的图之前先在 `[license]` 里写清 `assets` 的出处与授权；来源说不清就写 `UNVERIFIED` 并说明仅供演示。