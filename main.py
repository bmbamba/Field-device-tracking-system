"""
main.py - Entry point for the Tracking Control Center.

Run from inside the tracking_system folder:
    py main.py
"""

import sys
import os

# Add the folder containing this script to Python's search path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from main_window import MainWindow
from PySide6.QtGui import QIcon


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Field Device Tracking System")
    # Set application icon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracking_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.setWindowIcon(QIcon(icon_path))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
