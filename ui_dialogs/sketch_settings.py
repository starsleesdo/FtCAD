from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QLineEdit,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


SKETCH_TAB_CONFIGS = [
    {
        "title": "捕捉和栅格",
        "flags": [
            {"name": "snap", "label": "启用捕捉 (F9)"},
            {"name": "grid", "label": "启用栅格 (F7)"},
        ],
        "fields": [
            {"name": "snap_spacing_x", "label": "捕捉 X 间距", "type": "spin", "min": 1, "max": 500, "default": 10},
            {"name": "snap_spacing_y", "label": "捕捉 Y 间距", "type": "spin", "min": 1, "max": 500, "default": 10},
            {"name": "grid_spacing_x", "label": "栅格 X 间距", "type": "spin", "min": 1, "max": 500, "default": 10},
            {"name": "grid_spacing_y", "label": "栅格 Y 间距", "type": "spin", "min": 1, "max": 500, "default": 10},
            {"name": "grid_lines_per_block", "label": "每条主线包含的网格数", "type": "spin", "min": 1, "max": 10, "default": 5},
        ],
        "checkboxes": [
            {"name": "snap_equal_spacing", "label": "X / Y 轴间距相同", "default": True},
            {"name": "grid_adaptive", "label": "自适应栅格", "default": True},
            {"name": "grid_show_beyond", "label": "显示超出界限的栅格", "default": True},
            {"name": "grid_follow_ucs", "label": "遵循动态 UCS", "default": False},
        ],
    },
    {
        "title": "正交模式",
        "flags": [{"name": "ortho", "label": "启用正交模式 (F8)"}],
        "checkboxes": [
            {"name": "ortho_lock_horizontal", "label": "限制为水平/垂直方向", "default": True},
            {"name": "ortho_allow_override", "label": "允许按住 Shift 临时禁用", "default": True},
        ],
    },
    {
        "title": "极轴追踪",
        "flags": [{"name": "polar", "label": "启用极轴追踪 (F10)"}],
        "fields": [
            {"name": "polar_increment", "label": "增量角度 (°)", "type": "double", "min": 1, "max": 180, "decimals": 1, "default": 90.0},
        ],
        "checkboxes": [
            {"name": "polar_absolute", "label": "绝对角度", "default": True},
            {"name": "polar_relative", "label": "相对上一段", "default": False},
        ],
    },
    {
        "title": "对象捕捉",
        "flags": [
            {"name": "object_snap", "label": "启用对象捕捉 (F3)"},
            {"name": "object_track", "label": "启用对象跟踪 (F11)"},
        ],
        "checkboxes": [
            {"name": "osnap_endpoint", "label": "端点", "default": True},
            {"name": "osnap_midpoint", "label": "中点", "default": True},
            {"name": "osnap_center", "label": "圆心", "default": True},
            {"name": "osnap_node", "label": "节点", "default": False},
            {"name": "osnap_quadrant", "label": "象限点", "default": False},
            {"name": "osnap_perpendicular", "label": "垂足", "default": True},
            {"name": "osnap_tangent", "label": "切点", "default": True},
            {"name": "osnap_nearest", "label": "最近点", "default": False},
            {"name": "osnap_intersection", "label": "交点", "default": True},
            {"name": "osnap_extension", "label": "延长线", "default": False},
            {"name": "osnap_parallel", "label": "平行", "default": False},
            {"name": "osnap_divide", "label": "等分点", "default": False},
        ],
    },
    {
        "title": "动态输入",
        "flags": [{"name": "dynamic_input", "label": "启用动态输入 (F12)"}],
        "checkboxes": [
            {"name": "dynamic_show_command", "label": "在光标附近显示命令提示", "default": True},
            {"name": "dynamic_follow_cursor", "label": "动态提示随十字光标移动", "default": True},
            {"name": "dynamic_auto_complete", "label": "输入时显示建议列表", "default": True},
        ],
    },
    {
        "title": "快捷特性",
        "flags": [{"name": "quick_properties", "label": "启用快捷特性 (Ctrl+Shift+P)"}],
        "fields": [
            {"name": "quick_panel_offset", "label": "面板距光标像素", "type": "spin", "min": 10, "max": 200, "default": 50},
            {"name": "quick_panel_rows", "label": "最小显示行数", "type": "spin", "min": 1, "max": 10, "default": 3},
        ],
        "checkboxes": [
            {"name": "quick_auto_hide", "label": "自动收起面板", "default": True},
        ],
    },
    {
        "title": "放大镜",
        "flags": [{"name": "magnifier", "label": "启用放大镜"}],
        "fields": [
            {"name": "magnifier_scale", "label": "放大倍数", "type": "double", "min": 1, "max": 20, "decimals": 1, "default": 6.0},
            {"name": "magnifier_radius", "label": "放大镜半径", "type": "spin", "min": 32, "max": 256, "default": 128},
        ],
        "checkboxes": [
            {"name": "magnifier_circle", "label": "使用圆形放大镜", "default": True},
        ],
    },
    {
        "title": "线宽显示",
        "flags": [{"name": "lineweight", "label": "显示/隐藏线宽"}],
        "checkboxes": [
            {"name": "lineweight_follow_zoom", "label": "随缩放自适应线宽", "default": True},
        ],
    },
    {
        "title": "对称画线",
        "flags": [{"name": "symmetry", "label": "启用对称画线"}],
        "checkboxes": [
            {"name": "symmetry_mirror_x", "label": "沿 X 方向镜像", "default": True},
            {"name": "symmetry_mirror_y", "label": "沿 Y 方向镜像", "default": False},
        ],
    },
]


def default_sketch_settings():
    defaults = {}
    for tab in SKETCH_TAB_CONFIGS:
        for field in tab.get("fields", []):
            defaults.setdefault(field["name"], field.get("default"))
        for option in tab.get("checkboxes", []):
            defaults.setdefault(option["name"], option.get("default", False))
    return defaults


class SketchSettingsDialog(QDialog):
    def __init__(self, mode_state, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("草图设置")
        self.resize(720, 460)
        self.mode_state = mode_state
        self.settings = default_sketch_settings()
        if settings:
            self.settings.update(settings)

        self.flag_boxes = {}
        self.field_widgets = {}
        self.checkbox_widgets = {}

        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        for config in SKETCH_TAB_CONFIGS:
            self.tabs.addTab(self._build_tab(config), config["title"])
        root.addWidget(self.tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _build_tab(self, config):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        for flag in config.get("flags", []):
            box = QCheckBox(flag["label"])
            box.setChecked(self.mode_state.flag(flag["name"]))
            self.flag_boxes[flag["name"]] = box
            layout.addWidget(box)

        fields = config.get("fields")
        if fields:
            form = QFormLayout()
            for field in fields:
                widget = self._make_field_widget(field)
                form.addRow(field["label"], widget)
            layout.addLayout(form)

        options = config.get("checkboxes")
        if options:
            grid = QGridLayout()
            for index, option in enumerate(options):
                box = QCheckBox(option["label"])
                box.setChecked(self.settings.get(option["name"], option.get("default", False)))
                self.checkbox_widgets[option["name"]] = box
                row = index // 2
                col = index % 2
                grid.addWidget(box, row, col)
            layout.addLayout(grid)

        layout.addStretch()
        return page

    def _make_field_widget(self, field):
        field_type = field.get("type", "spin")
        default_value = self.settings.get(field["name"], field.get("default", 0))
        if field_type == "double":
            widget = QDoubleSpinBox()
            widget.setDecimals(field.get("decimals", 1))
            widget.setRange(field.get("min", 0.0), field.get("max", 360.0))
            widget.setSingleStep(field.get("step", 0.5))
            widget.setValue(default_value)
        elif field_type == "text":
            widget = QLineEdit(str(default_value))
        else:
            widget = QSpinBox()
            widget.setRange(field.get("min", 0), field.get("max", 1000))
            widget.setSingleStep(field.get("step", 1))
            widget.setValue(int(default_value))
        self.field_widgets[field["name"]] = widget
        return widget

    def values(self):
        flag_values = {name: box.isChecked() for name, box in self.flag_boxes.items()}
        data = dict(self.settings)
        for name, widget in self.field_widgets.items():
            if isinstance(widget, QSpinBox):
                data[name] = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                data[name] = widget.value()
            else:
                data[name] = widget.text().strip()
        for name, box in self.checkbox_widgets.items():
            data[name] = box.isChecked()
        return flag_values, data
