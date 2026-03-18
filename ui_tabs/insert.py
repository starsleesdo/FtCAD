from __future__ import annotations

from .types import RibbonSectionConfig, RibbonTabConfig


TAB = RibbonTabConfig(
    name="插入",
    sections=(
        RibbonSectionConfig(
            "插入",
            (
                "Insert Block",
                "Image",
                "PDF",
            ),
        ),
    ),
)


__all__ = ["TAB"]
