---
name: metasequoia-skin
description: 生成、校验、安装水杉输入法（metasequoia ime）的候选窗皮肤包。用户描述想要的观感（配色、圆角、阴影、背景图、装饰图、版式微调、卷轴展开、九宫格贴图面板、卡片外立绘挂件、翻页箭头、工具栏配色或工具栏图片模式），或需要手写/排查 skin.toml，或皮肤装上没反应、设置页报「缺少 candidate_window」「candidate 配色无效」「找不到 image 文件」时使用。产出 skin.toml + assets，并用 check_skin.py 离线校验（支持 schema_version 1 与 2）。
license: MIT
compatibility: opencode
metadata:
  product: metasequoia-ime
  language: zh-CN
---

# 水杉输入法皮肤（metasequoia-skin）

给非开发者用的皮肤生成流程：**用户描述想要的样子 → 你生成一个皮肤包 → 校验 → 装进皮肤目录 → 用户在设置页点开关**。

用户不需要懂代码，你也不该让他读代码。整个过程他只需要回答几个关于观感的问题，最后在设置页点两下。

> **本 skill 的字段与报错以 Server 解析器为准**：`server/src/skin/candidate_skin_catalog.cpp`
> （`CandidateSkinCatalog::Load`），配色回落见 `server/src/window/candidate_skin_palette.cpp`。
> 字段清单另见 `examples/skin-examples/schema/README.md`，带注释的完整样例见
> `examples/skin-examples/skins/niya-demo/skin.toml`，官方全贴图样板见 `skins/green_leaf/skin.toml`。
> **源码变了就回来改这份文档和 `scripts/check_skin.py`**，别让两套规则分叉。
>
> `schema_version` 支持 **1 与 2**：v1 是通用卡片皮肤（配色 + 圆角 + 版式 + 图片）；v2 是以
> `canvas` 为地基的全贴图皮肤，追加九宫格面板、面板内安全内边距、行距、卡外挂件与窗口外留白。
> **v2 字段只在 `schema_version = 2` 且 `base = "canvas"` 时被解析**（见 §0 规则 6）。
> `[animation]` 和装饰图的 `motion` / `motion_period_ms` 是 msime 各平台共用的 v2 键，Windows
> 按静态图显示，不报错也不提示——写了也不会动，别拿它当 Windows 的动图开关。

## 按需读取

主文件只放流程、边界和决策。写具体字段时再打开对应的参考，不要凭记忆：

| 文件 | 什么时候读 |
|---|---|
| [references/schema-v1.md](references/schema-v1.md) | 写 / 改 v1 字段，查某个键的范围、默认值、回落 |
| [references/schema-v2.md](references/schema-v2.md) | 用九宫格面板、面板内边距、行距、卡外挂件、卡外留白 |
| [references/toolbar-image-mode.md](references/toolbar-image-mode.md) | 工具栏整块图片模式：背景图、按钮坐标 / 状态图 / 自动排列 |
| [references/validation.md](references/validation.md) | 被拒，或要查完整硬性规则、报错文案、颜色格式、已移除字段 |
| [references/images.md](references/images.md) | 装饰图 / 背景图 / 面板图 / 挂件 / 动图的格式、尺寸、降级 |
| [references/troubleshooting.md](references/troubleshooting.md) | 装上没反应，或显示不符合预期 |
| [references/templates/skin-v1.toml](references/templates/skin-v1.toml) | 直接复制一份完整 v1 模板 |
| [references/templates/skin-v2.toml](references/templates/skin-v2.toml) | 直接复制一份完整 v2 模板 |
| `scripts/check_skin.py` | 离线校验；规则与 Server 的解析器逐条一致 |

## 0. 先确定边界：能改什么，不能改什么

外部皮肤**只有 `skin.toml` 一个文件是活的**，没有别的。**开工前先看这两张表**，用户要的东西不在里面就直接说做不到，别生成一个装上没反应的包。

| 能改 | 怎么改 |
|---|---|
| 候选窗配色：22 个颜色键 + 选中竖条开关 | `[candidate.dark]` / `[candidate.light]` |
| 候选窗右键菜单 4 色 | `[candidate.*.menu]` |
| 卡片圆角、线宽、高亮圆角、阴影、系统材质、字体族、最小宽度、贴文字收紧 | `[candidate_window]` 的直接键 |
| 版式：内边距、间距、序号大小与间距、选中竖条、高亮贴角 / 整行铺满、预编辑行边距；横竖排可各一套 | `[candidate_window]` 版式键 + `.horizontal` / `.vertical` |
| 翻页箭头、箭头样式与分隔线；横排卷轴展开 | `page_arrows` / `page_arrow_style` / `page_arrow_divider`；`expand_panel` / `expand_rows` |
| 卡内背景图、卡上装饰图、装饰图上叠一个候选词 | `[candidate_window.background]`、`[candidate_window.decoration]` |
| 工具栏配色、圆角、图标悬停圆角（bar 模式） | `[toolbar]` / `[toolbar.dark]` / `[toolbar.light]` |
| 工具栏整块图片模式：背景图、按钮位置 / 尺寸 / 状态图 / 自动排列 | `mode = "image"`、`image*`、`[toolbar.buttons.*]`、`button_defaults`、`button_flow` |
| v2：九宫格面板、面板内安全边距、行距、卡外挂件、卡外留白、动图 | `schema_version = 2` + `base = "canvas"`，见 §4 |
| 底子用哪套基底 | `base` |

| 做不到 | 说明 |
|---|---|
| 自定义 CSS 或 HTML / JavaScript | 外部皮肤**不能**提供任何 CSS 或脚本。写 `.css`、`.js` 放进包里不会有任何效果 |
| 改候选字号 / 预编辑字号 | 字号由设置页决定。皮肤能改的是版式尺寸与装饰图上叠加词的字号，不是候选本体字号 |
| 新增工具栏按钮种类、改内置图标字形 | 按钮种类（中英、全半角、标点、简繁、表情、屏幕键盘、设置）由输入法固定；图片模式只能给这些按钮换图、摆位置、隐藏，不能加新按钮 |
| 菜单里加自定义条目 | 右键菜单的条目是输入法内置的，皮肤只能改配色 |
| 全屏背景、窗口本身的其它透明特效 | 不在参数里。卡片背后的材质只有 `backdrop` 这一种 |
| 改内置皮肤（fluent / wechat / …）本身的外观 | 那是水杉仓库的源码，不是皮肤包。内置皮肤只有 `page_arrows`、`fit_content`、`expand_panel` 三个开关可改，改法见 §5 |

**毛玻璃是可以做的**，走 `candidate_window.backdrop`：`acrylic`（亚克力）/ `mica`（云母）。限制要说清：需要系统开着「透明效果」，关掉或系统太老时退回不透明底色；同一张皮肤写了 `border_image` 时不生效。细节见 [schema-v1.md 的卡片与开关](references/schema-v1.md#卡片与开关)。

**实现只有 Direct2D 一套**：候选窗、悬浮工具栏都由 `msimeui` 用 Direct2D 绘制。皮肤只能声明颜色与图片，没有第二个后端可选；没写的键由 `base` 补齐。

### 六条容易踩的一致性规则

1. **没写的键会走 `base` 的 D2D 令牌**：`base` 的配色与几何先铺底，你的键再逐项覆盖。**所以 `[candidate.dark]` 和 `[candidate.light]` 都要把配色键写全**，这样任何 `base` 下都只听你的。共享基底没写的键走的也是 fluent 的令牌。

2. **设置页的「候选文字颜色」压过 `text` / `candidate_text` / `preedit_text`**：用户在设置里动过候选文字颜色时，这三个键不生效——所以别靠它们定候选文字的主色。

3. **十六进制必须带 `#`**。这是清单格式的约定。渲染器对不带 `#` 的写法有容错（`e8a` 也会被当成 `#ee88aa`），但别依赖它：`check_skin.py` 会警告，而 `lightblue` 这种不是十六进制的写法会直接退回默认色。

4. **写了 `candidate_text` 就要配 `selected_text`**。`candidate_text` 只管普通候选行；选中行的文字仍取 `base` 的选中行配色——微信、微信卷轴、杨柳青、秋桂、石墨都自带选中文字色（不一定跟普通文字同色），fluent 这类竖条选中不另设、跟着普通文字色。想让选中行也听你的，就一并写 `selected_text`（和 `selected_number`）。

5. **写 `translation` 会连带重置词性与分隔符**：解析器给 `translation` 上色的同时，会把 `translation_pos` / `translation_separator` 一起拉成同色；写了 `selected_translation` 则把选中行的词性 / 分隔符也拉成它。要保留那几处独立颜色，得显式写 `translation_pos` / `translation_separator`（选中行另有 `selected_translation_pos` / `selected_translation_separator`）。

6. **v2 必须 `base = "canvas"`**。`schema_version = 2` 只是声明，真正的地基是 `canvas`——透明面板、无描边、直角、默认没有阴影，外观全部来自九宫格面板图与挂件。写了 `2` 但 `base` 是别的基底时，这个包仍能装也能用，但**按 v1 加载**：`border_image`（含 `.vertical`）、`content_insets_dip`（含 `.vertical`）、`line_gap_dip`、`outer_insets_dip`、`decorations` 全部被忽略（连同其中的错误），设置页诊断里会多一条说明。反过来，`schema_version = 1` 配 `canvas` 会被直接拒——没有面板贴图它只是一张透明卡片。`[animation]` 与装饰图的 `motion` / `motion_period_ms` 不在此列：它们是 msime 共用 v2 键，对任何基底都合法，Windows 只按静态显示。

**已移除的老字段**：根级 `preview`、根级 `toolbar_stylesheet` 写了不报错但完全无效；完整清单见 [已移除的字段](references/validation.md#已移除的字段)。

## 1. 先问用户什么

一轮问完，别挤牙膏：

1. **想要什么观感**——参考色、参考图、"像微信"、"性冷淡灰"、"赛博霓虹"、"像微软拼音"。说不出就给选项让他挑。
2. **明暗**：默认两套都做（推荐），除非用户明确只要一套。
3. **要不要图片**：候选框**里面**铺底图（`background`）、卡片**上方**放装饰图（`decoration`），还是都要。要就让他给图。
4. **要不要改悬浮工具栏**：默认只改配色和圆角；想要"搜狗状态栏那种整块图"再问图片模式（背景图、按钮贴图、自动排列）。不加按钮种类。
5. **要不要翻页箭头**：要的话再问折线还是实心三角（`page_arrow_style`）。不说就跟着 `base` 走。
6. **横排还是竖排**：默认 `supports` 全选。竖排要单独换面板图或安全内边距时再展开问。
7. **版式要不要微调**：只在用户说"太挤 / 太松 / 序号太大 / 高亮没铺满 / 想要微信那种整行"时问，不要把所有版式键变成必问项。
8. **要不要卷轴展开**：微信输入法式的横排展开（`expand_panel = true`），展开后一屏几行（`expand_rows`，2~8，默认 4）。只在横排生效，开了以后横排不再显示翻页箭头。
9. **装饰图上要不要叠候选词**：装饰图里画了对话框 / 气泡时，可以 `candidate_overlay = true` 叠一个候选词。没有这种图就别开。
10. **要不要 v2 能力**（整块贴图面板 / 面板内安全内边距 / 行距 / 卡外立绘与留白）：只有这些需求才需要 v2。要卡外立绘就必须 v2 且写 `outer_insets_dip`，否则立绘会被窗口边界裁掉。同时提醒用户：v2 的地基是透明的 `canvas`，只声明 v2 不给面板图，候选框里就只剩悬空的文字。

`base` 不用问用户，按观感你来定：

| base | 观感 | 选中形态 |
|---|---|---|
| `fluent` | 默认，Windows 11 味 | 左侧竖色条 |
| `wechat` | 微信绿 `#07C160` | 整行绿底白字，无竖条 |
| `wechat_scroll` | 微信绿 + 卷轴展开（横排） | 整行绿底白字，无竖条 |
| `graphite` | 石墨灰，紧凑平直 | 不铺底，只换文字色，无竖条 |
| `willow_green` | 杨柳青，无边框、高亮铺满 | 整行整列铺满，无竖条 |
| `autumn_osmanthus` | 秋桂，无边框、橙色高亮内缩 | 内缩橙块，无竖条 |
| `microsoft` | 仿微软拼音，紧凑、三角翻页箭头 | 灰块 + 竖条在块内 |

每个 base 的圆角 / 线宽 / 高亮圆角与 accent 见 [base 预设](references/schema-v1.md#base-预设)。

`base` 除了七个内置皮肤，还能写共享基底，以及只给 v2 用的 `canvas`：

| base | 观感 | 明暗 |
|---|---|---|
| `system` | 跟随宿主，没有自己的调色板 | 跟随系统 |
| `shuishan` | 水杉绿：深色底 + 浅绿强调 | 固定深色 |
| `light` | Windows 浅色：白底 + 蓝强调 | 固定浅色 |
| `paper` | 纸白：暖白底 + 绿强调 | 固定浅色 |
| `night` | 夜蓝：深蓝底 + 青绿强调 | 固定深色 |
| `ink` | 墨黑：黑底 + 白强调 | 固定深色 |
| `canvas` | 全贴图地基，**只给 v2 用** | 看你写哪套 |

共享基底加载后一律按 `fluent` 画，基底只补基础配色；固定明暗的基底会把 `themes` 收窄成它自己那一侧；`canvas` 不能单独在设置页选用。细节见 [base 预设](references/schema-v1.md#base-预设)。

**`microsoft` 唯一自带 `page_arrows = true`**（出厂清单如此），其余内置皮肤都是关的；**`wechat_scroll` 唯一自带 `expand_panel = true`**。选 `microsoft` 做 base 却不写 `page_arrows`，用户就会莫名多出翻页箭头；选 `wechat_scroll` 做 base 却不写 `expand_panel`，横排会直接变成卷轴展开——要么明确写 `false`，要么跟用户确认。

**🔴 CHECKPOINT · 生成前**：问完第 1 节后，把方案一行列给用户确认——「皮肤 ID / 显示名 / base / 明暗两套 / 背景图 / 装饰图 / 版式微调 / 卷轴展开 / 翻页箭头与样式 / 工具栏配色或图片模式 / 装饰图叠候选」，用户点头再生成文件。用户明确说「直接做」时可跳过这一步。

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
- 纯 ASCII，不能是内置名（`fluent`、`wechat`、`wechat_scroll`、`graphite`、`willow_green`、`autumn_osmanthus`、`microsoft`），也不能是保留名 `default`
- 官方随包皮肤 ID 是 `green_leaf`：它不是内置皮肤，但随安装包分发、在设置页单独成组，外部包不要复用这个 ID
- 例：`midnight-ink`、`sakura_2`、`gloss.v2` ✅　`Midnight`、`my skin`、`深夜`、`default`、`green_leaf` ❌

图片路径同样是纯 ASCII，只能含字母数字和 `./_-`，用 `/` 分层（如 `assets/paper.png`），不能有 `..`、不能以 `/` 开头、不能用 `\`、单段不能是 `.`，总长 ≤256 字节。

## 3. 最小可用的 v1 模板

直接照抄改值。这是最小骨架，只演示必填结构；完整模板（22 个颜色键、全部可选键带注释）在 [templates/skin-v1.toml](references/templates/skin-v1.toml)。

```toml
schema_version = 1                 # 数字 1；v2 改成 2（见 §4）
id = "midnight-ink"                # 必须等于目录名
name = "深夜墨水 Midnight Ink"      # ≤80 字节
version = "1.0.0"                  # ≤32 字节
base = "fluent"                    # 七个内置皮肤 / 共享基底之一

[supports]
layouts = ["horizontal", "vertical"]
themes = ["dark", "light"]

[candidate_window]                 # 表必须存在，哪怕只写 min_width_dip = 0
min_width_dip = 320
corner_radius_dip = 8
border_width_dip = 1.5
item_corner_radius_dip = 6
shadow = "soft"
page_arrows = false
page_arrow_style = "chevron"

[candidate.dark]                   # 22 个颜色键写全最稳；这里只给常用键
accent = "#6B69D6"
selected = "#3e3e3eb9"
surface = "#202020"
text = "#e9e8e8"
number = "#e9e8e89d"
show_selected_bar = true

[candidate.light]                  # 浅色主题也要写，别只写 dark
accent = "#6B69D6"
selected = "#E8E8E8"
surface = "#FFFFFF"
text = "#1A1A1A"
number = "#1A1A1A8C"
show_selected_bar = true
```

其余常用键（`backdrop`、`font_family`、`fit_content`、`expand_panel` / `expand_rows`、版式键、背景图、装饰图、工具栏）都在完整模板里，按需取消注释。

**TOML 顺序陷阱**：子表必须写在父表的直接键之后，而且父表只能出现一次。`[candidate_window]` 里先把 `min_width_dip`、版式键、`page_arrows`、`expand_panel` 等直接键写完，再写 `[candidate_window.horizontal]` / `.vertical` / `.background` / `.decoration`；v2 的 `[candidate_window.border_image]`、`.content_insets_dip`、`.outer_insets_dip` 和 `[[candidate_window.decorations]]` 同样要排在直接键之后。一旦进入任何一个子表，后面再出现 `[candidate_window]` 就是语法错误。嵌套管得更细：`[border_image]` 的键要在 `[border_image.vertical]` 之前，`[content_insets_dip]` 要在 `.vertical` 之前。工具栏同理：`[toolbar]` 的 `mode` / `image` / 圆角先写，再写 `[toolbar.dark]` / `.light`，最后才是 `button_defaults`、`button_flow` 和 `[toolbar.buttons.<按钮>]`。`[candidate.dark]` 的键写完才能开 `[candidate.dark.menu]`。

## 4. v2：什么时候需要，怎么开始

只有这几种需求需要 v2：**整块贴图面板**（九宫格拉伸）、**面板内的四边安全内边距**、**行距**、**挂到卡片外沿的立绘 / 挂件**（可多层、可动图）、**卡片外的留白**。其余情况停在 v1，v1 的包不用改。

v2 必须和 `base = "canvas"` 一起写。骨架：

```toml
schema_version = 2
base = "canvas"

[candidate_window]
line_gap_dip = 6

[candidate_window.border_image]      # 九宫格面板图；写错 base 时整段被忽略
source = "assets/panel.png"
slice_dip = [16, 44, 16, 44]

[[candidate_window.decorations]]     # 卡外挂件；要配 outer_insets_dip 才不会被裁
image = "assets/char.png"
width_dip = 149
height_dip = 161
```

完整字段、继承规则、`content_insets_dip` 空表的坑、`z_index` 与互斥关系见 [schema-v2.md](references/schema-v2.md)；完整模板见 [templates/skin-v2.toml](references/templates/skin-v2.toml)。

## 5. 生成 → 校验 → 安装

### 校验

用随本 skill 提供的 `scripts/check_skin.py`（路径相对本 skill 根目录），规则与 Server 的解析器逐条一致，错误文案也一样，方便和设置页对照。v1 与 v2 都校验。

```powershell
python scripts/check_skin.py <皮肤包目录>   # 单个包
python scripts/check_skin.py <skins 根目录>  # 一次校验多个子目录（自动跳过 default 与 *.bak）
```

需要 Python 3.11+（只用标准库 `tomllib`）。没有 python 就 `uv run`。**退出码 0 才算通过**；「错误」= Server 会拒绝这个包，「警告」= 能装但可能不符合预期。完整规则与报错见 [validation.md](references/validation.md)。

### 安装

**🛑 STOP · 安装前**：复制进 `skins` 是改用户本机目录，动手前把「皮肤 ID + 显示名 + 目标路径」展示给用户，用户说装再装。

1. 皮肤目录**以设置页显示的为准**：设置 → 皮肤 → 外部皮肤区域，那行灰色路径写着真实位置（数据目录安装时可以改到别的盘）。默认是 `%LOCALAPPDATA%\metasequoiaime\skins`。
2. 把整个 `my-skin/` 文件夹复制进去，**不要**把 `skin.toml` 直接丢进 `skins\`，也不要套一层 zip。「打开目录」按钮能直接打开这个目录，省得用户手敲路径。
3. 让用户：设置 → 皮肤 → **刷新皮肤** → 找到自己的皮肤 → 打开开关。列表里能实时预览（横排 / 竖排 / 工具栏三张，另有「预览浅色」按钮）。

**内置皮肤的开关**（翻页箭头、`fit_content`、卷轴展开）也能改，但不走这套流程：它是 `<skins 目录>\default\<内置名>\skin.toml` 里的 `[candidate_window] page_arrows`、`fit_content` 与 `expand_panel`，改完在设置页点「刷新皮肤」。只有 `id`、`name`、`description`、`schema_version`、`page_arrows`、`fit_content`、`expand_panel` 会被读，其余字段写了不生效。

### 改完没效果？

- **点「刷新皮肤」就是全量重载**：它会让 Server 重新读取 `skin.toml` 和皮肤目录里的图片、让候选窗按新清单重载，**不需要重启输入法服务**。
- 设置页底部出现「已忽略 N 个无效皮肤目录」展开就能看到被拒原因，和 `check_skin.py` 的错误文案一致。

## 6. 出问题先定位

1. 跑 `check_skin.py`：「错误」= 包会被拒，按报错文案改；「警告」= 能装但可能不符合预期。
2. 设置页底部「已忽略 N 个无效皮肤目录」展开就能看到被拒原因，文案与脚本一致。
3. 最常见的三类：目录层级 / 目录名与 `id` 不一致、颜色里有中文或 `;` `{}` 引号、图片路径不是纯 ASCII 相对路径。

版式、卷轴、工具栏按钮、v2 面板 / 挂件 / 动图的完整排查表见 [troubleshooting.md](references/troubleshooting.md)。

## 7. 交付与分享

**🔴 CHECKPOINT · 交付前**：核对三件必说项已写进回复——**放几级目录**、**设置页怎么启用**、**改完点「刷新皮肤」而不是重启服务**。

- 交付物是一个文件夹，`zip` 打包即可分享；对方解压进自己的 `skins` 目录、点「刷新皮肤」就能用。
- 附上 `check_skin.py` 的输出，省得对方装上才发现被拒。
- 告诉对方三件事：**要放几级目录**（`skins\皮肤名\skin.toml`）、**怎么在设置页启用**（设置 → 皮肤 → 刷新皮肤 → 打开开关）、**改完点刷新**。
- 提醒对方：**别把 `.css` 塞进包里**，那套机制已经没了。
- v2 皮肤要额外说清：`schema_version = 2` 必须配 `base = "canvas"`，面板长什么样全靠 `border_image` 与挂件；写了 `2` 却用别的基底会按 v1 加载。
- 用了 `backdrop` 就说清它依赖系统透明效果与 Windows 版本；皮肤同时写了 `border_image` 时也不生效。
- 用了工具栏图片模式就说清：图片、按钮坐标 / `button_flow`、按钮图都必须在包里；用户关掉某个按钮时，只有画在 `background` 的圆底会跟着消失。
- 用了卷轴展开就说清它只在横排生效；用了装饰图叠加候选就说清 `candidate_overlay_index` 的 0 / 1 起算方式。
- 用别人的图之前先在 `[license]` 里写清 `assets` 的出处与授权；来源说不清就写 `UNVERIFIED` 并说明仅供演示。
