from __future__ import annotations

from .types import RibbonSectionConfig, RibbonTabConfig


TAB = RibbonTabConfig(
    name="布局",
    sections=(
        RibbonSectionConfig(
            "布局",
            (
                "Viewport",
            ),
        ),
    ),
)


__all__ = ["TAB"]
