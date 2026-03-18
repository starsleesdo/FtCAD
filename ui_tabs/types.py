from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class RibbonSectionConfig:
    title: str
    tools: Tuple[str, ...]


@dataclass(frozen=True)
class RibbonTabConfig:
    name: str
    sections: Tuple[RibbonSectionConfig, ...]


__all__ = ["RibbonSectionConfig", "RibbonTabConfig"]
