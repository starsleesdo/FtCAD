import math

from PySide6.QtWidgets import QWidget, QInputDialog
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtCore import Qt, QPoint, QPointF, QRectF, Signal


class Canvas(QWidget):
    point_info = Signal(str)
    pointer_info = Signal(str)

    def __init__(self, mode_state):
        super().__init__()
        self.setMinimumSize(400, 300)
        self.shapes = []
        self._undo_stack = []
        self._redo_stack = []
        self.mode_state = mode_state
        self.current_tool = "select"
        self._start_pos = None
        self._temp_pos = None
        self._poly_points = []
        self._tool_points = []
        self._selection_start = None
        self._selection_end = None
        self._selecting = False
        self.selected_indices = set()
        self._moving_selection = False
        self._move_last_pos = None
        self._panning = False
        self._pan_last_pos = None
        self.selection_color = QColor(255, 200, 80)
        self.target_screen_width_units = 6400.0
        self.units_per_pixel = None
        self.setMouseTracking(True)
        self.setCursor(Qt.ArrowCursor)
        self._rect_first = None
        self._ellipse_first = None
        self._arc_first = None
        self._doubleline_first = None
        self._doubleline_prev = None
        self.background_color = QColor(30, 30, 30)
        self.grid_color = QColor(60, 60, 60)
        self.drawing_color = QColor(220, 220, 220)
        self.preview_color = QColor(180, 220, 255)
        self._point_markers = []
        self.grid_step = 20
        self.zoom_factor = 1.0
        self.setFocusPolicy(Qt.StrongFocus)
        self.centerline_color = QColor(255, 214, 120)
        self.pipe_radius_factor = 1.3
        self._last_centerline_index = None
        self._last_doubleline_segment_index = None
        self.symmetry_mode = False
        self.active_layer = {
            "name": "0",
            "color": "白",
            "linetype": "continuous",
            "lineweight": "0.25",
        }

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), self.background_color)
        if self.mode_state.grid:
            self._draw_grid(p)

        for shape in self.shapes:
            self._draw_shape(p, shape)

        self._draw_selection_highlight(p)
        self._draw_preview(p)
        self._draw_selection_rect(p)
        self._draw_point_markers(p)
        self._draw_axes(p)

    def _draw_shape(self, painter, shape):
        shape_type = shape['type']
        if shape_type not in ('centerline', 'center_arc'):
            self._apply_style_pen(painter, shape.get('style'))

        if shape_type == 'line':
            x1, y1, x2, y2 = shape['params']
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        elif shape_type == 'circle':
            cx, cy, radius = shape['params']
            painter.drawEllipse(int(cx - radius), int(cy - radius), int(2 * radius), int(2 * radius))
        elif shape_type == 'rect':
            x1, y1, x2, y2 = shape['params']
            painter.drawRect(int(min(x1, x2)), int(min(y1, y2)), abs(int(x2 - x1)), abs(int(y2 - y1)))
        elif shape_type == 'polyline':
            points, closed = shape['params']
            if len(points) < 2:
                return
            for index in range(len(points) - 1):
                x1, y1 = points[index]
                x2, y2 = points[index + 1]
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            if closed:
                x1, y1 = points[-1]
                x2, y2 = points[0]
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        elif shape_type == 'ellipse':
            x1, y1, x2, y2 = shape['params']
            painter.drawEllipse(int(min(x1, x2)), int(min(y1, y2)), abs(int(x2 - x1)), abs(int(y2 - y1)))
        elif shape_type == 'arc':
            x1, y1, x2, y2 = shape['params']
            rect = [int(min(x1, x2)), int(min(y1, y2)), abs(int(x2 - x1)), abs(int(y2 - y1))]
            painter.drawArc(*rect, 0 * 16, 180 * 16)
        elif shape_type == 'arc_angle':
            cx, cy, radius, start_angle, span_angle = shape['params']
            rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
            painter.drawArc(rect, self._qt_angle(start_angle), self._qt_span(span_angle))
        elif shape_type == 'centerline':
            painter.save()
            pen = QPen(self.centerline_color)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            x1, y1, x2, y2 = shape['params']
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            painter.restore()
        elif shape_type == 'center_mark':
            cx, cy, size = shape['params']
            half = size / 2.0
            painter.drawLine(int(cx - half), int(cy), int(cx + half), int(cy))
            painter.drawLine(int(cx), int(cy - half), int(cx), int(cy + half))
        elif shape_type == 'doubleline':
            x1, y1, x2, y2, width = shape['params']
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            if length == 0:
                return
            nx, ny = -dy / length, dx / length
            offset = width / 2
            p1a = QPointF(x1 + nx * offset, y1 + ny * offset)
            p1b = QPointF(x1 - nx * offset, y1 - ny * offset)
            p2a = QPointF(x2 + nx * offset, y2 + ny * offset)
            p2b = QPointF(x2 - nx * offset, y2 - ny * offset)
            painter.drawLine(p1a, p2a)
            painter.drawLine(p1b, p2b)
        elif shape_type in ('doubleline_arc', 'center_arc'):
            cx, cy, radius, start_angle, span_angle = shape['params']
            painter.save()
            if shape_type == 'center_arc':
                pen = QPen(self.centerline_color)
                pen.setStyle(Qt.DashLine)
                painter.setPen(pen)
            rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
            painter.drawArc(rect, self._qt_angle(start_angle), self._qt_span(span_angle))
            painter.restore()
        elif shape_type == 'text':
            x, y, text, height, rotation = shape['params']
            if not text:
                return
            painter.save()
            font = QFont('Microsoft YaHei UI')
            size = float(height) if height and height > 0 else 12.0 * max(0.1, self.zoom_factor)
            font.setPixelSize(max(1, int(round(size))))
            painter.setFont(font)
            lines = str(text).splitlines() or [str(text)]
            metrics = painter.fontMetrics()
            line_height = metrics.height()
            if rotation:
                painter.translate(x, y)
                painter.rotate(rotation)
                for idx, line in enumerate(lines):
                    painter.drawText(0, int(idx * line_height), line)
            else:
                for idx, line in enumerate(lines):
                    painter.drawText(int(x), int(y + idx * line_height), line)
            painter.restore()

    def _draw_shape_geometry(self, painter, shape):
        shape_type = shape['type']
        if shape_type in ('line', 'centerline'):
            x1, y1, x2, y2 = shape['params']
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        elif shape_type == 'circle':
            cx, cy, radius = shape['params']
            painter.drawEllipse(int(cx - radius), int(cy - radius), int(2 * radius), int(2 * radius))
        elif shape_type == 'rect':
            x1, y1, x2, y2 = shape['params']
            painter.drawRect(int(min(x1, x2)), int(min(y1, y2)), abs(int(x2 - x1)), abs(int(y2 - y1)))
        elif shape_type == 'polyline':
            points, closed = shape['params']
            if len(points) < 2:
                return
            for index in range(len(points) - 1):
                x1, y1 = points[index]
                x2, y2 = points[index + 1]
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            if closed:
                x1, y1 = points[-1]
                x2, y2 = points[0]
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        elif shape_type == 'ellipse':
            x1, y1, x2, y2 = shape['params']
            painter.drawEllipse(int(min(x1, x2)), int(min(y1, y2)), abs(int(x2 - x1)), abs(int(y2 - y1)))
        elif shape_type == 'arc':
            x1, y1, x2, y2 = shape['params']
            rect = [int(min(x1, x2)), int(min(y1, y2)), abs(int(x2 - x1)), abs(int(y2 - y1))]
            painter.drawArc(*rect, 0 * 16, 180 * 16)
        elif shape_type in ('arc_angle', 'doubleline_arc', 'center_arc'):
            cx, cy, radius, start_angle, span_angle = shape['params']
            rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
            painter.drawArc(rect, self._qt_angle(start_angle), self._qt_span(span_angle))
        elif shape_type == 'center_mark':
            cx, cy, size = shape['params']
            half = size / 2.0
            painter.drawLine(int(cx - half), int(cy), int(cx + half), int(cy))
            painter.drawLine(int(cx), int(cy - half), int(cx), int(cy + half))
        elif shape_type == 'doubleline':
            x1, y1, x2, y2, width = shape['params']
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            if length == 0:
                return
            nx, ny = -dy / length, dx / length
            offset = width / 2
            p1a = QPointF(x1 + nx * offset, y1 + ny * offset)
            p1b = QPointF(x1 - nx * offset, y1 - ny * offset)
            p2a = QPointF(x2 + nx * offset, y2 + ny * offset)
            p2b = QPointF(x2 - nx * offset, y2 - ny * offset)
            painter.drawLine(p1a, p2a)
            painter.drawLine(p1b, p2b)
        elif shape_type == 'text':
            x, y, text, height, rotation = shape['params']
            if not text:
                return
            painter.save()
            font = QFont('Microsoft YaHei UI')
            size = float(height) if height and height > 0 else 12.0 * max(0.1, self.zoom_factor)
            font.setPixelSize(max(1, int(round(size))))
            painter.setFont(font)
            lines = str(text).splitlines() or [str(text)]
            metrics = painter.fontMetrics()
            line_height = metrics.height()
            if rotation:
                painter.translate(x, y)
                painter.rotate(rotation)
                for idx, line in enumerate(lines):
                    painter.drawText(0, int(idx * line_height), line)
            else:
                for idx, line in enumerate(lines):
                    painter.drawText(int(x), int(y + idx * line_height), line)
            painter.restore()

    def _draw_selection_highlight(self, painter):
        if not self.selected_indices:
            return
        pen = QPen(self.selection_color)
        pen.setStyle(Qt.DashLine)
        pen.setWidth(2)
        painter.save()
        painter.setPen(pen)
        for index in sorted(self.selected_indices):
            if 0 <= index < len(self.shapes):
                self._draw_shape_geometry(painter, self.shapes[index])
        painter.restore()

    def _draw_selection_rect(self, painter):
        rect = self._selection_rect()
        if rect is None:
            return
        pen = QPen(self.selection_color)
        pen.setStyle(Qt.DashLine)
        painter.save()
        painter.setPen(pen)
        fill = QColor(self.selection_color)
        fill.setAlpha(40)
        painter.setBrush(fill)
        painter.drawRect(rect)
        painter.restore()

    def _selection_rect(self):
        if self._selection_start is None or self._selection_end is None:
            return None
        x1 = self._selection_start.x()
        y1 = self._selection_start.y()
        x2 = self._selection_end.x()
        y2 = self._selection_end.y()
        return QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))

    def _selection_bounds(self):
        if self._selection_start is None or self._selection_end is None:
            return None
        x1 = self._selection_start.x()
        y1 = self._selection_start.y()
        x2 = self._selection_end.x()
        y2 = self._selection_end.y()
        return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)

    def _is_selection_mode(self):
        return self.current_tool in (None, "select")

    def _ensure_units_per_pixel(self):
        if self.units_per_pixel is None:
            width = max(1.0, float(self.width()))
            self.units_per_pixel = self.target_screen_width_units / width
        return self.units_per_pixel

    def _format_units(self, value):
        scale = self._ensure_units_per_pixel()
        return f"{value * scale:.0f}"

    def _draw_preview(self, painter):
        pen = QPen(self.preview_color)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)

        if self.current_tool == 'line' and self._start_pos and self._temp_pos:
            painter.drawLine(self._start_pos.x(), self._start_pos.y(), self._temp_pos.x(), self._temp_pos.y())
        elif self.current_tool == 'circle' and self._start_pos and self._temp_pos:
            dx = self._temp_pos.x() - self._start_pos.x()
            dy = self._temp_pos.y() - self._start_pos.y()
            radius = (dx * dx + dy * dy) ** 0.5
            painter.drawEllipse(self._start_pos.x() - radius, self._start_pos.y() - radius, radius * 2, radius * 2)
        elif self.current_tool == 'rect' and self._rect_first and self._temp_pos:
            x1, y1 = self._rect_first.x(), self._rect_first.y()
            x2, y2 = self._temp_pos.x(), self._temp_pos.y()
            painter.drawRect(int(min(x1, x2)), int(min(y1, y2)), abs(int(x2 - x1)), abs(int(y2 - y1)))
        elif self.current_tool == 'ellipse' and self._ellipse_first and self._temp_pos:
            x1, y1 = self._ellipse_first.x(), self._ellipse_first.y()
            x2, y2 = self._temp_pos.x(), self._temp_pos.y()
            painter.drawEllipse(int(min(x1, x2)), int(min(y1, y2)), abs(int(x2 - x1)), abs(int(y2 - y1)))
        elif self.current_tool == 'arc' and self._arc_first and self._temp_pos:
            x1, y1 = self._arc_first.x(), self._arc_first.y()
            x2, y2 = self._temp_pos.x(), self._temp_pos.y()
            rect = [int(min(x1, x2)), int(min(y1, y2)), abs(int(x2 - x1)), abs(int(y2 - y1))]
            painter.drawArc(*rect, 0 * 16, 180 * 16)
        elif self.current_tool == 'doubleline' and self._doubleline_first and self._temp_pos:
            import math
            x1, y1 = self._doubleline_first.x(), self._doubleline_first.y()
            x2, y2 = self._temp_pos.x(), self._temp_pos.y()
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            if length:
                nx, ny = -dy / length, dx / length
                offset = 5
                painter.drawLine(int(x1 + nx * offset), int(y1 + ny * offset), int(x2 + nx * offset), int(y2 + ny * offset))
                painter.drawLine(int(x1 - nx * offset), int(y1 - ny * offset), int(x2 - nx * offset), int(y2 - ny * offset))
        elif self.current_tool == 'polyline' and self._poly_points:
            points = self._poly_points + ([self._temp_pos] if self._temp_pos else [])
            for index in range(len(points) - 1):
                painter.drawLine(points[index].x(), points[index].y(), points[index + 1].x(), points[index + 1].y())

    def _draw_point_markers(self, painter):
        if not self._point_markers:
            return
        painter.save()
        painter.setFont(QFont('Microsoft YaHei UI', 8))
        painter.setPen(QPen(QColor(255, 224, 120)))
        metrics = painter.fontMetrics()
        padding = 16
        for marker in self._point_markers[-8:]:
            point = marker['point']
            text = marker['text']
            painter.drawEllipse(point, 2, 2)
            text_width = metrics.horizontalAdvance(text)
            text_x = max(2, point.x() - text_width - padding)
            painter.drawText(int(text_x), int(point.y() - 8), text)
        painter.restore()

    def _draw_grid(self, painter):
        step = max(5, int(self.grid_step))
        painter.setPen(QPen(self.grid_color))
        for x in range(0, self.width(), step):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), step):
            painter.drawLine(0, y, self.width(), y)

    def _draw_axes(self, painter):
        margin = 30
        length = 60
        origin = QPointF(margin, self.height() - margin)
        painter.save()
        pen = QPen(QColor(200, 200, 200))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(origin.x(), origin.y(), origin.x() + length, origin.y())
        painter.drawLine(origin.x(), origin.y(), origin.x(), origin.y() - length)
        arrow = 6
        painter.drawLine(origin.x() + length, origin.y(), origin.x() + length - arrow, origin.y() - arrow)
        painter.drawLine(origin.x() + length, origin.y(), origin.x() + length - arrow, origin.y() + arrow)
        painter.drawLine(origin.x(), origin.y() - length, origin.x() - arrow, origin.y() - length + arrow)
        painter.drawLine(origin.x(), origin.y() - length, origin.x() + arrow, origin.y() - length + arrow)
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        painter.drawText(origin.x() + length + 6, origin.y() + 4, "X")
        painter.drawText(origin.x() - 12, origin.y() - length - 4, "Y")
        painter.restore()

    def set_theme(self, background=None, grid=None, drawing=None, preview=None):
        if background is not None:
            self.background_color = QColor(background)
        if grid is not None:
            self.grid_color = QColor(grid)
        if drawing is not None:
            self.drawing_color = QColor(drawing)
        if preview is not None:
            self.preview_color = QColor(preview)
        self.update()

    def set_active_layer(self, layer):
        if not layer:
            return
        self.active_layer = {
            "name": layer.get("name", self.active_layer.get("name", "0")),
            "color": layer.get("color", self.active_layer.get("color", "白")),
            "linetype": layer.get("linetype", self.active_layer.get("linetype", "continuous")),
            "lineweight": layer.get("lineweight", self.active_layer.get("lineweight", "0.25")),
        }

    def _color_from_name(self, name):
        if not name:
            return None
        key = str(name).strip().lower()
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

    def _lineweight_to_width(self, value):
        try:
            text = str(value).strip().lower().replace("mm", "")
            weight = float(text)
        except (TypeError, ValueError):
            return 1
        if weight <= 0:
            return 1
        return max(1, int(round(weight * 4)))

    def _linetype_to_penstyle(self, value):
        key = str(value or "").strip().lower()
        if "dash" in key:
            return Qt.DashLine
        if "center" in key:
            return Qt.DashDotLine
        if "phantom" in key:
            return Qt.DashDotDotLine
        return Qt.SolidLine

    def _apply_style_pen(self, painter, style):
        color = None
        width = 1
        pen_style = Qt.SolidLine
        if style:
            color = self._color_from_name(style.get("color"))
            width = self._lineweight_to_width(style.get("lineweight"))
            pen_style = self._linetype_to_penstyle(style.get("linetype"))
        pen = QPen(color or self.drawing_color)
        pen.setWidth(width)
        pen.setStyle(pen_style)
        painter.setPen(pen)

    def _append_shape(self, shape):
        if "layer" not in shape:
            shape["layer"] = self.active_layer.get("name", "0")
        if "style" not in shape:
            shape["style"] = {
                "color": self.active_layer.get("color", "白"),
                "linetype": self.active_layer.get("linetype", "continuous"),
                "lineweight": self.active_layer.get("lineweight", "0.25"),
            }
        self.shapes.append(shape)
        return len(self.shapes) - 1

    def add_line(self, x1, y1, x2, y2):
        self._push_undo()
        self._append_shape({'type': 'line', 'params': (x1, y1, x2, y2)})
        self.update()

    def add_centerline(self, x1, y1, x2, y2):
        self._push_undo()
        self._append_shape({'type': 'centerline', 'params': (x1, y1, x2, y2)})
        self._last_centerline_index = len(self.shapes) - 1
        self.update()

    def add_circle(self, cx, cy, radius):
        self._push_undo()
        self._append_shape({'type': 'circle', 'params': (cx, cy, radius)})
        self.update()

    def add_rect(self, x1, y1, x2, y2):
        self._push_undo()
        self._append_shape({'type': 'rect', 'params': (x1, y1, x2, y2)})
        self.update()

    def add_ellipse(self, x1, y1, x2, y2):
        self._push_undo()
        self._append_shape({'type': 'ellipse', 'params': (x1, y1, x2, y2)})
        self.update()

    def add_arc(self, x1, y1, x2, y2):
        self._push_undo()
        self._append_shape({'type': 'arc', 'params': (x1, y1, x2, y2)})
        self.update()

    def add_arc_angle(self, cx, cy, radius, start_angle, span_angle):
        self._push_undo()
        self._append_shape({'type': 'arc_angle', 'params': (cx, cy, radius, start_angle, span_angle)})
        end_angle = start_angle + span_angle
        end_point = (
            cx + math.cos(math.radians(end_angle)) * radius,
            cy + math.sin(math.radians(end_angle)) * radius,
        )
        self._last_arc_end = QPointF(end_point[0], end_point[1])
        self.update()

    def add_polyline(self, points, closed=False):
        if len(points) < 2:
            return
        self._push_undo()
        normalized = []
        for point in points:
            if isinstance(point, QPointF):
                normalized.append((point.x(), point.y()))
            else:
                normalized.append((float(point[0]), float(point[1])))
        self._append_shape({'type': 'polyline', 'params': (tuple(normalized), bool(closed))})
        self.update()

    def add_center_mark(self, cx, cy, size=8.0):
        self._push_undo()
        self._append_shape({'type': 'center_mark', 'params': (cx, cy, size)})
        self.update()

    def add_doubleline(self, x1, y1, x2, y2, width=10):
        self._push_undo()
        center_index = self._append_shape({'type': 'centerline', 'params': (x1, y1, x2, y2)})
        double_index = self._append_shape({'type': 'doubleline', 'params': (x1, y1, x2, y2, width)})
        self._last_centerline_index = center_index
        self._last_doubleline_segment_index = double_index
        self.update()

    def add_doubleline_segment(self, x1, y1, x2, y2, width=10, previous_point=None):
        self._push_undo()
        prev_center_idx = self._last_centerline_index
        prev_double_idx = self._last_doubleline_segment_index

        center_index = self._append_shape({'type': 'centerline', 'params': (x1, y1, x2, y2)})
        double_index = self._append_shape({'type': 'doubleline', 'params': (x1, y1, x2, y2, width)})

        if previous_point is not None and prev_center_idx is not None and prev_double_idx is not None:
            px, py = previous_point
            for connector in self._doubleline_corner_segments(
                px, py, x1, y1, x2, y2, width, prev_center_idx, prev_double_idx, center_index, double_index
            ):
                self._append_shape(connector)

        self._last_centerline_index = center_index
        self._last_doubleline_segment_index = double_index
        self.update()

    def _offset_pair(self, x1, y1, x2, y2, width):
        import math
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length == 0:
            return None
        nx = -dy / length
        ny = dx / length
        offset = width / 2
        return {
            'left_start': (x1 + nx * offset, y1 + ny * offset),
            'left_end': (x2 + nx * offset, y2 + ny * offset),
            'right_start': (x1 - nx * offset, y1 - ny * offset),
            'right_end': (x2 - nx * offset, y2 - ny * offset),
        }

    def _line_intersection(self, a1, a2, b1, b2):
        x1, y1 = a1
        x2, y2 = a2
        x3, y3 = b1
        x4, y4 = b2
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-6:
            return None
        det1 = x1 * y2 - y1 * x2
        det2 = x3 * y4 - y3 * x4
        px = (det1 * (x3 - x4) - (x1 - x2) * det2) / den
        py = (det1 * (y3 - y4) - (y1 - y2) * det2) / den
        return (px, py)

    def _unit_vector(self, x, y):
        length = math.hypot(x, y)
        if length < 1e-6:
            return None
        return (x / length, y / length)

    def _to_math_coords(self, x, y):
        return (x, -y)

    def _to_screen_coords(self, x, y):
        return (x, -y)

    def _fillet_arc_geometry(self, x0, y0, x1, y1, x2, y2, radius):
        p0 = self._to_math_coords(x0, y0)
        p1 = self._to_math_coords(x1, y1)
        p2 = self._to_math_coords(x2, y2)

        v_in = (p1[0] - p0[0], p1[1] - p0[1])
        v_out = (p2[0] - p1[0], p2[1] - p1[1])
        prev_len = math.hypot(*v_in)
        next_len = math.hypot(*v_out)
        if prev_len < 1e-6 or next_len < 1e-6:
            return None

        incoming = (v_in[0] / prev_len, v_in[1] / prev_len)
        outgoing = (v_out[0] / next_len, v_out[1] / next_len)
        dot = max(-1.0, min(1.0, incoming[0] * outgoing[0] + incoming[1] * outgoing[1]))
        theta = math.acos(dot)
        if theta < math.radians(5) or abs(theta - math.pi) < math.radians(1):
            return None

        tan_half = math.tan(theta / 2.0)
        if abs(tan_half) < 1e-6:
            return None

        max_radius_prev = prev_len / tan_half
        max_radius_next = next_len / tan_half
        effective_radius = min(radius, max_radius_prev, max_radius_next)
        if effective_radius < 1e-3:
            return None
        radius = effective_radius

        turn_cross = incoming[0] * outgoing[1] - incoming[1] * outgoing[0]
        turn_sign = 1 if turn_cross > 0 else -1

        normal_prev = (-turn_sign * incoming[1], turn_sign * incoming[0])
        normal_next = (-turn_sign * outgoing[1], turn_sign * outgoing[0])

        offset_prev = (p1[0] + normal_prev[0] * radius, p1[1] + normal_prev[1] * radius)
        offset_next = (p1[0] + normal_next[0] * radius, p1[1] + normal_next[1] * radius)

        def _intersect(point, direction, other_point, other_direction):
            den = direction[0] * other_direction[1] - direction[1] * other_direction[0]
            if abs(den) < 1e-6:
                return None
            dx = other_point[0] - point[0]
            dy = other_point[1] - point[1]
            t = (dx * other_direction[1] - dy * other_direction[0]) / den
            return (point[0] + direction[0] * t, point[1] + direction[1] * t)

        center_math = _intersect(offset_prev, incoming, offset_next, outgoing)
        if center_math is None:
            return None

        start_math = (center_math[0] - normal_prev[0] * radius, center_math[1] - normal_prev[1] * radius)
        end_math = (center_math[0] - normal_next[0] * radius, center_math[1] - normal_next[1] * radius)

        start_angle = math.degrees(math.atan2(start_math[1] - center_math[1], start_math[0] - center_math[0]))
        end_angle = math.degrees(math.atan2(end_math[1] - center_math[1], end_math[0] - center_math[0]))
        span = end_angle - start_angle
        if turn_sign > 0 and span < 0:
            span += 360
        elif turn_sign < 0 and span > 0:
            span -= 360

        return {
            'start_point': self._to_screen_coords(*start_math),
            'end_point': self._to_screen_coords(*end_math),
            'center': self._to_screen_coords(*center_math),
            'radius': radius,
            'start_angle': start_angle,
            'span_angle': span,
        }

    def _qt_angle(self, angle_deg):
        return int(round(angle_deg * 16))

    def _qt_span(self, span_deg):
        return int(round(span_deg * 16))

    def _normalize_angle(self, value):
        angle = value % 360.0
        if angle < 0:
            angle += 360.0
        return angle

    def _doubleline_corner_segments(self, x0, y0, x1, y1, x2, y2, width, prev_center_idx, prev_double_idx, curr_center_idx, curr_double_idx):
        radius = width * self.pipe_radius_factor
        radius = max(width * 1.2, min(width * 1.5, radius))
        geometry = self._fillet_arc_geometry(x0, y0, x1, y1, x2, y2, radius)
        if geometry is None:
            return []

        prev_center = self.shapes[prev_center_idx]
        prev_double = self.shapes[prev_double_idx]
        curr_center = self.shapes[curr_center_idx]
        curr_double = self.shapes[curr_double_idx]

        px1, py1, _, _ = prev_center['params']
        prev_center['params'] = (px1, py1, geometry['start_point'][0], geometry['start_point'][1])
        pdx1, pdy1, _, _, prev_width = prev_double['params']
        prev_double['params'] = (pdx1, pdy1, geometry['start_point'][0], geometry['start_point'][1], prev_width)

        _, _, cx2, cy2 = curr_center['params']
        curr_center['params'] = (geometry['end_point'][0], geometry['end_point'][1], cx2, cy2)
        _, _, cdx2, cdy2, curr_width = curr_double['params']
        curr_double['params'] = (geometry['end_point'][0], geometry['end_point'][1], cdx2, cdy2, curr_width)

        cx, cy = geometry['center']
        start_angle = geometry['start_angle']
        span_angle = geometry['span_angle']
        shapes = [
            {'type': 'center_arc', 'params': (cx, cy, geometry['radius'], start_angle, span_angle)},
        ]
        outer_radius = geometry['radius'] + width / 2.0
        inner_radius = max(geometry['radius'] - width / 2.0, width * 0.25)
        shapes.append({'type': 'doubleline_arc', 'params': (cx, cy, outer_radius, start_angle, span_angle)})
        shapes.append({'type': 'doubleline_arc', 'params': (cx, cy, inner_radius, start_angle, span_angle)})

        def _cap_points(point):
            vx = point[0] - cx
            vy = point[1] - cy
            base = math.hypot(vx, vy)
            if base < 1e-6:
                return None
            ux = vx / base
            uy = vy / base
            outer_pt = (cx + ux * outer_radius, cy + uy * outer_radius)
            inner_pt = (cx + ux * inner_radius, cy + uy * inner_radius)
            return outer_pt, inner_pt

        start_cap = _cap_points(geometry['start_point'])
        end_cap = _cap_points(geometry['end_point'])
        if start_cap:
            shapes.append({'type': 'line', 'params': (start_cap[0][0], start_cap[0][1], start_cap[1][0], start_cap[1][1])})
        if end_cap:
            shapes.append({'type': 'line', 'params': (end_cap[0][0], end_cap[0][1], end_cap[1][0], end_cap[1][1])})
        return shapes

    def cancel_active_tool(self):
        self._start_pos = None
        self._temp_pos = None
        self._poly_points = []
        self._tool_points = []
        self._selection_start = None
        self._selection_end = None
        self._selecting = False
        self._moving_selection = False
        self._move_last_pos = None
        self._panning = False
        self._pan_last_pos = None
        self._pending_shape_index = None
        self._pending_second_index = None
        self._pending_value = None
        self._pending_array_params = None
        self._rect_first = None
        self._ellipse_first = None
        self._arc_first = None
        self._doubleline_first = None
        self._doubleline_prev = None
        self._last_centerline_index = None
        self._last_doubleline_segment_index = None
        self.update()


    def _scale_value(self, value, anchor, factor):
        return anchor + (value - anchor) * factor

    def _scale_point(self, point, anchor_x, anchor_y, factor):
        if point is None:
            return None
        return QPointF(
            self._scale_value(point.x(), anchor_x, factor),
            self._scale_value(point.y(), anchor_y, factor),
        )

    def _offset_point(self, point, dx, dy):
        if point is None:
            return None
        return QPointF(point.x() + dx, point.y() + dy)

    def _apply_pan(self, dx, dy):
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            return
        for shape in self.shapes:
            self._translate_shape(shape, dx, dy)
        self._start_pos = self._offset_point(self._start_pos, dx, dy)
        self._rect_first = self._offset_point(self._rect_first, dx, dy)
        self._ellipse_first = self._offset_point(self._ellipse_first, dx, dy)
        self._arc_first = self._offset_point(self._arc_first, dx, dy)
        self._doubleline_first = self._offset_point(self._doubleline_first, dx, dy)
        self._doubleline_prev = self._offset_point(self._doubleline_prev, dx, dy)
        self._selection_start = self._offset_point(self._selection_start, dx, dy)
        self._selection_end = self._offset_point(self._selection_end, dx, dy)
        self._poly_points = [self._offset_point(point, dx, dy) for point in self._poly_points]
        self._tool_points = [self._offset_point(point, dx, dy) for point in self._tool_points]
        moved_markers = []
        for marker in self._point_markers:
            point = self._offset_point(marker['point'], dx, dy)
            moved_markers.append({'point': point, 'text': marker['text']})
        self._point_markers = moved_markers
        self.update()

    def _zoom_shape(self, shape, anchor_x, anchor_y, factor):
        shape_type = shape['type']
        params = shape['params']
        if shape_type in ('line', 'rect', 'ellipse', 'arc'):
            x1, y1, x2, y2 = params
            shape['params'] = (
                self._scale_value(x1, anchor_x, factor),
                self._scale_value(y1, anchor_y, factor),
                self._scale_value(x2, anchor_x, factor),
                self._scale_value(y2, anchor_y, factor),
            )
        elif shape_type == 'centerline':
            x1, y1, x2, y2 = params
            shape['params'] = (
                self._scale_value(x1, anchor_x, factor),
                self._scale_value(y1, anchor_y, factor),
                self._scale_value(x2, anchor_x, factor),
                self._scale_value(y2, anchor_y, factor),
            )
        elif shape_type == 'circle':
            cx, cy, radius = params
            shape['params'] = (
                self._scale_value(cx, anchor_x, factor),
                self._scale_value(cy, anchor_y, factor),
                radius * factor,
            )
        elif shape_type == 'doubleline':
            x1, y1, x2, y2, width = params
            shape['params'] = (
                self._scale_value(x1, anchor_x, factor),
                self._scale_value(y1, anchor_y, factor),
                self._scale_value(x2, anchor_x, factor),
                self._scale_value(y2, anchor_y, factor),
                width * factor,
            )
        elif shape_type == 'polyline':
            points, closed = params
            scaled = tuple(
                (
                    self._scale_value(x, anchor_x, factor),
                    self._scale_value(y, anchor_y, factor),
                )
                for x, y in points
            )
            shape['params'] = (scaled, closed)
        elif shape_type == 'arc_angle':
            cx, cy, radius, start_angle, span_angle = params
            shape['params'] = (
                self._scale_value(cx, anchor_x, factor),
                self._scale_value(cy, anchor_y, factor),
                radius * factor,
                start_angle,
                span_angle,
            )
        elif shape_type == 'center_mark':
            cx, cy, size = params
            shape['params'] = (
                self._scale_value(cx, anchor_x, factor),
                self._scale_value(cy, anchor_y, factor),
                size * factor,
            )
        elif shape_type in ('doubleline_arc', 'center_arc'):
            cx, cy, radius, start_angle, span_angle = params
            shape['params'] = (
                self._scale_value(cx, anchor_x, factor),
                self._scale_value(cy, anchor_y, factor),
                radius * factor,
                start_angle,
                span_angle,
            )
        elif shape_type == 'text':
            x, y, text, height, rotation = params
            shape['params'] = (
                self._scale_value(x, anchor_x, factor),
                self._scale_value(y, anchor_y, factor),
                text,
                height * factor if height else height,
                rotation,
            )

    def _apply_zoom(self, factor, anchor):
        anchor_x = anchor.x()
        anchor_y = anchor.y()
        self.zoom_factor *= factor
        self.grid_step = max(5, min(200, self.grid_step * factor))
        for shape in self.shapes:
            self._zoom_shape(shape, anchor_x, anchor_y, factor)
        self._start_pos = self._scale_point(self._start_pos, anchor_x, anchor_y, factor)
        self._temp_pos = self._scale_point(self._temp_pos, anchor_x, anchor_y, factor)
        self._rect_first = self._scale_point(self._rect_first, anchor_x, anchor_y, factor)
        self._ellipse_first = self._scale_point(self._ellipse_first, anchor_x, anchor_y, factor)
        self._arc_first = self._scale_point(self._arc_first, anchor_x, anchor_y, factor)
        self._doubleline_first = self._scale_point(self._doubleline_first, anchor_x, anchor_y, factor)
        self._doubleline_prev = self._scale_point(self._doubleline_prev, anchor_x, anchor_y, factor)
        self._poly_points = [self._scale_point(point, anchor_x, anchor_y, factor) for point in self._poly_points]
        self._tool_points = [self._scale_point(point, anchor_x, anchor_y, factor) for point in self._tool_points]
        scaled_markers = []
        for marker in self._point_markers:
            point = self._scale_point(marker['point'], anchor_x, anchor_y, factor)
            scaled_markers.append({'point': point, 'text': marker['text']})
        self._point_markers = scaled_markers
        self.update()

    def set_tool(self, name):
        self.current_tool = name
        self.cancel_active_tool()
        draw_tools = {
            'line',
            'circle',
            'circle_center_radius',
            'circle_center_diameter',
            'circle_2_point',
            'circle_3_point',
            'circle_concentric',
            'circle_tan_tan_radius',
            'circle_tan_tan_tan',
            'arc',
            'arc_3_point',
            'arc_start_center_end',
            'arc_start_center_angle',
            'arc_start_center_length',
            'arc_start_end_angle',
            'arc_start_end_direction',
            'arc_start_end_radius',
            'arc_center_start_end',
            'arc_center_start_angle',
            'arc_center_start_length',
            'arc_continue',
            'polyline',
            'rect',
            'skew_rect',
            'polygon',
            'revision_cloud',
            'ring',
            'ellipse',
            'ellipse_arc',
            'doubleline',
            'center_mark',
            'center_axis_endpoint',
            'hatch',
            'hatch_gradient',
            'hatch_boundary',
            'hatch_outline',
        }
        if name in draw_tools:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        self.update()

    def mousePressEvent(self, event):
        self.setFocus()
        pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_last_pos = QPointF(pos)
            event.accept()
            return
        if event.button() == Qt.RightButton:
            cancel_tools = {
                'line',
                'circle',
                'circle_center_radius',
                'circle_center_diameter',
                'circle_2_point',
                'circle_3_point',
                'circle_concentric',
                'circle_tan_tan_radius',
                'circle_tan_tan_tan',
                'arc',
                'arc_3_point',
                'arc_start_center_end',
                'arc_start_center_angle',
                'arc_start_center_length',
                'arc_start_end_angle',
                'arc_start_end_direction',
                'arc_start_end_radius',
                'arc_center_start_end',
                'arc_center_start_angle',
                'arc_center_start_length',
                'arc_continue',
                'polyline',
                'rect',
                'skew_rect',
                'polygon',
                'revision_cloud',
                'ring',
                'ellipse',
                'ellipse_arc',
                'doubleline',
                'center_mark',
                'center_axis_endpoint',
                'hatch',
                'hatch_gradient',
                'hatch_boundary',
                'hatch_outline',
                'array',
                'array_rect',
                'array_path',
                'array_polar',
                'array_classic',
                'trim',
                'extend',
                'fillet',
                'chamfer',
                'break',
                'break_at_point',
                'align_tool',
                'align',
                'distribute',
            }
            if self.current_tool in cancel_tools:
                self.cancel_active_tool()
                return
            super().mousePressEvent(event)
            return
        if event.button() != Qt.LeftButton:
            return
        if self.current_tool == 'move':
            if not self.selected_indices:
                index = self._hit_test(pos)
                if index is None:
                    return
                self.selected_indices = {index}
            self._moving_selection = True
            self._move_last_pos = QPointF(pos)
            self._push_undo()
            self.update()
            return
        if self._is_selection_mode():
            self._selection_start = QPointF(pos)
            self._selection_end = QPointF(pos)
            self._selecting = True
            self.update()
            return
        self._register_point(pos)
        if self.current_tool == 'line':
            if not self._start_pos:
                self._start_pos = pos
            else:
                self.add_line(self._start_pos.x(), self._start_pos.y(), pos.x(), pos.y())
                self._start_pos = QPointF(pos)
                self._temp_pos = pos
        elif self.current_tool == 'circle':
            if not self._start_pos:
                self._start_pos = pos
            else:
                dx = pos.x() - self._start_pos.x()
                dy = pos.y() - self._start_pos.y()
                radius = (dx * dx + dy * dy) ** 0.5
                self.add_circle(self._start_pos.x(), self._start_pos.y(), radius)
                self._start_pos = None
                self._temp_pos = None
        elif self.current_tool == 'rect':
            if not self._rect_first:
                self._rect_first = pos
            else:
                self.add_rect(self._rect_first.x(), self._rect_first.y(), pos.x(), pos.y())
                self._rect_first = None
                self._temp_pos = None
        elif self.current_tool == 'ellipse':
            if not self._ellipse_first:
                self._ellipse_first = pos
            else:
                self.add_ellipse(self._ellipse_first.x(), self._ellipse_first.y(), pos.x(), pos.y())
                self._ellipse_first = None
                self._temp_pos = None
        elif self.current_tool == 'arc':
            if not self._arc_first:
                self._arc_first = pos
            else:
                self.add_arc(self._arc_first.x(), self._arc_first.y(), pos.x(), pos.y())
                self._arc_first = None
                self._temp_pos = None
        elif self.current_tool == 'doubleline':
            if not self._doubleline_first:
                self._doubleline_first = pos
            else:
                previous_point = None
                if self._doubleline_prev is not None:
                    previous_point = (self._doubleline_prev.x(), self._doubleline_prev.y())
                self.add_doubleline_segment(
                    self._doubleline_first.x(), self._doubleline_first.y(), pos.x(), pos.y(), width=10, previous_point=previous_point
                )
                self._doubleline_prev = QPointF(self._doubleline_first)
                self._doubleline_first = QPointF(pos)
                self._temp_pos = pos
        elif self.current_tool == 'polyline':
            self._poly_points.append(pos)
        elif self.current_tool == 'delete':
            index = self._hit_test(pos)
            if index is not None:
                self._push_undo()
                del self.shapes[index]
                self.update()
        elif self._handle_extended_tools(pos):
            pass
        else:
            super().mousePressEvent(event)

    def _handle_extended_tools(self, pos):
        tool = self.current_tool
        if tool in {
            'circle_center_radius',
            'circle_center_diameter',
            'circle_2_point',
            'circle_3_point',
            'circle_concentric',
            'circle_tan_tan_radius',
            'circle_tan_tan_tan',
        }:
            return self._handle_circle_tool(tool, pos)
        if tool in {
            'arc_3_point',
            'arc_start_center_end',
            'arc_start_center_angle',
            'arc_start_center_length',
            'arc_start_end_angle',
            'arc_start_end_direction',
            'arc_start_end_radius',
            'arc_center_start_end',
            'arc_center_start_angle',
            'arc_center_start_length',
            'arc_continue',
        }:
            return self._handle_arc_tool(tool, pos)
        if tool in {'skew_rect', 'polygon', 'revision_cloud', 'ring'}:
            return self._handle_polyline_tool(tool, pos)
        if tool in {'center_mark', 'center_axis_endpoint', 'ellipse_arc'}:
            return self._handle_center_tool(tool, pos)
        if tool in {'hatch', 'hatch_gradient', 'hatch_boundary', 'hatch_outline'}:
            return self._handle_hatch_tool(tool, pos)
        if tool in {'array', 'array_rect', 'array_path', 'array_polar', 'array_classic'}:
            return self._handle_array_tool(tool, pos)
        if tool in {'trim', 'extend'}:
            return self._handle_trim_extend(tool, pos)
        if tool in {'fillet', 'chamfer'}:
            return self._handle_fillet_chamfer(tool, pos)
        if tool in {'break', 'break_at_point'}:
            return self._handle_break_tool(tool, pos)
        if tool in {'align_tool', 'align', 'distribute'}:
            return self._handle_align_tool(tool, pos)
        return False

    def _append_tool_point(self, pos):
        point = QPointF(pos)
        self._tool_points.append(point)
        return self._tool_points

    def _circle_from_3_points(self, p1, p2, p3):
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
        if abs(d) < 1e-6:
            return None
        x1_sq = x1 * x1 + y1 * y1
        x2_sq = x2 * x2 + y2 * y2
        x3_sq = x3 * x3 + y3 * y3
        ux = (x1_sq * (y2 - y3) + x2_sq * (y3 - y1) + x3_sq * (y1 - y2)) / d
        uy = (x1_sq * (x3 - x2) + x2_sq * (x1 - x3) + x3_sq * (x2 - x1)) / d
        radius = math.hypot(ux - x1, uy - y1)
        return ux, uy, radius

    def _angle_delta_ccw(self, start, end):
        return (end - start) % 360.0

    def _span_from_start_end(self, start, end, ccw=True):
        delta = self._angle_delta_ccw(start, end)
        return delta if ccw else delta - 360.0

    def _arc_from_three_points(self, p1, p2, p3):
        circle = self._circle_from_3_points(p1, p2, p3)
        if circle is None:
            return None
        cx, cy, radius = circle
        start = math.degrees(math.atan2(p1[1] - cy, p1[0] - cx))
        mid = math.degrees(math.atan2(p2[1] - cy, p2[0] - cx))
        end = math.degrees(math.atan2(p3[1] - cy, p3[0] - cx))
        ccw_span = self._angle_delta_ccw(start, end)
        if self._angle_in_span(start, ccw_span, mid):
            span = ccw_span
        else:
            span = ccw_span - 360.0
        return cx, cy, radius, start, span

    def _project_point_on_segment(self, px, py, x1, y1, x2, y2):
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return 0.0, (x1, y1)
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        return t, (x1 + t * dx, y1 + t * dy)

    def _line_params(self, shape):
        if shape['type'] in ('line', 'centerline'):
            x1, y1, x2, y2 = shape['params']
            return x1, y1, x2, y2, None
        if shape['type'] == 'doubleline':
            x1, y1, x2, y2, width = shape['params']
            return x1, y1, x2, y2, width
        return None

    def _set_line_params(self, shape, x1, y1, x2, y2):
        if shape['type'] in ('line', 'centerline'):
            shape['params'] = (x1, y1, x2, y2)
        elif shape['type'] == 'doubleline':
            _, _, _, _, width = shape['params']
            shape['params'] = (x1, y1, x2, y2, width)

    def _handle_circle_tool(self, tool, pos):
        points = self._append_tool_point(pos)
        if tool in ('circle_center_radius',):
            if len(points) >= 2:
                center = points[0]
                edge = points[1]
                radius = math.hypot(edge.x() - center.x(), edge.y() - center.y())
                self.add_circle(center.x(), center.y(), radius)
                self._tool_points = []
        elif tool == 'circle_center_diameter':
            if len(points) >= 2:
                center = points[0]
                edge = points[1]
                radius = math.hypot(edge.x() - center.x(), edge.y() - center.y()) / 2.0
                self.add_circle(center.x(), center.y(), radius)
                self._tool_points = []
        elif tool == 'circle_2_point':
            if len(points) >= 2:
                p1 = points[0]
                p2 = points[1]
                cx = (p1.x() + p2.x()) / 2.0
                cy = (p1.y() + p2.y()) / 2.0
                radius = math.hypot(p2.x() - p1.x(), p2.y() - p1.y()) / 2.0
                self.add_circle(cx, cy, radius)
                self._tool_points = []
        elif tool in ('circle_3_point', 'circle_tan_tan_tan'):
            if len(points) >= 3:
                circle = self._circle_from_3_points(
                    (points[0].x(), points[0].y()),
                    (points[1].x(), points[1].y()),
                    (points[2].x(), points[2].y()),
                )
                if circle:
                    cx, cy, radius = circle
                    self.add_circle(cx, cy, radius)
                self._tool_points = []
        elif tool == 'circle_concentric':
            if len(points) >= 2:
                center = points[0]
                edge = points[1]
                radius = math.hypot(edge.x() - center.x(), edge.y() - center.y())
                count, ok = QInputDialog.getInt(self, "同心圆", "数量", 3, 1, 20)
                if not ok:
                    self._tool_points = []
                    return True
                spacing, ok = QInputDialog.getDouble(self, "同心圆", "间距", 10.0, 0.1, 10000.0, 2)
                if not ok:
                    self._tool_points = []
                    return True
                self._push_undo()
                for idx in range(count):
                    r = radius - idx * spacing
                    if r <= 0:
                        break
                    self._append_shape({'type': 'circle', 'params': (center.x(), center.y(), r)})
                self.update()
                self._tool_points = []
        elif tool == 'circle_tan_tan_radius':
            if len(points) == 2 and self._pending_value is None:
                radius, ok = QInputDialog.getDouble(self, "相切相切半径", "半径", 20.0, 0.1, 100000.0, 2)
                if not ok:
                    self._tool_points = []
                    return True
                self._pending_value = radius
                return True
            if len(points) >= 3 and self._pending_value is not None:
                p1 = points[0]
                p2 = points[1]
                side = points[2]
                radius = float(self._pending_value)
                d = math.hypot(p2.x() - p1.x(), p2.y() - p1.y())
                if d <= 1e-6 or radius < d / 2.0:
                    self._tool_points = []
                    self._pending_value = None
                    return True
                mx = (p1.x() + p2.x()) / 2.0
                my = (p1.y() + p2.y()) / 2.0
                ux = -(p2.y() - p1.y()) / d
                uy = (p2.x() - p1.x()) / d
                h = math.sqrt(max(radius * radius - (d / 2.0) ** 2, 0.0))
                c1 = (mx + ux * h, my + uy * h)
                c2 = (mx - ux * h, my - uy * h)
                dist1 = math.hypot(side.x() - c1[0], side.y() - c1[1])
                dist2 = math.hypot(side.x() - c2[0], side.y() - c2[1])
                cx, cy = c1 if dist1 <= dist2 else c2
                self.add_circle(cx, cy, radius)
                self._tool_points = []
                self._pending_value = None
        return True

    def _handle_arc_tool(self, tool, pos):
        if tool == 'arc_continue' and not self._tool_points and self._last_arc_end is not None:
            self._tool_points.append(QPointF(self._last_arc_end))
        points = self._append_tool_point(pos)
        if tool == 'arc_3_point':
            if len(points) >= 3:
                arc = self._arc_from_three_points(
                    (points[0].x(), points[0].y()),
                    (points[1].x(), points[1].y()),
                    (points[2].x(), points[2].y()),
                )
                if arc:
                    cx, cy, radius, start, span = arc
                    self.add_arc_angle(cx, cy, radius, start, span)
                self._tool_points = []
        elif tool in ('arc_start_center_end', 'arc_center_start_end'):
            if len(points) >= 3:
                if tool == 'arc_start_center_end':
                    start = points[0]
                    center = points[1]
                    end = points[2]
                else:
                    center = points[0]
                    start = points[1]
                    end = points[2]
                start_angle = math.degrees(math.atan2(start.y() - center.y(), start.x() - center.x()))
                end_angle = math.degrees(math.atan2(end.y() - center.y(), end.x() - center.x()))
                cross = (start.x() - center.x()) * (end.y() - center.y()) - (start.y() - center.y()) * (end.x() - center.x())
                span = self._span_from_start_end(start_angle, end_angle, ccw=cross > 0)
                radius = math.hypot(start.x() - center.x(), start.y() - center.y())
                self.add_arc_angle(center.x(), center.y(), radius, start_angle, span)
                self._tool_points = []
        elif tool in ('arc_start_center_angle', 'arc_start_center_length', 'arc_center_start_angle', 'arc_center_start_length'):
            if len(points) == 2 and self._pending_value is None:
                if 'angle' in tool:
                    value, ok = QInputDialog.getDouble(self, "圆弧角度", "角度(度)", 90.0, 1.0, 359.0, 2)
                else:
                    value, ok = QInputDialog.getDouble(self, "圆弧长度", "长度", 50.0, 0.1, 100000.0, 2)
                if not ok:
                    self._tool_points = []
                    return True
                self._pending_value = float(value)
                return True
            if len(points) >= 3 and self._pending_value is not None:
                if tool in ('arc_start_center_angle', 'arc_start_center_length'):
                    start = points[0]
                    center = points[1]
                    guide = points[2]
                else:
                    center = points[0]
                    start = points[1]
                    guide = points[2]
                radius = math.hypot(start.x() - center.x(), start.y() - center.y())
                if radius < 1e-6:
                    self._tool_points = []
                    self._pending_value = None
                    return True
                start_angle = math.degrees(math.atan2(start.y() - center.y(), start.x() - center.x()))
                direction = (guide.x() - center.x()) * (start.y() - center.y()) - (guide.y() - center.y()) * (start.x() - center.x())
                sign = 1.0 if direction < 0 else -1.0
                if 'angle' in tool:
                    span = sign * float(self._pending_value)
                else:
                    angle = math.degrees(float(self._pending_value) / radius)
                    span = sign * angle
                self.add_arc_angle(center.x(), center.y(), radius, start_angle, span)
                self._tool_points = []
                self._pending_value = None
        elif tool in ('arc_start_end_angle', 'arc_start_end_radius'):
            if len(points) == 2 and self._pending_value is None:
                if tool == 'arc_start_end_angle':
                    value, ok = QInputDialog.getDouble(self, "圆弧角度", "角度(度)", 90.0, 5.0, 175.0, 2)
                else:
                    value, ok = QInputDialog.getDouble(self, "圆弧半径", "半径", 50.0, 0.1, 100000.0, 2)
                if not ok:
                    self._tool_points = []
                    return True
                self._pending_value = float(value)
                return True
            if len(points) >= 3 and self._pending_value is not None:
                start = points[0]
                end = points[1]
                side = points[2]
                chord = math.hypot(end.x() - start.x(), end.y() - start.y())
                if chord < 1e-6:
                    self._tool_points = []
                    self._pending_value = None
                    return True
                mx = (start.x() + end.x()) / 2.0
                my = (start.y() + end.y()) / 2.0
                vx = end.x() - start.x()
                vy = end.y() - start.y()
                length = math.hypot(vx, vy)
                ux = -vy / length
                uy = vx / length
                if tool == 'arc_start_end_angle':
                    angle = math.radians(float(self._pending_value))
                    h = (chord / 2.0) / math.tan(angle / 2.0)
                    radius = chord / (2.0 * math.sin(angle / 2.0))
                else:
                    radius = float(self._pending_value)
                    if radius < chord / 2.0:
                        self._tool_points = []
                        self._pending_value = None
                        return True
                    h = math.sqrt(max(radius * radius - (chord / 2.0) ** 2, 0.0))
                c1 = (mx + ux * h, my + uy * h)
                c2 = (mx - ux * h, my - uy * h)
                dist1 = math.hypot(side.x() - c1[0], side.y() - c1[1])
                dist2 = math.hypot(side.x() - c2[0], side.y() - c2[1])
                cx, cy = c1 if dist1 <= dist2 else c2
                start_angle = math.degrees(math.atan2(start.y() - cy, start.x() - cx))
                end_angle = math.degrees(math.atan2(end.y() - cy, end.x() - cx))
                cross = (start.x() - cx) * (end.y() - cy) - (start.y() - cy) * (end.x() - cx)
                span = self._span_from_start_end(start_angle, end_angle, ccw=cross > 0)
                self.add_arc_angle(cx, cy, radius, start_angle, span)
                self._tool_points = []
                self._pending_value = None
        elif tool == 'arc_start_end_direction':
            if len(points) >= 3:
                start = points[0]
                end = points[1]
                direction = points[2]
                tx = direction.x() - start.x()
                ty = direction.y() - start.y()
                if abs(tx) < 1e-6 and abs(ty) < 1e-6:
                    self._tool_points = []
                    return True
                chord_mid = ((start.x() + end.x()) / 2.0, (start.y() + end.y()) / 2.0)
                chord_dx = end.x() - start.x()
                chord_dy = end.y() - start.y()
                if abs(chord_dx) < 1e-6 and abs(chord_dy) < 1e-6:
                    self._tool_points = []
                    return True
                tan_dx, tan_dy = tx, ty
                normal = (-tan_dy, tan_dx)
                chord_normal = (-chord_dy, chord_dx)
                intersect = self._line_intersection(
                    (start.x(), start.y()),
                    (start.x() + normal[0], start.y() + normal[1]),
                    (chord_mid[0], chord_mid[1]),
                    (chord_mid[0] + chord_normal[0], chord_mid[1] + chord_normal[1]),
                )
                if intersect is None:
                    self._tool_points = []
                    return True
                cx, cy = intersect
                radius = math.hypot(start.x() - cx, start.y() - cy)
                start_angle = math.degrees(math.atan2(start.y() - cy, start.x() - cx))
                end_angle = math.degrees(math.atan2(end.y() - cy, end.x() - cx))
                cross = (start.x() - cx) * (end.y() - cy) - (start.y() - cy) * (end.x() - cx)
                span = self._span_from_start_end(start_angle, end_angle, ccw=cross > 0)
                self.add_arc_angle(cx, cy, radius, start_angle, span)
                self._tool_points = []
        elif tool == 'arc_continue':
            if len(points) >= 3:
                arc = self._arc_from_three_points(
                    (points[0].x(), points[0].y()),
                    (points[1].x(), points[1].y()),
                    (points[2].x(), points[2].y()),
                )
                if arc:
                    cx, cy, radius, start, span = arc
                    self.add_arc_angle(cx, cy, radius, start, span)
                self._tool_points = []
        return True

    def _handle_polyline_tool(self, tool, pos):
        points = self._append_tool_point(pos)
        if tool == 'skew_rect':
            if len(points) >= 3:
                p0 = points[0]
                p1 = points[1]
                p2 = points[2]
                dx = p2.x() - p0.x()
                dy = p2.y() - p0.y()
                p3 = (p1.x() + dx, p1.y() + dy)
                p4 = (p0.x() + dx, p0.y() + dy)
                self.add_polyline(
                    [(p0.x(), p0.y()), (p1.x(), p1.y()), p3, p4],
                    closed=True,
                )
                self._tool_points = []
        elif tool == 'polygon':
            if len(points) >= 2:
                center = points[0]
                vertex = points[1]
                radius = math.hypot(vertex.x() - center.x(), vertex.y() - center.y())
                angle0 = math.atan2(vertex.y() - center.y(), vertex.x() - center.x())
                pts = []
                for idx in range(self._polygon_sides):
                    angle = angle0 + 2 * math.pi * idx / self._polygon_sides
                    pts.append((center.x() + radius * math.cos(angle), center.y() + radius * math.sin(angle)))
                self.add_polyline(pts, closed=True)
                self._tool_points = []
        elif tool == 'revision_cloud':
            if len(points) >= 2:
                p0 = points[0]
                p1 = points[1]
                min_x = min(p0.x(), p1.x())
                max_x = max(p0.x(), p1.x())
                min_y = min(p0.y(), p1.y())
                max_y = max(p0.y(), p1.y())
                width = max_x - min_x
                height = max_y - min_y
                step = max(8.0, min(width, height) / 6.0)
                pts = []
                x = min_x
                while x <= max_x:
                    pts.append((x, min_y + (step / 2.0) * math.sin((x - min_x) / step * math.pi)))
                    x += step
                y = min_y
                while y <= max_y:
                    pts.append((max_x + (step / 2.0) * math.sin((y - min_y) / step * math.pi), y))
                    y += step
                x = max_x
                while x >= min_x:
                    pts.append((x, max_y + (step / 2.0) * math.sin((x - min_x) / step * math.pi)))
                    x -= step
                y = max_y
                while y >= min_y:
                    pts.append((min_x + (step / 2.0) * math.sin((y - min_y) / step * math.pi), y))
                    y -= step
                self.add_polyline(pts, closed=True)
                self._tool_points = []
        elif tool == 'ring':
            if len(points) >= 3:
                center = points[0]
                outer = points[1]
                inner = points[2]
                outer_radius = math.hypot(outer.x() - center.x(), outer.y() - center.y())
                inner_radius = math.hypot(inner.x() - center.x(), inner.y() - center.y())
                if inner_radius > outer_radius:
                    inner_radius, outer_radius = outer_radius, inner_radius
                self._push_undo()
                self._append_shape({'type': 'circle', 'params': (center.x(), center.y(), outer_radius)})
                self._append_shape({'type': 'circle', 'params': (center.x(), center.y(), inner_radius)})
                self.update()
                self._tool_points = []
        return True

    def _handle_center_tool(self, tool, pos):
        points = self._append_tool_point(pos)
        if tool == 'center_mark':
            self.add_center_mark(points[0].x(), points[0].y())
            self._tool_points = []
        elif tool == 'center_axis_endpoint':
            if len(points) >= 2:
                p0 = points[0]
                p1 = points[1]
                self._push_undo()
                self._append_shape({'type': 'centerline', 'params': (p0.x(), p0.y(), p1.x(), p1.y())})
                self.update()
                self._tool_points = []
        elif tool == 'ellipse_arc':
            if len(points) >= 2:
                p0 = points[0]
                p1 = points[1]
                self.add_ellipse(p0.x(), p0.y(), p1.x(), p1.y())
                self._tool_points = []
        return True

    def _add_hatch_lines(self, x1, y1, x2, y2, spacing):
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)
        y = min_y
        while y <= max_y:
            self._append_shape({'type': 'line', 'params': (min_x, y, max_x, y)})
            y += spacing

    def _handle_hatch_tool(self, tool, pos):
        points = self._append_tool_point(pos)
        if len(points) >= 2:
            p0 = points[0]
            p1 = points[1]
            if tool in ('hatch', 'hatch_gradient'):
                spacing = 6.0 if tool == 'hatch' else 3.0
                self._push_undo()
                self._add_hatch_lines(p0.x(), p0.y(), p1.x(), p1.y(), spacing)
                self.update()
            else:
                self.add_rect(p0.x(), p0.y(), p1.x(), p1.y())
            self._tool_points = []
        return True

    def _clone_shape(self, shape):
        base = {}
        if shape['type'] == 'polyline':
            points, closed = shape['params']
            base = {'type': 'polyline', 'params': (tuple(points), closed)}
        else:
            base = {'type': shape['type'], 'params': shape['params']}
        if 'layer' in shape:
            base['layer'] = shape['layer']
        if 'style' in shape:
            base['style'] = dict(shape['style'])
        return base

    def _translate_shape(self, shape, dx, dy):
        shape_type = shape['type']
        params = shape['params']
        if shape_type in ('line', 'rect', 'ellipse', 'arc', 'centerline'):
            x1, y1, x2, y2 = params
            shape['params'] = (x1 + dx, y1 + dy, x2 + dx, y2 + dy)
        elif shape_type == 'circle':
            cx, cy, radius = params
            shape['params'] = (cx + dx, cy + dy, radius)
        elif shape_type == 'doubleline':
            x1, y1, x2, y2, width = params
            shape['params'] = (x1 + dx, y1 + dy, x2 + dx, y2 + dy, width)
        elif shape_type in ('doubleline_arc', 'center_arc', 'arc_angle'):
            cx, cy, radius, start_angle, span_angle = params
            shape['params'] = (cx + dx, cy + dy, radius, start_angle, span_angle)
        elif shape_type == 'polyline':
            points, closed = params
            moved = tuple((x + dx, y + dy) for x, y in points)
            shape['params'] = (moved, closed)
        elif shape_type == 'center_mark':
            cx, cy, size = params
            shape['params'] = (cx + dx, cy + dy, size)
        elif shape_type == 'text':
            x, y, text, height, rotation = params
            shape['params'] = (x + dx, y + dy, text, height, rotation)

    def _rotate_point(self, x, y, cx, cy, angle_deg):
        angle = math.radians(angle_deg)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        tx = x - cx
        ty = y - cy
        return cx + tx * cos_a - ty * sin_a, cy + tx * sin_a + ty * cos_a

    def _rotate_shape(self, shape, center, angle_deg):
        cx, cy = center
        shape_type = shape['type']
        params = shape['params']
        if shape_type in ('line', 'centerline'):
            x1, y1, x2, y2 = params
            p1 = self._rotate_point(x1, y1, cx, cy, angle_deg)
            p2 = self._rotate_point(x2, y2, cx, cy, angle_deg)
            shape['params'] = (p1[0], p1[1], p2[0], p2[1])
        elif shape_type == 'doubleline':
            x1, y1, x2, y2, width = params
            p1 = self._rotate_point(x1, y1, cx, cy, angle_deg)
            p2 = self._rotate_point(x2, y2, cx, cy, angle_deg)
            shape['params'] = (p1[0], p1[1], p2[0], p2[1], width)
        elif shape_type == 'circle':
            ox, oy, radius = params
            new_center = self._rotate_point(ox, oy, cx, cy, angle_deg)
            shape['params'] = (new_center[0], new_center[1], radius)
        elif shape_type in ('doubleline_arc', 'center_arc', 'arc_angle'):
            ox, oy, radius, start_angle, span_angle = params
            new_center = self._rotate_point(ox, oy, cx, cy, angle_deg)
            shape['params'] = (new_center[0], new_center[1], radius, start_angle + angle_deg, span_angle)
        elif shape_type == 'polyline':
            points, closed = params
            rotated = tuple(self._rotate_point(x, y, cx, cy, angle_deg) for x, y in points)
            shape['params'] = (rotated, closed)
        elif shape_type == 'center_mark':
            ox, oy, size = params
            new_center = self._rotate_point(ox, oy, cx, cy, angle_deg)
            shape['params'] = (new_center[0], new_center[1], size)
        else:
            return False
        return True

    def _shape_center(self, shape):
        shape_type = shape['type']
        params = shape['params']
        if shape_type in ('line', 'centerline'):
            x1, y1, x2, y2 = params
            return QPointF((x1 + x2) / 2.0, (y1 + y2) / 2.0)
        if shape_type == 'doubleline':
            x1, y1, x2, y2, _ = params
            return QPointF((x1 + x2) / 2.0, (y1 + y2) / 2.0)
        if shape_type == 'circle':
            cx, cy, _ = params
            return QPointF(cx, cy)
        if shape_type in ('rect', 'ellipse', 'arc'):
            x1, y1, x2, y2 = params
            return QPointF((x1 + x2) / 2.0, (y1 + y2) / 2.0)
        if shape_type in ('doubleline_arc', 'center_arc', 'arc_angle'):
            cx, cy, _, _, _ = params
            return QPointF(cx, cy)
        if shape_type == 'polyline':
            points, _ = params
            if not points:
                return None
            sx = sum(x for x, _ in points)
            sy = sum(y for _, y in points)
            return QPointF(sx / len(points), sy / len(points))
        if shape_type == 'center_mark':
            cx, cy, _ = params
            return QPointF(cx, cy)
        return None

    def _handle_array_tool(self, tool, pos):
        if self._pending_shape_index is None:
            index = self._hit_test(pos)
            if index is None:
                return True
            self._pending_shape_index = index
            if tool in ('array', 'array_rect', 'array_classic'):
                rows, ok = QInputDialog.getInt(self, "矩形阵列", "行数", 3, 1, 100)
                if not ok:
                    self._pending_shape_index = None
                    return True
                cols, ok = QInputDialog.getInt(self, "矩形阵列", "列数", 3, 1, 100)
                if not ok:
                    self._pending_shape_index = None
                    return True
                dx, ok = QInputDialog.getDouble(self, "矩形阵列", "列间距", 40.0, 0.1, 100000.0, 2)
                if not ok:
                    self._pending_shape_index = None
                    return True
                dy, ok = QInputDialog.getDouble(self, "矩形阵列", "行间距", 40.0, 0.1, 100000.0, 2)
                if not ok:
                    self._pending_shape_index = None
                    return True
                base = self.shapes[self._pending_shape_index]
                self._push_undo()
                for r in range(rows):
                    for c in range(cols):
                        if r == 0 and c == 0:
                            continue
                        clone = self._clone_shape(base)
                        self._translate_shape(clone, c * dx, r * dy)
                        self._append_shape(clone)
                self.update()
                self._pending_shape_index = None
            else:
                if tool == 'array_path':
                    count, ok = QInputDialog.getInt(self, "路径阵列", "数量", 5, 2, 200)
                    if not ok:
                        self._pending_shape_index = None
                        return True
                    spacing, ok = QInputDialog.getDouble(self, "路径阵列", "间距", 40.0, 0.1, 100000.0, 2)
                    if not ok:
                        self._pending_shape_index = None
                        return True
                    self._pending_array_params = ("path", count, spacing)
                elif tool == 'array_polar':
                    count, ok = QInputDialog.getInt(self, "环形阵列", "数量", 6, 2, 200)
                    if not ok:
                        self._pending_shape_index = None
                        return True
                    span, ok = QInputDialog.getDouble(self, "环形阵列", "角度(度)", 360.0, 5.0, 360.0, 1)
                    if not ok:
                        self._pending_shape_index = None
                        return True
                    self._pending_array_params = ("polar", count, span)
            return True
        if tool == 'array_path' and self._pending_array_params:
            _, count, spacing = self._pending_array_params
            base = self.shapes[self._pending_shape_index]
            base_center = self._shape_center(base)
            if base_center is None:
                self._pending_shape_index = None
                self._pending_array_params = None
                return True
            dx = pos.x() - base_center.x()
            dy = pos.y() - base_center.y()
            length = math.hypot(dx, dy)
            if length < 1e-6:
                self._pending_shape_index = None
                self._pending_array_params = None
                return True
            ux = dx / length
            uy = dy / length
            self._push_undo()
            for idx in range(1, count):
                clone = self._clone_shape(base)
                self._translate_shape(clone, ux * spacing * idx, uy * spacing * idx)
                self._append_shape(clone)
            self.update()
            self._pending_shape_index = None
            self._pending_array_params = None
            return True
        if tool == 'array_polar' and self._pending_array_params:
            _, count, span = self._pending_array_params
            center = (pos.x(), pos.y())
            base = self.shapes[self._pending_shape_index]
            self._push_undo()
            for idx in range(1, count):
                clone = self._clone_shape(base)
                angle = span * idx / count
                if not self._rotate_shape(clone, center, angle):
                    continue
                self._append_shape(clone)
            self.update()
            self._pending_shape_index = None
            self._pending_array_params = None
            return True
        return True

    def _handle_trim_extend(self, tool, pos):
        if self._pending_shape_index is None:
            index = self._hit_test(pos)
            if index is None:
                return True
            shape = self.shapes[index]
            if self._line_params(shape) is None:
                return True
            self._pending_shape_index = index
            return True
        boundary = self.shapes[self._pending_shape_index]
        boundary_params = self._line_params(boundary)
        if boundary_params is None:
            self._pending_shape_index = None
            return True
        target_index = self._hit_test(pos)
        if target_index is None:
            self._pending_shape_index = None
            return True
        target = self.shapes[target_index]
        target_params = self._line_params(target)
        if target_params is None:
            self._pending_shape_index = None
            return True
        bx1, by1, bx2, by2, _ = boundary_params
        tx1, ty1, tx2, ty2, _ = target_params
        intersect = self._line_intersection((bx1, by1), (bx2, by2), (tx1, ty1), (tx2, ty2))
        if intersect is None:
            self._pending_shape_index = None
            return True
        ix, iy = intersect
        if tool == 'trim':
            dist1 = math.hypot(pos.x() - tx1, pos.y() - ty1)
            dist2 = math.hypot(pos.x() - tx2, pos.y() - ty2)
            self._push_undo()
            if dist1 <= dist2:
                self._set_line_params(target, ix, iy, tx2, ty2)
            else:
                self._set_line_params(target, tx1, ty1, ix, iy)
            self.update()
        else:
            t, _ = self._project_point_on_segment(ix, iy, tx1, ty1, tx2, ty2)
            if t <= 1e-6 or t >= 1 - 1e-6:
                dist1 = math.hypot(pos.x() - tx1, pos.y() - ty1)
                dist2 = math.hypot(pos.x() - tx2, pos.y() - ty2)
                self._push_undo()
                if dist1 <= dist2:
                    self._set_line_params(target, ix, iy, tx2, ty2)
                else:
                    self._set_line_params(target, tx1, ty1, ix, iy)
                self.update()
        self._pending_shape_index = None
        return True

    def _handle_fillet_chamfer(self, tool, pos):
        if self._pending_shape_index is None:
            index = self._hit_test(pos)
            if index is None:
                return True
            shape = self.shapes[index]
            if self._line_params(shape) is None:
                return True
            if tool == 'fillet':
                radius, ok = QInputDialog.getDouble(self, "圆角", "半径", self._default_fillet_radius, 0.1, 100000.0, 2)
                if not ok:
                    return True
                self._pending_value = radius
            else:
                distance, ok = QInputDialog.getDouble(self, "倒角", "距离", self._default_chamfer_distance, 0.1, 100000.0, 2)
                if not ok:
                    return True
                self._pending_value = distance
            self._pending_shape_index = index
            return True
        first = self.shapes[self._pending_shape_index]
        second_index = self._hit_test(pos)
        if second_index is None or second_index == self._pending_shape_index:
            self._pending_shape_index = None
            self._pending_value = None
            return True
        second = self.shapes[second_index]
        line1 = self._line_params(first)
        line2 = self._line_params(second)
        if line1 is None or line2 is None:
            self._pending_shape_index = None
            self._pending_value = None
            return True
        x1, y1, x2, y2, _ = line1
        x3, y3, x4, y4, _ = line2
        intersect = self._line_intersection((x1, y1), (x2, y2), (x3, y3), (x4, y4))
        if intersect is None:
            self._pending_shape_index = None
            self._pending_value = None
            return True
        ix, iy = intersect
        if tool == 'fillet':
            radius = float(self._pending_value)
            p1 = (x1, y1) if math.hypot(x1 - ix, y1 - iy) > math.hypot(x2 - ix, y2 - iy) else (x2, y2)
            p2 = (x3, y3) if math.hypot(x3 - ix, y3 - iy) > math.hypot(x4 - ix, y4 - iy) else (x4, y4)
            geometry = self._fillet_arc_geometry(p1[0], p1[1], ix, iy, p2[0], p2[1], radius)
            if geometry is None:
                self._pending_shape_index = None
                self._pending_value = None
                return True
            self._push_undo()
            self._set_line_params(first, p1[0], p1[1], geometry['start_point'][0], geometry['start_point'][1])
            self._set_line_params(second, geometry['end_point'][0], geometry['end_point'][1], p2[0], p2[1])
            cx, cy = geometry['center']
            self._append_shape({
                'type': 'arc_angle',
                'params': (cx, cy, geometry['radius'], geometry['start_angle'], geometry['span_angle']),
            })
            self.update()
        else:
            distance = float(self._pending_value)
            v1x = x1 - ix
            v1y = y1 - iy
            v2x = x2 - ix
            v2y = y2 - iy
            if math.hypot(v1x, v1y) < math.hypot(v2x, v2y):
                v1x, v1y = v2x, v2y
            v3x = x3 - ix
            v3y = y3 - iy
            v4x = x4 - ix
            v4y = y4 - iy
            if math.hypot(v3x, v3y) < math.hypot(v4x, v4y):
                v3x, v3y = v4x, v4y
            len1 = math.hypot(v1x, v1y)
            len2 = math.hypot(v3x, v3y)
            if len1 < 1e-6 or len2 < 1e-6:
                self._pending_shape_index = None
                self._pending_value = None
                return True
            p1x = ix + (v1x / len1) * distance
            p1y = iy + (v1y / len1) * distance
            p2x = ix + (v3x / len2) * distance
            p2y = iy + (v3y / len2) * distance
            self._push_undo()
            self._set_line_params(first, p1x, p1y, x2 if math.hypot(x2 - ix, y2 - iy) > math.hypot(x1 - ix, y1 - iy) else x1, y2 if math.hypot(x2 - ix, y2 - iy) > math.hypot(x1 - ix, y1 - iy) else y1)
            self._set_line_params(second, p2x, p2y, x4 if math.hypot(x4 - ix, y4 - iy) > math.hypot(x3 - ix, y3 - iy) else x3, y4 if math.hypot(x4 - ix, y4 - iy) > math.hypot(x3 - ix, y3 - iy) else y3)
            self._append_shape({'type': 'line', 'params': (p1x, p1y, p2x, p2y)})
            self.update()
        self._pending_shape_index = None
        self._pending_value = None
        return True

    def _handle_break_tool(self, tool, pos):
        index = self._hit_test(pos)
        if index is None:
            return True
        shape = self.shapes[index]
        params = self._line_params(shape)
        if params is None:
            return True
        x1, y1, x2, y2, _ = params
        if tool == 'break_at_point':
            t, (bx, by) = self._project_point_on_segment(pos.x(), pos.y(), x1, y1, x2, y2)
            if t <= 1e-3 or t >= 1 - 1e-3:
                return True
            self._push_undo()
            self._set_line_params(shape, x1, y1, bx, by)
            self._append_shape({'type': 'line', 'params': (bx, by, x2, y2)})
            self.update()
            return True
        if self._pending_shape_index is None:
            t, (bx, by) = self._project_point_on_segment(pos.x(), pos.y(), x1, y1, x2, y2)
            if t <= 1e-3 or t >= 1 - 1e-3:
                return True
            self._pending_shape_index = index
            self._pending_value = (bx, by)
            return True
        if index != self._pending_shape_index:
            self._pending_shape_index = None
            self._pending_value = None
            return True
        bx1, by1 = self._pending_value
        t1, _ = self._project_point_on_segment(bx1, by1, x1, y1, x2, y2)
        t2, (bx2, by2) = self._project_point_on_segment(pos.x(), pos.y(), x1, y1, x2, y2)
        if abs(t1 - t2) < 1e-3:
            self._pending_shape_index = None
            self._pending_value = None
            return True
        if t1 > t2:
            t1, t2 = t2, t1
            bx1, by1, bx2, by2 = bx2, by2, bx1, by1
        self._push_undo()
        self._set_line_params(shape, x1, y1, bx1, by1)
        self._append_shape({'type': 'line', 'params': (bx2, by2, x2, y2)})
        self.update()
        self._pending_shape_index = None
        self._pending_value = None
        return True

    def _handle_align_tool(self, tool, pos):
        if tool == 'distribute':
            if self._pending_shape_index is None:
                index = self._hit_test(pos)
                if index is None:
                    return True
                self._pending_shape_index = index
                return True
            start_shape = self.shapes[self._pending_shape_index]
            end_index = self._hit_test(pos)
            if end_index is None or end_index == self._pending_shape_index:
                self._pending_shape_index = None
                return True
            end_shape = self.shapes[end_index]
            start_center = self._shape_center(start_shape)
            end_center = self._shape_center(end_shape)
            if start_center is None or end_center is None:
                self._pending_shape_index = None
                return True
            vx = end_center.x() - start_center.x()
            vy = end_center.y() - start_center.y()
            length = math.hypot(vx, vy)
            if length < 1e-6:
                self._pending_shape_index = None
                return True
            ux = vx / length
            uy = vy / length
            candidates = []
            for idx, shape in enumerate(self.shapes):
                center = self._shape_center(shape)
                if center is None:
                    continue
                proj = (center.x() - start_center.x()) * ux + (center.y() - start_center.y()) * uy
                candidates.append((proj, idx, center))
            candidates.sort(key=lambda item: item[0])
            if len(candidates) < 3:
                self._pending_shape_index = None
                return True
            self._push_undo()
            step = length / (len(candidates) - 1)
            for i, (_, idx, center) in enumerate(candidates):
                target_x = start_center.x() + ux * step * i
                target_y = start_center.y() + uy * step * i
                dx = target_x - center.x()
                dy = target_y - center.y()
                self._translate_shape(self.shapes[idx], dx, dy)
            self.update()
            self._pending_shape_index = None
            return True
        if self._pending_shape_index is None:
            index = self._hit_test(pos)
            if index is None:
                return True
            self._pending_shape_index = index
            return True
        ref_shape = self.shapes[self._pending_shape_index]
        target_index = self._hit_test(pos)
        if target_index is None or target_index == self._pending_shape_index:
            self._pending_shape_index = None
            return True
        target_shape = self.shapes[target_index]
        ref_center = self._shape_center(ref_shape)
        target_center = self._shape_center(target_shape)
        if ref_center is None or target_center is None:
            self._pending_shape_index = None
            return True
        dx = ref_center.x() - target_center.x()
        dy = ref_center.y() - target_center.y()
        self._push_undo()
        self._translate_shape(target_shape, dx, dy)
        self.update()
        self._pending_shape_index = None
        return True

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1.1 if delta > 0 else 1 / 1.1
        self._apply_zoom(factor, event.position() if hasattr(event, 'position') else event.pos())
        event.accept()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        self.pointer_info.emit(f'光标: X={self._format_units(pos.x())} Y={self._format_units(pos.y())}')
        if self._panning:
            if self._pan_last_pos is None:
                self._pan_last_pos = QPointF(pos)
                return
            dx = pos.x() - self._pan_last_pos.x()
            dy = pos.y() - self._pan_last_pos.y()
            self._apply_pan(dx, dy)
            self._pan_last_pos = QPointF(pos)
            return
        if self._moving_selection:
            if self._move_last_pos is None:
                self._move_last_pos = QPointF(pos)
                return
            dx = pos.x() - self._move_last_pos.x()
            dy = pos.y() - self._move_last_pos.y()
            if abs(dx) > 1e-6 or abs(dy) > 1e-6:
                for idx in sorted(self.selected_indices):
                    if 0 <= idx < len(self.shapes):
                        self._translate_shape(self.shapes[idx], dx, dy)
                self.update()
            self._move_last_pos = QPointF(pos)
            return
        self._temp_pos = pos
        if self._selecting and self._is_selection_mode():
            self._selection_end = QPointF(pos)
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._panning = False
            self._pan_last_pos = None
            event.accept()
            return
        if event.button() != Qt.LeftButton:
            super().mouseReleaseEvent(event)
            return
        if self._moving_selection:
            self._moving_selection = False
            self._move_last_pos = None
            self.update()
            return
        if not self._selecting or not self._is_selection_mode():
            super().mouseReleaseEvent(event)
            return
        pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        self._selection_end = QPointF(pos)
        bounds = self._selection_bounds()
        self._selecting = False
        if bounds is None:
            self._selection_start = None
            self._selection_end = None
            self.update()
            return
        x1, y1, x2, y2 = bounds
        drag_distance = abs(x2 - x1) + abs(y2 - y1)
        modifiers = event.modifiers()
        additive = bool(modifiers & (Qt.ControlModifier | Qt.ShiftModifier))
        if drag_distance <= 4:
            index = self._hit_test(pos)
            if index is None:
                if not additive:
                    self.selected_indices.clear()
            else:
                if additive:
                    if index in self.selected_indices:
                        self.selected_indices.remove(index)
                    else:
                        self.selected_indices.add(index)
                else:
                    self.selected_indices = {index}
        else:
            window_select = False
            if self._selection_start is not None and self._selection_end is not None:
                window_select = self._selection_end.x() >= self._selection_start.x()
            hit_indices = self._indices_in_rect(bounds, require_containment=window_select)
            if additive:
                self.selected_indices.update(hit_indices)
            else:
                self.selected_indices = set(hit_indices)
        self._selection_start = None
        self._selection_end = None
        self.update()

    def mouseDoubleClickEvent(self, event):
        if self.current_tool == 'polyline' and len(self._poly_points) >= 2:
            self._push_undo()
            for index in range(len(self._poly_points) - 1):
                p1 = self._poly_points[index]
                p2 = self._poly_points[index + 1]
                self._append_shape({'type': 'line', 'params': (p1.x(), p1.y(), p2.x(), p2.y())})
            self._poly_points = []
            self._temp_pos = None
            self.update()
        else:
            super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            if self.selected_indices:
                self._push_undo()
                for idx in sorted(self.selected_indices, reverse=True):
                    if 0 <= idx < len(self.shapes):
                        del self.shapes[idx]
                self.selected_indices.clear()
                self.update()
                event.accept()
                return
        if event.key() == Qt.Key_Escape and self.current_tool in (
            'line',
            'doubleline',
            'polyline',
            'circle_center_radius',
            'circle_center_diameter',
            'circle_2_point',
            'circle_3_point',
            'circle_concentric',
            'circle_tan_tan_radius',
            'circle_tan_tan_tan',
            'arc_3_point',
            'arc_start_center_end',
            'arc_start_center_angle',
            'arc_start_center_length',
            'arc_start_end_angle',
            'arc_start_end_direction',
            'arc_start_end_radius',
            'arc_center_start_end',
            'arc_center_start_angle',
            'arc_center_start_length',
            'arc_continue',
            'skew_rect',
            'polygon',
            'revision_cloud',
            'ring',
            'center_mark',
            'center_axis_endpoint',
            'ellipse_arc',
            'hatch',
            'hatch_gradient',
            'hatch_boundary',
            'hatch_outline',
            'array',
            'array_rect',
            'array_path',
            'array_polar',
            'array_classic',
            'trim',
            'extend',
            'fillet',
            'chamfer',
            'break',
            'break_at_point',
            'align_tool',
            'align',
            'distribute',
        ):
            self.cancel_active_tool()
            event.accept()
            return
        super().keyPressEvent(event)

    def _register_point(self, pos):
        track_tools = {
            'line',
            'circle',
            'circle_center_radius',
            'circle_center_diameter',
            'circle_2_point',
            'circle_3_point',
            'circle_concentric',
            'circle_tan_tan_radius',
            'circle_tan_tan_tan',
            'arc',
            'arc_3_point',
            'arc_start_center_end',
            'arc_start_center_angle',
            'arc_start_center_length',
            'arc_start_end_angle',
            'arc_start_end_direction',
            'arc_start_end_radius',
            'arc_center_start_end',
            'arc_center_start_angle',
            'arc_center_start_length',
            'arc_continue',
            'polyline',
            'rect',
            'skew_rect',
            'polygon',
            'revision_cloud',
            'ring',
            'ellipse',
            'ellipse_arc',
            'doubleline',
            'center_mark',
            'center_axis_endpoint',
            'hatch',
            'hatch_gradient',
            'hatch_boundary',
            'hatch_outline',
        }
        if self.current_tool in track_tools:
            text = f'({self._format_units(pos.x())}, {self._format_units(pos.y())})'
            self._point_markers.append({'point': QPointF(pos), 'text': text})
            self.point_info.emit(f'点坐标: X={self._format_units(pos.x())} Y={self._format_units(pos.y())}')
            self.update()

    def _distance_point_to_segment(self, px, py, x1, y1, x2, y2):
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        projx = x1 + t * dx
        projy = y1 + t * dy
        return ((px - projx) ** 2 + (py - projy) ** 2) ** 0.5

    def _angle_in_span(self, start_angle, span_angle, angle):
        start = self._normalize_angle(start_angle)
        end = self._normalize_angle(start_angle + span_angle)
        angle = self._normalize_angle(angle)
        if span_angle >= 0:
            if start <= end:
                return start <= angle <= end
            return angle >= start or angle <= end
        if start >= end:
            return end <= angle <= start
        return angle <= start or angle >= end

    def _arc_bounds(self, cx, cy, radius, start_angle, span_angle):
        angles = [start_angle, start_angle + span_angle]
        for candidate in (0.0, 90.0, 180.0, 270.0):
            if self._angle_in_span(start_angle, span_angle, candidate):
                angles.append(candidate)
        xs = [cx + math.cos(math.radians(a)) * radius for a in angles]
        ys = [cy + math.sin(math.radians(a)) * radius for a in angles]
        return min(xs), min(ys), max(xs), max(ys)

    def _shape_bounds(self, shape):
        shape_type = shape['type']
        if shape_type in ('line', 'centerline'):
            x1, y1, x2, y2 = shape['params']
            return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
        if shape_type == 'doubleline':
            x1, y1, x2, y2, width = shape['params']
            pad = width / 2.0
            return min(x1, x2) - pad, min(y1, y2) - pad, max(x1, x2) + pad, max(y1, y2) + pad
        if shape_type == 'circle':
            cx, cy, radius = shape['params']
            return cx - radius, cy - radius, cx + radius, cy + radius
        if shape_type in ('rect', 'ellipse', 'arc'):
            x1, y1, x2, y2 = shape['params']
            return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
        if shape_type == 'polyline':
            points, _ = shape['params']
            if not points:
                return None
            xs = [pt[0] for pt in points]
            ys = [pt[1] for pt in points]
            return min(xs), min(ys), max(xs), max(ys)
        if shape_type == 'center_mark':
            cx, cy, size = shape['params']
            half = size / 2.0
            return cx - half, cy - half, cx + half, cy + half
        if shape_type in ('arc_angle', 'doubleline_arc', 'center_arc'):
            cx, cy, radius, start_angle, span_angle = shape['params']
            return self._arc_bounds(cx, cy, radius, start_angle, span_angle)
        if shape_type == 'text':
            x, y, text, height, rotation = shape['params']
            if not text:
                return None
            size = float(height) if height and height > 0 else 12.0 * max(0.1, self.zoom_factor)
            size = max(0.2, size)
            lines = str(text).splitlines() or [str(text)]
            max_len = max((len(line) for line in lines), default=1)
            width = max_len * size * 0.6
            total_height = size * len(lines)
            return x, y - total_height, x + width, y
        return None

    def _indices_in_rect(self, rect_bounds, require_containment=False):
        rx1, ry1, rx2, ry2 = rect_bounds
        indices = []
        for idx, shape in enumerate(self.shapes):
            bounds = self._shape_bounds(shape)
            if bounds is None:
                continue
            bx1, by1, bx2, by2 = bounds
            if require_containment:
                if bx1 < rx1 or by1 < ry1 or bx2 > rx2 or by2 > ry2:
                    continue
            else:
                if bx2 < rx1 or bx1 > rx2 or by2 < ry1 or by1 > ry2:
                    continue
            indices.append(idx)
        return indices

    def _hit_test(self, pos, tol=6):
        for index in range(len(self.shapes) - 1, -1, -1):
            shape = self.shapes[index]
            if shape['type'] in ('line', 'centerline'):
                x1, y1, x2, y2 = shape['params']
                distance = self._distance_point_to_segment(pos.x(), pos.y(), x1, y1, x2, y2)
                if distance <= tol:
                    return index
            elif shape['type'] == 'doubleline':
                x1, y1, x2, y2, width = shape['params']
                distance = self._distance_point_to_segment(pos.x(), pos.y(), x1, y1, x2, y2)
                if distance <= tol + width / 2.0:
                    return index
            elif shape['type'] == 'circle':
                cx, cy, radius = shape['params']
                distance = ((pos.x() - cx) ** 2 + (pos.y() - cy) ** 2) ** 0.5
                if abs(distance - radius) <= tol:
                    return index
            elif shape['type'] == 'center_mark':
                cx, cy, size = shape['params']
                half = size / 2.0
                if abs(pos.x() - cx) <= half + tol and abs(pos.y() - cy) <= half + tol:
                    return index
            elif shape['type'] == 'text':
                bounds = self._shape_bounds(shape)
                if bounds is None:
                    continue
                x1, y1, x2, y2 = bounds
                if x1 - tol <= pos.x() <= x2 + tol and y1 - tol <= pos.y() <= y2 + tol:
                    return index
            elif shape['type'] == 'rect':
                x1, y1, x2, y2 = shape['params']
                min_x, max_x = min(x1, x2), max(x1, x2)
                min_y, max_y = min(y1, y2), max(y1, y2)
                edges = [
                    (min_x, min_y, max_x, min_y),
                    (max_x, min_y, max_x, max_y),
                    (max_x, max_y, min_x, max_y),
                    (min_x, max_y, min_x, min_y),
                ]
                for ex1, ey1, ex2, ey2 in edges:
                    distance = self._distance_point_to_segment(pos.x(), pos.y(), ex1, ey1, ex2, ey2)
                    if distance <= tol:
                        return index
            elif shape['type'] == 'polyline':
                points, closed = shape['params']
                if len(points) < 2:
                    continue
                for idx in range(len(points) - 1):
                    x1, y1 = points[idx]
                    x2, y2 = points[idx + 1]
                    distance = self._distance_point_to_segment(pos.x(), pos.y(), x1, y1, x2, y2)
                    if distance <= tol:
                        return index
                if closed and len(points) > 2:
                    x1, y1 = points[-1]
                    x2, y2 = points[0]
                    distance = self._distance_point_to_segment(pos.x(), pos.y(), x1, y1, x2, y2)
                    if distance <= tol:
                        return index
            elif shape['type'] == 'ellipse':
                x1, y1, x2, y2 = shape['params']
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0
                rx = abs(x2 - x1) / 2.0
                ry = abs(y2 - y1) / 2.0
                if rx > 1e-6 and ry > 1e-6:
                    nx = (pos.x() - cx) / rx
                    ny = (pos.y() - cy) / ry
                    value = (nx * nx + ny * ny) ** 0.5
                    if abs(value - 1.0) * max(rx, ry) <= tol:
                        return index
            elif shape['type'] == 'arc':
                x1, y1, x2, y2 = shape['params']
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0
                rx = abs(x2 - x1) / 2.0
                ry = abs(y2 - y1) / 2.0
                if rx > 1e-6 and ry > 1e-6:
                    nx = (pos.x() - cx) / rx
                    ny = (pos.y() - cy) / ry
                    value = (nx * nx + ny * ny) ** 0.5
                    if abs(value - 1.0) * max(rx, ry) <= tol:
                        return index
            elif shape['type'] in ('arc_angle', 'doubleline_arc', 'center_arc'):
                cx, cy, radius, start_angle, span_angle = shape['params']
                distance = ((pos.x() - cx) ** 2 + (pos.y() - cy) ** 2) ** 0.5
                if abs(distance - radius) <= tol:
                    angle = math.degrees(math.atan2(pos.y() - cy, pos.x() - cx))
                    if self._angle_in_span(start_angle, span_angle, angle):
                        return index
        return None

    def set_symmetry_mode(self, enabled):
        self.symmetry_mode = bool(enabled)
        self.update()

    def set_grid_spacing(self, spacing_x, spacing_y):
        avg = max(5, int((spacing_x + spacing_y) / 2))
        self.grid_step = avg
        self.update()

    def clear(self):
        self._push_undo()
        self.shapes.clear()
        self._point_markers.clear()
        self.selected_indices.clear()
        self._last_centerline_index = None
        self._last_doubleline_segment_index = None
        self.update()

    def to_dict(self):
        return {'shapes': self.shapes}

    def load_from_dict(self, data):
        self._push_undo()
        self.shapes = data.get('shapes', [])
        self._point_markers = []
        self.selected_indices.clear()
        self._last_centerline_index = None
        self._last_doubleline_segment_index = None
        self.update()

    def _push_undo(self):
        self._undo_stack.append([shape.copy() for shape in self.shapes])
        self._redo_stack.clear()

    def undo(self):
        if not self._undo_stack:
            return
        self._redo_stack.append([shape.copy() for shape in self.shapes])
        self.shapes = self._undo_stack.pop()
        self._last_centerline_index = None
        self._last_doubleline_segment_index = None
        self.selected_indices.clear()
        self.update()

    def redo(self):
        if not self._redo_stack:
            return
        self._undo_stack.append([shape.copy() for shape in self.shapes])
        self.shapes = self._redo_stack.pop()
        self._last_centerline_index = None
        self._last_doubleline_segment_index = None
        self.selected_indices.clear()
        self.update()
