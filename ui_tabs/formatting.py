from __future__ import annotations

from .types import RibbonSectionConfig, RibbonTabConfig


TAB = RibbonTabConfig(
    name="格式",
    sections=(
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
            "属性",
            (
                "Color",
                "Linetype",
                "Lineweight",
                "Hatch",
            ),
        ),
    ),
)


__all__ = ["TAB"]
