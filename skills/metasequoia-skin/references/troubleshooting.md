# 故障排查

先按这三步走，大多数问题在第一步就能定位：

1. 跑 `python scripts/check_skin.py <皮肤包目录>`：错误 = 包会被拒，按报错文案改；警告 = 能装但可能不符合预期。
2. 看设置页 → 皮肤 → 外部皮肤底部的诊断：被忽略的包展开就能看到原因，文案与脚本一致。
3. 改完让用户点「刷新皮肤」——这是全量重载，不需要重启输入法服务。

## 完整排查表

| 现象 | 原因 | 处理 |
|---|---|---|
| 设置页根本不显示这个皮肤 | 目录放错层级 / 目录里没有 `skin.toml` / `id` 与目录名不一致 / 目录名是 `default` 或 `.bak` 结尾 | 目录名 = `id`，`skin.toml` 在目录第一层 |
| 显示「缺少 candidate_window」 | manifest 没写 `[candidate_window]` 表 | 哪怕只写 `min_width_dip = 0` 也要有这张表 |
| 显示「目录名不是有效的外部皮肤 ID」 | 目录名含大写、空格、中文，或与内置皮肤 / `default` 同名 | 改成 `小写字母数字.-_` |
| 显示「candidate 配色无效」，但看着没写错 | 颜色值里有中文等非 ASCII 字符，或 `;`、`{}`、引号之类白名单外符号 | 全改成 `#rrggbb` / `#rrggbbaa` / `rgb()` / `rgba()` |
| 显示「candidate_window.backdrop 只能是 none、acrylic 或 mica」 | 写了别的材质名，或写成了布尔 | 三选一；不想要材质就把这行删掉 |
| 装饰图 / 背景图整段被拒 | 写了 `[candidate_window.decoration]` 却漏了 `image`，或两个尺寸没都给 | 表要么完整给，要么整段删掉；两个尺寸必须都 > 0 |
| 显示「candidate_window.page_arrows 必须是 true 或 false」/「fit_content 必须是 true 或 false」 | 写了 `1`、`"yes"` 之类 | 只能是 TOML 的 `true` / `false` |
| 显示「找不到 …image 文件」 | 路径写错、图片没跟着复制、或用了中文、空格、`%`、反斜杠等非法字符（大写字母是允许的） | 用 `assets/xxx.png` 这种纯 ASCII 相对路径 |
| 显示「candidate_window 的版式数值无效」 | 某个版式键写成了 `"10px"`、`"1.5EM"`、`"2"`（字符串不带 em），或数字越界、布尔键写了字符串 | 长度只写 DIP 数字或小写 `em` 字符串；比例 / 布尔按 [validation.md](validation.md) 的范围写 |
| 显示「candidate_window.border_image 缺少 source」/「缺少 slice_dip」 | 写了 `[candidate_window.border_image]` 但漏了必填键 | 两个键都补上；`slice_dip` 是源图像素，不是屏幕 DIP |
| 显示「candidate_window.border_image.source 无效（需为 .png、.apng、.gif 或 .webp）」 | v2 的面板图、挂件与工具栏图片只认这四种扩展名，SVG、JPG 会被直接拒 | 换成 PNG；要动图就用 `.apng` / `.gif` / 动画 `.webp` |
| 列表里有，但标了「当前布局或明暗模式不受支持」 | `supports` 没覆盖当前布局或明暗；或 `base` 是固定明暗的共享基底，声明里没有那一侧（被收窄掉了） | `layouts` 和 `themes` 四项全选；固定明暗基底的收窄规则见 [schema-v1.md](schema-v1.md#base-预设) |
| 切过去了但颜色还是老样子 | 键名拼错、颜色不是合法 CSS 颜色、或只改了 `dark` 而系统是浅色 | 用 `check_skin.py`；两组配色都写；确认系统 / 候选窗主题 |
| 候选文字颜色怎么改都不变 | 设置页的「候选文字颜色」压过了 `text` / `candidate_text` / `preedit_text` | 让用户在设置页改，或提示这层优先级 |
| 翻译的词性 / 分隔符颜色改了没反应 | 写了 `translation`，解析时会先把词性 / 分隔符拉成同色，再轮到你的细分键 | 显式写 `translation_pos` / `translation_separator` |
| 选中行文字和普通候选一个色了 | 只写了 `candidate_text`，没写 `selected_text` | 补 `selected_text` / `selected_number` |
| 高亮色和设置页预览不一样 | 没写全配色键，没写的走 `base` 的 D2D 令牌，而 `base` 自己还有一套 | 配色键全写 |
| 圆角改了没反应 | `corner_radius_dip` 超过 32，或写成了字符串 | 只接受 0~32 的数字 |
| `border_width_dip` 写了但看不到框 | `border_width_dip` 只管线宽，颜色取 `border`；`base = willow_green` / `autumn_osmanthus` 的边框色是全透明 | 同时在 `[candidate.*]` 给 `border` 一个非透明色，或换 base |
| 字体写了没变化 | `font_family` 只排在用户字体前面，缺字时回落用户字体；**字号不由皮肤决定** | 换个含目标汉字的字体名；字号去设置页调 |
| 莫名其妙多了翻页箭头 | `base = microsoft`，而 `microsoft` 出厂 `page_arrows = true` | 显式写 `page_arrows = false` |
| 翻页箭头不出现 | 写了 `page_arrows` 但 base 的默认清单 / 出厂值是关的且你的键没生效；或横排开了 `expand_panel`，卷轴展开优先 | 确认写的是 `[candidate_window]` 里的 `page_arrows = true`；卷轴展开时横排本来就不显示箭头，竖排仍生效 |
| 三角翻页箭头前没有分隔线 | `page_arrow_style = "triangle"` 只在**横排**画分隔线，且颜色取 `[candidate.*].page_arrow_divider`；不写就不画 | 在 `[candidate.dark]` / `[candidate.light]` 补 `page_arrow_divider`；竖排没有这条线 |
| 写了 `expand_panel` 没生效 | 写进了 `[candidate_window.horizontal]`（那是版式子表，不认识这个键）；或用户看的是竖排；或 `supports.layouts` 没开横排 | 把 `expand_panel = true` 写进 `[candidate_window]` 直接键；卷轴展开只在横排生效 |
| 写了 `expand_rows` 没变化 | `expand_panel` 没开（也没有从 base 继承到 `true`），或值不是 2~8 的整数 | 先开 `expand_panel`；`expand_rows` 写整数，默认 4 |
| 版式数值写了却和没写一样 | 用了 `"10px"`、`"1.5EM"` 这类写法，Server 直接忽略整个包的版式；或 em 换算后四舍五入成 0 | 只写 DIP 数字或小写 `em` 字符串；`"0.3em"` 会按候选字号取整 |
| 卡片总是被最长那行撑宽 | `fit_content` 没写（出厂默认关，还垫 160 DIP 的出厂最小宽度） | 在 `[candidate_window]` 写 `fit_content = true`；嫌太窄再用 `min_width_dip` 兜底 |
| 背景图看不见 | `opacity` 太小，或图比 `surface` 还暗 | 先把 `opacity` 提到 0.5 以上看效果 |
| 装饰图和卡片挤在一起 | 装饰图 `width_dip` 太宽，卡片被迫撑宽 | 减小 `width_dip`，或提高 `min_width_dip` 让卡片稳定 |
| 装饰图上叠加的候选词没出现 | `candidate_overlay` 不是 `true`；`candidate_overlay_index` 超出当前页候选数（`0` 跟随高亮，`1` 是第一个）；或文字颜色和装饰图撞色 | 开 `candidate_overlay = true`，把 `index` 调到当前页有的候选；换 `candidate_overlay_color` |
| 写了 `toolbar.css` 没反应 | 外部皮肤已经不支持任何 CSS，工具栏只认 `[toolbar]` 表 | 把样式翻译成 `[toolbar.dark]` / `[toolbar.light]` 的颜色键 |
| 工具栏悬停色预览不出来 | 设置页预览不模拟悬停（预览宿主不吃指针事件） | 属正常，值本身是生效的 |
| 工具栏图片模式按钮不显示 | 没写 `button_flow` 又只写了一个坐标 / 两个坐标都没写；按钮名拼错；`visible = false`；用户在设置页关掉了这个按钮 | 要么 `x_dip` + `y_dip` 都写，要么写 `[toolbar.button_flow]`；按钮名只能用 status / fullwidth / punctuation / character_set / emoji / screen_keyboard / settings |
| 工具栏图片模式整段没生效 | `mode` 不是 `"image"`（默认是 `bar`），或 `image` / `image_width_dip` / `image_height_dip` 缺一个 | 三件套一起写；bar 模式下这些键只会被提示忽略 |
| 工具栏按钮的圆底留在图上 | 把按钮底图画进了背景图，而不是按钮的 `background` | 底图改放 `[toolbar.buttons.<按钮>].background` 或 `button_defaults.background` |
| 颜色写了 `rgba(0,0,0,0)` 之类看不见 | 透明度 0 | 脚本会警告 |
| 写了 `border_image` / `decorations` 之类完全没反应 | `schema_version` 不是 `2`，或者写了 `2` 但 `base` 不是 `canvas` | `schema_version = 2` 和 `base = "canvas"` 一起写 |
| 显示「base = "canvas" 只能用于 schema_version = 2 的皮肤」 | v1 皮肤用了 `canvas` | 要么改成 `schema_version = 2` 并补上面板图，要么换回内置基底 |
| 设置页诊断里出现「candidate_window.border_image 只在 base = "canvas" 时生效，已忽略」之类的提示 | v2 字段被整段忽略，皮肤是按 v1 加载的 | 把 `base` 改成 `canvas`（`check_skin.py` 对应的提示是「schema_version = 2 需要 base = "canvas"」） |
| v2 候选框里只有悬空文字、没有面板 | `canvas` 只是透明地基，没写 `[candidate_window.border_image]` | 补一张九宫格面板图 |
| 亚克力 / 云母没生效，卡片仍是不透明 | 系统关了「透明效果」（设置 → 个性化 → 颜色）；系统太老（低于 Windows 10 1903，云母还要 Windows 11）；或同时写了 `border_image`（有面板图就不垫材质） | 让用户打开透明效果 / 升级系统；只能留一种时只留一个 |
| 面板贴图被横着拉长 | 图里画死的装饰落进了可拉伸区 | 用 `stretch_dip` 把可拉伸区收窄到纯纹理处 |
| 九宫格写了 `repeat` 还是被拉长 / 花纹重复得不对 | `repeat` 写错了位置（应在 `[candidate_window.border_image]` 或 `.vertical` 里）；值不是 `stretch` / `repeat`；或装饰画在了边块里，平铺时被一块块重复 | 确认 `repeat = "repeat"` 或 `repeat = ["stretch", "repeat"]`；一次性装饰放回四角或改用 `stretch_dip` 排除边块 |
| 竖排面板图错位 / 横排的图套到竖排上 | 没写 `[candidate_window.border_image.vertical]` 的 `source` / `slice_dip`（`source` 会继承横排）；或竖排用了横排的切片；或以为 `light_source` 会继承 | 竖排单独给一张图并写自己的 `slice_dip`；要浅色变体就单独写 `.vertical.light_source` |
| 竖排文字离边框太近 / 横排的留白套到了竖排 | 只写了横排 `content_insets_dip`，竖排面板更窄时左右边距不够 | 补 `[candidate_window.content_insets_dip.vertical]`，只写要覆盖的边 |
| 候选文字压在贴图花纹上 / 离边框太近 | 没写 `content_insets_dip`，内容按「边宽 + 5 DIP」排 | 按面板外缘给四边 `content_insets_dip` |
| 浅色主题面板还是深色的 | 只写了 `source`，没写 `light_source`；或两张图的切片 / 边宽不一致 | 补 `light_source`，并让它和 `source` 用同一套几何 |
| 挂件被窗口边界切掉 | 没写 `outer_insets_dip`，或数值小于挂件超出卡片的距离 | 给超出那几边补 `outer_insets_dip` |
| 挂件盖住了候选文字 | 默认 `z_index = 2` 在面板与文字之上 | 调 `offset_x_dip` / `offset_y_dip` 挪开，或把 `z_index` 写到 1 以下让它落到面板后面（只有伸出面板的部分看得见） |
| 挂件图和框对不上、四周留白 | 图片在框内 `contain` 等比缩放、居中，`width_dip` / `height_dip` 与图片比例不一致就会留白 | 按图片宽高比给两个尺寸 |
| 挂件动图不动 | v1 皮肤里的图片从不播动画；系统关了「动画效果」（设置 → 辅助功能 → 视觉效果）；或这张图超过 1024 帧 / 解码后超过 64 MB / 文件损坏 | 确认是 `schema_version = 2` + `base = "canvas"` 的皮肤；其余属于系统设置或文件本身的问题 |
| 写了 `[[decorations]]` 却没有挂件效果 | 挂件不参与布局：伸到卡片外的部分没留白就被裁掉，`z_index < 1` 的只在面板外露出来；图片路径也可能写错 | 补 `outer_insets_dip`；用 `check_skin.py` 确认图片存在 |
