#!/usr/bin/env python3
"""水杉输入法外部皮肤校验器。

规则逐条对齐 Server 的解析实现 server/src/skin/candidate_skin_catalog.cpp（CandidateSkinCatalog::Load），
错误文案也沿用同一套中文，方便和设置页「皮肤 → 外部皮肤」底部的诊断信息对照。

支持 schema_version 1（通用卡片皮肤）与 2（canvas 全贴图基底：九宫格面板、自由挂件、面板内安全内边距、
行距、面板外留白）。v2 必须以 base = "canvas" 为基底：写了 2 而 base 不是 canvas 的皮肤按 v1 加载，
其中的 v2 字段（连同其中的错误）被忽略，只多一条警告；schema_version = 1 用 canvas 直接报错。

还覆盖 v1 的版式几何（[candidate_window] 与 horizontal / vertical 子表）、卷轴展开（expand_panel /
expand_rows）、翻页箭头样式（page_arrow_style / page_arrow_divider）、工具栏图片模式（[toolbar]
mode = "image"、[toolbar.buttons.*]、button_defaults、button_flow）、装饰图叠加候选（candidate_overlay_*），
以及 v2 的九宫格 repeat 与竖排覆盖（[border_image.vertical]、[content_insets_dip.vertical]）。

用法：
    uv run check_skin.py <皮肤包目录>      # 目录里应有 skin.toml
    uv run check_skin.py <skins 根目录>    # 目录本身没有 skin.toml 时，扫描其下所有子目录

退出码：0 = 全部通过（允许有警告），1 = 存在错误。
需要 Python 3.11+（用标准库 tomllib 解析 TOML，无第三方依赖）。
"""

from __future__ import annotations

import math
import re
import string
import sys
import tomllib
from pathlib import Path

# candidate_skin_catalog.cpp:BuiltInIds —— 与内置皮肤同名的目录会被当成内置 ID 拒绝。
BUILTIN_IDS = {
    "fluent",
    "wechat",
    "wechat_scroll",
    "graphite",
    "willow_green",
    "autumn_osmanthus",
    "microsoft",
}
# kDefaultSkinsFolder：内置皮肤的设置清单目录，Scan 跳过它，也不能被当成外部皮肤加载。
RESERVED_IDS = {"default"}
# kDefaultPageArrows / skins/default/<base>/skin.toml：内置皮肤翻页箭头的出厂值（microsoft 打开，
# 其余关闭；canvas 的出厂值取 fluent）。fit_content 出厂一律为 false。
DEFAULT_PAGE_ARROWS = {"microsoft": True}
# kDefaultExpandPanel：内置皮肤卷轴展开的出厂值（wechat_scroll 打开，其余关闭；canvas 取 fluent）。
DEFAULT_EXPAND_PANEL = {"wechat_scroll": True}
# 共享基底来自 msime 的固定主题，按 fluent 的结构绘制并补上基底配色；system 跟随宿主没有调色板。
SHARED_BASES = {"system", "shuishan", "light", "paper", "night", "ink"}
# 全贴图基底：只用于 v2，面板外观完全由九宫格与挂件决定。
CANVAS_BASE = "canvas"
ALL_BASES = BUILTIN_IDS | SHARED_BASES | {CANVAS_BASE}
# 这两个 base 的基础样式是 border: none，只写线宽看不到框，必须同时给 border 颜色。
NO_FRAME_BASES = {"willow_green", "autumn_osmanthus"}

LAYOUTS = ("horizontal", "vertical")
THEMES = ("dark", "light")
ALIGNMENTS = ("left", "center", "right")
FITS = ("cover", "contain", "stretch")
SHADOWS = ("none", "soft", "strong")
# ReadGeometry 的 page_arrow_style：chevron 折线 / triangle 实心三角。
PAGE_ARROW_STYLES = ("chevron", "triangle")
# ReadGeometry 里各长度键的 (DIP 上限, em 上限)。em 按候选字号换算后取整。
GEOMETRY_LENGTH_LIMITS = {
    "padding": (64.0, 4.0),
    "item_gap": (64.0, 4.0),
    "item_extra_height": (64.0, 4.0),
    "number_inset": (64.0, 4.0),
    "item_padding_right": (64.0, 4.0),
    "item_min_width": (500.0, 40.0),
    "number_gap": (64.0, 4.0),
    "selected_bar_width": (16.0, 1.0),
}
# 版式里直接按数字上限的键（ReadOptionalBounded）。
GEOMETRY_NUMBER_LIMITS = {
    "number_scale": 2.0,
    "selected_bar_height_em": 2.0,
}
GEOMETRY_BOOL_KEYS = (
    "selected_bar_inside",
    "item_corners_follow_card",
    "justify_rows",
    "trim_hidden_preedit_gap",
)
# [candidate_window.border_image] / .vertical 的 repeat：stretch（拉伸）或 repeat（按源图平铺）。
BORDER_IMAGE_REPEATS = ("stretch", "repeat")
# [toolbar] mode：bar（矩形条）/ image（整张背景图）。
TOOLBAR_MODES = ("bar", "image")
TOOLBAR_FLOW_DIRECTIONS = ("horizontal", "vertical")
# ToolbarButtonStates：按钮键 → 状态名。无状态按钮的 images 表直接报错。
TOOLBAR_BUTTON_STATES = {
    "status": ("cn", "en", "ja", "caps", "en-candidate"),
    "fullwidth": ("full", "half"),
    "punctuation": ("cn", "en"),
    "character_set": ("simplified", "traditional"),
    "emoji": (),
    "screen_keyboard": (),
    "settings": (),
}
# v2：[[candidate_window.decorations]] 的 anchor 白名单。
ANCHORS = (
    "top-left",
    "top-right",
    "bottom-left",
    "bottom-right",
    "left",
    "right",
    "top",
    "bottom",
    "center",
)
# v2：content_insets_dip 与 outer_insets_dip 的四边上限（C++ 里两边不同）。
CONTENT_INSET_BOUNDS = {"top": 200.0, "right": 500.0, "bottom": 200.0, "left": 500.0}
OUTER_INSET_BOUNDS = {"top": 500.0, "right": 500.0, "bottom": 500.0, "left": 500.0}
# v2 专有的 [candidate_window] 键：写在 schema_version = 1 里会被静默忽略。
V2_WINDOW_KEYS = (
    "border_image",
    "content_insets_dip",
    "line_gap_dip",
    "outer_insets_dip",
    "decorations",
)
# 动图扩展名：IsAnimatableImagePath。v2 的 border_image 与挂件只接受这四种。
ANIMATABLE_SUFFIXES = (".png", ".apng", ".gif", ".webp")
# 固定明暗的共享基底（SharedBase 表）：加载时 themes 被收窄成对应明暗（全不支持时收窄成空），
# base 同时被改写成 fluent；system 跟随宿主，不收窄。
FIXED_THEME_SHARED_BASES = {
    "shuishan": "dark",
    "light": "light",
    "paper": "light",
    "night": "dark",
    "ink": "dark",
}

# ReadColors 逐键检查的基础配色键，值上限 80 字节。
BASE_COLOR_KEYS = (
    "accent",
    "selected",
    "hover",
    "surface",
    "border",
    "text",
    "number",
    "translation",
)
# ReadColors 逐键检查的细分配色键，值上限 80 字节。
DETAIL_COLOR_KEYS = (
    "candidate_text",
    "preedit_text",
    "preedit_caret",
    "selected_text",
    "selected_number",
    "selected_translation",
    "selected_bar",
    "preedit_background",
    "preedit_divider",
    "page_arrow_divider",
)
# 翻译里的词性标记（`.cand-translation .cand-pos`）与义项分隔符（`.cand-sep`）可以单独配色，
# 选中行另有四个对应的 selected_ 键；都不写时与 translation 同色。
# 依据：examples/skin-examples/schema/README.md 的颜色格式表，上游是
# server/src/window/candidate_presenter.cpp 的 SetTranslationColors / SetSelectedTranslationColors。
TRANSLATION_RUN_COLOR_KEYS = (
    "translation_pos",
    "translation_separator",
    "selected_translation_pos",
    "selected_translation_separator",
)
CANDIDATE_COLOR_KEYS = BASE_COLOR_KEYS + DETAIL_COLOR_KEYS + TRANSLATION_RUN_COLOR_KEYS
# [candidate.dark.menu] / [candidate.light.menu] 的四个键，同样走 ReadCssColor。
MENU_COLOR_KEYS = ("background", "border", "text", "hover")
# ReadToolbarColors 逐键检查的工具栏配色键，值上限 80 字节。
TOOLBAR_COLOR_KEYS = ("background", "border", "handle", "divider", "icon", "hover")

# ReadCssColor 只放行颜色值会用到的字符，挡住 `;`、`{}` 之类能跳出 CSS 声明的写法。
CSS_COLOR_CHARS = set(string.ascii_letters + string.digits + "#(),.% -/")

# 动图文件上限：ui/include/msimeui/AnimatedImage.h 的 maxFileBytes，与 README 的 64MB 帧预算同源。
# 超过它的图片按静态首帧显示（皮肤仍可用，所以只给警告）。
ANIMATED_FILE_LIMIT_BYTES = 64 * 1024 * 1024

# IsSafeId：首字符 isalnum，其余 islower / isdigit / '.' / '_' / '-'，总长 ≤ 64。
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
# IsSafeRelativeResource：图片相对路径的字符集（区分大小写，允许大写字母）。
RESOURCE_PATTERN = re.compile(r"[A-Za-z0-9._/-]+\Z")
# ReadFontFamily：字体名会被拼进引号包裹的 CSS font-family 与脚本字符串。
FONT_FORBIDDEN = "\"'\\,;{}<>`"
FONT_PATTERN = re.compile(r"[^\x00-\x1f\x7f\"'\\,;{}<>`]+\Z")
# IsBackupFolder：安装包覆盖前留下的 <id>.bak / <id>.2.bak，Scan 跳过。
BACKUP_SUFFIX_PATTERN = re.compile(r"\.bak\Z", re.IGNORECASE)


def byte_len(text: str) -> int:
    # C++ 侧按 std::string 的字节数比较上限，中文 name/description 必须同样按 UTF-8 字节算。
    return len(text.encode("utf-8"))


def read_string(
    table: dict, key: str, maximum: int, required: bool
) -> tuple[bool, str | None]:
    """对应 ReadString：返回 (是否合法, 值)。"""
    if key not in table:
        return (not required), None
    value = table[key]
    if not isinstance(value, str):
        return False, None
    if required and not value:
        return False, None
    if byte_len(value) > maximum:
        return False, None
    return True, value


def read_enum_array(
    table: dict, key: str, allowed: tuple[str, ...]
) -> tuple[bool, list[str] | None]:
    """对应 ReadEnumArray：非空、元素全在白名单内、无重复。"""
    if key not in table:
        return False, None
    value = table[key]
    if not isinstance(value, list) or not value:
        return False, None
    out: list[str] = []
    for item in value:
        if not isinstance(item, str):
            return False, None
        if item not in allowed or item in out:
            return False, None
        out.append(item)
    return True, out


def read_enum(
    table: dict, key: str, allowed: tuple[str, ...]
) -> tuple[bool, str | None]:
    """对应 ReadEnum：缺省放行，写了就必须在白名单内且不超过 32 字节。"""
    if key not in table:
        return True, None
    ok, value = read_string(table, key, 32, True)
    if not ok or value is None or value not in allowed:
        return False, None
    return True, value


def numeric_value(value: object) -> float | None:
    """TOML 数字取值：bool 是 int 的子类但不算数字，NaN / inf 也拒绝。

    tomllib 会把超出 64 位范围的整数原样读成 Python int，转 float 可能溢出；
    C++ 侧 toml++ 会把它当解析失败，这里同样按非法值处理，别让脚本崩掉。
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            number = float(value)
        except OverflowError:
            return None
        return number if math.isfinite(number) else None
    return None


def bounded_value(value: object, maximum: float) -> float | None:
    """BoundedNumber 的单值版本：非数字、负数、越界、NaN 都返回 None。"""
    number = numeric_value(value)
    if number is None or number < 0.0 or number > maximum:
        return None
    return number


def bounded_number(table: dict, key: str, maximum: float) -> float | None:
    """对应 BoundedNumber：缺省 0.0；越界/类型错返回 None（C++ 返回 -1 表示非法）。"""
    if key not in table:
        return 0.0
    return bounded_value(table[key], maximum)


def read_slice_array(
    table: dict, key: str, maximum: float = 500.0
) -> tuple[str, list[float]]:
    """对应 border_image 的 slice_dip / stretch_dip / width_dip。

    返回 (状态, 值)，状态取自：
      "absent"   没写这个键（三个键里只有它不算错，slice_dip 缺了会报错）
      "not-list" 写了但不是数组（三个键都会因此报错）
      "shape"    数组长度不是 1、2 或 4
      "value"    数组里有没有 0~maximum 之外的值
      "ok"       合法
    """
    if key not in table:
        return "absent", []
    value = table[key]
    if not isinstance(value, list):
        return "not-list", []
    if len(value) not in (1, 2, 4):
        return "shape", []
    out: list[float] = []
    for item in value:
        number = bounded_value(item, maximum)
        if number is None:
            return "value", []
        out.append(number)
    return "ok", out


def read_optional_bounded(table: dict, key: str, maximum: float) -> bool:
    """对应 ReadOptionalBounded：缺省放行，写了就必须是 0~maximum 的数字。"""
    if key not in table:
        return True
    return bounded_number(table, key, maximum) is not None


def read_border_image_repeat(table: dict) -> bool:
    """对应 ReadBorderImageRepeat：stretch / repeat，1 个或 2 个值（横向 纵向）。"""
    if "repeat" not in table:
        return True
    value = table["repeat"]
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = value
    else:
        return False
    if not values or len(values) > 2:
        return False
    return all(
        isinstance(item, str) and item in BORDER_IMAGE_REPEATS for item in values
    )


def read_length(table: dict, key: str, maximum: float, maximum_em: float) -> bool:
    """对应 ReadLength：缺省放行；写了可以是 0~maximum 的 DIP 数字，或 "<数值>em"。

    em 的上限按 maximum_em 单独判断（如 item_min_width 是 40em，其他版式键是 4em）。
    C++ 用 from_chars 解析，只接受完整的十进制/科学计数写法；这里用 float 校验后
    再用 isfinite 挡住 nan / inf。
    """
    if key not in table:
        return True
    value = table[key]
    if isinstance(value, str):
        if len(value) < 3 or not value.endswith("em"):
            return False
        number_text = value[:-2]
        # std::from_chars 的十进制模式同 strtod：接受 ".5" 和 "1."，不接受 "+1"；
        # 负值由下面的 0 <= number 判断拒绝（"-0" 在 C++ 里同样算 0）。
        if not re.fullmatch(
            r"-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?",
            number_text,
        ):
            return False
        try:
            number = float(number_text)
        except ValueError:
            return False
        return math.isfinite(number) and 0.0 <= number <= maximum_em
    return bounded_value(value, maximum) is not None


def read_geometry(table: dict) -> bool:
    """对应 ReadGeometry：版式长度、比例、布尔与 page_arrow_style。

    [candidate_window]、[candidate_window.horizontal] 与 [candidate_window.vertical] 共用这套键；
    任何一项类型或范围不对，Server 都报「candidate_window 的版式数值无效」。
    """
    for key, (maximum, maximum_em) in GEOMETRY_LENGTH_LIMITS.items():
        if not read_length(table, key, maximum, maximum_em):
            return False
    for key, maximum in GEOMETRY_NUMBER_LIMITS.items():
        if key in table and bounded_value(table[key], maximum) is None:
            return False
    for key in GEOMETRY_BOOL_KEYS:
        if not read_optional_bool(table, key):
            return False
    if "page_arrow_style" in table:
        ok, _ = read_enum(table, "page_arrow_style", PAGE_ARROW_STYLES)
        if not ok:
            return False
    # preedit_margin_dip 用 ReadBoxValues：1 / 2 / 4 个 0~500 的数值，按 CSS 简写展开。
    state, _ = read_slice_array(table, "preedit_margin_dip")
    if state not in ("absent", "ok"):
        return False
    return True


def read_optional_bool(table: dict, key: str) -> bool:
    """对应 ReadOptionalBool：缺省放行，写了就必须是布尔。"""
    if key not in table:
        return True
    return isinstance(table[key], bool)


def is_safe_relative_resource(name: str) -> bool:
    """对应 IsSafeRelativeResource：图片路径必须是皮肤目录内的相对路径。"""
    if not name or byte_len(name) > 256 or name[0] in "/\\" or "\\" in name:
        return False
    if not RESOURCE_PATTERN.match(name):
        return False
    # std::filesystem::path 会把连续的内部分隔符压成一个（"assets//a.png" 能过），
    # 但末尾的 "/" 会留下一个空组件（"assets/a.png/" 会被拒）。
    if name.endswith("/"):
        return False
    return all(part not in (".", "..") for part in name.split("/") if part)


def is_animatable_image_path(name: str) -> bool:
    """对应 IsAnimatableImagePath：取整个路径最后一个 '.'，其后不能再有 '/'。

    不能用 Path().suffix：末段以点开头（如 ".png"）时 pathlib 认为没有后缀，
    而 C++ 会取到 ".png" 并放行。
    """
    dot = name.rfind(".")
    if dot == -1 or "/" in name[dot:]:
        return False
    return name[dot:].lower() in ANIMATABLE_SUFFIXES


def read_resource(table: dict, key: str) -> tuple[bool, str | None]:
    """对应 ReadResource：必须是包内相对路径；键不存在时同样返回成功（与 C++ 一致）。"""
    if key not in table:
        return True, None
    ok, value = read_string(table, key, 256, True)
    if not ok or value is None or not is_safe_relative_resource(value):
        return False, None
    return True, value


def read_css_color(table: dict, key: str) -> tuple[bool, str | None]:
    """对应 ReadCssColor：非空限制的字符串、≤80 字节、字符集只放行颜色值会用的那些。

    字符集是纯 ASCII 白名单，所以「红色」「lightblue」这类非十六进制写法在这里就被拒。
    """
    ok, value = read_string(table, key, 80, False)
    if not ok:
        return False, None
    if value is not None and not set(value) <= CSS_COLOR_CHARS:
        return False, None
    return True, value


def read_candidate_colors(table: object) -> tuple[bool, dict[str, object], bool]:
    """对应 ReadColors。

    返回 (是否合法, 读到的键值, 表是否不是普通表)。C++ 里 as_table() 拿不到表就整段跳过、
    不报错；这里把这种情况单拎出来，只给警告。
    """
    if table is None:
        return True, {}, False
    if not isinstance(table, dict):
        return True, {}, True
    for key in CANDIDATE_COLOR_KEYS:
        if key in table and not read_css_color(table, key)[0]:
            return False, {}, False
    if "show_selected_bar" in table and not isinstance(
        table["show_selected_bar"], bool
    ):
        return False, {}, False
    menu = table.get("menu")
    if menu is not None:
        if not isinstance(menu, dict):
            return False, {}, False
        for key in MENU_COLOR_KEYS:
            if key in menu and not read_css_color(menu, key)[0]:
                return False, {}, False
    for key in ("backdrop_opacity", "backdrop_luminosity"):
        if key in table and bounded_value(table[key], 1.0) is None:
            return False, {}, False
    return (
        True,
        {key: table[key] for key in CANDIDATE_COLOR_KEYS if key in table},
        False,
    )


def read_menu_colors(table: object) -> tuple[bool, dict[str, str]]:
    """对应 ReadColors 里的 menu 分支：表可选，写了就必须是表且逐键过白名单。"""
    if table is None:
        return True, {}
    if not isinstance(table, dict):
        return False, {}
    out: dict[str, str] = {}
    for key in MENU_COLOR_KEYS:
        ok, value = read_css_color(table, key)
        if not ok:
            return False, {}
        if value is not None:
            out[key] = value
    return True, out


def read_toolbar_colors(table: object) -> tuple[bool, dict[str, str]]:
    """对应 ReadToolbarColors：必须是表，且每个颜色值过一遍 CSS 字符白名单。"""
    if table is None:
        return True, {}
    if not isinstance(table, dict):
        return False, {}
    out: dict[str, str] = {}
    for key in TOOLBAR_COLOR_KEYS:
        if key not in table:
            continue
        ok, value = read_string(table, key, 80, False)
        if not ok or value is None:
            return False, {}
        if not set(value) <= CSS_COLOR_CHARS:
            return False, {}
        out[key] = value
    return True, out


def validate_decoration_overlay(decoration: dict, warnings: list[str]) -> list[str]:
    """对应 ReadDecorationCandidate：候选词叠加到装饰图上的那组键。

    candidate_overlay 不是 true 时，Server 不读其余 candidate_overlay_* 键；这里只提醒一句，
    不按它们的值报错。
    """
    enabled = decoration.get("candidate_overlay")
    if "candidate_overlay" in decoration and not isinstance(enabled, bool):
        return ["candidate_window.decoration.candidate_overlay 必须是 true 或 false"]
    if enabled is not True:
        if any(key.startswith("candidate_overlay_") for key in decoration):
            warnings.append(
                "candidate_window.decoration 写了 candidate_overlay_* 键，但 "
                "candidate_overlay 不是 true，这些键不会生效"
            )
        return []

    errors: list[str] = []
    for key in (
        "candidate_overlay_font_size_dip",
        "candidate_overlay_min_font_size_dip",
    ):
        if key in decoration:
            number = bounded_value(decoration[key], 200.0)
            if number is None or number <= 0.0:
                return [
                    "candidate_window.decoration 的 candidate_overlay_font_size_dip 与 "
                    "candidate_overlay_min_font_size_dip 必须是大于 0、不超过 200 的数值"
                ]
    if "candidate_overlay_max_width_dip" in decoration:
        if bounded_value(decoration["candidate_overlay_max_width_dip"], 2000.0) is None:
            return [
                "candidate_window.decoration.candidate_overlay_max_width_dip 必须是 0–2000 的数值"
            ]
    if "candidate_overlay_color" in decoration:
        ok, _ = read_css_color(decoration, "candidate_overlay_color")
        if not ok:
            return ["candidate_window.decoration.candidate_overlay_color 无效"]
    align_h_ok, _ = read_enum(decoration, "candidate_overlay_align_h", ALIGNMENTS)
    align_v_ok, _ = read_enum(
        decoration, "candidate_overlay_align_v", ("top", "center", "bottom")
    )
    if not align_h_ok or not align_v_ok:
        return [
            "candidate_window.decoration 的 candidate_overlay_align_h 只能是 left、center 或 right，"
            "candidate_overlay_align_v 只能是 top、center 或 bottom"
        ]
    for key in ("candidate_overlay_offset_x_dip", "candidate_overlay_offset_y_dip"):
        if key in decoration:
            number = numeric_value(decoration[key])
            if number is None or abs(number) > 2000.0:
                return [
                    "candidate_window.decoration 的 candidate_overlay_offset_x_dip / "
                    "candidate_overlay_offset_y_dip 必须在 -2000–2000 之间"
                ]
    if "candidate_overlay_strip_badge" in decoration and not isinstance(
        decoration["candidate_overlay_strip_badge"], bool
    ):
        return [
            "candidate_window.decoration.candidate_overlay_strip_badge 必须是 true 或 false"
        ]
    if "candidate_overlay_index" in decoration:
        index = decoration["candidate_overlay_index"]
        if (
            isinstance(index, bool)
            or not isinstance(index, int)
            or not 0 <= index <= 100
        ):
            return [
                "candidate_window.decoration.candidate_overlay_index 必须是 0–100 的整数"
            ]
    return errors


def validate_toolbar_image_mode(
    toolbar: dict, warnings: list[str]
) -> tuple[list[str], list[tuple[str, str]]]:
    """对应 ReadToolbarImageMode：mode、背景图尺寸、按钮、button_defaults 与 button_flow。

    返回 (错误, 图片引用)。图片引用是 (相对路径, 找不到时的报错文案)；bar 模式不检查文件存在。
    mode 不是 image 时 Server 仍会解析这些键（写错照样拒收），只是最终不生效并记一条提示。
    """
    mode_ok, mode_value = read_enum(toolbar, "mode", TOOLBAR_MODES)
    if not mode_ok:
        return ["toolbar.mode 只能是 bar 或 image"], []
    mode = mode_value or "bar"

    image: str | None = None
    if "image" in toolbar:
        image_ok, image_value = read_resource(toolbar, "image")
        if (
            not image_ok
            or image_value is None
            or not is_animatable_image_path(image_value)
        ):
            return [
                "toolbar.image 无效（需为皮肤目录里的 .png、.apng、.gif 或 .webp）"
            ], []
        image = image_value

    width: float | None = 0.0
    height: float | None = 0.0
    if "image_width_dip" in toolbar:
        width = bounded_value(toolbar["image_width_dip"], 2000.0)
    if "image_height_dip" in toolbar:
        height = bounded_value(toolbar["image_height_dip"], 2000.0)
    if width is None or height is None:
        return ["toolbar.image_width_dip / image_height_dip 必须是 0–2000 的数值"], []

    buttons: dict[str, dict] = {}
    if "buttons" in toolbar:
        raw_buttons = toolbar["buttons"]
        if not isinstance(raw_buttons, dict):
            return ["toolbar.buttons 必须是表"], []
        for key, node in raw_buttons.items():
            states = TOOLBAR_BUTTON_STATES.get(key)
            if states is None:
                warnings.append(f"没有 toolbar.buttons.{key} 这个按钮，已忽略")
                continue
            if not isinstance(node, dict):
                return [f"toolbar.buttons.{key} 必须是表"], []
            if "visible" in node and not isinstance(node["visible"], bool):
                return [f"toolbar.buttons.{key}.visible 必须是 true 或 false"], []
            for coordinate in ("x_dip", "y_dip"):
                if (
                    coordinate in node
                    and bounded_value(node[coordinate], 2000.0) is None
                ):
                    return [
                        f"toolbar.buttons.{key} 的 x_dip / y_dip 必须是 0–2000 的数值"
                    ], []
            look_error, background = read_toolbar_button_look(
                node, f"toolbar.buttons.{key}"
            )
            if look_error:
                return [look_error], []
            button_image: str | None = None
            if "image" in node:
                image_ok, image_value = read_resource(node, "image")
                if (
                    not image_ok
                    or image_value is None
                    or not is_animatable_image_path(image_value)
                ):
                    return [
                        f"toolbar.buttons.{key}.image 无效（需为皮肤目录里的 .png、.apng、.gif 或 .webp）"
                    ], []
                button_image = image_value
            state_images: list[tuple[str, str]] = []
            if "images" in node:
                raw_images = node["images"]
                if not isinstance(raw_images, dict):
                    return [f"toolbar.buttons.{key}.images 必须是表"], []
                if not states:
                    return [
                        f"toolbar.buttons.{key} 没有状态之分，只能写 image，不能写 images"
                    ], []
                for state, path in raw_images.items():
                    if (
                        not isinstance(path, str)
                        or not is_safe_relative_resource(path)
                        or not is_animatable_image_path(path)
                    ):
                        return [
                            f"toolbar.buttons.{key}.images.{state} 无效"
                            "（需为皮肤目录里的 .png、.apng、.gif 或 .webp）"
                        ], []
                    if state not in states:
                        warnings.append(
                            f"toolbar.buttons.{key}.images 里的 {state} 不是这个按钮的状态，已忽略"
                        )
                        continue
                    state_images.append((state, path))
            buttons[key] = {
                "background": background,
                "image": button_image,
                "states": state_images,
                "x": node.get("x_dip"),
                "y": node.get("y_dip"),
            }

    defaults_background: str | None = None
    if "button_defaults" in toolbar:
        raw_defaults = toolbar["button_defaults"]
        if not isinstance(raw_defaults, dict):
            return ["toolbar.button_defaults 必须是表"], []
        look_error, defaults_background = read_toolbar_button_look(
            raw_defaults, "toolbar.button_defaults"
        )
        if look_error:
            return [look_error], []

    flow: dict | None = None
    if "button_flow" in toolbar:
        raw_flow = toolbar["button_flow"]
        if not isinstance(raw_flow, dict):
            return ["toolbar.button_flow 必须是表"], []
        for coordinate in ("x_dip", "y_dip"):
            if coordinate in raw_flow:
                number = numeric_value(raw_flow[coordinate])
                if number is None or not 0.0 <= number <= 2000.0:
                    return [
                        "toolbar.button_flow 的 x_dip / y_dip 必须是 0–2000 的数值"
                    ], []
        direction_ok, _ = read_enum(raw_flow, "direction", TOOLBAR_FLOW_DIRECTIONS)
        if not direction_ok:
            return ["toolbar.button_flow.direction 只能是 horizontal 或 vertical"], []
        if "gap_dip" in raw_flow:
            number = numeric_value(raw_flow["gap_dip"])
            if number is None or not 0.0 <= number <= 500.0:
                return ["toolbar.button_flow.gap_dip 必须是 0–500 的数值"], []
        flow = raw_flow

    if mode != "image":
        if (
            image is not None
            or buttons
            or "button_defaults" in toolbar
            or "button_flow" in toolbar
        ):
            warnings.append(
                "toolbar 的 image、buttons、button_defaults 与 button_flow 只在 "
                'mode = "image" 时生效，已忽略'
            )
        return [], []

    errors: list[str] = []
    references: list[tuple[str, str]] = []
    if (
        image is None
        or width is None
        or width <= 0.0
        or height is None
        or height <= 0.0
    ):
        return [
            'toolbar.mode = "image" 需要同时写 image、image_width_dip 与 image_height_dip'
        ], []
    references.append((image, "找不到 toolbar.image 文件"))
    if defaults_background:
        references.append(
            (defaults_background, "找不到 toolbar.button_defaults.background 文件")
        )
    for key, button in buttons.items():
        if button["image"]:
            references.append(
                (button["image"], f"找不到 toolbar.buttons.{key}.image 文件")
            )
        if button["background"]:
            references.append(
                (button["background"], f"找不到 toolbar.buttons.{key}.background 文件")
            )
        for state, path in button["states"]:
            references.append(
                (
                    path,
                    f"找不到 toolbar.buttons.{key}.images.{state} 文件",
                )
            )
        if flow is None and (button["x"] is None) != (button["y"] is None):
            warnings.append(
                f"toolbar.buttons.{key} 只写了 x_dip、y_dip 其中一个，又没有 button_flow，"
                "这个按钮不会显示"
            )
    return errors, references


def read_toolbar_button_look(table: dict, where: str) -> tuple[str | None, str | None]:
    """对应 ReadToolbarButtonLook：按钮框宽高、图标字号与按钮底图。

    返回 (错误文案, 底图路径)。width_dip / height_dip / icon_size_dip 都必须 > 0 且 ≤ 500。
    """
    for key in ("width_dip", "height_dip"):
        if key in table:
            number = bounded_value(table[key], 500.0)
            if number is None or number <= 0.0:
                return (
                    f"{where} 的 width_dip / height_dip 必须是大于 0、不超过 500 的数值",
                    None,
                )
    if "icon_size_dip" in table:
        number = bounded_value(table["icon_size_dip"], 500.0)
        if number is None or number <= 0.0:
            return (
                f"{where}.icon_size_dip 必须是大于 0、不超过 500 的数值",
                None,
            )
    background: str | None = None
    if "background" in table:
        ok, value = read_resource(table, "background")
        if not ok or value is None or not is_animatable_image_path(value):
            return (
                f"{where}.background 无效（需为皮肤目录里的 .png、.apng、.gif 或 .webp）",
                None,
            )
        background = value
    return None, background


def looks_like_css_color(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"transparent", "currentcolor"}:
        return True
    if lowered.startswith("#"):
        return len(lowered) in (4, 5, 7, 9) and all(
            ch in "0123456789abcdef" for ch in lowered[1:]
        )
    if lowered.startswith(("rgb(", "rgba(")) and lowered.endswith(")"):
        inner = lowered[4:-1] if lowered.startswith("rgb(") else lowered[5:-1]
        parts = [
            part.strip()
            for part in inner.replace("/", " ").replace(",", " ").split()
            if part.strip()
        ]
        if len(parts) not in (3, 4):
            return False
        for part in parts:
            if part.endswith("%"):
                part = part[:-1]
            try:
                number = float(part)
            except ValueError:
                return False
            if number < 0:
                return False
        return True
    return False


def is_fully_transparent(value: str) -> bool:
    """判断一个颜色是否完全不透明的反面：alpha 为 0，写上去等于看不见。"""
    lowered = value.strip().lower()
    if lowered == "transparent":
        return True
    if lowered.startswith("#"):
        digits = lowered[1:]
        alpha_hex = {4: 1, 5: 1, 8: 2, 9: 3}.get(len(digits))
        if alpha_hex is not None:
            return set(digits[-alpha_hex:]) == {"0"}
        return False
    if lowered.startswith(("rgb(", "rgba(")) and lowered.endswith(")"):
        cut = 4 if lowered.startswith("rgb(") else 5
        parts = lowered[cut:-1].replace("/", " ").replace(",", " ").split()
        if len(parts) == 4:
            try:
                return float(parts[3].rstrip("%")) == 0.0
            except ValueError:
                return False
    return False


def check_image_file(
    package_dir: Path, relative: str, label: str, warnings: list[str]
) -> None:
    """Server 在 Load 末尾统一检查图片是否存在；这里只补充非致命的告警。"""
    image = package_dir / relative
    if not image.is_file():
        # 存在性本身是错误，已经由调用方报出。
        return
    size = image.stat().st_size
    if is_animatable_image_path(relative) and size > ANIMATED_FILE_LIMIT_BYTES:
        warnings.append(
            f"{label} {relative} 有 {size // (1024 * 1024)}MB，超过 64MB 的动图上限，"
            "只会显示第一帧（静态图）"
        )


def validate_package(package_dir: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    folder = package_dir.name

    # Load() 一进来就校验目录名：它同时是皮肤 ID。
    if not ID_PATTERN.match(folder):
        errors.append("目录名不是有效的外部皮肤 ID")
    elif folder in BUILTIN_IDS:
        errors.append("目录名不是有效的外部皮肤 ID（与内置皮肤同名）")
    elif folder in RESERVED_IDS:
        errors.append("目录名不是有效的外部皮肤 ID（default 是内置皮肤的设置清单目录）")
    if errors:
        return errors, warnings

    manifest = package_dir / "skin.toml"
    if not manifest.is_file():
        errors.append("缺少或无法解析 skin.toml")
        return errors, warnings
    try:
        # toml++ 会跳过 UTF-8 BOM（parser.inl 的 skip bom），Windows 记事本另存的
        # 「UTF-8 带 BOM」skin.toml 在 Server 那边能正常解析；utf-8-sig 与它一致。
        root = tomllib.loads(manifest.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError:
        # C++ 侧无效 UTF-8 走 toml::parse 的 parse_error，与其他解析失败同一条错误。
        errors.append("缺少或无法解析 skin.toml")
        return errors, warnings
    except tomllib.TOMLDecodeError:
        errors.append("缺少或无法解析 skin.toml")
        return errors, warnings
    if not isinstance(root, dict):
        errors.append("skin.toml 不是有效的 TOML manifest")
        return errors, warnings

    schema_version = root.get("schema_version")
    # C++ 侧按整数取值，字符串 "1" 和浮点 1.0 都取不到，一律拒绝。
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version not in (1, 2)
    ):
        errors.append("仅支持 schema_version 1 或 2")
        return errors, warnings

    # manifest 基本信息：id 必须与目录名一致，base 必须是内置皮肤之一。
    info_ok = True
    id_ok, skin_id = read_string(root, "id", 64, True)
    name_ok, skin_name = read_string(root, "name", 80, True)
    version_ok, version = read_string(root, "version", 32, True)
    base_ok, base = read_string(root, "base", 32, True)
    # 可选字段给了类型不对或超长同样算失败（ReadString 返回 false）。
    author_ok, author = read_string(root, "author", 120, False)
    desc_ok, desc = read_string(root, "description", 500, False)
    for ok in (id_ok, name_ok, version_ok, base_ok, author_ok, desc_ok):
        info_ok = info_ok and ok
    if not info_ok or skin_id != folder or base not in ALL_BASES:
        errors.append("manifest 的基本信息无效")
        return errors, warnings

    # canvas 没有自己的面板，只有 v2 的九宫格与挂件能让它可见；v1 皮肤用它只会得到一张透明卡片。
    if base == CANVAS_BASE and schema_version < 2:
        errors.append('base = "canvas" 只能用于 schema_version = 2 的皮肤')
        return errors, warnings
    # v2 字段只在 canvas 上生效：其他 base 的卡片几何与九宫格/挂件互相打架。这种皮肤仍可使用，按 v1 处理。
    downgraded_to_v1 = False
    if schema_version >= 2 and base != CANVAS_BASE:
        warnings.append(
            'schema_version = 2 需要 base = "canvas"，已按 schema_version = 1 '
            "加载，九宫格、挂件等 v2 字段被忽略"
        )
        schema_version = 1
        downgraded_to_v1 = True

    # 已被移除的字段：Server 静默忽略，写了只会让人以为生效了。
    for dead in ("preview", "toolbar_stylesheet"):
        if dead in root:
            warnings.append(
                f"根级 {dead} 已被 Server 移除，不会再生效；"
                + (
                    "装饰图改用 candidate_window.decoration.image"
                    if dead == "preview"
                    else "工具栏改用 [toolbar] / [toolbar.dark] / [toolbar.light] 的颜色键"
                )
            )
    for css in sorted(package_dir.rglob("*.css")):
        warnings.append(
            f"{css.relative_to(package_dir).as_posix()} 不会被读取：外部皮肤不支持任何 CSS"
        )

    supports = root.get("supports")
    if not isinstance(supports, dict):
        errors.append("supports.layouts 或 supports.themes 无效")
        return errors, warnings
    layouts_ok, layouts = read_enum_array(supports, "layouts", LAYOUTS)
    themes_ok, themes = read_enum_array(supports, "themes", THEMES)
    if not layouts_ok or not themes_ok:
        errors.append("supports.layouts 或 supports.themes 无效")
        return errors, warnings

    window = root.get("candidate_window")
    if not isinstance(window, dict):
        errors.append("缺少 candidate_window")
        return errors, warnings
    if bounded_number(window, "min_width_dip", 1000.0) is None:
        errors.append("candidate_window.min_width_dip 超出范围")
        return errors, warnings
    corner_radius: float | None = None
    if "corner_radius_dip" in window:
        corner_radius = bounded_number(window, "corner_radius_dip", 32.0)
        if corner_radius is None:
            errors.append("candidate_window.corner_radius_dip 超出范围")
            return errors, warnings
    if not read_optional_bounded(window, "border_width_dip", 4.0):
        errors.append("candidate_window.border_width_dip 超出范围")
        return errors, warnings
    item_radius: float | None = None
    if "item_corner_radius_dip" in window:
        item_radius = bounded_number(window, "item_corner_radius_dip", 16.0)
        if item_radius is None:
            errors.append("candidate_window.item_corner_radius_dip 超出范围")
            return errors, warnings
    shadow_ok, shadow = read_enum(window, "shadow", SHADOWS)
    if not shadow_ok:
        errors.append("candidate_window.shadow 只能是 none、soft 或 strong")
        return errors, warnings
    backdrop_ok, _ = read_enum(window, "backdrop", ("none", "acrylic", "mica"))
    if not backdrop_ok:
        errors.append("candidate_window.backdrop 只能是 none、acrylic 或 mica")
        return errors, warnings
    if not read_optional_bool(window, "fit_content"):
        errors.append("candidate_window.fit_content 必须是 true 或 false")
        return errors, warnings
    fit_content_given = "fit_content" in window
    font_family: str | None = None
    if "font_family" in window:
        font_ok, font_family = read_string(window, "font_family", 64, True)
        if not font_ok or font_family is None or not FONT_PATTERN.match(font_family):
            errors.append("candidate_window.font_family 无效")
            return errors, warnings
    if not read_optional_bool(window, "page_arrows"):
        errors.append("candidate_window.page_arrows 必须是 true 或 false")
        return errors, warnings
    page_arrows_given = "page_arrows" in window
    if not read_optional_bool(window, "expand_panel"):
        errors.append("candidate_window.expand_panel 必须是 true 或 false")
        return errors, warnings
    if "expand_rows" in window:
        rows = window["expand_rows"]
        if isinstance(rows, bool) or not isinstance(rows, int) or not 2 <= rows <= 8:
            errors.append("candidate_window.expand_rows 必须是 2–8 的整数")
            return errors, warnings

    # 版式：直接写在 [candidate_window] 里的对两种排列都生效，
    # [candidate_window.horizontal] / [candidate_window.vertical] 只覆盖那一种。
    if not read_geometry(window):
        errors.append("candidate_window 的版式数值无效")
        return errors, warnings
    for subtable in ("horizontal", "vertical"):
        if subtable not in window:
            continue
        if not isinstance(window[subtable], dict):
            errors.append("candidate_window 的版式数值无效")
            return errors, warnings
        if not read_geometry(window[subtable]):
            errors.append("candidate_window 的版式数值无效")
            return errors, warnings

    # 装饰图：表可选，一旦出现就必须给 image 和两个正数尺寸。
    decoration_image: str | None = None
    if "decoration" in window:
        decoration = window["decoration"]
        if not isinstance(decoration, dict):
            errors.append("candidate_window.decoration 无效")
            return errors, warnings
        if "image" not in decoration:
            errors.append("candidate_window.decoration 无效")
            return errors, warnings
        image_ok, decoration_image = read_resource(decoration, "image")
        align_ok, _ = read_enum(decoration, "align", ALIGNMENTS)
        if not image_ok or not align_ok:
            errors.append("candidate_window.decoration 无效")
            return errors, warnings
        top = bounded_number(decoration, "top_inset_dip", 500.0)
        width = bounded_number(decoration, "width_dip", 1000.0)
        if top is None or width is None or top <= 0.0 or width <= 0.0:
            # 两个尺寸都必须给出且都 > 0；缺一个按 0 处理，等于没给。
            errors.append("candidate_window.decoration 尺寸无效")
            return errors, warnings
        overlay_errors = validate_decoration_overlay(decoration, warnings)
        if overlay_errors:
            errors.extend(overlay_errors)
            return errors, warnings

    # 背景图：同样可选，一旦出现就必须给 image。
    background_image: str | None = None
    if "background" in window:
        background = window["background"]
        if not isinstance(background, dict):
            errors.append("candidate_window.background 无效")
            return errors, warnings
        if "image" not in background:
            errors.append("candidate_window.background 无效")
            return errors, warnings
        image_ok, background_image = read_resource(background, "image")
        fit_ok, _ = read_enum(background, "fit", FITS)
        if not image_ok or not fit_ok:
            errors.append("candidate_window.background 无效")
            return errors, warnings
        if (
            "opacity" in background
            and bounded_number(background, "opacity", 1.0) is None
        ):
            errors.append("candidate_window.background.opacity 超出范围")
            return errors, warnings

    # v2 专有字段：只在 schema_version = 2（即 base = canvas）时被解析。
    border_image_image: str | None = None
    border_image_light: str | None = None
    border_image_vertical_image: str | None = None
    border_image_vertical_light: str | None = None
    border_image_vertical_source_given = False
    decoration_images: list[str] = []
    if schema_version >= 2:
        if "border_image" in window:
            border_image = window["border_image"]
            if not isinstance(border_image, dict):
                errors.append("candidate_window.border_image 必须是表")
                return errors, warnings
            if "source" not in border_image:
                errors.append("candidate_window.border_image 缺少 source")
                return errors, warnings
            source_ok, border_image_image = read_resource(border_image, "source")
            if (
                not source_ok
                or border_image_image is None
                or not is_animatable_image_path(border_image_image)
            ):
                errors.append(
                    "candidate_window.border_image.source 无效（需为 .png、.apng、.gif 或 .webp）"
                )
                return errors, warnings
            if "light_source" in border_image:
                light_ok, border_image_light = read_resource(
                    border_image, "light_source"
                )
                if (
                    not light_ok
                    or border_image_light is None
                    or not is_animatable_image_path(border_image_light)
                ):
                    errors.append(
                        "candidate_window.border_image.light_source 无效"
                        "（需为 .png、.apng、.gif 或 .webp）"
                    )
                    return errors, warnings
            # slice_dip 是必填的：没有它九宫格无从切起；缺键与写错各有一条文案。
            state, _ = read_slice_array(border_image, "slice_dip")
            if state == "absent":
                errors.append("candidate_window.border_image 缺少 slice_dip")
                return errors, warnings
            if state != "ok":
                errors.append(
                    "candidate_window.border_image.slice_dip 必须是 1、2 或 4 个 0–500 的数值"
                )
                return errors, warnings
            for key in ("stretch_dip", "width_dip"):
                state, _ = read_slice_array(border_image, key)
                if state == "absent":
                    continue
                if state in ("not-list", "shape", "value"):
                    errors.append(
                        f"candidate_window.border_image.{key} 必须是 1、2 或 4 个 0–500 的数值"
                    )
                    return errors, warnings
            if "fill" in border_image and not isinstance(border_image["fill"], bool):
                errors.append("candidate_window.border_image.fill 必须是 true 或 false")
                return errors, warnings
            if not read_border_image_repeat(border_image):
                errors.append(
                    "candidate_window.border_image.repeat 必须是 stretch 或 repeat，1 个或 2 个值"
                )
                return errors, warnings

            # 竖排覆盖：只写与横排不同的键。source / slice_dip 不写就继承横排；
            # light_source 不继承——横排那张浅色图是按横排几何画的。
            if "vertical" in border_image:
                vertical = border_image["vertical"]
                if not isinstance(vertical, dict):
                    errors.append("candidate_window.border_image.vertical 必须是表")
                    return errors, warnings
                border_image_vertical_image = border_image_image
                if "source" in vertical:
                    border_image_vertical_source_given = True
                    source_ok, border_image_vertical_image = read_resource(
                        vertical, "source"
                    )
                    if (
                        not source_ok
                        or border_image_vertical_image is None
                        or not is_animatable_image_path(border_image_vertical_image)
                    ):
                        errors.append(
                            "candidate_window.border_image.vertical.source 无效"
                            "（需为 .png、.apng、.gif 或 .webp）"
                        )
                        return errors, warnings
                if "light_source" in vertical:
                    light_ok, border_image_vertical_light = read_resource(
                        vertical, "light_source"
                    )
                    if (
                        not light_ok
                        or border_image_vertical_light is None
                        or not is_animatable_image_path(border_image_vertical_light)
                    ):
                        errors.append(
                            "candidate_window.border_image.vertical.light_source 无效"
                            "（需为 .png、.apng、.gif 或 .webp）"
                        )
                        return errors, warnings
                state, _ = read_slice_array(vertical, "slice_dip")
                if state not in ("absent", "ok"):
                    errors.append(
                        "candidate_window.border_image.vertical.slice_dip 必须是 "
                        "1、2 或 4 个 0–500 的数值"
                    )
                    return errors, warnings
                for key in ("stretch_dip", "width_dip"):
                    state, _ = read_slice_array(vertical, key)
                    if state == "absent":
                        continue
                    if state in ("not-list", "shape", "value"):
                        errors.append(
                            f"candidate_window.border_image.vertical.{key} 必须是 "
                            "1、2 或 4 个 0–500 的数值"
                        )
                        return errors, warnings
                if "fill" in vertical and not isinstance(vertical["fill"], bool):
                    errors.append(
                        "candidate_window.border_image.vertical.fill 必须是 true 或 false"
                    )
                    return errors, warnings
                if not read_border_image_repeat(vertical):
                    errors.append(
                        "candidate_window.border_image.vertical.repeat 必须是 stretch 或 "
                        "repeat，1 个或 2 个值"
                    )
                    return errors, warnings

        if "content_insets_dip" in window:
            content_insets = window["content_insets_dip"]
            if not isinstance(content_insets, dict):
                errors.append("candidate_window.content_insets_dip 必须是表")
                return errors, warnings
            for key, maximum in CONTENT_INSET_BOUNDS.items():
                if (
                    key in content_insets
                    and bounded_value(content_insets[key], maximum) is None
                ):
                    errors.append("candidate_window.content_insets_dip 数值超出范围")
                    return errors, warnings
            if "vertical" in content_insets:
                vertical_insets = content_insets["vertical"]
                if not isinstance(vertical_insets, dict):
                    errors.append(
                        "candidate_window.content_insets_dip.vertical 必须是表"
                    )
                    return errors, warnings
                for key, maximum in CONTENT_INSET_BOUNDS.items():
                    if (
                        key in vertical_insets
                        and bounded_value(vertical_insets[key], maximum) is None
                    ):
                        errors.append(
                            "candidate_window.content_insets_dip.vertical 数值超出范围"
                        )
                        return errors, warnings
            if not any(key in content_insets for key in CONTENT_INSET_BOUNDS):
                # 空表与「整段不写」不是一回事：解析器会把四边都当成 0，
                # 于是「边宽 + 5 DIP」的默认留白也一并消失。
                warnings.append(
                    "写了空的 [candidate_window.content_insets_dip]（四边都没给）："
                    "四边按 0 处理，不会再按「边宽 + 5 DIP」留白；"
                    "不想要自定义内边距就整段删掉"
                )

        if "line_gap_dip" in window and not read_optional_bounded(
            window, "line_gap_dip", 100.0
        ):
            errors.append("candidate_window.line_gap_dip 超出范围")
            return errors, warnings

        if "outer_insets_dip" in window:
            outer_insets = window["outer_insets_dip"]
            if not isinstance(outer_insets, dict):
                errors.append("candidate_window.outer_insets_dip 必须是表")
                return errors, warnings
            for key, maximum in OUTER_INSET_BOUNDS.items():
                if (
                    key in outer_insets
                    and bounded_value(outer_insets[key], maximum) is None
                ):
                    errors.append("candidate_window.outer_insets_dip 数值超出范围")
                    return errors, warnings

        if "decorations" in window:
            decorations = window["decorations"]
            if not isinstance(decorations, list):
                errors.append("candidate_window.decorations 必须是数组")
                return errors, warnings
            if len(decorations) > 32:
                errors.append("candidate_window.decorations 最多 32 层")
                return errors, warnings
            for decoration in decorations:
                if not isinstance(decoration, dict) or "image" not in decoration:
                    errors.append(
                        "candidate_window.decorations.image 无效（需为 .png、.apng、.gif 或 .webp）"
                    )
                    return errors, warnings
                image_ok, free_image = read_resource(decoration, "image")
                if (
                    not image_ok
                    or free_image is None
                    or not is_animatable_image_path(free_image)
                ):
                    errors.append(
                        "candidate_window.decorations.image 无效（需为 .png、.apng、.gif 或 .webp）"
                    )
                    return errors, warnings
                decoration_images.append(free_image)
                anchor_ok, _ = read_enum(decoration, "anchor", ANCHORS)
                if not anchor_ok:
                    errors.append("candidate_window.decorations.anchor 无效")
                    return errors, warnings
                # 两个尺寸都必填且 > 0：缺省按 0 处理，同样落到这条错误上。
                width = bounded_number(decoration, "width_dip", 2000.0)
                height = bounded_number(decoration, "height_dip", 2000.0)
                if width is None or height is None or width <= 0.0 or height <= 0.0:
                    errors.append(
                        "candidate_window.decorations 的 width_dip 与 height_dip 必须大于 0"
                    )
                    return errors, warnings
                for key in ("offset_x_dip", "offset_y_dip"):
                    if key in decoration:
                        number = numeric_value(decoration[key])
                        if number is None or abs(number) > 2000.0:
                            errors.append(
                                "candidate_window.decorations 的 offset_x_dip / offset_y_dip "
                                "必须在 -2000–2000 之间"
                            )
                            return errors, warnings
                if "z_index" in decoration:
                    z_index = decoration["z_index"]
                    if (
                        isinstance(z_index, bool)
                        or not isinstance(z_index, int)
                        or not -1000 <= z_index <= 1000
                    ):
                        errors.append(
                            "candidate_window.decorations.z_index 必须是 -1000–1000 的整数"
                        )
                        return errors, warnings

    # 候选配色：[candidate] 整体不是表时 C++ 静默跳过，这里只警告。
    candidate = root.get("candidate")
    if candidate is not None and not isinstance(candidate, dict):
        warnings.append(
            "candidate 不是表，已被 Server 忽略（想写配色请用 [candidate.dark] / [candidate.light]）"
        )
        candidate = None
    dark_colors: dict[str, object] = {}
    light_colors: dict[str, object] = {}
    dark_menu: dict[str, str] = {}
    light_menu: dict[str, str] = {}
    if isinstance(candidate, dict):
        for theme_name, bucket, menu_bucket in (
            ("dark", dark_colors, dark_menu),
            ("light", light_colors, light_menu),
        ):
            table = candidate.get(theme_name)
            ok, values, mis_typed = read_candidate_colors(table)
            if not ok:
                errors.append("candidate 配色无效")
                return errors, warnings
            if mis_typed:
                warnings.append(f"[candidate.{theme_name}] 不是表，已被 Server 忽略")
            else:
                bucket.update(values)
            menu_ok, menu_values = read_menu_colors(
                table.get("menu") if isinstance(table, dict) else None
            )
            if not menu_ok:
                errors.append("candidate 配色无效")
                return errors, warnings
            menu_bucket.update(menu_values)

    # 悬浮工具栏配色与图片模式。
    toolbar_dark: dict[str, str] = {}
    toolbar_light: dict[str, str] = {}
    toolbar_files: list[tuple[str, str]] = []
    if "toolbar" in root:
        toolbar = root["toolbar"]
        if not isinstance(toolbar, dict):
            errors.append("toolbar 配色无效")
            return errors, warnings
        dark_ok, toolbar_dark = read_toolbar_colors(toolbar.get("dark"))
        light_ok, toolbar_light = read_toolbar_colors(toolbar.get("light"))
        if not dark_ok or not light_ok:
            errors.append("toolbar 配色无效")
            return errors, warnings
        if (
            "corner_radius_dip" in toolbar
            and bounded_number(toolbar, "corner_radius_dip", 32.0) is None
        ):
            errors.append("toolbar.corner_radius_dip 超出范围")
            return errors, warnings
        if (
            "icon_corner_radius_dip" in toolbar
            and bounded_number(toolbar, "icon_corner_radius_dip", 16.0) is None
        ):
            errors.append("toolbar.icon_corner_radius_dip 超出范围")
            return errors, warnings
        toolbar_errors, toolbar_files = validate_toolbar_image_mode(toolbar, warnings)
        if toolbar_errors:
            errors.extend(toolbar_errors)
            return errors, warnings

    # 图片存在性：Server 在 Load 的最后统一检查。
    # 竖排没写 source / light_source 时分别继承横排 / 为空，不必重复检查横排那张。
    for relative, message in (
        (decoration_image, "找不到 candidate_window.decoration.image 文件"),
        (background_image, "找不到 candidate_window.background.image 文件"),
        (border_image_image, "找不到 candidate_window.border_image.source 文件"),
        (border_image_light, "找不到 candidate_window.border_image.light_source 文件"),
        (
            border_image_vertical_image if border_image_vertical_source_given else None,
            "找不到 candidate_window.border_image.vertical.source 文件",
        ),
        (
            border_image_vertical_light,
            "找不到 candidate_window.border_image.vertical.light_source 文件",
        ),
    ):
        if relative and not (package_dir / relative).is_file():
            errors.append(message)
    for relative in decoration_images:
        if not (package_dir / relative).is_file():
            errors.append("找不到 candidate_window.decorations.image 文件")
    for relative, message in toolbar_files:
        if not (package_dir / relative).is_file():
            errors.append(message)
    if errors:
        return errors, warnings

    # 以下是 Server 不报错、但会让皮肤「装了没效果」的坑，作为警告给出。
    if set(layouts) != set(LAYOUTS) or set(themes) != set(THEMES):
        missing = [
            f"{kind}={'/'.join(sorted(set(options) - set(chosen)))}"
            for kind, options, chosen in (
                ("layouts", LAYOUTS, layouts),
                ("themes", THEMES, themes),
            )
            if set(options) - set(chosen)
        ]
        warnings.append(
            f"supports 只声明了 {'/'.join(sorted(layouts))} / {'/'.join(sorted(themes))}；"
            f"缺少 {'、'.join(missing)} 这些组合时，设置页的这张卡片会显示"
            "「当前布局或明暗模式不受支持」并禁用开关，且当前布局/明暗下直接回退 fluent"
        )
    # 固定明暗的共享基底在 AdaptSharedBase 里收窄 themes 并把 base 改写成 fluent：
    # 另一明暗下的配色与声明不会生效，声明里没有固定明暗时收窄成空、处处回退 fluent。
    fixed_theme = FIXED_THEME_SHARED_BASES.get(base)
    if fixed_theme is not None:
        other = "light" if fixed_theme == "dark" else "dark"
        zh = "深" if fixed_theme == "dark" else "浅"
        if fixed_theme not in themes:
            warnings.append(
                f"base = {base} 固定{zh}色明暗，themes 会被收窄成 ['{fixed_theme}']："
                f"声明的 {'/'.join(themes)} 里没有 {fixed_theme}，收窄后没有任何可用主题，"
                "设置页的这张卡片会显示「当前布局或明暗模式不受支持」，两种明暗都会回退 fluent"
            )
        elif other in themes:
            warnings.append(
                f"base = {base} 固定{zh}色明暗，themes 会被收窄成 ['{fixed_theme}']："
                f"{other} 一侧的配色不会生效"
            )
    if not author:
        warnings.append("没写 author，分享给别人时设置页只显示 id 和版本")
    if not desc:
        warnings.append("没写 description，设置页会显示「基于 <base>」")
    if "license" not in root:
        warnings.append(
            "没写 [license]，发布前建议补上 code / assets，素材来源未核实时写 "
            'assets = "UNVERIFIED"，别让他人误用'
        )
    if not isinstance(candidate, dict):
        warnings.append(
            "完全没写 [candidate] 配色：颜色将按 base 走；建议把 dark/light 两组配色键都显式写全"
        )
    for theme_name, bucket in (("dark", dark_colors), ("light", light_colors)):
        if isinstance(candidate, dict) and not bucket:
            warnings.append(
                f"[candidate.{theme_name}] 没有任何配色键，该明暗下相应颜色会沿用默认"
            )
        for key in CANDIDATE_COLOR_KEYS:
            value = bucket.get(key)
            if value is None:
                continue
            if not isinstance(value, str) or not value:
                warnings.append(
                    f"[candidate.{theme_name}].{key} 是空字符串，等同于不设置"
                )
                continue
            if not looks_like_css_color(value):
                warnings.append(
                    f"[candidate.{theme_name}].{key} = {value} 不是可识别的 CSS 颜色，"
                    "会退回默认色；请用 #rgb / #rgba / #rrggbb / #rrggbbaa / rgb() / rgba()"
                )
            elif is_fully_transparent(value):
                warnings.append(
                    f"[candidate.{theme_name}].{key} 透明度为 0，会看不见"
                    + ("（surface 全透明时连卡片底都没有）" if key == "surface" else "")
                )
        overridden = [
            key for key in ("text", "candidate_text", "preedit_text") if key in bucket
        ]
        if overridden:
            warnings.append(
                f"[candidate.{theme_name}].{' / '.join(overridden)} 会被设置页的「候选文字颜色」覆盖，"
                "用户在设置里改过颜色时这几个键不生效"
            )
    for theme_name, bucket in (("dark", dark_menu), ("light", light_menu)):
        for key, value in bucket.items():
            if not looks_like_css_color(value):
                warnings.append(
                    f"[candidate.{theme_name}.menu].{key} = {value} 不是可识别的 CSS 颜色，"
                    "会退回 base 的菜单颜色"
                )
    for theme_name, bucket in (("dark", toolbar_dark), ("light", toolbar_light)):
        for key, value in bucket.items():
            if not looks_like_css_color(value):
                warnings.append(
                    f"[toolbar.{theme_name}].{key} = {value} 不是可识别的 CSS 颜色，"
                    "会退回 base 的工具栏颜色"
                )
    if corner_radius == 0.0:
        warnings.append("corner_radius_dip = 0 是直角候选框；不想要直角就别写这个键")
    if corner_radius is not None and corner_radius > 24:
        warnings.append(
            f"corner_radius_dip = {corner_radius:g} 偏大，圆角几乎吃掉一整格高，候选文字可能被裁"
        )
    if item_radius is not None and item_radius > 12:
        warnings.append(
            f"item_corner_radius_dip = {item_radius:g} 偏大，高亮块会比候选行更高，"
            "相邻两行的高亮块可能连成一片"
        )
    if "border_width_dip" in window and base in NO_FRAME_BASES:
        if "border" not in dark_colors and "border" not in light_colors:
            warnings.append(
                f"base = {base} 的基础样式没有外框，border_width_dip 要看得见还得在 "
                "[candidate.*] 里给 border 颜色"
            )
    if font_family:
        if byte_len(font_family) >= 60:
            warnings.append(
                f"font_family 有 {byte_len(font_family)} 字节，接近 64 字节上限，"
                "再长就会被 Server 拒收"
            )
        warnings.append(
            "font_family 只排在用户字体前面，字号仍由设置页决定；一次只能写一个字体名，"
            "缺字时回落到用户字体"
        )
    if not page_arrows_given:
        # 内置皮肤出厂值读自数据目录 skins\default\<base>\skin.toml；canvas 与共享基底都取 fluent：
        # AdaptSharedBase 会把共享基底的 base 改写成 fluent，ResolvePageArrows 拿到的是改写后的值
        # （server/tests/src/test_candidate_skin_catalog_bases.cpp 覆盖了这条）。
        arrows_base = "fluent" if base == CANVAS_BASE or base in SHARED_BASES else base
        inherited = DEFAULT_PAGE_ARROWS.get(arrows_base, False)
        warnings.append(
            "没写 page_arrows：沿用 base 的默认皮肤设置（"
            f"数据目录 skins\\default\\{arrows_base}\\skin.toml，出厂为 "
            f"{'true' if inherited else 'false'}）"
        )
    if not fit_content_given:
        fit_base = "fluent" if base == CANVAS_BASE or base in SHARED_BASES else base
        warnings.append(
            "没写 fit_content：沿用 base 的默认皮肤设置（"
            f"数据目录 skins\\default\\{fit_base}\\skin.toml，出厂为 false，"
            "卡片垫 160 DIP 的出厂最小宽度）"
        )
    # 卷轴展开和 page_arrows 一样读 base 的出厂值；canvas 与共享基底的 base 已被改写为 fluent。
    expand_base = "fluent" if base == CANVAS_BASE or base in SHARED_BASES else base
    expand_inherited = DEFAULT_EXPAND_PANEL.get(expand_base, False)
    expand_enabled = window.get("expand_panel", expand_inherited)
    if not isinstance(expand_enabled, bool):
        expand_enabled = expand_inherited
    if "expand_panel" not in window:
        warnings.append(
            "没写 expand_panel：沿用 base 的默认皮肤设置（"
            f"数据目录 skins\\default\\{expand_base}\\skin.toml，出厂为 "
            f"{'true' if expand_inherited else 'false'}）"
        )
    if "expand_rows" in window and not expand_enabled:
        warnings.append(
            "写了 expand_rows，但当前皮肤没有打开 expand_panel（也没有从 base 继承到 true）："
            "行数不会生效"
        )
    # page_arrows 没写时也可能从 base 继承到 true（microsoft）；两种来源都要算进来，
    # 否则 expand_panel = true 时横排箭头被卷轴展开顶掉，提示却不会出现。
    page_arrows_base = "fluent" if base == CANVAS_BASE or base in SHARED_BASES else base
    page_arrows_enabled = window.get(
        "page_arrows", DEFAULT_PAGE_ARROWS.get(page_arrows_base, False)
    )
    if not isinstance(page_arrows_enabled, bool):
        page_arrows_enabled = DEFAULT_PAGE_ARROWS.get(page_arrows_base, False)
    if expand_enabled and page_arrows_enabled:
        warnings.append(
            "expand_panel 与 page_arrows 同时生效：横排不会显示翻页箭头（卷轴展开优先），"
            "竖排仍按 page_arrows 显示"
        )
    # page_arrow_style 可以写在横排子表里；只有横排真的会画箭头时才需要分隔线。
    page_arrow_style = window.get("page_arrow_style")
    horizontal = window.get("horizontal")
    if isinstance(horizontal, dict) and "page_arrow_style" in horizontal:
        page_arrow_style = horizontal["page_arrow_style"]
    if (
        page_arrow_style == "triangle"
        and page_arrows_enabled
        and not expand_enabled
        and "horizontal" in layouts
        and not dark_colors.get("page_arrow_divider")
        and not light_colors.get("page_arrow_divider")
    ):
        warnings.append(
            'page_arrow_style = "triangle" 但没写 page_arrow_divider：'
            "横排三角箭头前的分隔线不会画（竖排本来就不画）"
        )
    # v2 字段只在 canvas 上被解析；走到这里 schema_version 已按 base 修正过。
    # 上面那条降级说明已经交代了 v2 字段被忽略，这里不再重复（也不要再劝人「改成 2」，人家本来就写了 2）。
    if schema_version == 1:
        if not downgraded_to_v1:
            present = [key for key in V2_WINDOW_KEYS if key in window]
            if present:
                warnings.append(
                    "[candidate_window] 里的 "
                    + " / ".join(present)
                    + " 是 v2 专有字段，schema_version = 1 时不会被解析（不报错也不生效）；"
                    '要用它们就把 schema_version 改成 2 并用 base = "canvas"'
                )
    else:
        if not any(key in window for key in V2_WINDOW_KEYS):
            warnings.append(
                "schema_version = 2 但没用任何 v2 字段（border_image / content_insets_dip / "
                "line_gap_dip / outer_insets_dip / decorations）：`canvas` 只是一张透明卡片，"
                "没有九宫格面板与挂件，候选框里只剩悬空的文字"
            )
        if decoration_images and "outer_insets_dip" not in window:
            warnings.append(
                "有 decorations 却没写 outer_insets_dip：挂到卡片外沿的挂件会被窗口边界裁掉"
            )
        if "outer_insets_dip" in window and not decoration_images:
            warnings.append(
                "写了 outer_insets_dip 却没有 decorations：窗口会四周多留空白，但没有挂件用上它"
            )
    if decoration_image:
        check_image_file(package_dir, decoration_image, "装饰图", warnings)
    if background_image:
        check_image_file(package_dir, background_image, "背景图", warnings)
    if border_image_image:
        check_image_file(package_dir, border_image_image, "九宫格面板图", warnings)
    if border_image_light:
        check_image_file(
            package_dir, border_image_light, "九宫格面板图（浅色）", warnings
        )
    if border_image_vertical_source_given and border_image_vertical_image:
        check_image_file(
            package_dir, border_image_vertical_image, "竖排九宫格面板图", warnings
        )
    if border_image_vertical_light:
        check_image_file(
            package_dir,
            border_image_vertical_light,
            "竖排九宫格面板图（浅色）",
            warnings,
        )
    for relative in decoration_images:
        check_image_file(package_dir, relative, "挂件图", warnings)
    for relative, _ in toolbar_files:
        check_image_file(package_dir, relative, "工具栏图片", warnings)
    if decoration_image and background_image:
        warnings.append(
            "同时有装饰图和卡片背景图：两者叠加后容易糊在一起，建议背景图的 opacity 压到 0.5 以下"
        )
    return errors, warnings


def collect_targets(arg: Path) -> list[Path]:
    # 给的是皮肤包目录（含 skin.toml）就只校验它；否则当作 skins 根目录，扫描子目录。
    if (arg / "skin.toml").is_file():
        return [arg]
    children = sorted(child for child in arg.iterdir() if child.is_dir())
    # Scan 会跳过 default 与 *.bak，这里跟着跳过，免得把它们报成损坏的皮肤。
    return [
        child
        for child in children
        if child.name not in RESERVED_IDS
        and not BACKUP_SUFFIX_PATTERN.search(child.name)
    ]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip())
        return 1
    target = Path(argv[1]).expanduser()
    if not target.is_dir():
        print(f"目录不存在：{target}")
        return 1

    packages = collect_targets(target)
    if not packages:
        print(f"{target} 下没有找到任何皮肤子目录。")
        return 1

    failed = 0
    for package in packages:
        errors, warnings = validate_package(package)
        label = f"== {package.name} =="
        if errors:
            failed += 1
            print(f"[FAIL] {label}")
            for error in errors:
                print(f"  错误: {error}")
        else:
            print(f"[ OK ] {label}")
        for warning in warnings:
            print(f"  警告: {warning}")

    if failed:
        print(f"\n{failed}/{len(packages)} 个皮肤未通过。修好后再复制到 skins 目录。")
        return 1
    print(f"\n{len(packages)} 个皮肤全部通过。")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(
            encoding="utf-8", errors="replace"
        )  # pwsh/Windows Terminal 按 UTF-8 显示
    except (AttributeError, ValueError):
        pass
    raise SystemExit(main(sys.argv))
