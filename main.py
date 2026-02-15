import sys
from PyQt6.QtWidgets import QApplication
from log import MainWindow, QFont

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Open Sans", 10))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
