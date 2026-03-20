from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit


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
