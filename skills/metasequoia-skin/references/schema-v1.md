# v1 字段参考

v1 是通用卡片皮肤：配色、圆角、版式、背景图、装饰图，`base` 决定没写到的默认值。`schema_version = 1` 时读这一份；需要九宫格面板、卡片外挂件、行距等 v2 能力时，看 [schema-v2.md](schema-v2.md)。

字段的硬性范围和报错文案见 [validation.md](validation.md)。图片与动图规则见 [images.md](images.md)。完整可复制模板见 [templates/skin-v1.toml](templates/skin-v1.toml)。

字段语义以 Server 解析器为准：`server/src/skin/candidate_skin_catalog.cpp`（`CandidateSkinCatalog::Load`），配色回落见 `server/src/window/candidate_skin_palette.cpp`。

## 顶层字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `schema_version` | 是 | 数字 `1` 或 `2`。字符串 `"1"` 和浮点 `1.0` 都会被拒 |
| `id` | 是 | 必须等于目录名；规则见 [SKILL.md](../SKILL.md) 的「ID 规则」 |
| `name` | 是 | 设置页显示的名字，≤80 字节 |
| `version` | 是 | 版本号，≤32 字节 |
| `author` | 否 | ≤120 字节 |
| `description` | 否 | ≤500 字节；不写时设置页显示「基于 <base>」 |
| `base` | 是 | 七个内置皮肤、六个共享基底或 `canvas`（`canvas` 只给 v2） |
| `[supports]` | 是 | `layouts`（`horizontal` / `vertical`）与 `themes`（`dark` / `light`），非空、无重复 |
| `[license]` | 否 | `code`、`assets`、`source`；输入法不读，分享前建议写 |

长度上限按 **UTF-8 字节数**算，中文一个字 3 字节，不是字符数。

`[supports]` 建议四项全选：`layouts = ["horizontal", "vertical"]`、`themes = ["dark", "light"]`。只支持一种布局或明暗时，设置页会标「当前布局或明暗模式不受支持」。

## `[license]`

输入法不读这段，纯给分享对象看的授权声明：

```toml
[license]
code = "MIT"                  # skin.toml 本身的授权
assets = "CC-BY-4.0 / 自绘"    # 图片素材的授权；来源未核实就写 UNVERIFIED
source = "素材出处与授权说明"
```

用别人的图之前先写清 `assets` 的出处与授权；来源说不清就写 `UNVERIFIED` 并说明仅供演示。

## `[candidate_window]`

表必须存在，哪怕只写 `min_width_dip = 0`。

### 卡片与开关

| 键 | 范围 / 取值 | 说明 |
|---|---|---|
| `min_width_dip` | 0~1000 | 卡片最小宽度；装饰图 `width_dip` 还会把它撑大 |
| `corner_radius_dip` | 0~32 | 卡片圆角；0 = 直角 |
| `border_width_dip` | 0~4 | 外框线宽；颜色取 `[candidate.*].border` |
| `item_corner_radius_dip` | 0~16 | 选中 / 悬停高亮圆角 |
| `shadow` | `none` / `soft` / `strong` | 卡片阴影；不影响右键菜单 |
| `backdrop` | `none` / `acrylic` / `mica` | 卡片背后的系统材质；写了 `border_image` 时不生效 |
| `font_family` | ≤64 字节，非空 | 候选字体族，排在用户字体前；字号不由皮肤决定 |
| `page_arrows` | `true` / `false` | 翻页箭头；不写沿用 `base` 的出厂清单（`microsoft` 为 `true`） |
| `fit_content` | `true` / `false` | 卡片严格按文字宽度收紧；不写沿用 `base` 出厂值（默认 `false`） |
| `expand_panel` | `true` / `false` | 横排用卷轴展开代替翻页；不写沿用 `base`（`wechat_scroll` 为 `true`） |
| `expand_rows` | 2~8 的整数 | 展开后一屏的网格行数；默认 4 |

`font_family` 不能含引号、反斜杠、逗号、分号、尖括号、花括号、反引号和 ASCII 控制字符；汉字可以。一次只能写一个字体名。

**毛玻璃**走 `backdrop`：`acrylic`（亚克力）模糊卡片后面的窗口，`mica`（云母）取样桌面壁纸、只透出壁纸色调。它需要系统开着「透明效果」（设置 → 个性化 → 颜色）；关掉或系统太老（低于 Windows 10 1903；云母还要 Windows 11，更早的系统按亚克力画）时会退回不透明底色。同一张皮肤写了 `border_image` 时不生效（有面板贴图就不垫材质）。

### 版式几何

长度键可以写 **DIP 数字**，也可以写 **`"<数值>em"`** 字符串（按候选字号换算，四舍五入到整 DIP）。`em` 必须小写、贴着数值；`"10px"`、`"1.5EM"`、`"2"` 都非法。

| 键 | 范围 | 说明 |
|---|---|---|
| `padding` | 0~64 / ≤4em | 卡片内边距 |
| `item_gap` | 0~64 / ≤4em | 候选项之间的空隙 |
| `item_extra_height` | 0~64 / ≤4em | 候选项比 1.35 倍字号多出的高度，上下各一半 |
| `number_inset` | 0~64 / ≤4em | 高亮左缘到序号左端的距离；渲染时减去序号固定的 5 DIP 前置留白，小于 5 的值效果接近贴边 |
| `item_padding_right` | 0~64 / ≤4em | 候选文字后面的留白 |
| `item_min_width` | 0~500 / ≤40em | 横排每项的最小宽度；0 = 不限 |
| `number_gap` | 0~64 / ≤4em | 序号与候选之间的空 |
| `number_scale` | 0~2 | 序号字号相对候选字号的比例，默认 0.8 |
| `selected_bar_width` | 0~16 / ≤1em | 选中竖条宽度，默认 3 |
| `selected_bar_height_em` | 0~2 | 选中竖条高度，按字号倍数，默认 0.85 |
| `selected_bar_inside` | 布尔 | `true` = 竖条落在高亮左缘之内，而不是骑在左缘上 |
| `item_corners_follow_card` | 布尔 | 落在卡片四角上的高亮角改用卡片圆角 |
| `justify_rows` | 布尔 | 横排时把卡片多出的宽度均分给同一行，高亮铺满到卡片右边 |
| `trim_hidden_preedit_gap` | 布尔 | 预编辑行隐藏时抵掉它与候选之间的 2 DIP 行距；贴角皮肤总是这样做 |
| `page_arrow_style` | `chevron` / `triangle` | 翻页箭头样式；`triangle` 横排时前面会画一条分隔线 |
| `preedit_margin_dip` | 1 / 2 / 4 个 0~500 的数值 | 预编辑行的外边距，按 CSS 简写展开成上右下左 |

不写的版式键沿用 `base`；`[candidate_window]` 里的直接键对横排 / 竖排都生效。

横排 / 竖排可以各写一套覆盖：

```toml
[candidate_window]
padding = 5
item_gap = 2

[candidate_window.horizontal]
item_min_width = "3.5em"
item_gap = "0.15em"

[candidate_window.vertical]
selected_bar_height_em = 0.8
```

`.horizontal` / `.vertical` 只覆盖写了的键，优先于直接键。子表必须排在直接键之后。

### `[candidate_window.decoration]`（可选）

卡片上方的装饰图。表一旦出现，`image`、`top_inset_dip`、`width_dip` 都必须给。

| 键 | 说明 |
|---|---|
| `image` | 图片路径 |
| `top_inset_dip` | 装饰框高度，0~500 且 > 0 |
| `width_dip` | 装饰框宽度，0~1000 且 > 0 |
| `align` | `left` / `center` / `right`，默认 `right` |

装饰图上可以叠一个候选词（例如把首选词写进立绘的对话框）。只有 `candidate_overlay = true` 时，下面这组键才会被解析：

| 键 | 说明 |
|---|---|
| `candidate_overlay` | 布尔，默认 `false` |
| `candidate_overlay_index` | 0~100 的整数。`0` 跟随高亮；`1` 是当前页第一个；默认 `1` |
| `candidate_overlay_font_size_dip` | 字号，>0 且 ≤200，默认 16 |
| `candidate_overlay_min_font_size_dip` | 缩字号下限，>0 且 ≤200，默认 8 |
| `candidate_overlay_max_width_dip` | 词最多占多宽，0~2000；`0` = 装饰框宽度 |
| `candidate_overlay_color` | 文字颜色，默认白色 |
| `candidate_overlay_align_h` | `left` / `center` / `right`，默认 `center` |
| `candidate_overlay_align_v` | `top` / `center` / `bottom`，默认 `center` |
| `candidate_overlay_offset_x_dip` | 对齐后平移，-2000~2000 |
| `candidate_overlay_offset_y_dip` | 对齐后平移，-2000~2000 |
| `candidate_overlay_strip_badge` | `true` 只画词本身，不带候选后的标注，默认 `true` |

词太宽时先缩小字号到下限，再宽就允许超出，不折行。当前页没有 `index` 指定的候选时不画。

### `[candidate_window.background]`（可选）

卡片内的背景图，画在底色之上、文字之下，按外框圆角裁剪。

| 键 | 说明 |
|---|---|
| `image` | 图片路径；表出现时必须给 |
| `fit` | `cover`（默认，铺满裁切）/ `contain`（完整显示）/ `stretch`（拉伸） |
| `opacity` | 0~1，默认 1；数值越小越淡 |

同一张背景图对深浅两套主题都生效。图自身带 alpha 时保持 `opacity = 1.0` 通常最好。

## `[candidate.dark]` / `[candidate.light]`

两套主题各写一份。22 个颜色键 + `show_selected_bar`；建议写全，没写的走 `base` 的 D2D 令牌。

| 键 | 作用 | 不写时 |
|---|---|---|
| `accent` | 强调色：预编辑光标、选中竖条默认色 | `base` |
| `selected` | 选中行背景 | `base` |
| `hover` | 悬停行背景；翻页箭头悬停也用它 | `base` |
| `surface` | 候选窗背景；也是亚克力 / 云母的色调 | `base` |
| `border` | 候选窗外框 | `base` |
| `text` | 候选文字；会被设置页「候选文字颜色」覆盖 | `base` |
| `number` | 序号；翻页箭头也用它 | `base` |
| `translation` | 候选后的翻译；不写则取文字色 62% 不透明 | `base` |
| `candidate_text` | 普通候选文字 | `text` |
| `preedit_text` | 预编辑拼音文字 | `text` |
| `preedit_caret` | 预编辑光标 | `accent` |
| `selected_text` | 选中候选文字 | `base` 的选中行文字色 |
| `selected_number` | 选中候选序号 | `base` 的选中行序号色 |
| `selected_translation` | 选中候选翻译 | `base` 的选中翻译色 → `translation` → 选中文字色 62% |
| `selected_bar` | 选中项左侧竖条 | `accent` |
| `preedit_background` | 预编辑行底色，圆角同高亮圆角 | 透明 |
| `preedit_divider` | 预编辑行下方 1px 分隔线 | 不画 |
| `page_arrow_divider` | 横排三角箭头前的分隔线 | 不画 |
| `translation_pos` | 翻译里的词性标记 | 与 `translation` 同色 |
| `translation_separator` | 翻译里义项之间的分隔符 | 与 `translation` 同色 |
| `selected_translation_pos` | 选中行翻译的词性 | 写了 `selected_translation` 时跟它，否则 `translation_pos` |
| `selected_translation_separator` | 选中行翻译的分隔符 | 写了 `selected_translation` 时跟它，否则 `translation_separator` |

`show_selected_bar` 是布尔：选中行左侧是否画竖色条；不写沿用 `base`。

**设置页的「候选文字颜色」压过 `text` / `candidate_text` / `preedit_text`**：用户在设置里动过候选文字颜色时，这三个键不生效——所以别靠它们定候选文字的主色。

两条容易踩的规则：

1. **写了 `translation` 会连带重置词性与分隔符**：解析器会把 `translation_pos` / `translation_separator` 拉成同色；写了 `selected_translation` 则把选中行的词性 / 分隔符也拉成它。想保留独立颜色，显式写那四个键。
2. **写了 `candidate_text` 就配 `selected_text`**：`candidate_text` 只管普通行；选中行仍取 `base` 的选中配色。微信、微信卷轴、杨柳青、秋桂、石墨都自带选中文字色（不一定跟普通文字同色）；fluent 这类竖条选中不另设，跟着普通文字色。

### 材质参数

`candidate_window.backdrop` 不是 `none` 时，两套主题各自还可以写：

| 键 | 范围 | 说明 |
|---|---|---|
| `backdrop_opacity` | 0~1 | `surface` 色调盖在材质上的不透明度；不写取 `surface` 自带的 alpha |
| `backdrop_luminosity` | 0~1 | 亮度层不透明度；不写时亚克力 0.85、云母 1 |

Windows 11 默认值可作参考：亚克力深色 `#2c2c2c` / `0.15` / `0.96`，浅色 `#fcfcfc` / `0` / `0.85`；云母深色 `#202020` / `0.8` / `1`，浅色 `#f3f3f3` / `0.5` / `1`。

### `[candidate.dark.menu]` / `[candidate.light.menu]`（可选）

候选窗右键菜单：`background`、`border`、`text`、`hover`。不写沿用 `base`。

## `[toolbar]`（bar 模式）

悬浮工具栏的默认形态。所有键可省略，不写的沿用 `base`。

- `corner_radius_dip`：0~32
- `icon_corner_radius_dip`：0~16，图标悬停底色的圆角
- `[toolbar.dark]` / `[toolbar.light]`：`background`、`border`、`handle`（左侧拖动条）、`divider`、`icon`、`hover`
- `handle` 不写时取同主题的 `[candidate.*].accent`，与选中竖条、预编辑光标同色；`accent` 也没写才沿用 `base`

工具栏整块换成图片、按钮贴图与自动排列，见 [toolbar-image-mode.md](toolbar-image-mode.md)。

## `base` 预设

### 七个内置皮肤

| base | 观感 | 圆角 / 线宽 / 高亮圆角 | 选中形态 | accent（dark / light） |
|---|---|---|---|---|
| `fluent` | 默认，Windows 11 味 | 6 / 1.5 / 4 | 左侧竖色条 | `#6B69D6` / `#6B69D6` |
| `wechat` | 微信绿 `#07C160` | 5 / 1 / 4 | 整行绿底白字，无竖条 | `#07C160` |
| `wechat_scroll` | 微信绿 + 卷轴展开（横排） | 10 / 1 / 6 | 整行绿底白字，无竖条 | `#07C160` |
| `graphite` | 石墨灰，紧凑平直 | 3 / 1 / 2 | 不铺底，只换文字色，无竖条 | `#8993A0` / `#5F6B7A` |
| `willow_green` | 杨柳青，无边框、高亮铺满 | 9 / 0 / 0 | 整行整列铺满，无竖条 | `#65C98D` / `#58B980` |
| `autumn_osmanthus` | 秋桂，无边框、橙色高亮内缩 | 10 / 0 / 6 | 内缩橙块，无竖条 | `#F97D0A` / `#E6A817` |
| `microsoft` | 仿微软拼音，紧凑、三角翻页箭头 | 8 / 1 / 4 | 灰块 + 竖条在块内 | `#E183D9` / `#E183D9` |

`base` 决定几何和没写到的键的默认值。自己写了 `corner_radius_dip`、`item_corner_radius_dip`、版式键和全部配色键之后，`base` 还剩下「高亮是铺满还是内缩」这类形态和没写到的键。版式可以在 `[candidate_window]` 里逐项覆盖，不必为了改内边距换 base。

出厂开关：`microsoft` 的 `page_arrows = true`，`wechat_scroll` 的 `expand_panel = true`，其余内置皮肤这两个开关都是 `false`；`fit_content` 出厂一律 `false`。

**内置皮肤本身不是皮肤包**，只有 `page_arrows`、`fit_content`、`expand_panel` 三个开关可改：改 `<skins 目录>\default\<内置名>\skin.toml` 里 `[candidate_window]` 的对应键，点「刷新皮肤」。其余字段写了不生效。

### 共享基底

| base | 观感 | 明暗 |
|---|---|---|
| `system` | 跟随宿主，没有自己的调色板 | 跟随系统 |
| `shuishan` | 水杉绿：深色底 + 浅绿强调 | 固定深色 |
| `light` | Windows 浅色：白底 + 蓝强调 | 固定浅色 |
| `paper` | 纸白：暖白底 + 绿强调 | 固定浅色 |
| `night` | 夜蓝：深蓝底 + 青绿强调 | 固定深色 |
| `ink` | 墨黑：黑底 + 白强调 | 固定深色 |
| `canvas` | 全贴图地基，只给 v2 用 | 看你写哪套 |

- **共享基底加载后一律被当作 `fluent`**：绘制结构、几何和设置页预览都按 fluent 走，基底只补基础配色（`surface` / `text` / `accent` / `number`，以及由它们派生出来的选中、悬停、翻译、菜单、工具栏色）。没写的键走 fluent 的 D2D 令牌，不是别的，也不是宿主系统那套。
- **固定明暗的基底会把 `[supports] themes` 收窄**成它自己那一侧：`shuishan` / `night` / `ink` 收成 `dark`，`light` / `paper` 收成 `light`。声明里没有对应明暗时收窄成空，两种明暗都回退 fluent；声明了另一侧也只是摆设，那一侧的配色不会生效。`system` 不收窄。
- **`canvas` 不能单独在设置页选用**：它只是 v2 皮肤的地基，没有九宫格面板图与挂件时什么也看不见；`schema_version = 1` 用它会直接被拒。

## 颜色格式

所有颜色键（`[candidate.*]` 里除 `show_selected_bar` 外的键、`[candidate.*.menu]` 与 `[toolbar.*]` 的全部键）接受：

| 写法 | 示例 | 说明 |
|---|---|---|
| `#rgb` / `#rrggbb` | `#e8a`、`#e08aa8` | 不透明 |
| `#rgba` / `#rrggbbaa` | `#e8a4`、`#e08aa847` | 末尾一位或两位是不透明度 |
| `rgb(r, g, b)` | `rgb(224, 138, 168)` | `r`、`g`、`b` 为 0~255 |
| `rgba(r, g, b, a)` | `rgba(224, 138, 168, 0.28)` | `a` 为 0~1 |
| `transparent` | `transparent` | 全透明，等同 `#0000` |

十六进制大小写均可，但**必须带 `#`**；不透明度在末尾（`#RRGGBBAA`），不是 Windows 常见的 `#AARRGGBB`。

颜色值只放行纯 ASCII 白名单：字母、数字和 `#(),.% -/`。含中文（`绿色`）或 `;`、`{}`、引号之类字符会被 Server 拒收整个包。`lightblue`、`hsl(...)` 这类纯 ASCII 写法能过解析，但渲染认不出来，会静默退回默认色；`check_skin.py` 会为此报警告。

## 已移除的字段

根级 `preview`、根级 `toolbar_stylesheet` 写了不报错但完全无效；`[candidate_window.decoration]` 两个尺寸都填 0 现在会被拒。完整清单与现状见 [validation.md 的「已移除的字段」](validation.md#已移除的字段)。

未知字段一律静默忽略；`[license]` 也属于「输入法不读」的字段。
