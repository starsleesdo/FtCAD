from __future__ import annotations

from .types import RibbonSectionConfig, RibbonTabConfig


TAB = RibbonTabConfig(
    name="三维",
    sections=(
        RibbonSectionConfig(
            "实体",
            (
                "Box",
                "Extrude",
                "Orbit",
            ),
        ),
    ),
)


__all__ = ["TAB"]
