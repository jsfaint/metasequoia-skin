# 工具栏图片模式

`[toolbar] mode = "image"` 时，整条悬浮工具栏画成一张背景图，按钮按坐标或 flow 摆在图上，类似搜狗的状态栏皮肤。与默认的 `bar` 模式二选一。

## 基本行为

- 不画底色、描边、圆角、阴影、拖动条和分隔线。
- **窗口按图片的透明区域裁成异形**：完全透明的地方点击会落到后面的窗口上。
- 按钮框总是算在窗口里，所以按钮也可以摆在背景图透明的地方（比如人物旁边的空白处），不必在背景图里给它垫底。
- 图上除按钮以外的地方都能按住拖动；设置页「悬浮工具栏」里的缩放会同时放大背景图、按钮位置和尺寸。
- 图片模式的图片扩展名只能是 `.png` / `.apng` / `.gif` / `.webp`，SVG / JPG 会被 Server 拒收。动图只在 `schema_version = 2` 且 `base = "canvas"` 的皮肤里播放；工具栏隐藏或自动隐藏淡出后停止播放。窗口形状按所有帧合起来的轮廓裁，任何一帧画到的地方都不会被裁掉，也都能点到、能拖动。

## `[toolbar]` 的图片模式键

| 键 | 必填 | 范围 | 说明 |
|---|---|---|---|
| `mode` | 否 | `bar` / `image` | 默认 `bar` |
| `image` | 是 | 包内图片路径 | 背景图。窗口按图片的透明区域裁成异形 |
| `image_width_dip` | 是 | >0 且 ≤2000 | 背景图显示宽度（屏幕 DIP） |
| `image_height_dip` | 是 | >0 且 ≤2000 | 背景图显示高度（屏幕 DIP） |
| `icon_corner_radius_dip` | 否 | 0~16 | 图标悬停底色的圆角 |

`image_width_dip` / `image_height_dip` 是图片拉伸后的显示尺寸；窗口按背景图与所有按钮合起来的范围开，按钮排到图外时窗口跟着变大。给 2 倍图时写像素的一半。

**三件套必须同时写**：`mode = "image"` 时缺 `image`、`image_width_dip`、`image_height_dip` 任意一个，整个包会被拒（`toolbar.mode = "image"` 需要同时写 image、image_width_dip 与 image_height_dip）。

## `[toolbar.buttons.<按钮>]`

每个按钮一张表，所有键都可省略。

| 键 | 范围 | 说明 |
|---|---|---|
| `x_dip` / `y_dip` | 0~2000 | 按钮框左上角相对背景图左上角的位置。两个都写了就固定在这里；否则按 `button_flow` 排 |
| `width_dip` / `height_dip` | >0 且 ≤500，默认 26 | 按钮框宽高 |
| `icon_size_dip` | >0 且 ≤500 | 没有贴图时内置矢量图标的字号；不写时是按钮框短边的 0.82 倍 |
| `visible` | 布尔 | `false` 时把这个按钮藏起来。皮肤只能藏；用户在设置页关掉的按钮写 `true` 也不会出现 |
| `background` | 包内图片路径 | 按钮自己的底图（比如圆底），拉满按钮框，画在按钮图或图标下面，跟着按钮一起显示、一起隐藏 |
| `image` | 包内图片路径 | 按钮图，在按钮框里等比缩放；各状态共用，`images` 里缺某个状态时也用它 |
| `[toolbar.buttons.<按钮>.images]` | 表 | 状态名 → 按钮图，只有有状态的按钮能写 |

按钮图的绘制顺序：`background`（最下面）→ `image` 或当前状态的图 → 都没有时画内置矢量图标（颜色取 `[toolbar.*].icon`）；鼠标悬停和按下时按钮上盖一层 `[toolbar.*].hover`。

**按钮底图请画在 `background`，不要画进背景图**：用户关掉按钮时底图会跟着消失；画进背景图就会留下一个空圆。

### 按钮名与状态名

| 按钮键 | 作用 | 可用状态名 |
|---|---|---|
| `status` | 中 / 英切换 | `cn`、`en`、`ja`、`caps`、`en-candidate` |
| `fullwidth` | 全 / 半角 | `full`、`half` |
| `punctuation` | 中 / 英标点 | `cn`、`en` |
| `character_set` | 简 / 繁 | `simplified`、`traditional` |
| `emoji` | 表情面板 | 无（只能写 `image`） |
| `screen_keyboard` | 屏幕键盘 | 无（只能写 `image`） |
| `settings` | 设置 | 无（只能写 `image`） |

未知按钮名、未知状态名只会在设置页诊断里提示，不会让皮肤加载失败。

## `[toolbar.button_defaults]`

所有按钮共用的默认值。只读取下面四个键，其它键静默忽略：

| 键 | 范围 |
|---|---|
| `width_dip` / `height_dip` | >0 且 ≤500 |
| `icon_size_dip` | >0 且 ≤500 |
| `background` | 包内图片路径 |

每个按钮没写的 `width_dip` / `height_dip` / `icon_size_dip` / `background` 就取这里的。

## `[toolbar.button_flow]`

没写坐标的按钮从这里开始排，不用逐个写坐标。

| 键 | 范围 | 说明 |
|---|---|---|
| `x_dip` / `y_dip` | 0~2000 | 第一个按钮框的左上角 |
| `direction` | `horizontal`（默认）/ `vertical` | 排列方向 |
| `gap_dip` | 0~500 | 按钮之间的空隙 |

- 只排**当前显示**的按钮，按按钮表的书写顺序；写了 `x_dip` 和 `y_dip` 的按钮固定在原处，不占队里的位置；`visible = false` 的也不占。
- 皮肤没写 `button_flow`、按钮又只写了一个坐标（或两个都没写）时，这个按钮不画；设置仍可从托盘菜单打开。
- 用户在设置页关掉某个按钮后：写了坐标的按钮那里就空着；按 `button_flow` 排的按钮后面的会往前补上。打开一个按钮时同理，皮肤没给它写表也会排进队里。

## 未知内容与模式混用

- 未知的按钮名、状态名不会让皮肤读不出来，只在设置页的诊断信息里提示一条。
- `mode` 不是 `image` 时写 `image` / `buttons` / `button_defaults` / `button_flow`：不报错，只在设置页诊断里提示「只在 mode = "image" 时生效，已忽略」。

## 可复制的 TOML 示例

```toml
[toolbar]
mode = "image"
image = "assets/toolbar.png"       # 换成真实文件
image_width_dip = 160
image_height_dip = 40

[toolbar.button_defaults]
width_dip = 26
height_dip = 26
icon_size_dip = 18
background = "assets/plate.png"

[toolbar.button_flow]
x_dip = 170
y_dip = 0
direction = "vertical"
gap_dip = 2

[toolbar.buttons.status]
x_dip = 10
y_dip = 7

[toolbar.buttons.status.images]
cn = "assets/cn.png"
en = "assets/en.png"

[toolbar.buttons.settings]
x_dip = 124
y_dip = 7
image = "assets/settings.png"
```

完整 v2 模板见 [templates/skin-v2.toml](templates/skin-v2.toml)。
