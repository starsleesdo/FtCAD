import os
import sys
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from ui_main import MainWindow


def main():
    app = QApplication(sys.argv)
    icon_path = os.path.join(os.path.dirname(__file__), "icons", "绘图.svg")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
