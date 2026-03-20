from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QSpinBox


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
