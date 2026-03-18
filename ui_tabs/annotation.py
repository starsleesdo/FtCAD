from __future__ import annotations

from .types import RibbonSectionConfig, RibbonTabConfig


TAB = RibbonTabConfig(
    name="标注",
    sections=(
        RibbonSectionConfig(
            "文字与符号",
            (
                "Text",
                "Leader",
                "LeaderNote",
                "Table",
            ),
        ),
        RibbonSectionConfig(
            "尺寸",
            (
                "DimLinear",
                "Hatch",
            ),
        ),
    ),
)


__all__ = ["TAB"]
