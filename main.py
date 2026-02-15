import sys
import os
from PyQt6.QtWidgets import QApplication

def setup_environment():
    """Sets up platform-specific environment variables."""
    if sys.platform == "darwin":
        # Mac Cocoa Fix: handles "could not find cocoa" error
        try:
            import PyQt6
            qt_path = os.path.join(os.path.dirname(PyQt6.__file__), 'Qt6', 'plugins', 'platforms')
            if os.path.exists(qt_path):
                os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_path
        except ImportError:
            pass

def main():
    setup_environment()
    from log import MainWindow, QFont
    app = QApplication(sys.argv)
    app.setFont(QFont("Open Sans", 10))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
