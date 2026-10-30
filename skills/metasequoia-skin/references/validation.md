# 校验规则与报错

本 skill 的字段与报错以 Server 解析器为准：`server/src/skin/candidate_skin_catalog.cpp`（`CandidateSkinCatalog::Load`），配色回落见 `server/src/window/candidate_skin_palette.cpp`。`scripts/check_skin.py` 与这些致命校验逐条一致，错误文案也沿用同一套中文，方便和设置页「皮肤 → 外部皮肤」底部的诊断信息对照。

字段的取值与默认值见 [schema-v1.md](schema-v1.md) 和 [schema-v2.md](schema-v2.md)，图片规则见 [images.md](images.md)。

## 报错与警告的含义

- **错误** = Server 会拒绝这个包，设置页里根本装不上。
- **警告** = 能装，但可能不符合预期：配色没写全、颜色格式不认识、写了已废弃的字段、base 无外框却只改线宽、写了 `schema_version = 2` 却没配 `base = "canvas"`、固定明暗的基底把 `themes` 收窄、动图超过 64 MB、未知按钮 / 状态、bar 模式下的图片模式键等。
- 退出码 0 才算通过。`check_skin.py` 的「错误」对应 Server 的拒收，「警告」对应设置页诊断里的提示。

## 通用规则

- **长度上限按 UTF-8 字节数算**（中文一个字 3 字节），不是字符数。
- **颜色格式**：`#rgb`、`#rgba`、`#rrggbb`、`#rrggbbaa`、`rgb(1,2,3)`、`rgba(1,2,3,.5)`、`transparent`。不透明度在**末尾**（`#RRGGBBAA`），不是 Windows 常见的 `#AARRGGBB`。十六进制大小写均可，但**必须带 `#`**。
- 颜色值只放行纯 ASCII 白名单：字母、数字和 `#(),.% -/`。含非 ASCII 字符（`绿色`）或白名单外符号（`;`、`{}`、引号）的**会被 Server 直接拒收整个包**。`lightblue`、`hsl(...)` 这类纯 ASCII 写法能过解析、包也能装，但渲染认不出来，会静默退回默认色（`check_skin.py` 会为此报警告）。
- **未知字段静默忽略**，不报错也不生效。包括已废弃的 `preview` / `toolbar_stylesheet` 和 `[license]`（输入法不读授权声明）。

## v1 与包结构

| 规则 | 违反后的报错 |
|---|---|
| `schema_version` 必须是**数字** `1` 或 `2`（字符串 `"1"` 和浮点 `1.0` 都不行） | 仅支持 schema_version 1 或 2 |
| `id` / `name` / `version` / `base` 必填且是字符串且非空，`id` 必须等于目录名 | manifest 的基本信息无效 |
| `base` 必须是七个内置名（`fluent` / `wechat` / `wechat_scroll` / `graphite` / `willow_green` / `autumn_osmanthus` / `microsoft`）、六个共享基底（`system` / `shuishan` / `light` / `paper` / `night` / `ink`）或 `canvas` 之一 | manifest 的基本信息无效 |
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
| `expand_panel` 写了就必须是布尔 | candidate_window.expand_panel 必须是 true 或 false |
| `expand_rows` 写了必须是 **2~8 的整数**（浮点、布尔、字符串都不行） | candidate_window.expand_rows 必须是 2–8 的整数 |
| 版式长度键（`padding` / `item_gap` / `item_extra_height` / `number_inset` / `item_padding_right` / `item_min_width` / `number_gap` / `selected_bar_width`）只能写 **DIP 数字**或 **`"<数值>em"` 字符串**；越界、负值、`"10px"`、`"1.5EM"` 都非法 | candidate_window 的版式数值无效 |
| `number_scale`、`selected_bar_height_em` 写了必须是 0~2 的数字；`selected_bar_inside`、`item_corners_follow_card`、`justify_rows`、`trim_hidden_preedit_gap` 写了必须是布尔 | candidate_window 的版式数值无效 |
| `page_arrow_style` 只能是 `chevron` / `triangle` | candidate_window 的版式数值无效 |
| `preedit_margin_dip` 必须是 1 / 2 / 4 个 0~500 的数值（按 CSS 简写展开成上右下左） | candidate_window 的版式数值无效 |
| `[candidate_window.horizontal]` / `[candidate_window.vertical]` 一旦出现必须是表，里面的版式键遵守同一套范围 | candidate_window 的版式数值无效 |
| `[candidate_window.decoration]` **可选**；一旦出现就**必须**同时有 `image` 和 `top_inset_dip`、`width_dip`，且 `align` 只能是 left / center / right | candidate_window.decoration 无效 |
| `top_inset_dip` ∈ (0, 500]、`width_dip` ∈ (0, 1000]，**两个都必须 > 0** | candidate_window.decoration 尺寸无效 |
| `decoration.image` 指向的文件必须真实存在 | 找不到 candidate_window.decoration.image 文件 |
| `candidate_overlay` 写了就必须是布尔；只有为 `true` 时下面这组键才被解析 | candidate_window.decoration.candidate_overlay 必须是 true 或 false |
| `candidate_overlay_font_size_dip` / `candidate_overlay_min_font_size_dip` 写了必须 **> 0 且 ≤ 200** | candidate_window.decoration 的 candidate_overlay_font_size_dip 与 candidate_overlay_min_font_size_dip 必须是大于 0、不超过 200 的数值 |
| `candidate_overlay_max_width_dip` 写了必须是 0~2000 | candidate_window.decoration.candidate_overlay_max_width_dip 必须是 0–2000 的数值 |
| `candidate_overlay_color` 走颜色白名单；`candidate_overlay_align_h` ∈ {left, center, right}、`candidate_overlay_align_v` ∈ {top, center, bottom} | candidate_window.decoration.candidate_overlay_color 无效 / candidate_window.decoration 的 candidate_overlay_align_h 只能是 left、center 或 right，candidate_overlay_align_v 只能是 top、center 或 bottom |
| `candidate_overlay_offset_x_dip` / `candidate_overlay_offset_y_dip` 写了必须在 -2000~2000 之间 | candidate_window.decoration 的 candidate_overlay_offset_x_dip / candidate_overlay_offset_y_dip 必须在 -2000–2000 之间 |
| `candidate_overlay_strip_badge` 写了必须是布尔；`candidate_overlay_index` 写了必须是 0~100 的整数 | candidate_window.decoration.candidate_overlay_strip_badge 必须是 true 或 false / candidate_window.decoration.candidate_overlay_index 必须是 0–100 的整数 |
| `[candidate_window.background]` **可选**；一旦出现就**必须**有 `image`，`fit` 只能是 cover / contain / stretch，`opacity` 只能是 0~1 的数字 | candidate_window.background 无效 / candidate_window.background.opacity 超出范围 |
| `background.image` 指向的文件必须真实存在 | 找不到 candidate_window.background.image 文件 |
| 22 个配色键（含 `page_arrow_divider`）给了必须是 ≤80 字节的字符串，且字符集只放行字母数字与 `# ( ) , . %` 空格 `-` `/` | candidate 配色无效 |
| `show_selected_bar` 给了就必须是布尔 | candidate 配色无效 |
| `translation_pos` / `translation_separator` / `selected_translation_pos` / `selected_translation_separator` 给了同样要过颜色白名单；不写则与 `translation` 同色 | candidate 配色无效 |
| `backdrop_opacity` / `backdrop_luminosity` 给了必须是 0~1 的**数字**（不是颜色） | candidate 配色无效 |
| `[candidate.dark.menu]` / `[candidate.light.menu]` 给了必须是表，里面的 4 个键同配色规则 | candidate 配色无效 |
| 目录名不合法 / 与内置名或 `default` 同名 | 目录名不是有效的外部皮肤 ID |

## 工具栏（bar 与图片模式）

| 规则 | 违反后的报错 |
|---|---|
| `[toolbar]` 给了必须是表，`[toolbar.dark]` / `[toolbar.light]` 给了必须是表，键集同配色规则 | toolbar 配色无效 |
| `[toolbar] corner_radius_dip` 写了必须是 0~32；`icon_corner_radius_dip` 写了必须是 0~16 | toolbar.corner_radius_dip 超出范围 / toolbar.icon_corner_radius_dip 超出范围 |
| `[toolbar] mode` 只能是 `bar` / `image` | toolbar.mode 只能是 bar 或 image |
| `toolbar.image` 必须是包内相对路径且扩展名在 `.png` / `.apng` / `.gif` / `.webp` 里；`image_width_dip` / `image_height_dip` 各 0~2000 | toolbar.image 无效（需为皮肤目录里的 .png、.apng、.gif 或 .webp） / toolbar.image_width_dip / image_height_dip 必须是 0–2000 的数值 |
| `[toolbar.buttons]` 给了必须是表；每个已知按钮名下面是表（未知按钮名只提示、不报错） | toolbar.buttons 必须是表 / toolbar.buttons.\<按钮\> 必须是表 |
| 按钮的 `visible` 必须是布尔；`x_dip` / `y_dip` 各 0~2000 | toolbar.buttons.\<按钮\>.visible 必须是 true 或 false / toolbar.buttons.\<按钮\> 的 x_dip / y_dip 必须是 0–2000 的数值 |
| 按钮的 `width_dip` / `height_dip` 必须 **> 0 且 ≤ 500**；`icon_size_dip` 必须 **> 0 且 ≤ 500** | toolbar.buttons.\<按钮\> 的 width_dip / height_dip 必须是大于 0、不超过 500 的数值 / toolbar.buttons.\<按钮\>.icon_size_dip 必须是大于 0、不超过 500 的数值 |
| 按钮的 `background` / `image` 必须是包内图片路径且在四种扩展名里 | toolbar.buttons.\<按钮\>.background 无效（需为皮肤目录里的 .png、.apng、.gif 或 .webp） / .image 同 |
| `[toolbar.buttons.<按钮>.images]` 必须是表；只有有状态的按钮能写 | toolbar.buttons.\<按钮\>.images 必须是表 / toolbar.buttons.\<按钮\> 没有状态之分，只能写 image，不能写 images |
| 状态图路径必须是包内图片；未知状态名只提示、不报错 | toolbar.buttons.\<按钮\>.images.\<状态\> 无效（需为皮肤目录里的 .png、.apng、.gif 或 .webp） |
| `[toolbar.button_defaults]` 必须是表，只读取 `width_dip` / `height_dip` / `icon_size_dip` / `background`，范围同按钮（其它键静默忽略） | toolbar.button_defaults 必须是表 / toolbar.button_defaults 的 width_dip / height_dip 必须是大于 0、不超过 500 的数值 / toolbar.button_defaults.icon_size_dip 必须是大于 0、不超过 500 的数值 / toolbar.button_defaults.background 无效（需为皮肤目录里的 .png、.apng、.gif 或 .webp） |
| `[toolbar.button_flow]` 必须是表；`x_dip` / `y_dip` 各 0~2000，`direction` 只能是 horizontal / vertical，`gap_dip` 0~500 | toolbar.button_flow 必须是表 / toolbar.button_flow 的 x_dip / y_dip 必须是 0–2000 的数值 / toolbar.button_flow.direction 只能是 horizontal 或 vertical / toolbar.button_flow.gap_dip 必须是 0–500 的数值 |
| `mode = "image"` 时必须同时写 `image`、`image_width_dip`、`image_height_dip`，且两个尺寸都 > 0 | toolbar.mode = "image" 需要同时写 image、image_width_dip 与 image_height_dip |
| 图片模式引用的 `toolbar.image`、`button_defaults.background`、按钮 `image` / `background` / `images.*` 文件必须真实存在 | 找不到 toolbar.image 文件 / 找不到 toolbar.button_defaults.background 文件 / 找不到 toolbar.buttons.\<按钮\>.(image\|background) 文件 / 找不到 toolbar.buttons.\<按钮\>.images.\<状态\> 文件 |
| `mode` 不是 `image` 时写 `image` / `buttons` / `button_defaults` / `button_flow` | 不报错：只在设置页诊断里提示「只在 mode = "image" 时生效，已忽略」 |

## v2

| 规则 | 违反后的报错 |
|---|---|
| **v2**：`schema_version = 2` 而 `base` 不是 `canvas` | 不报错：按 v1 加载，v2 字段全部忽略，设置页诊断里多一条说明 |
| **v2**：`[candidate_window.border_image]` 一旦出现必须是表；必须写 `source`（文件要存在、扩展名只能是 .png / .apng / .gif / .webp） | candidate_window.border_image 必须是表 / candidate_window.border_image 缺少 source / candidate_window.border_image.source 无效（需为 .png、.apng、.gif 或 .webp） |
| **v2**：`light_source` 同规则，格式不对或不在白名单同样拒 | candidate_window.border_image.light_source 无效（需为 .png、.apng、.gif 或 .webp） |
| **v2**：`slice_dip` 必填（1 / 2 / 4 个 0~500 的数值，单位是源图像素） | candidate_window.border_image 缺少 slice_dip / candidate_window.border_image.slice_dip 必须是 1、2 或 4 个 0–500 的数值 |
| **v2**：`stretch_dip` / `width_dip` 写了就必须是 1 / 2 / 4 个 0~500 的数值（不是数组、长度不对、越界都报错；前者是源图像素，后者是屏幕 DIP） | candidate_window.border_image.stretch_dip 必须是 1、2 或 4 个 0–500 的数值 / candidate_window.border_image.width_dip 必须是 1、2 或 4 个 0–500 的数值 |
| **v2**：`fill` 写了必须是布尔 | candidate_window.border_image.fill 必须是 true 或 false |
| **v2**：`repeat` 只能是 `stretch` / `repeat`，写 1 个或 2 个值（横向 纵向） | candidate_window.border_image.repeat 必须是 stretch 或 repeat，1 个或 2 个值 |
| **v2**：`border_image.source` / `light_source` 指向的文件必须真实存在 | 找不到 candidate_window.border_image.source 文件 / 找不到 candidate_window.border_image.light_source 文件 |
| **v2**：`[candidate_window.border_image.vertical]` 必须是表；`source` / `slice_dip` 不写继承横排，写了就按上面的规则校验；`light_source` 不继承 | candidate_window.border_image.vertical 必须是表 / candidate_window.border_image.vertical.source 无效（需为 .png、.apng、.gif 或 .webp） / .light_source 同 / .vertical.slice_dip 必须是 1、2 或 4 个 0–500 的数值 / .vertical.repeat 必须是 stretch 或 repeat，1 个或 2 个值 |
| **v2**：竖排面板图（含浅色变体）指向的文件必须真实存在 | 找不到 candidate_window.border_image.vertical.source 文件 / 找不到 candidate_window.border_image.vertical.light_source 文件 |
| **v2**：`[candidate_window.content_insets_dip]` 必须是表，四边各自 0~上限（top / bottom ≤ 200，left / right ≤ 500），缺的边按 0；空表等于四边全 0，不会再按「边宽 + 5 DIP」留白 | candidate_window.content_insets_dip 必须是表 / candidate_window.content_insets_dip 数值超出范围 |
| **v2**：`[candidate_window.content_insets_dip.vertical]` 必须是表，只校验写了的边，范围同上 | candidate_window.content_insets_dip.vertical 必须是表 / candidate_window.content_insets_dip.vertical 数值超出范围 |
| **v2**：`line_gap_dip` 必须是 0~100 的数字 | candidate_window.line_gap_dip 超出范围 |
| **v2**：`[candidate_window.outer_insets_dip]` 必须是表，四边各自 ≤ 500 | candidate_window.outer_insets_dip 必须是表 / candidate_window.outer_insets_dip 数值超出范围 |
| **v2**：`[[candidate_window.decorations]]` 必须是数组，最多 32 层 | candidate_window.decorations 必须是数组 / candidate_window.decorations 最多 32 层 |
| **v2**：每项要有 `image`（文件要存在、扩展名只能在白名单里） | candidate_window.decorations.image 无效（需为 .png、.apng、.gif 或 .webp） |
| **v2**：`anchor` 只能是九个锚点之一 | candidate_window.decorations.anchor 无效 |
| **v2**：`width_dip` 与 `height_dip` 都要 > 0 且 ≤ 2000 | candidate_window.decorations 的 width_dip 与 height_dip 必须大于 0 |
| **v2**：`offset_x_dip` / `offset_y_dip` 写了必须在 -2000~2000 之间 | candidate_window.decorations 的 offset_x_dip / offset_y_dip 必须在 -2000–2000 之间 |
| **v2**：`z_index` 写了必须是 -1000~1000 的整数 | candidate_window.decorations.z_index 必须是 -1000–1000 的整数 |
| **v2**：`decorations[].image` 指向的文件必须真实存在 | 找不到 candidate_window.decorations.image 文件 |
| **v2 字段写在没配 `canvas` 的皮肤里** | 不报错：按 v1 加载，字段全部忽略，设置页诊断里多一条说明 |
| `[animation]`、装饰图的 `motion` / `motion_period_ms` | msime 共用 v2 键，Windows 按静态图显示：不报错、不提示，也不会动 |

## 已移除的字段

写了不报错，但完全无效，别再生成：

| 老字段 | 现状 |
|---|---|
| 根级 `preview = "preview.png"` | 已移除。装饰图改由 `candidate_window.decoration.image` 指定 |
| 根级 `toolbar_stylesheet = "toolbar.css"` | 已移除。工具栏改由 `[toolbar]` 系列表配置，不做任何兼容 |
| `[candidate_window.decoration]` 里两个尺寸都填 0 | 现在是**非法**，会被拒 |

## `check_skin.py`

```powershell
python scripts/check_skin.py <皮肤包目录>   # 单个包
python scripts/check_skin.py <skins 根目录>  # 一次校验多个子目录（自动跳过 default 与 *.bak）
```

需要 Python 3.11+（只用标准库 `tomllib`）。没有 python 就 `uv run`。脚本同时校验 v1 与 v2，包括版式几何、卷轴展开、翻页箭头样式、工具栏图片模式、装饰图叠加候选、九宫格 `repeat` 与竖排覆盖：格式错误报错，其它问题以警告给出。
