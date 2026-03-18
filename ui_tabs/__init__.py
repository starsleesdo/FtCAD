from .annotation import TAB as ANNOTATION_TAB
from .formatting import TAB as FORMAT_TAB
from .general import TAB as GENERAL_TAB
from .insert import TAB as INSERT_TAB
from .layout import TAB as LAYOUT_TAB
from .manage import TAB as MANAGE_TAB
from .modeling import TAB as MODELING_TAB
from .output import TAB as OUTPUT_TAB
from .types import RibbonSectionConfig, RibbonTabConfig
from .tools import TAB as TOOLS_TAB
from .view import TAB as VIEW_TAB

ALL_TABS = (
    GENERAL_TAB,
    INSERT_TAB,
    FORMAT_TAB,
    TOOLS_TAB,
    ANNOTATION_TAB,
    MODELING_TAB,
    LAYOUT_TAB,
    VIEW_TAB,
    MANAGE_TAB,
    OUTPUT_TAB,
)


__all__ = [
    "ALL_TABS",
    "RibbonSectionConfig",
    "RibbonTabConfig",
]
