from __future__ import annotations

from .types import RibbonSectionConfig, RibbonTabConfig


TAB = RibbonTabConfig(
    name="常规",
    sections=(
        RibbonSectionConfig(
            "绘图",
            (
                "Select",
                "DoubleLine",
                "Line",
                "Arc",
                "Polyline",
                "Circle",
                "Center",
                "Ellipse",
                "Rect",
            ),
        ),
        RibbonSectionConfig(
            "修改",
            (
                "Move",
                "Rotate",
                "Trim",
                "Copy",
                "Mirror",
                "Fillet",
                "Stretch",
                "Scale",
                "Array",
                "Delete",
                "Explode",
                "Offset",
            ),
        ),
        RibbonSectionConfig(
            "图层",
            (
                "Layer Props",
                "Turn Off",
                "Isolate",
                "Set Current",
            ),
        ),
        RibbonSectionConfig(
            "注释",
            (
                "Text",
                "Table",
                "Leader",
                "Dimension",
            ),
        ),
        RibbonSectionConfig(
            "块",
            (
                "Insert Block",
                "Create Block",
                "Edit Block",
            ),
        ),
        RibbonSectionConfig(
            "特性",
            (
                "Color",
                "Linetype",
                "Lineweight",
            ),
        ),
        RibbonSectionConfig(
            "剪贴板",
            (
                "Paste",
                "Paste Block",
                "Paste Special",
                "Copy Link",
                "Cut",
            ),
        ),
        RibbonSectionConfig(
            "实用工具",
            (
                "Query",
                "Calculator",
                "Quick Select",
            ),
        ),
    ),
)


__all__ = ["TAB"]
