from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Any


@dataclass(frozen=True)
class ToolActionContext:
    tool_tips: dict
    drawing_tools: dict
    inner_cylinder_tool: str
    pending_component_tools: set
    layer_props_tool: str
    table_tool: str
    color_tool: str
    get_canvas: Callable[[], Any]
    set_current_tool_status: Callable[[str], None]
    open_inner_cylinder_params_dialog: Callable[[], None]
    notify_component_pending: Callable[[str], None]
    toggle_layer_manager: Callable[[bool], None]
    on_layer_manager_opened: Callable[[], None]
    request_table_insert: Callable[[], Optional[dict]]
    on_table_inserted: Callable[[dict], None]
    request_color: Callable[[], Optional[str]]
    apply_layer_color: Callable[[str], None]
    on_tool_enabled: Callable[[str], None]
    on_tool_placeholder: Callable[[str], None]


class ToolActionHandler:
    def __init__(self, context: ToolActionContext):
        self._context = context

    def handle_tool(self, name: str, display_name: Optional[str] = None) -> None:
        canvas = self._context.get_canvas()
        if canvas is None:
            return

        key = "".join(ch for ch in name.lower() if ch.isalnum() or ch == "_")
        label = display_name or self._context.tool_tips.get(name, name)
        self._context.set_current_tool_status(label)

        if name == self._context.inner_cylinder_tool:
            self._context.open_inner_cylinder_params_dialog()
            return
        if name in self._context.pending_component_tools:
            self._context.notify_component_pending(label)
            return
        if name == self._context.layer_props_tool:
            self._context.toggle_layer_manager(True)
            self._context.on_layer_manager_opened()
            return
        if name == self._context.table_tool:
            settings = self._context.request_table_insert()
            if settings is not None:
                self._context.on_table_inserted(settings)
            return
        if name == self._context.color_tool:
            color_name = self._context.request_color()
            if color_name:
                self._context.apply_layer_color(color_name)
            return
        if key in self._context.drawing_tools:
            canvas.set_tool(self._context.drawing_tools[key])
            self._context.on_tool_enabled(label)
            return
        self._context.on_tool_placeholder(label)
