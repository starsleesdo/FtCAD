from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


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
