#!/usr/bin/env python3
"""水杉输入法外部皮肤校验器。

规则逐条对齐 Server 的解析实现 server/src/skin/candidate_skin_catalog.cpp（CandidateSkinCatalog::Load），
错误文案也沿用同一套中文，方便和设置页「皮肤 → 外部皮肤」底部的诊断信息对照。

用法：
    uv run check_skin.py <皮肤包目录>      # 目录里应有 skin.toml
    uv run check_skin.py <skins 根目录>    # 目录本身没有 skin.toml 时，扫描其下所有子目录

退出码：0 = 全部通过（允许有警告），1 = 存在错误。
需要 Python 3.11+（用标准库 tomllib 解析 TOML，无第三方依赖）。
"""

from __future__ import annotations

import re
import string
import sys
import tomllib
from pathlib import Path

# candidate_skin_catalog.cpp:BuiltInIds —— 与内置皮肤同名的目录会被当成内置 ID 拒绝。
BUILTIN_IDS = {
    "fluent",
    "wechat",
    "graphite",
    "willow_green",
    "autumn_osmanthus",
    "microsoft",
}
# kDefaultSkinsFolder：内置皮肤的设置清单目录，Scan 跳过它，也不能被当成外部皮肤加载。
RESERVED_IDS = {"default"}
# kDefaultPageArrows / skins/default/<base>/skin.toml：内置皮肤翻页箭头的出厂值。
DEFAULT_PAGE_ARROWS = {"microsoft": True}
# 这两个 base 的基础样式是 border: none，只写线宽看不到框，必须同时给 border 颜色。
NO_FRAME_BASES = {"willow_green", "autumn_osmanthus"}

LAYOUTS = ("horizontal", "vertical")
THEMES = ("dark", "light")
ALIGNMENTS = ("left", "center", "right")
FITS = ("cover", "contain", "stretch")
SHADOWS = ("none", "soft", "strong")

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
)
CANDIDATE_COLOR_KEYS = BASE_COLOR_KEYS + DETAIL_COLOR_KEYS
# [candidate.dark.menu] / [candidate.light.menu] 的四个键，同样走 ReadCssColor。
MENU_COLOR_KEYS = ("background", "border", "text", "hover")
# ReadToolbarColors 逐键检查的工具栏配色键，值上限 80 字节。
TOOLBAR_COLOR_KEYS = ("background", "border", "handle", "divider", "icon", "hover")

# ReadCssColor 只放行颜色值会用到的字符，挡住 `;`、`{}` 之类能跳出 CSS 声明的写法。
CSS_COLOR_CHARS = set(string.ascii_letters + string.digits + "#(),.% -/")

EMBED_MAX_BYTES = 1500 * 1024  # windows_webview2_skin.cpp:kMaxEmbedBytes

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


def bounded_number(table: dict, key: str, maximum: float) -> float | None:
    """对应 BoundedNumber：缺省 0.0；越界/类型错返回 None（C++ 返回 -1 表示非法）。"""
    if key not in table:
        return 0.0
    value = table[key]
    if isinstance(value, bool):  # bool 是 int 的子类，TOML 的 true 不能当数字用
        return None
    if isinstance(value, (int, float)):
        value = float(value)
        if value == value and 0.0 <= value <= maximum:  # NaN 与越界同样拒绝
            return value
    return None


def read_optional_bounded(table: dict, key: str, maximum: float) -> bool:
    """对应 ReadOptionalBounded：缺省放行，写了就必须是 0~maximum 的数字。"""
    if key not in table:
        return True
    return bounded_number(table, key, maximum) is not None


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
    return all(part not in ("", ".", "..") for part in name.split("/"))


def read_resource(table: dict, key: str) -> tuple[bool, str | None]:
    """对应 ReadResource：必须是包内相对路径。"""
    if key not in table:
        return False, None
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
    return (
        True,
        {key: table[key] for key in CANDIDATE_COLOR_KEYS if key in table},
        False,
    )


def read_menu_colors(table: object) -> tuple[bool, dict[str, str], bool]:
    """对应 ReadColors 里的 menu 分支：表可选，写了就必须是表且逐键过白名单。"""
    if table is None:
        return True, {}, False
    if not isinstance(table, dict):
        return True, {}, True
    out: dict[str, str] = {}
    for key in MENU_COLOR_KEYS:
        ok, value = read_css_color(table, key)
        if not ok:
            return False, {}, False
        if value is not None:
            out[key] = value
    return True, out, False


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
    if size > EMBED_MAX_BYTES:
        warnings.append(
            f"{label} {relative} 有 {size // 1024}KB，超过 1500KB 的内联上限，"
            "WebView2 端会改走虚拟主机加载（更慢）"
        )
    if image.suffix.lower() not in (".png", ".jpg", ".jpeg", ".bmp", ".gif"):
        warnings.append(
            f"{label} {relative} 是 {image.suffix or '（无扩展名）'} 格式，原生后端靠 Windows 图片解码器加载，"
            "webp/svg 在部分 Windows 上不支持，建议用 png"
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
        root = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        errors.append("skin.toml 不是有效的 TOML manifest")
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
        or schema_version != 1
    ):
        errors.append("仅支持 schema_version 1")
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
    if not info_ok or skin_id != folder or base not in BUILTIN_IDS:
        errors.append("manifest 的基本信息无效")
        return errors, warnings

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
            menu_ok, menu_values, menu_mis_typed = read_menu_colors(
                table.get("menu") if isinstance(table, dict) else None
            )
            if not menu_ok:
                errors.append("candidate 配色无效")
                return errors, warnings
            if menu_mis_typed:
                warnings.append(
                    f"[candidate.{theme_name}.menu] 不是表，已被 Server 忽略"
                )
            else:
                menu_bucket.update(menu_values)

    # 悬浮工具栏配色。
    toolbar_dark: dict[str, str] = {}
    toolbar_light: dict[str, str] = {}
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

    # 图片存在性：Server 在 Load 的最后统一检查。
    for relative, label in (
        (decoration_image, "装饰图"),
        (background_image, "背景图"),
    ):
        if relative and not (package_dir / relative).is_file():
            field = "decoration" if label == "装饰图" else "background"
            errors.append(f"找不到 candidate_window.{field}.image 文件")
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
            f"缺少 {'、'.join(missing)} 这些组合时，设置页会标「不兼容」，"
            "且当前布局/明暗下 WebView2 后端直接回退 fluent"
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
            "完全没写 [candidate] 配色：颜色将按 base 走，但原生后端与 WebView2 的默认值来源不同，"
            "换后端可能有差别。建议把 dark/light 两组配色键都显式写全"
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
                    "原生后端会退回默认色；请用 #rgb / #rgba / #rrggbb / #rrggbbaa / rgb() / rgba()"
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
                    "两个后端都会退回 base 的菜单颜色"
                )
    for theme_name, bucket in (("dark", toolbar_dark), ("light", toolbar_light)):
        for key, value in bucket.items():
            if not looks_like_css_color(value):
                warnings.append(
                    f"[toolbar.{theme_name}].{key} = {value} 不是可识别的 CSS 颜色，"
                    "两个后端都会退回 base 的工具栏颜色"
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
        inherited = DEFAULT_PAGE_ARROWS.get(base, False)
        warnings.append(
            "没写 page_arrows：沿用 base 的内置皮肤设置（"
            f"数据目录 skins\\default\\{base}\\skin.toml，出厂为 "
            f"{'true' if inherited else 'false'}）"
        )
    if decoration_image:
        check_image_file(package_dir, decoration_image, "装饰图", warnings)
    if background_image:
        check_image_file(package_dir, background_image, "背景图", warnings)
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
