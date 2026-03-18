from __future__ import annotations

from .types import RibbonSectionConfig, RibbonTabConfig


TAB = RibbonTabConfig(
    name="工具",
    sections=(
        RibbonSectionConfig(
            "编辑",
            (
                "Move",
                "Rotate",
                "Mirror",
                "Offset",
                "Stretch",
                "Scale",
                "Align",
                "Copy",
                "Rect Array",
                "Array",
                "Boolean",
                "Break",
                "Fillet",
                "Trim",
                "Explode",
                "Delete",
            ),
        ),
        RibbonSectionConfig(
            "实用",
            (
                "Measure",
                "Manager",
            ),
        ),
    ),
)


__all__ = ["TAB"]
