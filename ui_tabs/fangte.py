from __future__ import annotations

from .types import RibbonSectionConfig, RibbonTabConfig


TAB = RibbonTabConfig(
    name="方特上升管换热器",
    sections=(
        RibbonSectionConfig(
            "部件",
            (
                "1内筒体组件",
                "2内筒体",
                "3 下接环组件",
                "3-1 下连接圈",
                "3-2下连接环",
            ),
        ),
    ),
)


__all__ = ["TAB"]
