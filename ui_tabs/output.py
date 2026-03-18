from __future__ import annotations

from .types import RibbonSectionConfig, RibbonTabConfig


TAB = RibbonTabConfig(
    name="输出",
    sections=(
        RibbonSectionConfig(
            "输出",
            (
                "Plot",
                "Export",
                "Print",
            ),
        ),
    ),
)


__all__ = ["TAB"]
