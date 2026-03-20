import json
import math
import os
import re
import shutil
import sqlite3

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QBrush,
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStyle,
    QTabBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTableView,
    QTextEdit,
    QToolButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from canvas import Canvas
from commands import CommandProcessor
from modes import ModeState
from heat_exchanger_data import load_upcomer_pdf_data, resolve_inner_cylinder_spec, summarize_extraction
from tool_actions import ToolActionContext, ToolActionHandler
from ui_tabs import ALL_TABS, RibbonTabConfig


TOOL_TIPS = {
    "Cut": "剪切: 剪切对象",
    "Paste": "粘贴: 粘贴对象",
    "Select": "选择: 选择对象",
    "DoubleLine": "双线管: 绘制两条平行线",
    "Line": "直线: 绘制两点直线",
    "Arc": "圆弧: 绘制圆弧",
    "Polyline": "多段线: 连续绘制折线",
    "Circle": "圆: 以圆心和半径绘制",
    "Center": "圆心: 标注圆心或中心线",
    "Ellipse": "椭圆: 通过两点绘制椭圆",
    "Rect": "矩形: 通过两点绘制矩形",
    "Move": "移动: 平移对象",
    "Rotate": "旋转: 旋转对象",
    "Trim": "修剪: 截断多余部分",
    "Copy": "复制: 复制对象",
    "Mirror": "镜像: 按轴镜像对象",
    "Fillet": "圆角: 连接两条边",
    "Stretch": "拉伸: 拉伸对象",
    "Scale": "缩放: 按比例调整大小",
    "Array": "阵列: 批量复制排列",
    "Rect Array": "矩形阵列: 复制多行多列排列",
    "Boolean": "布尔: 对选中对象执行并、交、差操作",
    "Align": "对齐: 通过参考点快速对齐对象",
    "Break": "对象断线: 在选定位置打断曲线",
    "Delete": "删除: 移除对象",
    "Explode": "分解: 拆开组合对象",
    "Offset": "偏移: 生成平行对象",
    "Layer Props": "图层属性: 管理图层设置",
    "Turn Off": "关闭图层: 隐藏当前图层",
    "Isolate": "隔离图层: 仅显示目标图层",
    "Set Current": "设为当前: 切换当前图层",
    "Text": "文字: 插入文本标注",
    "DimLinear": "线性标注: 标注直线距离",
    "Leader": "引线: 添加引线说明",
    "Table": "表格: 插入表格对象",
    "Create Block": "创建块: 生成块定义",
    "Edit Block": "编辑块: 修改块内容",
    "Insert Block": "插入块: 放置块对象",
    "Color": "颜色: 设置对象颜色",
    "Linetype": "线型: 设置线条样式",
    "Lineweight": "线宽: 设置线条粗细",
    "Measure": "测量: 测量长度或距离",
    "Query": "查询: 查询对象信息",
    "Calculator": "计算器: 打开计算器",
    "Quick Select": "快速选择: 过滤并选择对象",
    "Image": "图像: 插入图片",
    "PDF": "PDF: 导入 PDF 参考",
    "Hatch": "填充: 创建图案填充",
    "LeaderNote": "注释引线: 添加说明",
    "Dimension": "标注: 尺寸标注",
    "Paste": "粘贴: 粘贴内容",
    "Paste Block": "粘贴为块: 粘贴为块",
    "Paste Special": "选择性粘贴: 选择性粘贴",
    "Copy Link": "复制链接: 复制链接",
    "Cut": "剪切: 剪切对象",
    "Box": "长方体: 创建三维体块",
    "Extrude": "拉伸体: 生成实体",
    "Orbit": "三维旋转: 旋转观察视角",
    "Viewport": "视口: 创建布局视口",
    "Pan": "平移: 移动画面",
    "Zoom": "缩放: 调整显示比例",
    "Manager": "管理器: 打开管理工具",
    "Plot": "打印输出: 设置图纸输出",
    "Export": "导出: 输出为其他格式",
    "Print": "打印: 提交打印任务",
    "1内筒体组件": "1内筒体组件: 绘制上升管换热器内筒体组件",
    "2内筒体": "2内筒体: 绘制内筒体",
    "3 下接环组件": "3 下接环组件: 绘制下接环组件",
    "3-1 下连接圈": "3-1 下连接圈: 绘制下连接圈",
    "3-2下连接环": "3-2下连接环: 绘制下连接环",
}

TOOL_MENUS = {
    "Text": {
        "default": ("单行文字", "text_single"),
        "items": [
            ("单行文字", "text_single"),
            ("多行文字", "text_multi"),
        ],
    },
    "Leader": {
        "default": ("引线", "leader"),
        "items": [
            ("引线", "leader"),
            ("添加引线", "leader_add"),
            ("删除引线", "leader_remove"),
            ("对齐合并", "leader_align"),
        ],
    },
    "Dimension": {
        "default": ("线性", "dim_linear"),
        "items": [
            ("线性", "dim_linear"),
            ("对齐", "dim_aligned"),
            ("角度", "dim_angular"),
            ("半径", "dim_radius"),
            ("直径", "dim_diameter"),
            ("坐标", "dim_ordinate"),
            ("折弯", "dim_bend"),
            ("面积标注", "dim_area"),
        ],
    },
    "Polyline": {
        "default": ("多段线", "polyline"),
        "items": [
            ("多段线", "polyline"),
            ("矩形", "rect"),
            ("倾斜矩形", "skew_rect"),
            ("多边形", "polygon"),
            ("修订云线", "revision_cloud"),
            ("圆环", "ring"),
        ],
    },
    "Circle": {
        "default": ("圆心, 半径", "circle_center_radius"),
        "items": [
            ("圆心, 半径", "circle_center_radius"),
            ("圆心, 直径", "circle_center_diameter"),
            ("同心圆", "circle_concentric"),
            ("两点", "circle_2_point"),
            ("三点", "circle_3_point"),
            ("相切, 相切, 半径", "circle_tan_tan_radius"),
            ("相切, 相切, 相切", "circle_tan_tan_tan"),
        ],
    },
    "Arc": {
        "default": ("三点", "arc_3_point"),
        "items": [
            ("三点", "arc_3_point"),
            ("起点, 圆心, 端点", "arc_start_center_end"),
            ("起点, 圆心, 角度", "arc_start_center_angle"),
            ("起点, 圆心, 长度", "arc_start_center_length"),
            ("起点, 端点, 角度", "arc_start_end_angle"),
            ("起点, 端点, 方向", "arc_start_end_direction"),
            ("起点, 端点, 半径", "arc_start_end_radius"),
            ("圆心, 起点, 端点", "arc_center_start_end"),
            ("圆心, 起点, 角度", "arc_center_start_angle"),
            ("圆心, 起点, 长度", "arc_center_start_length"),
            ("连续", "arc_continue"),
        ],
    },
    "Center": {
        "default": ("圆心", "center_mark"),
        "items": [
            ("圆心", "center_mark"),
            ("轴, 端点", "center_axis_endpoint"),
            ("椭圆弧", "ellipse_arc"),
        ],
    },
    "Hatch": {
        "default": ("图案填充", "hatch"),
        "items": [
            ("图案填充", "hatch"),
            ("渐变色", "hatch_gradient"),
            ("边界", "hatch_boundary"),
            ("轮廓线", "hatch_outline"),
        ],
    },
    "Array": {
        "default": ("矩形阵列", "array_rect"),
        "items": [
            ("矩形阵列", "array_rect"),
            ("路径阵列", "array_path"),
            ("环形阵列", "array_polar"),
            ("经典阵列", "array_classic"),
        ],
    },
    "Rect Array": {
        "default": ("矩形阵列", "array_rect"),
        "items": [
            ("矩形阵列", "array_rect"),
            ("路径阵列", "array_path"),
            ("环形阵列", "array_polar"),
            ("经典阵列", "array_classic"),
        ],
    },
    "Fillet": {
        "default": ("圆角", "fillet"),
        "items": [
            ("圆角", "fillet"),
            ("倒角", "chamfer"),
        ],
    },
    "Trim": {
        "default": ("修剪", "trim"),
        "items": [
            ("修剪", "trim"),
            ("延伸", "extend"),
        ],
    },
    "Break": {
        "default": ("打断", "break"),
        "items": [
            ("打断", "break"),
            ("打断于点", "break_at_point"),
        ],
    },
    "Align": {
        "default": ("对齐工具", "align_tool"),
        "items": [
            ("对齐工具", "align_tool"),
            ("对齐", "align"),
            ("均布", "distribute"),
        ],
    },
}

LAYER_COLOR_OPTIONS = (
    "白",
    "红",
    "黄",
    "绿",
    "青",
    "蓝",
    "洋红",
)

LAYER_LINETYPE_OPTIONS = (
    "block",
    "center",
    "bylayer",
    "continuous",
    "dashed",
    "PHANTOM",
)

LAYER_LINEWEIGHT_OPTIONS = (
    "0",
    "0.01",
    "0.05",
    "0.09",
    "0.13",
    "0.15",
    "0.18",
    "0.20",
    "0.25",
    "0.30",
    "0.35",
    "0.40",
    "0.50",
    "0.53",
)

DEFAULT_LAYERS = (
    {
        "name": "0",
        "color": "白",
        "linetype": "bylayer",
        "lineweight": "0.25",
        "on": True,
        "frozen": False,
        "locked": False,
        "transparency": 0.0,
        "plot_style": "默认",
    },
    {
        "name": "文字",
        "color": "绿",
        "linetype": "continuous",
        "lineweight": "0.25",
        "on": True,
        "frozen": False,
        "locked": False,
        "transparency": 0.0,
        "plot_style": "默认",
    },
    {
        "name": "尺寸",
        "color": "黄",
        "linetype": "continuous",
        "lineweight": "0.18",
        "on": True,
        "frozen": False,
        "locked": False,
        "transparency": 0.0,
        "plot_style": "默认",
    },
    {
        "name": "中心线",
        "color": "青",
        "linetype": "center",
        "lineweight": "0.13",
        "on": True,
        "frozen": False,
        "locked": False,
        "transparency": 0.0,
        "plot_style": "默认",
    },
    {
        "name": "虚线",
        "color": "红",
        "linetype": "dashed",
        "lineweight": "0.13",
        "on": True,
        "frozen": False,
        "locked": False,
        "transparency": 0.0,
        "plot_style": "默认",
    },
)

LAYER_SELECTOR_COLUMNS = ("开", "冻", "锁", "颜色", "图层")
LAYER_SELECTOR_NAME_COL = 4

THEMES = {
    "银色": {"surface": "#d9dde3", "accent": "#8b95a1", "text": "#1f2a35"},
    "水绿色": {"surface": "#cfe9e2", "accent": "#4f9d8f", "text": "#12332d"},
    "墨绿色": {"surface": "#c9d6cc", "accent": "#345648", "text": "#15251f"},
    "浅蓝色": {"surface": "#d9e8f6", "accent": "#5d8fc1", "text": "#1f3550"},
    "黑色": {"surface": "#3c4148", "accent": "#8aa7c5", "text": "#f2f5f7"},
}

STATUS_TOGGLES = [
    {"flag": "snap", "label": "捕捉模式", "abbr": "SN", "tooltip": "捕捉模式 (F9)", "color": "#1f9dff"},
    {"flag": "grid", "label": "栅格显示", "abbr": "GR", "tooltip": "栅格显示 (F7)", "color": "#3bbd64"},
    {"flag": "ortho", "label": "正交模式", "abbr": "OR", "tooltip": "正交模式 (F8)", "color": "#ff9800"},
    {"flag": "polar", "label": "极轴追踪", "abbr": "PL", "tooltip": "极轴追踪 (F10)", "color": "#9c27b0"},
    {"flag": "object_snap", "label": "对象捕捉", "abbr": "OS", "tooltip": "对象捕捉 (F3)", "color": "#00bfa5"},
    {"flag": "object_track", "label": "对象跟踪", "abbr": "OT", "tooltip": "对象跟踪 (F11)", "color": "#ff7043"},
    {"flag": "lineweight", "label": "线宽显示", "abbr": "LW", "tooltip": "显示/隐藏线宽", "color": "#5d4037"},
    {"flag": "dynamic_input", "label": "动态输入", "abbr": "DI", "tooltip": "动态输入 (F12)", "color": "#3f51b5"},
    {"flag": "quick_properties", "label": "快捷特性", "abbr": "QP", "tooltip": "快捷特性 (Ctrl+Shift+P)", "color": "#455a64"},
    {"flag": "magnifier", "label": "放大镜", "abbr": "MG", "tooltip": "放大镜 (Ctrl+Shift+M)", "color": "#3949ab"},
    {"flag": "symmetry", "label": "对称画线", "abbr": "SY", "tooltip": "对称画线", "color": "#e91e63"},
]

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

DRAWING_TOOLS = {
    "select": "select",
    "doubleline": "doubleline",
    "line": "line",
    "arc": "arc",
    "arc_3_point": "arc_3_point",
    "arc_start_center_end": "arc_start_center_end",
    "arc_start_center_angle": "arc_start_center_angle",
    "arc_start_center_length": "arc_start_center_length",
    "arc_start_end_angle": "arc_start_end_angle",
    "arc_start_end_direction": "arc_start_end_direction",
    "arc_start_end_radius": "arc_start_end_radius",
    "arc_center_start_end": "arc_center_start_end",
    "arc_center_start_angle": "arc_center_start_angle",
    "arc_center_start_length": "arc_center_start_length",
    "arc_continue": "arc_continue",
    "polyline": "polyline",
    "circle": "circle",
    "circle_center_radius": "circle_center_radius",
    "circle_center_diameter": "circle_center_diameter",
    "circle_2_point": "circle_2_point",
    "circle_3_point": "circle_3_point",
    "circle_concentric": "circle_concentric",
    "circle_tan_tan_radius": "circle_tan_tan_radius",
    "circle_tan_tan_tan": "circle_tan_tan_tan",
    "ellipse": "ellipse",
    "ellipse_arc": "ellipse_arc",
    "rect": "rect",
    "skew_rect": "skew_rect",
    "polygon": "polygon",
    "revision_cloud": "revision_cloud",
    "ring": "ring",
    "center_mark": "center_mark",
    "center_axis_endpoint": "center_axis_endpoint",
    "hatch": "hatch",
    "hatch_gradient": "hatch_gradient",
    "hatch_boundary": "hatch_boundary",
    "hatch_outline": "hatch_outline",
    "array": "array",
    "array_rect": "array_rect",
    "array_path": "array_path",
    "array_polar": "array_polar",
    "array_classic": "array_classic",
    "fillet": "fillet",
    "chamfer": "chamfer",
    "trim": "trim",
    "extend": "extend",
    "break": "break",
    "break_at_point": "break_at_point",
    "align_tool": "align_tool",
    "align": "align",
    "distribute": "distribute",
    "delete": "delete",
    "move": "move",
}


class NewDrawingDialog(QDialog):
    def __init__(self, default_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建图纸")
        layout = QFormLayout(self)

        self.template_combo = QComboBox()
        self.template_combo.addItems(["二维草图", "三维零件", "机械模板"])
        self.name_edit = QLineEdit(default_name)

        layout.addRow("模板", self.template_combo)
        layout.addRow("文件名", self.name_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self):
        name = self.name_edit.text().strip() or "Drawing"
        if name.lower().endswith(".dwg"):
            name = name[:-4]
        return self.template_combo.currentText(), name


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


class TableInsertDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("插入表格")
        layout = QFormLayout(self)

        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 200)
        self.rows_spin.setValue(5)

        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 200)
        self.cols_spin.setValue(4)

        self.style_combo = QComboBox()
        self.style_combo.addItems(["标准", "数据", "标题", "自定义"])

        self.title_row = QCheckBox("包含标题行")
        self.title_row.setChecked(True)

        layout.addRow("行数", self.rows_spin)
        layout.addRow("列数", self.cols_spin)
        layout.addRow("样式", self.style_combo)
        layout.addRow("", self.title_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self):
        return {
            "rows": self.rows_spin.value(),
            "cols": self.cols_spin.value(),
            "style": self.style_combo.currentText(),
            "title_row": self.title_row.isChecked(),
        }


class InnerCylinderParamsDialog(QDialog):
    def __init__(self, params, parent=None):
        super().__init__(parent)
        self.setWindowTitle("内筒体参数设置")
        self.resize(760, 520)
        self.params = params

        layout = QVBoxLayout(self)
        hint = QLabel(
            "读取 project/1内筒体组件.dxf 的尺寸参数，修改后将写入 project_new/1内筒体组件.dxf。"
            "标注文本含 <> 的行，请在新值中仅填写数字。"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.table = QTableWidget(len(params), 4)
        self.table.setHorizontalHeaderLabels(["序号", "标注文本", "当前值", "新值"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked | QAbstractItemView.EditKeyPressed
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        for row, param in enumerate(params):
            idx_item = QTableWidgetItem(str(row + 1))
            idx_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 0, idx_item)

            text_item = QTableWidgetItem(param.get("text_display", ""))
            text_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 1, text_item)

            current_item = QTableWidgetItem(param.get("current", ""))
            current_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 2, current_item)

            new_item = QTableWidgetItem(param.get("current", ""))
            self.table.setItem(row, 3, new_item)

        layout.addWidget(self.table)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        values = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 3)
            values.append(item.text().strip() if item is not None else "")
        return values


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1440, 900)
        self.setWindowTitle("FTCAD")

        self.toolbar_icon_size = QSize(16, 16)
        self.toolbar_button_size = QSize(28, 28)
        self.mode_state = ModeState()
        self.documents = []
        self.document_counter = 1
        self.active_interface = "二维界面"
        self.active_theme = "银色"
        self.current_tool_name = "选择"
        self.sketch_settings = default_sketch_settings()
        self.canvas_theme = {
            "background": "#1e232b",
            "grid": "#353c48",
            "drawing": "#f1f3f5",
            "preview": "#7cc4ff",
        }
        icon_path = os.path.join(os.path.dirname(__file__), "icons", "绘图.svg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        base_dir = os.path.dirname(__file__)
        legacy_db = os.path.join(base_dir, "layers.db")
        self.layer_db_path = os.path.join(base_dir, "Layers.db")
        if not os.path.exists(self.layer_db_path) and os.path.exists(legacy_db):
            try:
                shutil.copy2(legacy_db, self.layer_db_path)
            except OSError:
                self.layer_db_path = legacy_db
        self._ensure_layer_db()
        self.layer_manager_visible = False
        self.layer_manager_width = 260
        self.layer_selector = None
        self.layer_selector_model = None
        self.layer_selector_view = None
        self.prop_color_combo = None
        self.prop_linetype_combo = None
        self.prop_lineweight_combo = None
        self.layer_table = None
        self._layer_table_updating = False
        self._syncing_layer_ui = False
        self.upcomer_pdf_data = None
        self.tool_actions = None

        self._build_option_actions()
        self._load_upcomer_pdf_data()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.menu_widget = self._build_menu_row()
        root.addWidget(self.menu_widget)

        self.ribbon_tabs = self._build_ribbon_tabs()
        root.addWidget(self.ribbon_tabs)

        self.layer_manager_panel = self._build_layer_manager_panel()

        self.doc_tabs = QTabWidget()
        self.doc_tabs.setTabsClosable(True)
        self.doc_tabs.tabCloseRequested.connect(self._close_document)
        self.doc_tabs.currentChanged.connect(self._on_document_changed)

        self.layout_tabs = QTabBar()
        self.layout_tabs.addTab("模型")
        self.layout_tabs.addTab("布局1")
        self.layout_tabs.addTab("布局2")
        self.layout_tabs.currentChanged.connect(self._on_layout_changed)
        self.layout_tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.layout_tabs.customContextMenuRequested.connect(self._show_layout_menu)
        self.cmd_widget = QWidget()
        cmd_layout = QVBoxLayout(self.cmd_widget)
        cmd_layout.setContentsMargins(6, 3, 6, 3)
        cmd_layout.setSpacing(2)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumHeight(42)
        self.input = QLineEdit()
        self.input.setFixedHeight(22)
        self.input.setPlaceholderText("输入命令，例如: line 10 10 100 100")
        self.input.returnPressed.connect(self._on_command_entered)
        cmd_layout.addWidget(self.output)
        cmd_layout.addWidget(self.input)

        self.work_area = QWidget()
        work_layout = QVBoxLayout(self.work_area)
        work_layout.setContentsMargins(0, 0, 0, 0)
        work_layout.setSpacing(0)
        work_layout.addWidget(self.doc_tabs, 1)
        work_layout.addWidget(self.layout_tabs)

        self.workspace_splitter = QSplitter(Qt.Horizontal)
        self.workspace_splitter.setChildrenCollapsible(False)
        self.workspace_splitter.setHandleWidth(6)
        self.workspace_splitter.addWidget(self.layer_manager_panel)
        self.workspace_splitter.addWidget(self.work_area)
        self.workspace_splitter.setStretchFactor(0, 0)
        self.workspace_splitter.setStretchFactor(1, 1)
        self.layer_manager_panel.setVisible(False)

        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(6)
        self.main_splitter.addWidget(self.workspace_splitter)
        self.main_splitter.addWidget(self.cmd_widget)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        root.addWidget(self.main_splitter, 1)

        self.status_widget = QWidget()
        status_layout = QVBoxLayout(self.status_widget)
        status_layout.setContentsMargins(8, 4, 8, 4)
        status_layout.setSpacing(2)

        info_row = QHBoxLayout()
        info_row.setContentsMargins(0, 0, 0, 0)
        info_row.setSpacing(6)
        self.status_label = QLabel("就绪")
        self.mode_label = QLabel("模式: 无")
        info_row.addWidget(self.status_label)
        info_row.addStretch()
        info_row.addWidget(self.mode_label)
        status_layout.addLayout(info_row)

        coord_row = QHBoxLayout()
        coord_row.setContentsMargins(0, 0, 0, 0)
        coord_row.setSpacing(6)
        self.coord_label = QLabel("光标: X=0 Y=0")
        self.coord_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.coord_label.customContextMenuRequested.connect(self._open_sketch_settings_dialog)
        coord_row.addWidget(self.coord_label)
        coord_row.addStretch()
        self.status_toggle_buttons = {}
        coord_row.addWidget(self._build_status_toggle_bar())
        status_layout.addLayout(coord_row)
        root.addWidget(self.status_widget)

        self._style_command_area()
        self._apply_theme(self.active_theme)
        self._refresh_mode_summary()
        self._create_default_document()
        self.main_splitter.setSizes([780, 84])
        self.workspace_splitter.setSizes([0, 1])
        self.tool_actions = ToolActionHandler(self._build_tool_action_context())

    def _build_option_actions(self):
        self.interface_action_group = QActionGroup(self)
        self.interface_action_group.setExclusive(True)
        for label in ["二维界面", "三维界面"]:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(label == self.active_interface)
            action.triggered.connect(lambda checked=False, value=label: self._set_interface_mode(value))
            self.interface_action_group.addAction(action)

        self.theme_action_group = QActionGroup(self)
        self.theme_action_group.setExclusive(True)
        for label in THEMES:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(label == self.active_theme)
            action.triggered.connect(lambda checked=False, value=label: self._apply_theme(value))
            self.theme_action_group.addAction(action)

    def _load_upcomer_pdf_data(self):
        base_dir = os.path.dirname(__file__)
        try:
            self.upcomer_pdf_data = load_upcomer_pdf_data(base_dir)
        except Exception:
            self.upcomer_pdf_data = None

    def _build_menu_row(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(2)

        labels = ["新建", "打开", "保存", "另存", "打印", "撤销", "重做"]
        buttons = [QPushButton(text) for text in labels]
        (
            self.new_btn,
            self.open_btn,
            self.save_btn,
            self.save_as_btn,
            self.print_btn,
            self.undo_btn,
            self.redo_btn,
        ) = buttons
        base_dir = os.path.dirname(__file__)
        undo_icon = os.path.join(base_dir, "icons", "上一步.svg")
        redo_icon = os.path.join(base_dir, "icons", "下一步.svg")
        if os.path.exists(undo_icon):
            self.undo_btn.setIcon(QIcon(undo_icon))
            self.undo_btn.setIconSize(self.toolbar_icon_size)
        if os.path.exists(redo_icon):
            self.redo_btn.setIcon(QIcon(redo_icon))
            self.redo_btn.setIconSize(self.toolbar_icon_size)
        for button in buttons:
            layout.addWidget(button)

        self.options_btn = QToolButton()
        self.options_btn.setText("选项框")
        self.options_btn.setPopupMode(QToolButton.InstantPopup)
        self.options_btn.setMenu(self._build_options_menu())
        layout.addWidget(self.options_btn)
        layout.addStretch()

        self.new_btn.clicked.connect(self._new_document)
        self.open_btn.clicked.connect(self._open_file)
        self.save_btn.clicked.connect(self._save_file)
        self.save_as_btn.clicked.connect(self._save_file_as)
        self.print_btn.clicked.connect(self._print_current)
        self.undo_btn.clicked.connect(self._undo_current)
        self.redo_btn.clicked.connect(self._redo_current)
        return widget

    def _build_status_toggle_bar(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        for config in STATUS_TOGGLES:
            button = QToolButton()
            button.setText(config["abbr"])
            button.setToolTip(config["tooltip"])
            button.setCheckable(True)
            button.setChecked(self.mode_state.flag(config["flag"]))
            button.setFixedHeight(22)
            button.setStyleSheet(
                "QToolButton { min-width: 30px; padding: 2px 6px; border: 1px solid #4d5968; border-radius: 3px; }"
                f"QToolButton:checked {{ background: {config['color']}; color: white; }}"
            )
            button.setContextMenuPolicy(Qt.CustomContextMenu)
            button.customContextMenuRequested.connect(self._open_sketch_settings_dialog)
            button.toggled.connect(
                lambda checked, flag=config["flag"], label=config["label"]: self._on_status_toggle(flag, label, checked)
            )
            layout.addWidget(button)
            self.status_toggle_buttons[config["flag"]] = button
        return widget

    def _build_options_menu(self):
        menu = QMenu(self)
        interface_menu = menu.addMenu("界面模式")
        interface_menu.addActions(self.interface_action_group.actions())
        theme_menu = menu.addMenu("选项框颜色")
        theme_menu.addActions(self.theme_action_group.actions())
        return menu

    def _build_ribbon_tabs(self):
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        for tab_config in ALL_TABS:
            tabs.addTab(self._build_tab_page(tab_config), tab_config.name)
        return tabs

    def _build_tab_page(self, tab_config: RibbonTabConfig):
        page = QWidget()
        page_layout = QHBoxLayout(page)
        page_layout.setContentsMargins(6, 2, 6, 2)
        page_layout.setSpacing(4)
        text_buttons = tab_config.name == "方特上升管换热器"
        for section in tab_config.sections:
            if tab_config.name == "常规" and section.title == "图层":
                page_layout.addWidget(self._make_layer_section(section.tools, section.title))
            elif tab_config.name == "常规" and section.title == "特性":
                page_layout.addWidget(self._make_properties_section(section.title))
            else:
                page_layout.addWidget(
                    self._make_ribbon_section(section.tools, section.title, text_buttons=text_buttons)
                )
        page_layout.addStretch()
        return page

    def _on_status_toggle(self, flag_name, label, checked):
        self.mode_state.set_flag(flag_name, checked)
        state_text = "开启" if checked else "关闭"
        self.status_label.setText(f"{label}: {state_text}")
        self._refresh_mode_summary()
        self._apply_mode_effects(flag_name)

    def _apply_mode_effects(self, flag_name=None):
        if not self.documents:
            return
        flags = [flag_name] if flag_name else [config["flag"] for config in STATUS_TOGGLES]
        for flag in flags:
            if flag == "grid":
                spacing_x = self.sketch_settings.get("grid_spacing_x", 10)
                spacing_y = self.sketch_settings.get("grid_spacing_y", 10)
                for document in self.documents:
                    canvas = document["canvas"]
                    canvas.set_grid_spacing(spacing_x, spacing_y)
                    canvas.update()
            elif flag == "symmetry":
                enabled = self.mode_state.flag("symmetry")
                for document in self.documents:
                    document["canvas"].set_symmetry_mode(enabled)

    def _refresh_mode_summary(self):
        enabled = []
        for config in STATUS_TOGGLES:
            is_enabled = self.mode_state.flag(config["flag"])
            if is_enabled:
                enabled.append(config["abbr"])
            button = self.status_toggle_buttons.get(config["flag"])
            if button is not None:
                prev = button.blockSignals(True)
                button.setChecked(is_enabled)
                button.blockSignals(prev)
        summary = "、".join(enabled) if enabled else "无"
        self.mode_label.setText(f"模式: {summary}")

    def _make_ribbon_section(self, names, title_text, text_buttons=False):
        frame = QWidget()
        frame.setObjectName("ribbonSection")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(2)
        grid.setVerticalSpacing(2)
        for index, name in enumerate(names):
            row = index % 3
            col = index // 3
            grid.addWidget(self._icon_button(name, full_text=text_buttons), row, col)
        layout.addWidget(grid_widget)

        title = QLabel(title_text)
        title.setProperty("role", "sectionTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        return frame

    def _make_layer_section(self, names, title_text):
        frame = QWidget()
        frame.setObjectName("ribbonSection")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(2)
        grid.setVerticalSpacing(2)
        for index, name in enumerate(names):
            row = index % 3
            col = index // 3
            grid.addWidget(self._icon_button(name), row, col)
        layout.addWidget(grid_widget)

        selector = QComboBox()
        selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        selector.setMinimumWidth(180)
        selector.currentTextChanged.connect(self._on_layer_selected)
        view = QTableView()
        view.setShowGrid(False)
        view.verticalHeader().setVisible(False)
        view.horizontalHeader().setVisible(False)
        view.setSelectionBehavior(QAbstractItemView.SelectRows)
        view.setSelectionMode(QAbstractItemView.SingleSelection)
        view.setEditTriggers(QAbstractItemView.SelectedClicked)
        view.setAlternatingRowColors(True)
        view.verticalHeader().setDefaultSectionSize(22)
        selector.setView(view)
        model = QStandardItemModel(0, len(LAYER_SELECTOR_COLUMNS), selector)
        selector.setModel(model)
        selector.setModelColumn(LAYER_SELECTOR_NAME_COL)
        model.itemChanged.connect(self._on_layer_selector_item_changed)
        self.layer_selector = selector
        self.layer_selector_view = view
        self.layer_selector_model = model
        layout.addWidget(selector)

        title = QLabel(title_text)
        title.setProperty("role", "sectionTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        return frame

    def _make_properties_section(self, title_text):
        frame = QWidget()
        frame.setObjectName("ribbonSection")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(2)

        self.prop_color_combo = QComboBox()
        self.prop_color_combo.addItems(LAYER_COLOR_OPTIONS)
        self.prop_color_combo.currentTextChanged.connect(
            lambda value, prop="color": self._on_layer_property_changed(prop, value)
        )

        self.prop_linetype_combo = QComboBox()
        self.prop_linetype_combo.addItems(LAYER_LINETYPE_OPTIONS)
        self.prop_linetype_combo.currentTextChanged.connect(
            lambda value, prop="linetype": self._on_layer_property_changed(prop, value)
        )

        self.prop_lineweight_combo = QComboBox()
        self.prop_lineweight_combo.addItems(LAYER_LINEWEIGHT_OPTIONS)
        self.prop_lineweight_combo.currentTextChanged.connect(
            lambda value, prop="lineweight": self._on_layer_property_changed(prop, value)
        )

        for icon_name, combo in (
            ("Color", self.prop_color_combo),
            ("Linetype", self.prop_linetype_combo),
            ("Lineweight", self.prop_lineweight_combo),
        ):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            row.addWidget(self._icon_button(icon_name))
            combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            row.addWidget(combo, 1)
            content_layout.addLayout(row)

        layout.addWidget(content)

        title = QLabel(title_text)
        title.setProperty("role", "sectionTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        return frame

    def _icon_button(self, name, full_text=False):
        button = QToolButton()
        button.setToolTip(TOOL_TIPS.get(name, name))

        safe = "".join(ch for ch in name if ch.isalnum() or ch in (" ", "_")).lower().replace(" ", "_")
        icon_path = os.path.join(os.path.dirname(__file__), "icons", f"{safe}.svg")
        if os.path.exists(icon_path):
            button.setFixedSize(self.toolbar_button_size)
            button.setIconSize(self.toolbar_icon_size)
            button.setIcon(QIcon(icon_path))
            button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        else:
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            if full_text:
                button.setText(name)
                button.setFixedHeight(self.toolbar_button_size.height())
                text_width = button.fontMetrics().horizontalAdvance(name)
                min_width = max(self.toolbar_button_size.width(), text_width + 16)
                button.setMinimumWidth(min_width)
                button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            else:
                display = "".join(ch for ch in name if ch.isalnum())
                if not display:
                    display = name
                button.setText(display[:2])
                button.setFixedSize(self.toolbar_button_size)

        menu_config = TOOL_MENUS.get(name)
        if menu_config:
            menu = QMenu(button)
            for label, tool_key in menu_config["items"]:
                action = QAction(label, menu)
                action.triggered.connect(
                    lambda checked=False, tool=tool_key, label=label: self._tool_clicked(tool, label)
                )
                menu.addAction(action)
            button.setMenu(menu)
            button.setPopupMode(QToolButton.MenuButtonPopup)
            default_label, default_tool = menu_config.get("default", menu_config["items"][0])
            button.clicked.connect(
                lambda checked=False, tool=default_tool, label=default_label: self._tool_clicked(tool, label)
            )
        else:
            button.clicked.connect(lambda checked=False, tool=name: self._tool_clicked(tool))
        return button

    def _build_layer_manager_panel(self):
        panel = QWidget()
        panel.setObjectName("layerManagerPanel")
        panel.setMinimumWidth(220)
        panel.setMaximumWidth(360)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("图层特性管理器")
        title.setProperty("role", "sectionTitle")
        header.addWidget(title)
        header.addStretch()
        close_btn = QToolButton()
        close_btn.setText("×")
        close_btn.setFixedSize(18, 18)
        close_btn.clicked.connect(lambda: self._toggle_layer_manager(False))
        header.addWidget(close_btn)
        layout.addLayout(header)

        for label in ("新建图层过滤器", "新建组过滤器", "图层状态管理器"):
            button = QPushButton(label)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(lambda checked=False, text=label: self._on_layer_manager_action(text))
            layout.addWidget(button)

        self.layer_table = QTableWidget(0, 9)
        self.layer_table.setHorizontalHeaderLabels(
            ["图层", "开", "冻", "锁", "颜色", "线型", "线宽", "透明度", "打印样式"]
        )
        self.layer_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layer_table.verticalHeader().setVisible(False)
        self.layer_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.layer_table.setEditTriggers(QAbstractItemView.SelectedClicked)
        self.layer_table.setAlternatingRowColors(True)
        self.layer_table.itemSelectionChanged.connect(self._on_layer_table_selection)
        self.layer_table.itemChanged.connect(self._on_layer_table_item_changed)
        layout.addWidget(self.layer_table, 1)

        return panel

    def _on_layer_manager_action(self, label):
        self.output.append(f"{label}: 功能暂未实现")
        self.status_label.setText(f"{label}: 功能暂未实现")

    def _toggle_layer_manager(self, show=None):
        if show is None:
            show = not self.layer_manager_panel.isVisible()

        if show:
            self.layer_manager_panel.setVisible(True)
            sizes = self.workspace_splitter.sizes()
            total = sum(sizes) if sizes else max(600, self.width())
            width = max(200, self.layer_manager_width or 260)
            self.workspace_splitter.setSizes([width, max(200, total - width)])
            self.layer_manager_visible = True
            self._refresh_layer_table()
            return

        sizes = self.workspace_splitter.sizes()
        total = sum(sizes) if sizes else max(1, self.width())
        if sizes and sizes[0] > 0:
            self.layer_manager_width = sizes[0]
        self.layer_manager_panel.setVisible(False)
        self.workspace_splitter.setSizes([0, max(1, total)])
        self.layer_manager_visible = False

    def _ensure_layer_db(self):
        os.makedirs(os.path.dirname(self.layer_db_path), exist_ok=True)
        with sqlite3.connect(self.layer_db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS layers (
                    name TEXT PRIMARY KEY,
                    is_on INTEGER NOT NULL,
                    is_frozen INTEGER NOT NULL,
                    is_locked INTEGER NOT NULL,
                    color TEXT NOT NULL,
                    linetype TEXT NOT NULL,
                    lineweight TEXT NOT NULL,
                    transparency REAL NOT NULL,
                    plot_style TEXT NOT NULL
                )
                """
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(layers)")}
            if "transparency" not in columns:
                conn.execute("ALTER TABLE layers ADD COLUMN transparency REAL NOT NULL DEFAULT 0.0")
            if "plot_style" not in columns:
                conn.execute("ALTER TABLE layers ADD COLUMN plot_style TEXT NOT NULL DEFAULT '默认'")

    def _load_layers_from_db(self):
        self._ensure_layer_db()
        with sqlite3.connect(self.layer_db_path) as conn:
            cursor = conn.execute(
                "SELECT name, is_on, is_frozen, is_locked, color, linetype, lineweight, transparency, plot_style FROM layers ORDER BY name"
            )
            rows = cursor.fetchall()

        if not rows:
            for layer in DEFAULT_LAYERS:
                self._upsert_layer_to_db(layer)
            return [layer.copy() for layer in DEFAULT_LAYERS]

        layers = []
        for row in rows:
            layers.append(
                {
                    "name": row[0],
                    "on": bool(row[1]),
                    "frozen": bool(row[2]),
                    "locked": bool(row[3]),
                    "color": row[4],
                    "linetype": row[5],
                    "lineweight": row[6],
                    "transparency": float(row[7] if row[7] is not None else 0.0),
                    "plot_style": row[8] if row[8] is not None else "默认",
                }
            )
        return layers

    def _upsert_layer_to_db(self, layer):
        self._ensure_layer_db()
        payload = (
            layer.get("name", ""),
            1 if layer.get("on", True) else 0,
            1 if layer.get("frozen", False) else 0,
            1 if layer.get("locked", False) else 0,
            layer.get("color", LAYER_COLOR_OPTIONS[0]),
            layer.get("linetype", LAYER_LINETYPE_OPTIONS[0]),
            layer.get("lineweight", LAYER_LINEWEIGHT_OPTIONS[0]),
            float(layer.get("transparency", 0.0)),
            layer.get("plot_style", "默认"),
        )
        with sqlite3.connect(self.layer_db_path) as conn:
            conn.execute(
                """
                INSERT INTO layers
                (name, is_on, is_frozen, is_locked, color, linetype, lineweight, transparency, plot_style)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    is_on=excluded.is_on,
                    is_frozen=excluded.is_frozen,
                    is_locked=excluded.is_locked,
                    color=excluded.color,
                    linetype=excluded.linetype,
                    lineweight=excluded.lineweight,
                    transparency=excluded.transparency,
                    plot_style=excluded.plot_style
                """,
                payload,
            )

    def _fetch_layer_from_db(self, name):
        if not name:
            return None
        self._ensure_layer_db()
        with sqlite3.connect(self.layer_db_path) as conn:
            cursor = conn.execute(
                "SELECT name, is_on, is_frozen, is_locked, color, linetype, lineweight, transparency, plot_style FROM layers WHERE name = ?",
                (name,),
            )
            row = cursor.fetchone()
        if not row:
            return None
        return {
            "name": row[0],
            "on": bool(row[1]),
            "frozen": bool(row[2]),
            "locked": bool(row[3]),
            "color": row[4],
            "linetype": row[5],
            "lineweight": row[6],
            "transparency": float(row[7] if row[7] is not None else 0.0),
            "plot_style": row[8] if row[8] is not None else "默认",
        }

    def _ensure_document_layers(self, document):
        if "layers" not in document or not document["layers"]:
            document["layers"] = self._load_layers_from_db()
        for layer in document["layers"]:
            layer.setdefault("on", True)
            layer.setdefault("frozen", False)
            layer.setdefault("locked", False)
            layer.setdefault("color", LAYER_COLOR_OPTIONS[0])
            layer.setdefault("linetype", LAYER_LINETYPE_OPTIONS[0])
            layer.setdefault("lineweight", LAYER_LINEWEIGHT_OPTIONS[0])
            layer.setdefault("transparency", 0.0)
            layer.setdefault("plot_style", "默认")
        layer_names = [layer["name"] for layer in document["layers"]]
        current = document.get("current_layer")
        if not current or current not in layer_names:
            document["current_layer"] = layer_names[0] if layer_names else "0"

    def _set_combo_value(self, combo, value):
        if combo is None:
            return
        items = [combo.itemText(index) for index in range(combo.count())]
        if value not in items:
            combo.addItem(value)
        prev = combo.blockSignals(True)
        combo.setCurrentText(value)
        combo.blockSignals(prev)

    def _color_from_name(self, name):
        if not name:
            return None
        key = name.strip().lower()
        if key == "bylayer":
            return None
        if key.startswith("#") and len(key) in (4, 7):
            color = QColor(name)
            return color if color.isValid() else None
        mapping = {
            "white": "#ffffff",
            "red": "#e53935",
            "yellow": "#fdd835",
            "green": "#43a047",
            "cyan": "#00acc1",
            "blue": "#1e88e5",
            "magenta": "#d81b60",
            "白": "#ffffff",
            "红": "#e53935",
            "黄": "#fdd835",
            "绿": "#43a047",
            "青": "#00acc1",
            "蓝": "#1e88e5",
            "洋红": "#d81b60",
        }
        if key in mapping:
            return QColor(mapping[key])
        if name in mapping:
            return QColor(mapping[name])
        return None

    def _text_color_for_background(self, color):
        if color is None or not color.isValid():
            return None
        luminance = (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue())
        return QColor("#000000") if luminance > 140 else QColor("#ffffff")

    def _color_name_from_qcolor(self, color):
        if color is None or not color.isValid():
            return None
        candidates = {
            "白": QColor("#ffffff"),
            "红": QColor("#e53935"),
            "黄": QColor("#fdd835"),
            "绿": QColor("#43a047"),
            "青": QColor("#00acc1"),
            "蓝": QColor("#1e88e5"),
            "洋红": QColor("#d81b60"),
        }
        best_name = None
        best_dist = None
        for name, ref in candidates.items():
            dr = color.red() - ref.red()
            dg = color.green() - ref.green()
            db = color.blue() - ref.blue()
            dist = dr * dr + dg * dg + db * db
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_name = name
        if best_name is not None and best_dist is not None and best_dist <= 4000:
            return best_name
        return color.name()

    def _sync_layer_ui(self):
        if self._syncing_layer_ui:
            return
        self._syncing_layer_ui = True
        document = self.current_document()
        if document is None:
            self._refresh_layer_selector(None)
            for combo in (self.prop_color_combo, self.prop_linetype_combo, self.prop_lineweight_combo):
                if combo:
                    combo.setEnabled(False)
            if self.layer_table is not None:
                self.layer_table.setRowCount(0)
            self._syncing_layer_ui = False
            return

        self._ensure_document_layers(document)
        db_layers = {layer["name"]: layer for layer in self._load_layers_from_db()}
        layers = []
        for layer in document["layers"]:
            merged = dict(layer)
            if layer.get("name") in db_layers:
                merged.update(db_layers[layer["name"]])
            layers.append(merged)
        document["layers"] = [layer.copy() for layer in layers]
        layer_names = [layer["name"] for layer in layers]
        current_name = document.get("current_layer")
        if not current_name or current_name not in layer_names:
            document["current_layer"] = layer_names[0] if layer_names else None
            current_name = document["current_layer"]
        current_layer = next((layer for layer in layers if layer["name"] == current_name), None)
        if current_layer is None and layers:
            current_layer = layers[0]
            document["current_layer"] = current_layer["name"]

        self._refresh_layer_selector(document)

        for combo in (self.prop_color_combo, self.prop_linetype_combo, self.prop_lineweight_combo):
            if combo:
                combo.setEnabled(True)

        if current_layer:
            self._set_combo_value(self.prop_color_combo, current_layer["color"])
            self._set_combo_value(self.prop_linetype_combo, current_layer["linetype"])
            self._set_combo_value(self.prop_lineweight_combo, current_layer["lineweight"])
            canvas = document.get("canvas")
            if canvas is not None:
                canvas.set_active_layer(current_layer)

        self._refresh_layer_table()
        self._syncing_layer_ui = False

    def _refresh_layer_selector(self, document=None):
        selector = self.layer_selector
        model = self.layer_selector_model
        view = self.layer_selector_view
        if selector is None:
            return
        if model is None or view is None:
            prev = selector.blockSignals(True)
            selector.clear()
            selector.setEnabled(False)
            selector.blockSignals(prev)
            return
        if document is None:
            prev = selector.blockSignals(True)
            model.blockSignals(True)
            model.removeRows(0, model.rowCount())
            selector.setEnabled(False)
            model.blockSignals(False)
            selector.blockSignals(prev)
            return

        self._ensure_document_layers(document)
        layers = document["layers"]
        current_name = document.get("current_layer")

        prev = selector.blockSignals(True)
        model.blockSignals(True)
        model.removeRows(0, model.rowCount())

        for row, layer in enumerate(layers):
            on_item = QStandardItem()
            on_item.setCheckable(True)
            on_item.setCheckState(Qt.Checked if layer.get("on", True) else Qt.Unchecked)
            on_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)

            frozen_item = QStandardItem()
            frozen_item.setCheckable(True)
            frozen_item.setCheckState(Qt.Checked if layer.get("frozen", False) else Qt.Unchecked)
            frozen_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)

            locked_item = QStandardItem()
            locked_item.setCheckable(True)
            locked_item.setCheckState(Qt.Checked if layer.get("locked", False) else Qt.Unchecked)
            locked_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)

            color_name = layer.get("color", "ByLayer")
            color_item = QStandardItem(color_name)
            color_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            swatch = self._color_from_name(color_name)
            if swatch is not None:
                color_item.setBackground(QBrush(swatch))
                text_color = self._text_color_for_background(swatch)
                if text_color is not None:
                    color_item.setForeground(QBrush(text_color))

            name_item = QStandardItem(layer.get("name", ""))
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            model.appendRow([on_item, frozen_item, locked_item, color_item, name_item])

        selector.setEnabled(True)
        if current_name:
            for row, layer in enumerate(layers):
                if layer.get("name") == current_name:
                    selector.setCurrentIndex(row)
                    view.selectRow(row)
                    break

        model.blockSignals(False)
        selector.blockSignals(prev)

        if view is not None:
            view.resizeColumnsToContents()
            view.setColumnWidth(0, 28)
            view.setColumnWidth(1, 28)
            view.setColumnWidth(2, 28)
            view.setColumnWidth(3, 60)
            view.setColumnWidth(4, 140)
            total_width = sum(view.columnWidth(i) for i in range(model.columnCount())) + 24
            view.setMinimumWidth(max(220, total_width))

    def _refresh_layer_table(self):
        if self.layer_table is None:
            return
        document = self.current_document()
        layers = self._load_layers_from_db()
        if document is None:
            self.layer_table.setRowCount(0)
            return
        document["layers"] = [layer.copy() for layer in layers]
        current_name = document.get("current_layer")

        self._layer_table_updating = True
        self.layer_table.blockSignals(True)
        self.layer_table.setRowCount(len(layers))
        current_row = -1
        for row, layer in enumerate(layers):
            if layer["name"] == current_name:
                current_row = row

            name_item = QTableWidgetItem(layer.get("name", ""))
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.layer_table.setItem(row, 0, name_item)

            for col, key in ((1, "on"), (2, "frozen"), (3, "locked")):
                state_item = QTableWidgetItem("")
                state_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
                state_item.setCheckState(Qt.Checked if layer.get(key, False) else Qt.Unchecked)
                self.layer_table.setItem(row, col, state_item)

            color_name = layer.get("color", "")
            color_item = QTableWidgetItem(color_name)
            color_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            swatch = self._color_from_name(color_name)
            if swatch is not None:
                color_item.setBackground(QBrush(swatch))
                text_color = self._text_color_for_background(swatch)
                if text_color is not None:
                    color_item.setForeground(QBrush(text_color))
            self.layer_table.setItem(row, 4, color_item)

            linetype_item = QTableWidgetItem(str(layer.get("linetype", "")))
            linetype_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.layer_table.setItem(row, 5, linetype_item)

            lineweight_item = QTableWidgetItem(str(layer.get("lineweight", "")))
            lineweight_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.layer_table.setItem(row, 6, lineweight_item)

            transparency_item = QTableWidgetItem(str(layer.get("transparency", 0.0)))
            transparency_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.layer_table.setItem(row, 7, transparency_item)

            plot_item = QTableWidgetItem(str(layer.get("plot_style", "")))
            plot_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.layer_table.setItem(row, 8, plot_item)

        if current_row >= 0:
            self.layer_table.selectRow(current_row)
        self.layer_table.blockSignals(False)
        self._layer_table_updating = False

    def _on_layer_table_selection(self):
        if self._layer_table_updating:
            return
        row = self.layer_table.currentRow() if self.layer_table is not None else -1
        if row < 0:
            return
        item = self.layer_table.item(row, 0)
        if item:
            self._set_current_layer(item.text())

    def _on_layer_table_item_changed(self, item):
        if self._layer_table_updating or item is None:
            return
        row = item.row()
        col = item.column()
        document = self.current_document()
        if document is None:
            return
        self._ensure_document_layers(document)
        layers = document["layers"]
        if row < 0 or row >= len(layers):
            return
        layer = layers[row]
        if col == 1:
            layer["on"] = item.checkState() == Qt.Checked
        elif col == 2:
            layer["frozen"] = item.checkState() == Qt.Checked
        elif col == 3:
            layer["locked"] = item.checkState() == Qt.Checked
        else:
            return
        self._upsert_layer_to_db(layer)
        self._refresh_layer_selector(document)

    def _on_layer_selected(self, layer_name):
        if self._syncing_layer_ui:
            return
        self._set_current_layer(layer_name)

    def _on_layer_selector_item_changed(self, item):
        if self._syncing_layer_ui:
            return
        document = self.current_document()
        if document is None or item is None:
            return
        self._ensure_document_layers(document)
        row = item.row()
        if row < 0 or row >= len(document["layers"]):
            return
        layer = document["layers"][row]
        col = item.column()
        if col == 0:
            layer["on"] = item.checkState() == Qt.Checked
        elif col == 1:
            layer["frozen"] = item.checkState() == Qt.Checked
        elif col == 2:
            layer["locked"] = item.checkState() == Qt.Checked
        else:
            return
        self._upsert_layer_to_db(layer)
        self._refresh_layer_table()

    def _set_current_layer(self, layer_name):
        document = self.current_document()
        if document is None:
            return
        self._ensure_document_layers(document)
        if layer_name not in [layer["name"] for layer in document["layers"]]:
            return
        document["current_layer"] = layer_name
        db_layer = self._fetch_layer_from_db(layer_name)
        if db_layer:
            for layer in document["layers"]:
                if layer["name"] == layer_name:
                    layer.update(db_layer)
                    break
            self._set_combo_value(self.prop_color_combo, db_layer["color"])
            self._set_combo_value(self.prop_linetype_combo, db_layer["linetype"])
            self._set_combo_value(self.prop_lineweight_combo, db_layer["lineweight"])
            canvas = document.get("canvas")
            if canvas is not None:
                canvas.set_active_layer(db_layer)
        self.status_label.setText(f"当前图层: {layer_name}")
        self._sync_layer_ui()

    def _on_layer_property_changed(self, prop, value):
        if self._syncing_layer_ui:
            return
        document = self.current_document()
        if document is None:
            return
        self._ensure_document_layers(document)
        current_name = document.get("current_layer")
        for layer in document["layers"]:
            if layer["name"] == current_name:
                layer[prop] = value
                self._upsert_layer_to_db(layer)
                canvas = document.get("canvas")
                if canvas is not None:
                    canvas.set_active_layer(layer)
                break
        self._refresh_layer_table()
        self._refresh_layer_selector(document)

    def _center_dialog(self, dialog):
        dialog.ensurePolished()
        window_center = self.mapToGlobal(self.rect().center())
        dialog_center = dialog.rect().center()
        dialog.move(window_center - dialog_center)

    def _open_sketch_settings_dialog(self, pos=None):
        del pos
        dialog = SketchSettingsDialog(self.mode_state, self.sketch_settings, self)
        self._center_dialog(dialog)
        if dialog.exec() == QDialog.Accepted:
            flag_values, settings = dialog.values()
            for name, value in flag_values.items():
                self.mode_state.set_flag(name, value)
            self.sketch_settings.update(settings)
            self.status_label.setText("草图设置已更新")
            self._refresh_mode_summary()
            self._apply_mode_effects()

    def _style_command_area(self):
        self.cmd_widget.setStyleSheet(
            "QWidget { background: #151a20; color: #dfe6ee; }"
            "QTextEdit, QLineEdit { background: #20252c; color: #f2f5f7; border: 1px solid #3a4553; }"
        )

    def _normalize_document_name(self, name):
        base_name = (name or 'Drawing').strip() or 'Drawing'
        lower_name = base_name.lower()
        if not (lower_name.endswith('.dwg') or lower_name.endswith('.dxf')):
            base_name = f'{base_name}.dxf'
        return base_name

    def _add_document(self, file_name, template_name, path=None, shapes=None):
        normalized_name = self._normalize_document_name(file_name)
        canvas, page = self._create_document_canvas(template_name)
        if shapes is not None:
            canvas.load_from_dict({'shapes': shapes})
        document = {
            'name': normalized_name,
            'template': template_name,
            'path': path,
            'canvas': canvas,
            'page': page,
        }
        self.documents.append(document)
        index = self.doc_tabs.addTab(page, normalized_name)
        self.doc_tabs.setCurrentIndex(index)
        self.status_label.setText(f'当前图纸: {normalized_name}')
        self._sync_title()
        self._sync_layer_ui()
        return document

    def _create_default_document(self):
        self._add_document('Drawing', '二维草图')

    def _create_document_canvas(self, template_name):
        canvas = Canvas(self.mode_state)
        canvas.point_info.connect(self._on_canvas_point)
        canvas.pointer_info.connect(self.coord_label.setText)
        canvas.tool_changed.connect(self._on_canvas_tool_changed)
        canvas.set_theme(**self.canvas_theme)
        canvas.set_symmetry_mode(self.mode_state.flag("symmetry"))
        canvas.set_grid_spacing(
            self.sketch_settings.get("grid_spacing_x", 10),
            self.sketch_settings.get("grid_spacing_y", 10),
        )

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(canvas)
        return canvas, page

    def _new_document(self):
        default_name = f"Drawing{self.document_counter}"
        dialog = NewDrawingDialog(default_name, self)
        if dialog.exec() != QDialog.Accepted:
            return

        template_name, file_name = dialog.values()
        document = self._add_document(file_name, template_name)
        self.document_counter += 1
        self.output.append(f"新建图纸: {document['name']} | {template_name}")

    def _open_file(self):
        filters = "AutoCAD DXF (*.dxf)"
        path, selected_filter = QFileDialog.getOpenFileName(self, "打开图纸", "", filters)
        if not path:
            return

        try:
            payload = self._load_document_from_path(path, selected_filter)
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            QMessageBox.critical(self, "打开失败", f"无法读取该文件:\n{path}\n\n{exc}")
            self.output.append(f"打开失败: {exc}")
            self.status_label.setText("打开失败")
            return

        name = payload.get("name") or os.path.splitext(os.path.basename(path))[0]
        template_name = payload.get("template", "二维草图")
        shapes = payload.get("shapes", [])
        document = self._add_document(name, template_name, path=path, shapes=shapes)
        self._fit_canvas_on_shapes(document["canvas"])
        self.output.append(f"已打开: {path}")
        self.status_label.setText(f"当前图纸: {document['name']}")

    def _load_document_from_path(self, path, selected_filter):
        selected = (selected_filter or "").lower()
        extension = os.path.splitext(path)[1].lower()
        if "dxf" in selected or extension == ".dxf":
            return self._load_dxf_document(path)
        raise ValueError("仅支持 DXF 文件")

    def _load_json_document(self, path):
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if "shapes" not in data:
            raise ValueError("JSON 文件缺少 shapes 数据")
        return data

    def _load_dxf_document(self, path):
        cleaned_lines, _, _ = self._read_dxf_lines(path)
        if len(cleaned_lines) < 2:
            raise ValueError("DXF 内容为空")

        pairs = []
        index = 0
        while index + 1 < len(cleaned_lines):
            code = cleaned_lines[index].strip()
            value = cleaned_lines[index + 1].strip()
            pairs.append((code, value))
            index += 2

        shapes = []
        arcs = []
        blocks = {}
        layer_styles = {}
        text_styles = {}
        section = None
        idx = 0
        total = len(pairs)
        while idx < total:
            code, value = pairs[idx]
            if code == "0" and value == "SECTION":
                idx += 1
                if idx < total and pairs[idx][0] == "2":
                    section = pairs[idx][1]
                    idx += 1
                continue
            if code == "0" and value == "ENDSEC":
                section = None
                idx += 1
                continue
            if section == "TABLES" and code == "0" and value.upper() == "TABLE":
                if idx + 1 < total and pairs[idx + 1][0] == "2":
                    table_name = pairs[idx + 1][1].upper()
                    if table_name == "LAYER":
                        idx = self._parse_dxf_layer_table(pairs, idx, layer_styles)
                        continue
                    if table_name == "STYLE":
                        idx = self._parse_dxf_style_table(pairs, idx, text_styles)
                        continue
            if section == "BLOCKS" and code == "0" and value.upper() == "BLOCK":
                idx = self._parse_dxf_block(pairs, idx, blocks, layer_styles, text_styles)
                continue
            if section == "ENTITIES" and code == "0":
                entity = value.upper()
                layer_name, style = self._extract_entity_style(pairs, idx, layer_styles)
                if entity == "INSERT":
                    idx = self._parse_dxf_insert(pairs, idx, shapes, blocks, style, layer_name)
                    continue
                if entity == "DIMENSION":
                    idx = self._parse_dxf_dimension(pairs, idx, shapes, blocks, style, layer_name)
                    continue
                if entity == "LINE":
                    idx = self._parse_dxf_line(pairs, idx, shapes, style, layer_name)
                    continue
                if entity == "CIRCLE":
                    idx = self._parse_dxf_circle(pairs, idx, shapes, style, layer_name)
                    continue
                if entity == "ARC":
                    idx = self._parse_dxf_arc(pairs, idx, arcs, style, layer_name)
                    continue
                if entity == "ELLIPSE":
                    idx = self._parse_dxf_ellipse(pairs, idx, shapes, style, layer_name)
                    continue
                if entity == "LWPOLYLINE":
                    idx = self._parse_dxf_polyline(pairs, idx, shapes, style, layer_name)
                    continue
                if entity == "POLYLINE":
                    idx = self._parse_dxf_polyline_legacy(pairs, idx, shapes, style, layer_name)
                    continue
                if entity == "SPLINE":
                    idx = self._parse_dxf_spline(pairs, idx, shapes, style, layer_name)
                    continue
                if entity == "TEXT":
                    idx = self._parse_dxf_text(pairs, idx, shapes, style, layer_name, text_styles)
                    continue
                if entity == "MTEXT":
                    idx = self._parse_dxf_mtext(pairs, idx, shapes, style, layer_name, text_styles)
                    continue
                if entity == "ATTRIB":
                    idx = self._parse_dxf_text(pairs, idx, shapes, style, layer_name, text_styles)
                    continue
                if entity == "ATTDEF":
                    idx = self._parse_dxf_text(pairs, idx, shapes, style, layer_name, text_styles)
                    continue
                if entity == "LEADER":
                    idx = self._parse_dxf_leader(pairs, idx, shapes, style, layer_name)
                    continue
                if entity == "SOLID":
                    idx = self._parse_dxf_solid(pairs, idx, shapes, style, layer_name)
                    continue
                if entity == "HATCH":
                    idx = self._parse_dxf_hatch(pairs, idx, shapes, style, layer_name)
                    continue
                if entity == "HATCH":
                    idx = self._parse_dxf_hatch(pairs, idx, shapes, style, layer_name)
                    continue
            idx += 1

        shapes.extend(self._convert_dxf_arcs(arcs))
        if not shapes:
            raise ValueError(
                "未在 DXF 中解析到已支持的图元 "
                "(LINE / CIRCLE / ARC / LWPOLYLINE / POLYLINE / INSERT / DIMENSION / TEXT / "
                "SPLINE / ELLIPSE / LEADER / SOLID / HATCH)"
            )
        return {
            "name": os.path.splitext(os.path.basename(path))[0],
            "template": "二维草图",
            "shapes": shapes,
        }

    def _detect_dxf_encoding(self, path):
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except OSError:
            return "utf-8"

        if data.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
        if data.startswith(b"\xff\xfe"):
            return "utf-16-le"
        if data.startswith(b"\xfe\xff"):
            return "utf-16-be"

        try:
            data.decode("utf-8")
            return "utf-8"
        except UnicodeDecodeError:
            pass

        sample = data[:65536]
        text = sample.decode("latin-1", errors="ignore")
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        codepage = None
        for idx, line in enumerate(lines):
            if line.strip().upper() == "$DWGCODEPAGE":
                if idx + 2 < len(lines):
                    codepage = lines[idx + 2].strip()
                elif idx + 1 < len(lines):
                    codepage = lines[idx + 1].strip()
                break
        return self._map_dxf_codepage(codepage)

    def _map_dxf_codepage(self, codepage):
        if not codepage:
            return "utf-8"
        normalized = codepage.strip().upper()
        mapping = {
            "ANSI_932": "shift_jis",
            "ANSI_936": "gbk",
            "ANSI_949": "cp949",
            "ANSI_950": "cp950",
            "ANSI_1250": "cp1250",
            "ANSI_1251": "cp1251",
            "ANSI_1252": "cp1252",
            "ANSI_1253": "cp1253",
            "ANSI_1254": "cp1254",
            "ANSI_1255": "cp1255",
            "ANSI_1256": "cp1256",
            "ANSI_1257": "cp1257",
            "ANSI_1258": "cp1258",
            "UTF-8": "utf-8",
            "UTF8": "utf-8",
        }
        if normalized in mapping:
            return mapping[normalized]
        if normalized.startswith("ANSI_"):
            suffix = normalized.split("_", 1)[1]
            if suffix.isdigit():
                return f"cp{suffix}"
        return "utf-8"

    def _read_dxf_lines(self, path):
        encoding = self._detect_dxf_encoding(path)
        with open(path, "r", encoding=encoding, errors="replace", newline="") as handle:
            raw_lines = handle.readlines()
        cleaned = [line.rstrip("\r\n") for line in raw_lines]
        return cleaned, raw_lines, encoding

    def _safe_int(self, value):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    def _aci_color_to_hex(self, index):
        mapping = {
            1: "#ff0000",
            2: "#ffff00",
            3: "#00ff00",
            4: "#00ffff",
            5: "#0000ff",
            6: "#ff00ff",
            7: "#ffffff",
            8: "#808080",
            9: "#c0c0c0",
        }
        return mapping.get(index)

    def _truecolor_to_hex(self, value):
        number = self._safe_int(value)
        if number is None:
            return None
        r = (number >> 16) & 0xFF
        g = (number >> 8) & 0xFF
        b = number & 0xFF
        return f"#{r:02x}{g:02x}{b:02x}"

    def _layer_style_from_entry(self, entry):
        if not entry:
            return None
        style = {}
        if entry.get("true_color") is not None:
            color = self._truecolor_to_hex(entry.get("true_color"))
            if color:
                style["color"] = color
        else:
            idx = entry.get("color_index")
            if idx is not None and idx not in (0, 256):
                color = self._aci_color_to_hex(abs(idx))
                if color:
                    style["color"] = color
        linetype = entry.get("linetype")
        if linetype:
            style["linetype"] = linetype
        lineweight = entry.get("lineweight")
        if lineweight is not None:
            lw = self._safe_int(lineweight)
            if lw is not None and lw > 0:
                style["lineweight"] = f"{lw / 100.0:.2f}"
        return style or None

    def _parse_dxf_layer_table(self, pairs, start_index, layer_styles):
        idx = start_index + 1
        total = len(pairs)
        current = None
        while idx < total:
            code, value = pairs[idx]
            if code == "0" and value.upper() == "ENDTAB":
                if current and current.get("name"):
                    layer_styles[current["name"]] = self._layer_style_from_entry(current) or {}
                idx += 1
                break
            if code == "0" and value.upper() == "LAYER":
                if current and current.get("name"):
                    layer_styles[current["name"]] = self._layer_style_from_entry(current) or {}
                current = {}
                idx += 1
                continue
            if current is not None:
                if code == "2":
                    current["name"] = value
                elif code == "62":
                    current["color_index"] = self._safe_int(value)
                elif code == "420":
                    current["true_color"] = self._safe_int(value)
                elif code == "6":
                    current["linetype"] = value
                elif code == "370":
                    current["lineweight"] = value
            idx += 1
        return idx

    def _parse_dxf_style_table(self, pairs, start_index, text_styles):
        idx = start_index + 1
        total = len(pairs)
        current = None
        while idx < total:
            code, value = pairs[idx]
            if code == "0" and value.upper() == "ENDTAB":
                if current and current.get("name"):
                    height = current.get("height")
                    if height is not None and height > 0:
                        text_styles[current["name"]] = height
                idx += 1
                break
            if code == "0" and value.upper() == "STYLE":
                if current and current.get("name"):
                    height = current.get("height")
                    if height is not None and height > 0:
                        text_styles[current["name"]] = height
                current = {}
                idx += 1
                continue
            if current is not None:
                if code == "2":
                    current["name"] = value
                elif code == "40":
                    current["height"] = self._parse_float(value)
            idx += 1
        return idx

    def _extract_entity_style(self, pairs, start_index, layer_styles):
        idx = start_index + 1
        total = len(pairs)
        layer_name = None
        color_index = None
        true_color = None
        linetype = None
        lineweight = None
        while idx < total:
            code, value = pairs[idx]
            if code == "0":
                break
            if code == "8":
                layer_name = value
            elif code == "62":
                color_index = self._safe_int(value)
            elif code == "420":
                true_color = self._safe_int(value)
            elif code == "6":
                linetype = value
            elif code == "370":
                lineweight = self._safe_int(value)
            idx += 1

        style = {}
        base = layer_styles.get(layer_name)
        if base:
            style.update(base)
        if true_color is not None:
            color = self._truecolor_to_hex(true_color)
            if color:
                style["color"] = color
        elif color_index is not None and color_index not in (0, 256):
            color = self._aci_color_to_hex(abs(color_index))
            if color:
                style["color"] = color
        if linetype:
            style["linetype"] = linetype
        if lineweight is not None and lineweight > 0:
            style["lineweight"] = f"{lineweight / 100.0:.2f}"
        return layer_name, style or None

    def _merge_styles(self, base, override):
        if not base and not override:
            return None
        merged = dict(base) if base else {}
        if override:
            for key, value in override.items():
                if value is not None:
                    merged[key] = value
        return merged or None

    def _extract_dxf_dimension_params(self, path):
        cleaned, raw_lines, encoding = self._read_dxf_lines(path)
        if len(cleaned) < 2:
            raise ValueError("DXF 内容为空")

        entries = []
        section = None
        idx = 0
        total = len(cleaned)
        while idx + 1 < total:
            code = cleaned[idx].strip()
            value = cleaned[idx + 1].strip()
            if code == "0" and value == "SECTION":
                if idx + 3 < total and cleaned[idx + 2].strip() == "2":
                    section = cleaned[idx + 3].strip()
                idx += 2
                continue
            if code == "0" and value == "ENDSEC":
                section = None
                idx += 2
                continue
            if section == "ENTITIES" and code == "0" and value.upper() == "DIMENSION":
                text_value = None
                text_index = None
                meas_value = None
                meas_index = None
                j = idx + 2
                while j + 1 < total:
                    c = cleaned[j].strip()
                    v = cleaned[j + 1].strip()
                    if c == "0":
                        break
                    if c == "1" and text_value is None:
                        text_value = v
                        text_index = j + 1
                    elif c == "42" and meas_value is None:
                        meas_value = v
                        meas_index = j + 1
                    j += 2
                text_value = text_value or ""
                use_measure = (not text_value) or ("<>" in text_value)
                current = meas_value if use_measure else text_value
                text_display = text_value if text_value else "<>"
                entries.append(
                    {
                        "text": text_value,
                        "text_display": text_display,
                        "text_index": text_index,
                        "measurement": meas_value,
                        "measurement_index": meas_index,
                        "use_measure": use_measure,
                        "current": current or "",
                    }
                )
                idx = j
                continue
            idx += 2
        return raw_lines, entries, encoding

    def _replace_dxf_value_line(self, raw_lines, index, value):
        if index is None or index < 0 or index >= len(raw_lines):
            return
        line = raw_lines[index]
        if line.endswith("\r\n"):
            newline = "\r\n"
        elif line.endswith("\n"):
            newline = "\n"
        else:
            newline = ""
        raw_lines[index] = f"{value}{newline}"

    def _apply_dimension_updates(self, raw_lines, entries, new_values):
        for idx, (entry, new_value) in enumerate(zip(entries, new_values), start=1):
            value = (new_value or "").strip()
            if not value:
                continue
            if entry["use_measure"]:
                number = self._parse_float(value)
                if number is None:
                    raise ValueError(f"第 {idx} 行参数需要输入数字。")
                if entry["measurement_index"] is None:
                    raise ValueError(f"第 {idx} 行缺少测量值，无法写入。")
                self._replace_dxf_value_line(raw_lines, entry["measurement_index"], value)
                if entry["text_index"] is not None and "<>" in (entry.get("text") or ""):
                    replaced = entry["text"].replace("<>", value)
                    self._replace_dxf_value_line(raw_lines, entry["text_index"], replaced)
            else:
                if entry["text_index"] is not None:
                    self._replace_dxf_value_line(raw_lines, entry["text_index"], value)
                elif entry["measurement_index"] is not None:
                    number = self._parse_float(value)
                    if number is None:
                        raise ValueError(f"第 {idx} 行参数需要输入数字。")
                    self._replace_dxf_value_line(raw_lines, entry["measurement_index"], value)
                number = self._parse_float(value)
                if number is not None and entry["measurement_index"] is not None:
                    self._replace_dxf_value_line(raw_lines, entry["measurement_index"], value)

    def _parse_dxf_line(self, pairs, start_index, shapes, style=None, layer=None):
        idx = start_index + 1
        x1 = y1 = x2 = y2 = None
        total = len(pairs)
        while idx < total:
            code, value = pairs[idx]
            if code == "0":
                break
            number = self._parse_float(value)
            if number is None:
                idx += 1
                continue
            if code == "10":
                x1 = number
            elif code == "20":
                y1 = -number
            elif code == "11":
                x2 = number
            elif code == "21":
                y2 = -number
            idx += 1
        if None not in (x1, y1, x2, y2):
            shape = {"type": "line", "params": (x1, y1, x2, y2)}
            if layer:
                shape["layer"] = layer
            if style:
                shape["style"] = dict(style)
            shapes.append(shape)
        return idx

    def _parse_dxf_circle(self, pairs, start_index, shapes, style=None, layer=None):
        idx = start_index + 1
        cx = cy = radius = None
        total = len(pairs)
        while idx < total:
            code, value = pairs[idx]
            if code == "0":
                break
            number = self._parse_float(value)
            if number is None:
                idx += 1
                continue
            if code == "10":
                cx = number
            elif code == "20":
                cy = -number
            elif code == "40":
                radius = abs(number)
            idx += 1
        if None not in (cx, cy, radius):
            shape = {"type": "circle", "params": (cx, cy, radius)}
            if layer:
                shape["layer"] = layer
            if style:
                shape["style"] = dict(style)
            shapes.append(shape)
        return idx

    def _parse_dxf_arc(self, pairs, start_index, arcs, style=None, layer=None):
        idx = start_index + 1
        cx = cy = radius = start_angle = end_angle = None
        total = len(pairs)
        while idx < total:
            code, value = pairs[idx]
            if code == "0":
                break
            number = self._parse_float(value)
            if number is None:
                idx += 1
                continue
            if code == "10":
                cx = number
            elif code == "20":
                cy = -number
            elif code == "40":
                radius = abs(number)
            elif code == "50":
                start_angle = number
            elif code == "51":
                end_angle = number
            idx += 1
        if None not in (cx, cy, radius, start_angle, end_angle):
            arc = {
                "cx": cx,
                "cy": cy,
                "radius": radius,
                "start": start_angle,
                "end": end_angle,
            }
            if layer:
                arc["layer"] = layer
            if style:
                arc["style"] = dict(style)
            arcs.append(arc)
        return idx

    def _bulge_arc_points(self, p1, p2, bulge):
        if abs(bulge) < 1e-6:
            return [p1, p2]
        x1, y1 = p1
        x2, y2 = p2
        dx = x2 - x1
        dy = y2 - y1
        chord = math.hypot(dx, dy)
        if chord < 1e-6:
            return [p1, p2]
        theta = 4 * math.atan(bulge)
        radius = chord / (2 * math.sin(theta / 2.0))
        mx = (x1 + x2) / 2.0
        my = (y1 + y2) / 2.0
        ux = -dy / chord
        uy = dx / chord
        h = radius * math.cos(theta / 2.0)
        if bulge < 0:
            h = -h
        cx = mx + ux * h
        cy = my + uy * h
        start_angle = math.atan2(y1 - cy, x1 - cx)
        end_angle = math.atan2(y2 - cy, x2 - cx)
        if bulge > 0 and end_angle <= start_angle:
            end_angle += math.tau
        if bulge < 0 and end_angle >= start_angle:
            end_angle -= math.tau
        span = end_angle - start_angle
        steps = max(6, int(abs(span) / (math.pi / 12.0)))
        points = []
        for i in range(steps + 1):
            angle = start_angle + span * (i / steps)
            points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
        return points

    def _bulge_vertices_to_points(self, vertices, closed):
        if not vertices:
            return []
        if closed and len(vertices) > 1:
            vertices = list(vertices) + [vertices[0]]
        output = []
        for index in range(len(vertices) - 1):
            p1 = vertices[index]
            p2 = vertices[index + 1]
            if not output:
                output.append((p1["x"], p1["y"]))
            bulge = p1.get("bulge", 0.0) or 0.0
            if abs(bulge) < 1e-6:
                output.append((p2["x"], p2["y"]))
            else:
                arc_pts = self._bulge_arc_points((p1["x"], p1["y"]), (p2["x"], p2["y"]), bulge)
                output.extend(arc_pts[1:])
        return output

    def _parse_dxf_polyline(self, pairs, start_index, shapes, style=None, layer=None):
        idx = start_index + 1
        total = len(pairs)
        vertices = []
        pending_x = None
        pending_bulge = 0.0
        last_index = None
        closed = False
        while idx < total:
            code, value = pairs[idx]
            if code == "0":
                break
            if code == "10":
                pending_x = self._parse_float(value)
            elif code == "20":
                if pending_x is not None:
                    y_val = self._parse_float(value)
                    if y_val is not None:
                        vertices.append({"x": pending_x, "y": -y_val, "bulge": pending_bulge})
                        last_index = len(vertices) - 1
                pending_x = None
                pending_bulge = 0.0
            elif code == "42":
                bulge_val = -(self._parse_float(value) or 0.0)
                if last_index is not None and pending_x is None:
                    vertices[last_index]["bulge"] = bulge_val
                else:
                    pending_bulge = bulge_val
            elif code == "70":
                try:
                    closed = (int(float(value)) & 1) == 1
                except ValueError:
                    closed = False
            idx += 1
        points = self._bulge_vertices_to_points(vertices, closed)
        if len(points) >= 2:
            shape = {"type": "polyline", "params": (tuple(points), False)}
            if layer:
                shape["layer"] = layer
            if style:
                shape["style"] = dict(style)
            shapes.append(shape)
        return idx

    def _parse_dxf_polyline_legacy(self, pairs, start_index, shapes, style=None, layer=None):
        idx = start_index + 1
        total = len(pairs)
        closed = False
        while idx < total:
            code, value = pairs[idx]
            if code == "0":
                break
            if code == "70":
                try:
                    closed = (int(float(value)) & 1) == 1
                except ValueError:
                    closed = False
            idx += 1

        vertices = []
        while idx < total:
            code, value = pairs[idx]
            if code == "0" and value.upper() == "VERTEX":
                idx += 1
                vx = vy = None
                bulge = 0.0
                while idx < total:
                    c, v = pairs[idx]
                    if c == "0":
                        break
                    if c == "10":
                        vx = self._parse_float(v)
                    elif c == "20":
                        vy = self._parse_float(v)
                    elif c == "42":
                        bulge = -(self._parse_float(v) or 0.0)
                    idx += 1
                if vx is not None and vy is not None:
                    vertices.append({"x": vx, "y": -vy, "bulge": bulge})
                continue
            if code == "0" and value.upper() == "SEQEND":
                idx += 1
                break
            if code == "0":
                break
            idx += 1

        points = self._bulge_vertices_to_points(vertices, closed)
        if len(points) >= 2:
            shape = {"type": "polyline", "params": (tuple(points), False)}
            if layer:
                shape["layer"] = layer
            if style:
                shape["style"] = dict(style)
            shapes.append(shape)
        return idx

    def _parse_dxf_spline(self, pairs, start_index, shapes, style=None, layer=None):
        idx = start_index + 1
        total = len(pairs)
        ctrl_points = []
        fit_points = []
        pending_ctrl_x = None
        pending_fit_x = None
        while idx < total:
            code, value = pairs[idx]
            if code == "0":
                break
            if code == "10":
                pending_ctrl_x = self._parse_float(value)
            elif code == "20":
                if pending_ctrl_x is not None:
                    y_val = self._parse_float(value)
                    if y_val is not None:
                        ctrl_points.append((pending_ctrl_x, -y_val))
                pending_ctrl_x = None
            elif code == "11":
                pending_fit_x = self._parse_float(value)
            elif code == "21":
                if pending_fit_x is not None:
                    y_val = self._parse_float(value)
                    if y_val is not None:
                        fit_points.append((pending_fit_x, -y_val))
                pending_fit_x = None
            idx += 1

        points = fit_points if len(fit_points) >= 2 else ctrl_points
        if len(points) >= 2:
            shape = {"type": "polyline", "params": (tuple(points), False)}
            if layer:
                shape["layer"] = layer
            if style:
                shape["style"] = dict(style)
            shapes.append(shape)
        return idx

    def _parse_dxf_ellipse(self, pairs, start_index, shapes, style=None, layer=None):
        idx = start_index + 1
        total = len(pairs)
        cx = cy = None
        major_dx = major_dy = None
        ratio = None
        start_param = 0.0
        end_param = 0.0
        while idx < total:
            code, value = pairs[idx]
            if code == "0":
                break
            if code == "10":
                cx = self._parse_float(value)
            elif code == "20":
                cy = self._parse_float(value)
            elif code == "11":
                major_dx = self._parse_float(value)
            elif code == "21":
                major_dy = self._parse_float(value)
            elif code == "40":
                ratio = self._parse_float(value)
            elif code == "41":
                start_param = self._parse_float(value) or 0.0
            elif code == "42":
                end_param = self._parse_float(value) or 0.0
            idx += 1

        if None in (cx, cy, major_dx, major_dy, ratio):
            return idx

        cy = -cy
        major_vec = (major_dx, -major_dy)
        minor_vec = (-major_vec[1] * ratio, major_vec[0] * ratio)
        span = end_param - start_param
        if span <= 0:
            span += math.tau
        steps = max(12, int(abs(span) / (math.tau / 48)))
        points = []
        for i in range(steps + 1):
            t = start_param + span * (i / steps)
            x = cx + major_vec[0] * math.cos(t) + minor_vec[0] * math.sin(t)
            y = cy + major_vec[1] * math.cos(t) + minor_vec[1] * math.sin(t)
            points.append((x, y))
        if len(points) >= 2:
            shape = {"type": "polyline", "params": (tuple(points), False)}
            if layer:
                shape["layer"] = layer
            if style:
                shape["style"] = dict(style)
            shapes.append(shape)
        return idx

    def _parse_dxf_text(self, pairs, start_index, shapes, style=None, layer=None, text_styles=None):
        idx = start_index + 1
        total = len(pairs)
        x = y = None
        height = None
        rotation = 0.0
        text_value = ""
        style_name = None
        while idx < total:
            code, value = pairs[idx]
            if code == "0":
                break
            if code == "10":
                x = self._parse_float(value)
            elif code == "20":
                y = self._parse_float(value)
            elif code == "1":
                text_value = value
            elif code == "40":
                height = self._parse_float(value)
            elif code == "50":
                rotation = self._parse_float(value) or 0.0
            elif code == "7":
                style_name = value
            idx += 1

        if x is None or y is None or text_value is None:
            return idx
        text_value = self._decode_dxf_text(text_value)
        if (height is None or height <= 0) and text_styles and style_name:
            height = text_styles.get(style_name, height)
        shape = {
            "type": "text",
            "params": (x, -y, text_value, height, -rotation),
        }
        if layer:
            shape["layer"] = layer
        if style:
            shape["style"] = dict(style)
        shapes.append(shape)
        return idx

    def _decode_dxf_text(self, text):
        if text is None:
            return ""
        value = str(text)

        def _pct_repl(match):
            mapping = {"c": "Ø", "d": "°", "p": "±"}
            return mapping.get(match.group(1).lower(), match.group(0))

        value = re.sub(r"%%([cCdDpP])", _pct_repl, value)

        def _uni_repl(match):
            try:
                return chr(int(match.group(1), 16))
            except ValueError:
                return match.group(0)

        value = re.sub(r"\\U\+([0-9A-Fa-f]{4,8})", _uni_repl, value)
        return value

    def _clean_mtext(self, text):
        if not text:
            return ""
        cleaned = text.replace("\\P", "\n").replace("\\~", " ")
        cleaned = re.sub(r"\\S([^;]+);", lambda m: m.group(1).replace("#", "/"), cleaned)
        cleaned = re.sub(r"\\[ACQFLHWT][^;]*;", "", cleaned)
        cleaned = re.sub(r"\\A\d+", "", cleaned)
        cleaned = re.sub(r"\\[OoLlKk]", "", cleaned)
        if "{" in cleaned and "}" in cleaned:
            cleaned = cleaned.replace("{", "").replace("}", "")
        return self._decode_dxf_text(cleaned)

    def _parse_dxf_mtext(self, pairs, start_index, shapes, style=None, layer=None, text_styles=None):
        idx = start_index + 1
        total = len(pairs)
        x = y = None
        height = None
        rotation = 0.0
        parts = []
        style_name = None
        while idx < total:
            code, value = pairs[idx]
            if code == "0":
                break
            if code == "10":
                x = self._parse_float(value)
            elif code == "20":
                y = self._parse_float(value)
            elif code in ("1", "3"):
                parts.append(value)
            elif code == "40":
                height = self._parse_float(value)
            elif code == "50":
                rotation = self._parse_float(value) or 0.0
            elif code == "7":
                style_name = value
            idx += 1

        if x is None or y is None or not parts:
            return idx
        text_value = self._clean_mtext("".join(parts))
        if (height is None or height <= 0) and text_styles and style_name:
            height = text_styles.get(style_name, height)
        shape = {
            "type": "text",
            "params": (x, -y, text_value, height, -rotation),
        }
        if layer:
            shape["layer"] = layer
        if style:
            shape["style"] = dict(style)
        shapes.append(shape)
        return idx

    def _parse_dxf_leader(self, pairs, start_index, shapes, style=None, layer=None):
        idx = start_index + 1
        total = len(pairs)
        points = []
        pending_x = None
        while idx < total:
            code, value = pairs[idx]
            if code == "0":
                break
            if code == "10":
                pending_x = self._parse_float(value)
            elif code == "20":
                if pending_x is not None:
                    y_val = self._parse_float(value)
                    if y_val is not None:
                        points.append((pending_x, -y_val))
                pending_x = None
            idx += 1
        if len(points) >= 2:
            shape = {"type": "polyline", "params": (tuple(points), False)}
            if layer:
                shape["layer"] = layer
            if style:
                shape["style"] = dict(style)
            shapes.append(shape)
        return idx

    def _parse_dxf_solid(self, pairs, start_index, shapes, style=None, layer=None):
        idx = start_index + 1
        total = len(pairs)
        coords = {"10": None, "20": None, "11": None, "21": None, "12": None, "22": None, "13": None, "23": None}
        while idx < total:
            code, value = pairs[idx]
            if code == "0":
                break
            if code in coords:
                coords[code] = self._parse_float(value)
            idx += 1
        points = []
        for x_code, y_code in (("10", "20"), ("11", "21"), ("12", "22"), ("13", "23")):
            x_val = coords.get(x_code)
            y_val = coords.get(y_code)
            if x_val is not None and y_val is not None:
                points.append((x_val, -y_val))
        if len(points) >= 3:
            shape = {"type": "polyline", "params": (tuple(points), True)}
            if layer:
                shape["layer"] = layer
            if style:
                shape["style"] = dict(style)
            shapes.append(shape)
        return idx

    def _parse_dxf_hatch(self, pairs, start_index, shapes, style=None, layer=None):
        idx = start_index + 1
        total = len(pairs)
        loops = []

        def _segment_tol(points):
            min_seg = None
            for idx in range(len(points) - 1):
                dx = points[idx + 1][0] - points[idx][0]
                dy = points[idx + 1][1] - points[idx][1]
                seg = math.hypot(dx, dy)
                if seg > 1e-6:
                    min_seg = seg if min_seg is None else min(min_seg, seg)
            if min_seg is None:
                return 0.2
            return min(5.0, max(0.2, min_seg * 0.1))

        def _append_loop(points):
            if not points or len(points) < 3:
                return
            loop = list(points)
            xs = [pt[0] for pt in loop]
            ys = [pt[1] for pt in loop]
            diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
            tol = _segment_tol(loop)
            if diag > 1e-6:
                tol = min(tol, diag * 0.02)
            if loop[0] != loop[-1]:
                gap = math.hypot(loop[0][0] - loop[-1][0], loop[0][1] - loop[-1][1])
                if gap > tol:
                    return
                loop.append(loop[0])
            if len(loop) >= 4:
                loops.append(tuple(loop))

        def _ordered_chain(edge_points):
            if not edge_points:
                return []
            tol = max(_segment_tol(points) for points in edge_points if points) if edge_points else 0.2
            loops_out = []
            current = []
            for edge in edge_points:
                if not edge or len(edge) < 2:
                    continue
                edge_pts = list(edge)
                if not current:
                    current = edge_pts
                    continue
                last = current[-1]
                d_start = math.hypot(last[0] - edge_pts[0][0], last[1] - edge_pts[0][1])
                d_end = math.hypot(last[0] - edge_pts[-1][0], last[1] - edge_pts[-1][1])
                if d_start <= tol or d_end <= tol:
                    if d_end < d_start:
                        edge_pts.reverse()
                        d_start = d_end
                    if d_start <= tol:
                        current.extend(edge_pts[1:])
                    else:
                        current.extend(edge_pts)
                else:
                    if current and math.hypot(current[0][0] - current[-1][0], current[0][1] - current[-1][1]) <= tol:
                        if current[0] != current[-1]:
                            current.append(current[0])
                        loops_out.append(current)
                    current = edge_pts
            if current and math.hypot(current[0][0] - current[-1][0], current[0][1] - current[-1][1]) <= tol:
                if current[0] != current[-1]:
                    current.append(current[0])
                loops_out.append(current)
            return loops_out

        def _arc_edge_points(cx, cy, radius, start, end, ccw_flag):
            if radius <= 0:
                return []
            start_angle = math.radians(start)
            end_angle = math.radians(end)
            if bool(ccw_flag):
                span = (end_angle - start_angle) % (math.tau)
            else:
                span = -((start_angle - end_angle) % (math.tau))
            if abs(span) < 1e-9:
                span = math.tau
            steps = max(8, int(abs(span) / (math.pi / 18.0)))
            pts = []
            for i in range(steps + 1):
                angle = start_angle + span * (i / steps)
                pts.append((cx + math.cos(angle) * radius, -(cy + math.sin(angle) * radius)))
            return pts

        def _ellipse_edge_points(cx, cy, major_dx, major_dy, ratio, start_param, end_param, ccw_flag):
            if ratio is None:
                return []
            cy_screen = -cy
            major_vec = (major_dx, -major_dy)
            minor_vec = (-major_vec[1] * ratio, major_vec[0] * ratio)
            start = start_param
            end = end_param
            if bool(ccw_flag):
                span = (end - start) % (math.tau)
            else:
                span = -((start - end) % (math.tau))
            if abs(span) < 1e-9:
                span = math.tau
            steps = max(12, int(abs(span) / (math.pi / 18.0)))
            pts = []
            for i in range(steps + 1):
                t = start + span * (i / steps)
                x = cx + major_vec[0] * math.cos(t) + minor_vec[0] * math.sin(t)
                y = cy_screen + major_vec[1] * math.cos(t) + minor_vec[1] * math.sin(t)
                pts.append((x, y))
            return pts

        def _spline_edge_points(ctrl_points, fit_points):
            points = fit_points if len(fit_points) >= 2 else ctrl_points
            return list(points)

        while idx < total:
            code, value = pairs[idx]
            if code == "0":
                break
            if code == "92":
                try:
                    path_type = int(float(value))
                except ValueError:
                    path_type = 0
                if path_type & 2:
                    has_bulge = False
                    closed = False
                    num_vertices = 0
                    idx += 1
                    while idx < total:
                        code2, value2 = pairs[idx]
                        if code2 == "0" or code2 == "92":
                            idx -= 1
                            break
                        if code2 == "72":
                            has_bulge = value2.strip() == "1"
                        elif code2 == "73":
                            closed = value2.strip() == "1"
                        elif code2 == "93":
                            try:
                                num_vertices = int(float(value2))
                            except ValueError:
                                num_vertices = 0
                            idx += 1
                            break
                        idx += 1
                    vertices = []
                    count = 0
                    pending_x = None
                    pending_bulge = 0.0
                    while idx < total and count < num_vertices:
                        code3, value3 = pairs[idx]
                        if code3 == "0":
                            idx -= 1
                            break
                        if code3 == "10":
                            pending_x = self._parse_float(value3)
                        elif code3 == "20":
                            if pending_x is not None:
                                y_val = self._parse_float(value3)
                                if y_val is not None:
                                    vertices.append({"x": pending_x, "y": -y_val, "bulge": pending_bulge})
                                    count += 1
                            pending_x = None
                            pending_bulge = 0.0
                        elif code3 == "42" and has_bulge:
                            pending_bulge = -(self._parse_float(value3) or 0.0)
                        idx += 1
                    points = self._bulge_vertices_to_points(vertices, closed)
                    _append_loop(points)
                else:
                    num_edges = 0
                    idx += 1
                    while idx < total:
                        code2, value2 = pairs[idx]
                        if code2 == "0" or code2 == "92":
                            idx -= 1
                            break
                        if code2 == "93":
                            try:
                                num_edges = int(float(value2))
                            except ValueError:
                                num_edges = 0
                            idx += 1
                            break
                        idx += 1

                    edge_points = []
                    for _ in range(num_edges):
                        while idx < total and pairs[idx][0] not in ("72", "0", "92"):
                            idx += 1
                        if idx >= total or pairs[idx][0] in ("0", "92"):
                            break
                        if pairs[idx][0] != "72":
                            break
                        try:
                            edge_type = int(float(pairs[idx][1]))
                        except ValueError:
                            edge_type = 0
                        idx += 1

                        if edge_type == 1:
                            x1 = y1 = x2 = y2 = None
                            while idx < total:
                                code3, value3 = pairs[idx]
                                if code3 in ("72", "0", "92"):
                                    break
                                if code3 == "10":
                                    x1 = self._parse_float(value3)
                                elif code3 == "20":
                                    y1 = self._parse_float(value3)
                                elif code3 == "11":
                                    x2 = self._parse_float(value3)
                                elif code3 == "21":
                                    y2 = self._parse_float(value3)
                                idx += 1
                            if None not in (x1, y1, x2, y2):
                                edge_pts = [(x1, -y1), (x2, -y2)]
                                edge_points.append(edge_pts)
                        elif edge_type == 2:
                            cx = cy = radius = start = end = None
                            ccw_flag = 1
                            while idx < total:
                                code3, value3 = pairs[idx]
                                if code3 in ("72", "0", "92"):
                                    break
                                if code3 == "10":
                                    cx = self._parse_float(value3)
                                elif code3 == "20":
                                    cy = self._parse_float(value3)
                                elif code3 == "40":
                                    radius = abs(self._parse_float(value3) or 0.0)
                                elif code3 == "50":
                                    start = self._parse_float(value3)
                                elif code3 == "51":
                                    end = self._parse_float(value3)
                                elif code3 == "73":
                                    try:
                                        ccw_flag = int(float(value3))
                                    except ValueError:
                                        ccw_flag = 1
                                idx += 1
                            if None not in (cx, cy, radius, start, end):
                                edge_pts = _arc_edge_points(cx, cy, radius, start, end, ccw_flag)
                                if edge_pts:
                                    edge_points.append(edge_pts)
                        elif edge_type == 3:
                            cx = cy = major_dx = major_dy = ratio = None
                            ccw_flag = 1
                            start_param = 0.0
                            end_param = 0.0
                            while idx < total:
                                code3, value3 = pairs[idx]
                                if code3 in ("72", "0", "92"):
                                    break
                                if code3 == "10":
                                    cx = self._parse_float(value3)
                                elif code3 == "20":
                                    cy = self._parse_float(value3)
                                elif code3 == "11":
                                    major_dx = self._parse_float(value3)
                                elif code3 == "21":
                                    major_dy = self._parse_float(value3)
                                elif code3 == "40":
                                    ratio = self._parse_float(value3)
                                elif code3 == "50":
                                    start_param = self._parse_float(value3) or 0.0
                                elif code3 == "51":
                                    end_param = self._parse_float(value3) or 0.0
                                elif code3 == "73":
                                    try:
                                        ccw_flag = int(float(value3))
                                    except ValueError:
                                        ccw_flag = 1
                                idx += 1
                            if None not in (cx, cy, major_dx, major_dy, ratio):
                                edge_pts = _ellipse_edge_points(cx, cy, major_dx, major_dy, ratio, start_param, end_param, ccw_flag)
                                if edge_pts:
                                    edge_points.append(edge_pts)
                        elif edge_type == 4:
                            ctrl_points = []
                            fit_points = []
                            pending_ctrl_x = None
                            pending_fit_x = None
                            while idx < total:
                                code3, value3 = pairs[idx]
                                if code3 in ("72", "0", "92"):
                                    break
                                if code3 == "10":
                                    pending_ctrl_x = self._parse_float(value3)
                                elif code3 == "20":
                                    if pending_ctrl_x is not None:
                                        y_val = self._parse_float(value3)
                                        if y_val is not None:
                                            ctrl_points.append((pending_ctrl_x, -y_val))
                                    pending_ctrl_x = None
                                elif code3 == "11":
                                    pending_fit_x = self._parse_float(value3)
                                elif code3 == "21":
                                    if pending_fit_x is not None:
                                        y_val = self._parse_float(value3)
                                        if y_val is not None:
                                            fit_points.append((pending_fit_x, -y_val))
                                    pending_fit_x = None
                                idx += 1
                            edge_pts = _spline_edge_points(ctrl_points, fit_points)
                            if edge_pts:
                                edge_points.append(edge_pts)
                        else:
                            while idx < total:
                                code3, _ = pairs[idx]
                                if code3 in ("72", "0", "92"):
                                    break
                                idx += 1

                    for loop in _ordered_chain(edge_points):
                        _append_loop(loop)
                    if idx < total and pairs[idx][0] in ("92", "0"):
                        idx -= 1
            idx += 1
        if loops:
            shape = {"type": "hatch", "params": tuple(loops)}
            if layer:
                shape["layer"] = layer
            if style:
                shape["style"] = dict(style)
            shapes.append(shape)
        return idx

    def _block_bounds(self, block):
        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")
        has_any = False
        for shape in block.get("shapes", []):
            shape_type = shape.get("type")
            params = shape.get("params", ())
            if shape_type in ("line", "centerline"):
                x1, y1, x2, y2 = params
                points = [(x1, y1), (x2, y2)]
            elif shape_type == "circle":
                cx, cy, radius = params
                points = [(cx - radius, cy - radius), (cx + radius, cy + radius)]
            elif shape_type in ("arc_angle", "doubleline_arc", "center_arc"):
                cx, cy, radius, _, _ = params
                points = [(cx - radius, cy - radius), (cx + radius, cy + radius)]
            elif shape_type == "polyline":
                pts, _ = params
                points = list(pts)
            elif shape_type == "hatch":
                loops = params or []
                points = [pt for loop in loops for pt in loop]
            elif shape_type == "text":
                x, y, *_ = params
                points = [(x, y)]
            elif shape_type in ("rect", "ellipse", "arc"):
                x1, y1, x2, y2 = params
                points = [(x1, y1), (x2, y2)]
            elif shape_type == "doubleline":
                x1, y1, x2, y2, width = params
                pad = width / 2.0
                points = [(x1 - pad, y1 - pad), (x2 + pad, y2 + pad)]
            else:
                continue
            for px, py in points:
                min_x = min(min_x, px)
                min_y = min(min_y, py)
                max_x = max(max_x, px)
                max_y = max(max_y, py)
                has_any = True
        if not has_any:
            return None
        return min_x, min_y, max_x, max_y

    def _parse_dxf_dimension(self, pairs, start_index, shapes, blocks, style=None, layer=None):
        idx = start_index + 1
        total = len(pairs)
        block_name = None
        def_x = def_y = None
        text_x = text_y = None
        rotation = 0.0
        text_override = None
        measurement = None
        while idx < total:
            code, value = pairs[idx]
            if code == "0":
                break
            if code == "2":
                block_name = value.strip()
            elif code == "10":
                def_x = self._parse_float(value)
            elif code == "20":
                def_y = self._parse_float(value)
            elif code == "11":
                text_x = self._parse_float(value)
            elif code == "21":
                text_y = self._parse_float(value)
            elif code == "1":
                text_override = value
            elif code == "42":
                measurement = value
            elif code == "50":
                rotation = self._parse_float(value) or 0.0
            idx += 1

        insert_point = None
        if def_x is not None and def_y is not None:
            insert_point = (def_x, -def_y)
        if insert_point is None and text_x is not None and text_y is not None:
            insert_point = (text_x, -text_y)

        block_has_text = False
        if block_name and block_name in blocks:
            block = blocks[block_name]
            block_has_text = any(shape.get("type") == "text" for shape in block.get("shapes", []))
            use_absolute = block_name.upper().startswith("*D")
            if insert_point is None or use_absolute:
                self._append_block_shapes(
                    shapes,
                    block,
                    (0.0, 0.0),
                    1.0,
                    1.0,
                    0.0,
                    override_style=style,
                    override_layer=layer,
                    absolute=True,
                )
            else:
                self._append_block_shapes(
                    shapes,
                    block,
                    insert_point,
                    1.0,
                    1.0,
                    rotation,
                    override_style=style,
                    override_layer=layer,
                )

        display_text = text_override or ""
        if (not display_text) or ("<>" in display_text):
            if measurement:
                display_text = display_text.replace("<>", measurement) if display_text else measurement
        display_text = self._decode_dxf_text(display_text)
        if display_text and text_x is not None and text_y is not None and not block_has_text:
            shape = {
                "type": "text",
                "params": (text_x, -text_y, display_text, None, -rotation),
            }
            if layer:
                shape["layer"] = layer
            if style:
                shape["style"] = dict(style)
            shapes.append(shape)
        return idx

    def _parse_dxf_block(self, pairs, start_index, blocks, layer_styles, text_styles):
        idx = start_index + 1
        total = len(pairs)
        name = None
        base_x = 0.0
        base_y = 0.0
        while idx < total:
            code, value = pairs[idx]
            if code == "0":
                break
            if code == "2":
                name = value.strip()
            elif code == "10":
                base_x = self._parse_float(value) or base_x
            elif code == "20":
                base_y = self._parse_float(value) or base_y
            idx += 1

        shapes = []
        arcs = []
        while idx < total:
            code, value = pairs[idx]
            if code == "0" and value.upper() == "ENDBLK":
                idx += 1
                break
            if code == "0":
                entity = value.upper()
                layer_name, style = self._extract_entity_style(pairs, idx, layer_styles)
                if entity == "LINE":
                    idx = self._parse_dxf_line(pairs, idx, shapes, style, layer_name)
                    continue
                if entity == "CIRCLE":
                    idx = self._parse_dxf_circle(pairs, idx, shapes, style, layer_name)
                    continue
                if entity == "ARC":
                    idx = self._parse_dxf_arc(pairs, idx, arcs, style, layer_name)
                    continue
                if entity == "ELLIPSE":
                    idx = self._parse_dxf_ellipse(pairs, idx, shapes, style, layer_name)
                    continue
                if entity == "LWPOLYLINE":
                    idx = self._parse_dxf_polyline(pairs, idx, shapes, style, layer_name)
                    continue
                if entity == "POLYLINE":
                    idx = self._parse_dxf_polyline_legacy(pairs, idx, shapes, style, layer_name)
                    continue
                if entity == "SPLINE":
                    idx = self._parse_dxf_spline(pairs, idx, shapes, style, layer_name)
                    continue
                if entity == "TEXT":
                    idx = self._parse_dxf_text(pairs, idx, shapes, style, layer_name, text_styles)
                    continue
                if entity == "MTEXT":
                    idx = self._parse_dxf_mtext(pairs, idx, shapes, style, layer_name, text_styles)
                    continue
                if entity == "ATTRIB":
                    idx = self._parse_dxf_text(pairs, idx, shapes, style, layer_name, text_styles)
                    continue
                if entity == "ATTDEF":
                    idx = self._parse_dxf_text(pairs, idx, shapes, style, layer_name, text_styles)
                    continue
                if entity == "INSERT":
                    idx = self._parse_dxf_insert(pairs, idx, shapes, blocks, style, layer_name)
                    continue
                if entity == "LEADER":
                    idx = self._parse_dxf_leader(pairs, idx, shapes, style, layer_name)
                    continue
                if entity == "SOLID":
                    idx = self._parse_dxf_solid(pairs, idx, shapes, style, layer_name)
                    continue
                if entity == "HATCH":
                    idx = self._parse_dxf_hatch(pairs, idx, shapes, style, layer_name)
                    continue
            idx += 1

        shapes.extend(self._convert_dxf_arcs(arcs))
        if name:
            blocks[name] = {"base": (base_x, -base_y), "shapes": shapes}
        return idx

    def _parse_dxf_insert(self, pairs, start_index, shapes, blocks, style=None, layer=None):
        idx = start_index + 1
        total = len(pairs)
        name = None
        ins_x = 0.0
        ins_y = 0.0
        scale_x = 1.0
        scale_y = 1.0
        scale_x_set = False
        scale_y_set = False
        rotation = 0.0
        while idx < total:
            code, value = pairs[idx]
            if code == "0":
                break
            if code == "2":
                name = value.strip()
            elif code == "10":
                ins_x = self._parse_float(value) or ins_x
            elif code == "20":
                ins_y = self._parse_float(value) or ins_y
            elif code == "41":
                scale_x = self._parse_float(value) or scale_x
                scale_x_set = True
            elif code == "42":
                scale_y = self._parse_float(value) or scale_y
                scale_y_set = True
            elif code == "50":
                rotation = self._parse_float(value) or rotation
            idx += 1

        if scale_x_set and not scale_y_set:
            scale_y = scale_x
        elif scale_y_set and not scale_x_set:
            scale_x = scale_y

        block = blocks.get(name)
        if block:
            insert_point = (ins_x, -ins_y)
            self._append_block_shapes(
                shapes,
                block,
                insert_point=insert_point,
                scale_x=scale_x,
                scale_y=scale_y,
                rotation=rotation,
                override_style=style,
                override_layer=layer,
            )
        return idx

    def _append_block_shapes(
        self,
        shapes,
        block,
        insert_point,
        scale_x=1.0,
        scale_y=1.0,
        rotation=0.0,
        override_style=None,
        override_layer=None,
        absolute=False,
    ):
        base_x, base_y = block.get("base", (0.0, 0.0))
        angle = math.radians(-rotation)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        scale_factor = (abs(scale_x) + abs(scale_y)) / 2.0

        if absolute:
            for shape in block.get("shapes", []):
                new_shape = dict(shape)
                merged_style = self._merge_styles(shape.get("style"), override_style)
                layer_name = shape.get("layer")
                if override_layer and (not layer_name or layer_name == "0"):
                    layer_name = override_layer
                if merged_style:
                    new_shape["style"] = merged_style
                if layer_name:
                    new_shape["layer"] = layer_name
                shapes.append(new_shape)
            return

        def transform_point(x, y):
            rx = (x - base_x) * scale_x
            ry = (y - base_y) * scale_y
            tx = rx * cos_a - ry * sin_a
            ty = rx * sin_a + ry * cos_a
            return (tx + insert_point[0], ty + insert_point[1])

        for shape in block.get("shapes", []):
            shape_type = shape.get("type")
            params = shape.get("params", ())
            merged_style = self._merge_styles(shape.get("style"), override_style)
            layer_name = shape.get("layer")
            if override_layer and (not layer_name or layer_name == "0"):
                layer_name = override_layer
            if shape_type in ("line", "centerline"):
                x1, y1, x2, y2 = params
                p1 = transform_point(x1, y1)
                p2 = transform_point(x2, y2)
                new_shape = dict(shape)
                new_shape["params"] = (p1[0], p1[1], p2[0], p2[1])
                if merged_style:
                    new_shape["style"] = merged_style
                if layer_name:
                    new_shape["layer"] = layer_name
                shapes.append(new_shape)
            elif shape_type == "polyline":
                points, closed = params
                new_points = [transform_point(x, y) for x, y in points]
                new_shape = dict(shape)
                new_shape["params"] = (tuple(new_points), closed)
                if merged_style:
                    new_shape["style"] = merged_style
                if layer_name:
                    new_shape["layer"] = layer_name
                shapes.append(new_shape)
            elif shape_type == "circle":
                cx, cy, radius = params
                center = transform_point(cx, cy)
                new_shape = dict(shape)
                new_shape["params"] = (center[0], center[1], radius * scale_factor)
                if merged_style:
                    new_shape["style"] = merged_style
                if layer_name:
                    new_shape["layer"] = layer_name
                shapes.append(new_shape)
            elif shape_type in ("arc_angle", "doubleline_arc", "center_arc"):
                cx, cy, radius, start_angle, span_angle = params
                center = transform_point(cx, cy)
                new_shape = dict(shape)
                new_shape["params"] = (
                    center[0],
                    center[1],
                    radius * scale_factor,
                    start_angle - rotation,
                    span_angle,
                )
                if merged_style:
                    new_shape["style"] = merged_style
                if layer_name:
                    new_shape["layer"] = layer_name
                shapes.append(new_shape)
            elif shape_type == "text":
                x, y, text_value, height, text_rotation = params
                pos = transform_point(x, y)
                new_height = height * scale_factor if height else height
                new_rotation = (text_rotation or 0.0) - rotation
                new_shape = dict(shape)
                new_shape["params"] = (pos[0], pos[1], text_value, new_height, new_rotation)
                if merged_style:
                    new_shape["style"] = merged_style
                if layer_name:
                    new_shape["layer"] = layer_name
                shapes.append(new_shape)

    def _convert_dxf_arcs(self, arcs):
        if not arcs:
            return []

        buckets = {}
        for arc in arcs:
            key = (
                round(arc["cx"], 4),
                round(arc["cy"], 4),
                round(self._normalize_angle_value(arc["start"]), 4),
                round(self._normalize_angle_value(arc["end"]), 4),
            )
            buckets.setdefault(key, []).append(arc)

        for bucket in buckets.values():
            size = len(bucket)
            for arc in bucket:
                arc["_group_size"] = size
            if size >= 2:
                bucket.sort(key=lambda item: item["radius"])
                bucket[0]["kind"] = "center_arc"
                for arc in bucket[1:]:
                    arc["kind"] = "doubleline_arc"
            else:
                bucket[0]["kind"] = "doubleline_arc"

        shapes = []
        for arc in arcs:
            span = -self._angle_span(arc["start"], arc["end"])
            start_angle = -arc["start"]
            shape = {
                "type": arc.get("kind", "doubleline_arc"),
                "params": (arc["cx"], arc["cy"], arc["radius"], start_angle, span),
            }
            if arc.get("layer"):
                shape["layer"] = arc.get("layer")
            if arc.get("style"):
                shape["style"] = dict(arc.get("style"))
            shapes.append(shape)
        return shapes

    def _angle_span(self, start, end):
        span = (end - start) % 360.0
        if abs(span) < 1e-6:
            span = 360.0
        return span

    def _normalize_angle_value(self, angle):
        value = angle % 360.0
        if value < 0:
            value += 360.0
        return value

    def _parse_float(self, text):
        try:
            return float(text)
        except (TypeError, ValueError):
            return None


    def _save_file(self):
        self._save_file_as()

    def _save_file_as(self):
        document = self.current_document()
        if document is None:
            return

        default_name = document["path"] or f"{os.path.splitext(document['name'])[0]}.dxf"
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "保存图纸",
            default_name,
            "AutoCAD DXF (*.dxf);;FTCAD JSON (*.json)",
        )
        if not path:
            return

        save_as_json = path.lower().endswith(".json") or "JSON" in selected_filter
        if save_as_json:
            if not path.lower().endswith(".json"):
                path = f"{path}.json"
        else:
            if path.lower().endswith(".dwg"):
                QMessageBox.warning(
                    self,
                    "暂不支持 DWG",
                    "当前环境无法直接生成真 DWG 文件，已改为建议保存为可被 AutoCAD/浩辰打开的 DXF。",
                )
                path = f"{os.path.splitext(path)[0]}.dxf"
            elif not path.lower().endswith(".dxf"):
                path = f"{path}.dxf"

        new_name = self._normalize_document_name(os.path.splitext(os.path.basename(path))[0])
        try:
            self._write_document(document, path, save_as_json=save_as_json)
        except PermissionError:
            QMessageBox.critical(
                self,
                "保存失败",
                f"没有权限写入该位置:\n{path}\n\n常见原因:\n1. 文件正在被其他程序占用\n2. 桌面目录受 Windows 安全策略保护\n3. 当前程序对该目录没有写权限\n\n请改存到其他目录，或关闭占用该文件的程序后重试。",
            )
            self.output.append(f"保存失败: 无法写入 {path}")
            self.status_label.setText("保存失败")
            return
        except OSError as exc:
            QMessageBox.critical(self, "保存失败", f"写入文件时出错:\n{path}\n\n{exc}")
            self.output.append(f"保存失败: {exc}")
            self.status_label.setText("保存失败")
            return

        document["path"] = path
        document["name"] = new_name
        self._sync_title()

    def _write_document(self, document, path, save_as_json=False):
        if save_as_json:
            payload = {
                "name": document["name"],
                "template": document["template"],
                "shapes": document["canvas"].to_dict()["shapes"],
            }
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
        else:
            self._write_dxf(document, path)
        self.output.append(f"已保存: {path}")
        self.status_label.setText(f"已保存到 {path}")

    def _write_dxf(self, document, path):
        shapes = document["canvas"].to_dict()["shapes"]
        entities = []
        for shape in shapes:
            entities.extend(self._shape_to_dxf_entities(shape))
        min_x, min_y, max_x, max_y = self._document_bounds(shapes)
        content = []
        content.extend(self._dxf_header(min_x, min_y, max_x, max_y))
        content.extend(self._dxf_tables_section())
        content.extend(self._dxf_blocks_section())
        content.extend(self._dxf_entities_section(entities))
        content.append("0")
        content.append("EOF")
        with open(path, "w", encoding="ascii", newline="\r\n") as handle:
            handle.write("\n".join(content))

    def _dxf_header(self, min_x, min_y, max_x, max_y):
        return [
            "0", "SECTION", "2", "HEADER",
            "9", "$ACADVER", "1", "AC1009",
            "9", "$INSBASE", "10", "0.0", "20", "0.0", "30", "0.0",
            "9", "$EXTMIN", "10", f"{min_x:.4f}", "20", f"{min_y:.4f}", "30", "0.0",
            "9", "$EXTMAX", "10", f"{max_x:.4f}", "20", f"{max_y:.4f}", "30", "0.0",
            "9", "$LIMMIN", "10", f"{min_x:.4f}", "20", f"{min_y:.4f}",
            "9", "$LIMMAX", "10", f"{max_x:.4f}", "20", f"{max_y:.4f}",
            "0", "ENDSEC",
        ]

    def _dxf_tables_section(self):
        tables = ["0", "SECTION", "2", "TABLES"]
        tables.extend([
            "0", "TABLE", "2", "VPORT", "70", "1",
            "0", "VPORT", "2", "*ACTIVE", "70", "0",
            "10", "0.0", "20", "0.0", "11", "1.0", "21", "1.0",
            "12", "0.0", "22", "0.0", "13", "0.0", "23", "0.0",
            "14", "1.0", "24", "1.0", "15", "0.0", "25", "0.0",
            "16", "0.0", "26", "0.0", "36", "1.0", "37", "1.0",
            "40", "1000.0", "41", "1.0", "42", "50.0", "43", "0.0", "44", "0.0",
            "50", "0.0", "51", "0.0",
            "71", "0", "72", "1000", "73", "1", "74", "3", "75", "0", "76", "0", "77", "0", "78", "0",
            "0", "ENDTAB",
        ])
        tables.extend([
            "0", "TABLE", "2", "LTYPE", "70", "1",
            "0", "LTYPE", "2", "CONTINUOUS", "70", "64", "3", "Solid line", "72", "65", "73", "0", "40", "0.0",
            "0", "ENDTAB",
        ])
        tables.extend([
            "0", "TABLE", "2", "LAYER", "70", "1",
            "0", "LAYER", "2", "0", "70", "0", "62", "7", "6", "CONTINUOUS",
            "0", "ENDTAB",
        ])
        tables.extend([
            "0", "TABLE", "2", "STYLE", "70", "1",
            "0", "STYLE", "2", "STANDARD", "70", "0", "40", "0.0", "41", "1.0", "50", "0.0",
            "71", "0", "42", "0.2", "3", "txt", "4", "",
            "0", "ENDTAB",
        ])
        tables.extend(["0", "TABLE", "2", "VIEW", "70", "0", "0", "ENDTAB"])
        tables.extend(["0", "TABLE", "2", "UCS", "70", "0", "0", "ENDTAB"])
        tables.extend([
            "0", "TABLE", "2", "APPID", "70", "1",
            "0", "APPID", "2", "ACAD", "70", "0",
            "0", "ENDTAB",
        ])
        tables.extend([
            "0", "TABLE", "2", "DIMSTYLE", "70", "1",
            "0", "DIMSTYLE", "2", "STANDARD", "70", "0",
            "3", "", "4", "", "5", "", "6", "", "7", "",
            "40", "0.0", "41", "0.0", "42", "0.0", "43", "0.0", "44", "0.0",
            "45", "0.0", "46", "0.0", "47", "0.0", "48", "0.0",
            "140", "0.0", "141", "0.0", "142", "0.0", "143", "0.0", "144", "0.0",
            "145", "0.0", "146", "0.0", "147", "0.0", "148", "0.0",
            "71", "0", "72", "0", "73", "0", "74", "0", "75", "0",
            "76", "0", "77", "0", "78", "0", "79", "0",
            "0", "ENDTAB",
        ])
        tables.extend(["0", "ENDSEC"])
        return tables

    def _dxf_blocks_section(self):
        return [
            "0", "SECTION", "2", "BLOCKS",
            "0", "BLOCK", "8", "0", "2", "*MODEL_SPACE", "70", "0",
            "10", "0.0", "20", "0.0", "30", "0.0", "3", "*MODEL_SPACE", "1", "*MODEL_SPACE",
            "0", "ENDBLK", "8", "0",
            "0", "BLOCK", "8", "0", "2", "*PAPER_SPACE", "70", "0",
            "10", "0.0", "20", "0.0", "30", "0.0", "3", "*PAPER_SPACE", "1", "*PAPER_SPACE",
            "0", "ENDBLK", "8", "0",
            "0", "ENDSEC",
        ]

    def _dxf_entities_section(self, entities):
        section = ["0", "SECTION", "2", "ENTITIES"]
        section.extend(entities)
        section.extend(["0", "ENDSEC"])
        return section

    def _document_bounds(self, shapes):
        if not shapes:
            return 0.0, -100.0, 100.0, 0.0

        min_x = float("inf")
        min_y = float("inf")
        max_x = float("-inf")
        max_y = float("-inf")
        for shape in shapes:
            sx1, sy1, sx2, sy2 = self._shape_bounds(shape)
            min_x = min(min_x, sx1)
            min_y = min(min_y, sy1)
            max_x = max(max_x, sx2)
            max_y = max(max_y, sy2)

        padding = max(10.0, max(max_x - min_x, max_y - min_y) * 0.05)
        return min_x - padding, min_y - padding, max_x + padding, max_y + padding

    def _shape_bounds(self, shape):
        shape_type = shape["type"]
        params = shape["params"]
        if shape_type in ("line", "rect", "ellipse", "arc"):
            x1, y1, x2, y2 = params
            ys = (-y1, -y2)
            return min(x1, x2), min(ys), max(x1, x2), max(ys)
        if shape_type == "polyline":
            points, _closed = params
            if not points:
                return 0.0, 0.0, 0.0, 0.0
            xs = [pt[0] for pt in points]
            ys = [-pt[1] for pt in points]
            return min(xs), min(ys), max(xs), max(ys)
        if shape_type == "hatch":
            loops = params or []
            points = [pt for loop in loops for pt in loop]
            if not points:
                return 0.0, 0.0, 0.0, 0.0
            xs = [pt[0] for pt in points]
            ys = [-pt[1] for pt in points]
            return min(xs), min(ys), max(xs), max(ys)
        if shape_type == "circle":
            cx, cy, radius = params
            return cx - radius, -(cy + radius), cx + radius, -(cy - radius)
        if shape_type == "doubleline":
            x1, y1, x2, y2, width = params
            half = width / 2
            ys = (-y1, -y2)
            return min(x1, x2) - half, min(ys) - half, max(x1, x2) + half, max(ys) + half
        if shape_type in ("arc_angle", "doubleline_arc", "center_arc"):
            cx, cy, radius, _start, _span = params
            return cx - radius, -(cy + radius), cx + radius, -(cy - radius)
        if shape_type == "center_mark":
            cx, cy, size = params
            half = size / 2.0
            ys = (-(cy - half), -(cy + half))
            return cx - half, min(ys), cx + half, max(ys)
        return 0.0, 0.0, 0.0, 0.0

    def _shape_to_dxf_entities(self, shape):
        shape_type = shape["type"]
        params = shape["params"]
        if shape_type == "line":
            x1, y1, x2, y2 = params
            return self._dxf_line(x1, y1, x2, y2)
        if shape_type == "centerline":
            x1, y1, x2, y2 = params
            return self._dxf_line(x1, y1, x2, y2)
        if shape_type == "center_mark":
            cx, cy, size = params
            half = size / 2.0
            return (
                self._dxf_line(cx - half, cy, cx + half, cy)
                + self._dxf_line(cx, cy - half, cx, cy + half)
            )
        if shape_type == "circle":
            cx, cy, radius = params
            return self._dxf_circle(cx, cy, radius)
        if shape_type == "rect":
            x1, y1, x2, y2 = params
            return self._dxf_polyline([(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)])
        if shape_type == "polyline":
            points, closed = params
            return self._dxf_polyline(points, closed=closed)
        if shape_type == "ellipse":
            x1, y1, x2, y2 = params
            return self._dxf_polyline(self._ellipse_points(x1, y1, x2, y2))
        if shape_type == "arc":
            x1, y1, x2, y2 = params
            return self._dxf_polyline(self._arc_points(x1, y1, x2, y2))
        if shape_type == "doubleline":
            x1, y1, x2, y2, width = params
            return self._dxf_doubleline(x1, y1, x2, y2, width)
        if shape_type in ("doubleline_arc", "center_arc"):
            cx, cy, radius, start_angle, span_angle = params
            start = start_angle
            end = start_angle + span_angle
            if span_angle < 0:
                start, end = end, start
            return self._dxf_arc(cx, cy, radius, start, end)
        if shape_type == "arc_angle":
            cx, cy, radius, start_angle, span_angle = params
            start = start_angle
            end = start_angle + span_angle
            if span_angle < 0:
                start, end = end, start
            return self._dxf_arc(cx, cy, radius, start, end)
        return []

    def _dxf_line(self, x1, y1, x2, y2):
        return [
            "0", "LINE", "8", "0",
            "10", f"{x1:.4f}", "20", f"{-y1:.4f}", "30", "0.0",
            "11", f"{x2:.4f}", "21", f"{-y2:.4f}", "31", "0.0",
        ]

    def _dxf_circle(self, cx, cy, radius):
        return [
            "0", "CIRCLE", "8", "0",
            "10", f"{cx:.4f}", "20", f"{-cy:.4f}", "30", "0.0",
            "40", f"{radius:.4f}",
        ]

    def _dxf_arc(self, cx, cy, radius, start_angle, end_angle):
        return [
            "0", "ARC", "8", "0",
            "10", f"{cx:.4f}", "20", f"{-cy:.4f}", "30", "0.0",
            "40", f"{radius:.4f}",
            "50", f"{self._normalize_angle(start_angle):.4f}",
            "51", f"{self._normalize_angle(end_angle):.4f}",
        ]

    def _dxf_polyline(self, points, closed=False):
        entities = ["0", "LWPOLYLINE", "8", "0", "90", str(len(points)), "70", "1" if closed else "0"]
        for x, y in points:
            entities.extend(["10", f"{x:.4f}", "20", f"{-y:.4f}"])
        return entities

    def _ellipse_points(self, x1, y1, x2, y2, steps=48):
        import math
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        rx = abs(x2 - x1) / 2
        ry = abs(y2 - y1) / 2
        points = []
        for index in range(steps + 1):
            angle = 2 * math.pi * index / steps
            points.append((cx + rx * math.cos(angle), cy + ry * math.sin(angle)))
        return points

    def _arc_points(self, x1, y1, x2, y2, steps=24):
        import math
        left = min(x1, x2)
        top = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        cx = left + width / 2
        cy = top + height / 2
        rx = width / 2
        ry = height / 2
        points = []
        for index in range(steps + 1):
            angle = math.pi * index / steps
            points.append((cx + rx * math.cos(angle), cy - ry * math.sin(angle)))
        return points

    def _dxf_doubleline(self, x1, y1, x2, y2, width):
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if not length:
            return []
        nx = -dy / length
        ny = dx / length
        offset = width / 2
        return self._dxf_line(x1 + nx * offset, y1 + ny * offset, x2 + nx * offset, y2 + ny * offset) + self._dxf_line(x1 - nx * offset, y1 - ny * offset, x2 - nx * offset, y2 - ny * offset)

    def _normalize_angle(self, value):
        angle = value % 360.0
        if angle < 0:
            angle += 360.0
        return angle

    def _print_current(self):
        document = self.current_document()
        if document is None:
            return

        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QDialog.Accepted:
            self.output.append(f"打印任务已提交: {document['name']}")
            self.status_label.setText("打印任务已提交")

    def _undo_current(self):
        canvas = self.current_canvas()
        if canvas is not None:
            canvas.undo()

    def _redo_current(self):
        canvas = self.current_canvas()
        if canvas is not None:
            canvas.redo()

    def _close_document(self, index):
        page = self.doc_tabs.widget(index)
        self.doc_tabs.removeTab(index)
        self.documents = [doc for doc in self.documents if doc["page"] is not page]
        page.deleteLater()
        self._sync_title()
        if self.doc_tabs.count() == 0:
            self.status_label.setText("暂无打开的图纸")

    def _on_document_changed(self, index):
        del index
        document = self.current_document()
        if document is None:
            return
        self.status_label.setText(f"当前图纸: {document['name']}")
        self._sync_title()
        self._sync_layer_ui()

    def _on_layout_changed(self, index):
        self.mode_label.setText(self.layout_tabs.tabText(index))
        self.output.append(f"切换空间: {self.layout_tabs.tabText(index)}")

    def _show_layout_menu(self, pos):
        if self.layout_tabs.tabAt(pos) < 0:
            return

        self._open_sketch_settings_dialog(pos)

    def _set_interface_mode(self, mode):
        self.active_interface = mode
        for action in self.interface_action_group.actions():
            action.setChecked(action.text() == mode)
        self.status_label.setText(f"界面模式: {mode}")
        if mode == "三维界面":
            self.ribbon_tabs.setCurrentIndex(3)
        else:
            self.ribbon_tabs.setCurrentIndex(0)

    def _apply_theme(self, theme_name):
        self.active_theme = theme_name
        for action in self.theme_action_group.actions():
            action.setChecked(action.text() == theme_name)

        theme = THEMES[theme_name]
        surface_css = f"background: {theme['surface']}; color: {theme['text']};"
        control_css = (
            "QWidget { background: %s; color: %s; }"
            "QPushButton, QToolButton { background: rgba(255,255,255,0.75); color: %s; border: 1px solid %s; border-radius: 3px; padding: 1px 4px; min-height: 18px; }"
            "QLabel[role='sectionTitle'] { color: %s; font-size: 11px; }"
        ) % (theme["surface"], theme["text"], theme["text"], theme["accent"], theme["text"])
        tab_css = (
            "QTabWidget::pane { border: 1px solid %s; background: %s; }"
            "QTabBar::tab { background: %s; color: %s; border: 1px solid %s; padding: 3px 8px; margin-right: 1px; }"
            "QTabBar::tab:selected { background: %s; color: white; }"
        ) % (theme["accent"], theme["surface"], theme["surface"], theme["text"], theme["accent"], theme["accent"])

        self.menu_widget.setStyleSheet(surface_css + control_css)
        self.ribbon_tabs.setStyleSheet(
            tab_css
            + control_css
            + ("QWidget#ribbonSection { border: 1px solid %s; border-radius: 4px; }" % theme["accent"])
        )
        self.layout_tabs.setStyleSheet(tab_css)
        self.doc_tabs.setStyleSheet(tab_css)
        if self.layer_manager_panel is not None:
            self.layer_manager_panel.setStyleSheet(surface_css + control_css)
        self.status_widget.setStyleSheet(surface_css)
        self.status_label.setText(f"界面颜色: {theme_name}")

    def _ensure_upcomer_pdf_data(self):
        if self.upcomer_pdf_data is None:
            self._load_upcomer_pdf_data()
        return self.upcomer_pdf_data

    def _notify_component_pending(self, name):
        if self.output is not None:
            self.output.append(f"{name}：绘制功能尚未实现。")
        self.status_label.setText(f"{name}: 待实现")

    def _draw_inner_cylinder_assembly(self):
        canvas = self.current_canvas()
        if canvas is None:
            return

        data = self._ensure_upcomer_pdf_data()
        if data is None:
            if self.output is not None:
                self.output.append("未找到上升管1.7.pdf，无法提取尺寸并绘制内筒体组件。")
            self.status_label.setText("未找到上升管1.7.pdf")
            return

        spec = resolve_inner_cylinder_spec(data)
        canvas.clear()

        margin = 60
        available_w = max(200, canvas.width() - margin * 2)
        available_h = max(200, canvas.height() - margin * 2)
        total_h = spec["height"] + spec["flange_thickness"] * 2
        total_w = max(spec["outer_diameter"], spec["flange_outer_diameter"])
        scale = min(available_w / total_w, available_h / total_h) if total_w > 0 and total_h > 0 else 1.0
        if scale <= 0:
            scale = 1.0

        cx = canvas.width() / 2.0
        top = float(margin)
        flange_thk = spec["flange_thickness"] * scale
        body_height = spec["height"] * scale
        body_top = top + flange_thk
        body_bottom = body_top + body_height
        flange_bottom = body_bottom + flange_thk
        half_body = spec["outer_diameter"] * scale / 2.0
        half_inner = spec["inner_diameter"] * scale / 2.0
        half_flange = spec["flange_outer_diameter"] * scale / 2.0

        canvas.add_rect(cx - half_flange, top, cx + half_flange, body_top)
        canvas.add_rect(cx - half_body, body_top, cx + half_body, body_bottom)
        canvas.add_rect(cx - half_flange, body_bottom, cx + half_flange, flange_bottom)

        if 0 < spec["inner_diameter"] < spec["outer_diameter"]:
            canvas.add_line(cx - half_inner, body_top, cx - half_inner, body_bottom)
            canvas.add_line(cx + half_inner, body_top, cx + half_inner, body_bottom)

        canvas.add_centerline(cx, top, cx, flange_bottom)

        if self.output is not None:
            summary = summarize_extraction(data)
            self.output.append(
                "已读取{pdf}，{summary}。绘制内筒体组件：外径∅{outer:.0f}、内径∅{inner:.0f}、高度{height:.0f}、"
                "法兰外径∅{flange:.0f}。".format(
                    pdf=os.path.basename(data.pdf_path),
                    summary=summary,
                    outer=spec["outer_diameter"],
                    inner=spec["inner_diameter"],
                    height=spec["height"],
                    flange=spec["flange_outer_diameter"],
                )
            )
        self.status_label.setText("已绘制: 内筒体组件")

    def _open_inner_cylinder_params_dialog(self):
        base_dir = os.path.dirname(__file__)
        source_dir = os.path.join(base_dir, "project")
        target_dir = os.path.join(base_dir, "project_new")
        source_path = os.path.join(source_dir, "1内筒体组件.dxf")
        target_path = os.path.join(target_dir, "1内筒体组件.dxf")
        if not os.path.exists(source_path):
            QMessageBox.critical(self, "未找到文件", "未找到 project/1内筒体组件.dxf，无法读取尺寸参数。")
            if self.output is not None:
                self.output.append("未找到 project/1内筒体组件.dxf，无法读取尺寸参数。")
            self.status_label.setText("未找到 project/1内筒体组件.dxf")
            return

        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(self, "复制失败", f"无法创建 project_new 文件夹：\n{exc}")
            if self.output is not None:
                self.output.append(f"创建 project_new 文件夹失败：{exc}")
            self.status_label.setText("创建 project_new 失败")
            return

        try:
            shutil.copy2(source_path, target_path)
        except OSError as exc:
            QMessageBox.critical(self, "复制失败", f"无法复制 1内筒体组件.dxf 到 project_new：\n{exc}")
            if self.output is not None:
                self.output.append(f"复制到 project_new 失败：{exc}")
            self.status_label.setText("复制到 project_new 失败")
            return

        try:
            raw_lines, entries, encoding = self._extract_dxf_dimension_params(target_path)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "读取失败", f"无法读取 DXF 尺寸参数：\n{exc}")
            if self.output is not None:
                self.output.append(f"读取 DXF 尺寸参数失败：{exc}")
            self.status_label.setText("读取尺寸参数失败")
            return

        if not entries:
            QMessageBox.information(self, "未找到尺寸参数", "未在 project_new/1内筒体组件.dxf 中读取到尺寸参数。")
            if self.output is not None:
                self.output.append("未在 project_new/1内筒体组件.dxf 中读取到尺寸参数。")
            self.status_label.setText("未读取到尺寸参数")
            return

        dialog = InnerCylinderParamsDialog(entries, self)
        self._center_dialog(dialog)
        if dialog.exec() != QDialog.Accepted:
            return

        new_values = dialog.values()
        try:
            self._apply_dimension_updates(raw_lines, entries, new_values)
        except ValueError as exc:
            QMessageBox.warning(self, "参数错误", str(exc))
            self.status_label.setText("参数校验失败")
            return

        try:
            with open(target_path, "w", encoding=encoding or "utf-8", newline="") as handle:
                handle.writelines(raw_lines)
        except OSError as exc:
            QMessageBox.critical(self, "保存失败", f"无法保存 DXF：\n{exc}")
            if self.output is not None:
                self.output.append(f"保存 DXF 失败：{exc}")
            self.status_label.setText("保存失败")
            return

        try:
            payload = self._load_dxf_document(target_path)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "打开失败", f"无法加载生成的 DXF：\n{exc}")
            if self.output is not None:
                self.output.append(f"打开生成的 DXF 失败：{exc}")
            self.status_label.setText("打开失败")
            return

        name = payload.get("name") or "1内筒体组件"
        template = payload.get("template", "二维草图")
        shapes = payload.get("shapes", [])
        document = self._add_document(name, template, path=target_path, shapes=shapes)
        self._fit_canvas_on_shapes(document["canvas"])
        if self.output is not None:
            self.output.append(f"已生成并打开：{target_path}")
        self.status_label.setText("已生成: project_new/1内筒体组件.dxf")

    def _center_canvas_on_shapes(self, canvas):
        if canvas is None:
            return
        bounds = None
        for shape in canvas.shapes:
            shape_bounds = canvas._shape_bounds(shape)
            if shape_bounds is None:
                continue
            if bounds is None:
                bounds = list(shape_bounds)
            else:
                bounds[0] = min(bounds[0], shape_bounds[0])
                bounds[1] = min(bounds[1], shape_bounds[1])
                bounds[2] = max(bounds[2], shape_bounds[2])
                bounds[3] = max(bounds[3], shape_bounds[3])
        if bounds is None:
            return
        x1, y1, x2, y2 = bounds
        center_x = (x1 + x2) / 2.0
        center_y = (y1 + y2) / 2.0
        target_x = canvas.width() / 2.0
        target_y = canvas.height() / 2.0
        dx = target_x - center_x
        dy = target_y - center_y
        if abs(dx) > 0.01 or abs(dy) > 0.01:
            canvas._apply_pan(dx, dy)
            canvas.update()

    def _fit_canvas_on_shapes(self, canvas, margin=40):
        if canvas is None:
            return
        bounds = None
        for shape in canvas.shapes:
            shape_bounds = canvas._shape_bounds(shape)
            if shape_bounds is None:
                continue
            if bounds is None:
                bounds = list(shape_bounds)
            else:
                bounds[0] = min(bounds[0], shape_bounds[0])
                bounds[1] = min(bounds[1], shape_bounds[1])
                bounds[2] = max(bounds[2], shape_bounds[2])
                bounds[3] = max(bounds[3], shape_bounds[3])
        if bounds is None:
            return
        x1, y1, x2, y2 = bounds
        width = max(1.0, x2 - x1)
        height = max(1.0, y2 - y1)
        avail_w = max(50.0, canvas.width() - margin * 2)
        avail_h = max(50.0, canvas.height() - margin * 2)
        factor = min(avail_w / width, avail_h / height)
        factor = min(1.0, factor)
        if factor < 0.99:
            anchor = QPoint(int((x1 + x2) / 2.0), int((y1 + y2) / 2.0))
            canvas._apply_zoom(factor, anchor)
        self._center_canvas_on_shapes(canvas)

    def _tool_clicked(self, name, display_name=None):
        if self.tool_actions is None:
            return
        self.tool_actions.handle_tool(name, display_name)

    def _build_tool_action_context(self):
        return ToolActionContext(
            tool_tips=TOOL_TIPS,
            drawing_tools=DRAWING_TOOLS,
            inner_cylinder_tool="1内筒体组件",
            pending_component_tools={"2内筒体", "3 下接环组件", "3-1 下连接圈", "3-2下连接环"},
            layer_props_tool="Layer Props",
            table_tool="Table",
            color_tool="Color",
            get_canvas=self.current_canvas,
            set_current_tool_status=self._set_current_tool_status,
            open_inner_cylinder_params_dialog=self._open_inner_cylinder_params_dialog,
            notify_component_pending=self._notify_component_pending,
            toggle_layer_manager=self._toggle_layer_manager,
            on_layer_manager_opened=self._on_layer_manager_opened,
            request_table_insert=self._request_table_insert,
            on_table_inserted=self._on_table_inserted,
            request_color=self._request_color,
            apply_layer_color=self._apply_layer_color,
            on_tool_enabled=self._on_tool_enabled,
            on_tool_placeholder=self._on_tool_placeholder,
        )

    def _set_current_tool_status(self, label):
        self.current_tool_name = label
        self.status_label.setText(f"当前工具: {label}")

    def _on_tool_enabled(self, label):
        self.output.append(f"工具已启用: {label}")

    def _on_tool_placeholder(self, label):
        self.output.append(f"工具: {label} | 当前为界面占位。")

    def _on_layer_manager_opened(self):
        self.status_label.setText("图层特性管理器已打开")

    def _request_table_insert(self):
        dialog = TableInsertDialog(self)
        self._center_dialog(dialog)
        if dialog.exec() == QDialog.Accepted:
            return dialog.values()
        return None

    def _on_table_inserted(self, settings):
        self.output.append(f"插入表格: {settings}")
        self.status_label.setText("表格样式已选择")

    def _request_color(self):
        dialog = QColorDialog(self)
        dialog.setWindowTitle("选择颜色")
        dialog.setOption(QColorDialog.ShowAlphaChannel, False)
        if dialog.exec() == QDialog.Accepted:
            chosen = dialog.currentColor()
            return self._color_name_from_qcolor(chosen)
        return None

    def _apply_layer_color(self, color_name):
        if not color_name:
            return
        self._set_combo_value(self.prop_color_combo, color_name)
        self._on_layer_property_changed("color", color_name)

    def _on_canvas_point(self, text):
        title = self.current_tool_name or "绘图"
        self.status_label.setText(f"{title} | {text}")

    def _on_canvas_tool_changed(self, tool_key):
        if tool_key == "select":
            label = TOOL_TIPS.get("Select", "Select")
            self._set_current_tool_status(label)

    def _on_command_entered(self):
        text = self.input.text().strip()
        if not text:
            return

        canvas = self.current_canvas()
        if canvas is None:
            return

        self.output.append(f"> {text}")
        processor = CommandProcessor(canvas)
        try:
            result = processor.process(text)
            if result:
                self.output.append(result)
        except Exception as exc:
            self.output.append(f"Error: {exc}")
        self.input.clear()

    def current_document(self):
        current_page = self.doc_tabs.currentWidget()
        for document in self.documents:
            if document["page"] is current_page:
                return document
        return None

    def current_canvas(self):
        document = self.current_document()
        return document["canvas"] if document else None

    def _sync_title(self):
        document = self.current_document()
        if document is None:
            self.setWindowTitle("FTCAD")
            return
        self.setWindowTitle(f"FTCAD - [{document['name']}]")
        index = self.doc_tabs.currentIndex()
        if index >= 0:
            self.doc_tabs.setTabText(index, document["name"])
