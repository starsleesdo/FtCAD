from __future__ import annotations

from .types import RibbonSectionConfig, RibbonTabConfig


TAB = RibbonTabConfig(
    name="视图",
    sections=(
        RibbonSectionConfig(
            "导航",
            (
                "Pan",
                "Zoom",
            ),
        ),
    ),
)


__all__ = ["TAB"]
