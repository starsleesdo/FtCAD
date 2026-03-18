from __future__ import annotations

from .types import RibbonSectionConfig, RibbonTabConfig


TAB = RibbonTabConfig(
    name="管理",
    sections=(
        RibbonSectionConfig(
            "管理",
            (
                "Manager",
                "Color",
                "Linetype",
                "Lineweight",
            ),
        ),
    ),
)


__all__ = ["TAB"]
