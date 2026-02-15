import os
import sys

_BASE_PATH = None

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    global _BASE_PATH
    if _BASE_PATH is None:
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            _BASE_PATH = sys._MEIPASS
        except Exception:
            _BASE_PATH = os.path.abspath(".")

    return os.path.join(_BASE_PATH, relative_path)

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTextEdit, QLabel, QCheckBox, QFileDialog, 
                             QFrame, QDialog, QLineEdit, QFormLayout, QProgressBar)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QPropertyAnimation, QEasingCurve, QSettings, QSize, QTimer
from PyQt6.QtGui import QFont, QPixmap, QFontDatabase, QColor, QIcon

# Branding Colors
CAVALIER_BLUE = "#0C2340"
CAVALIER_ORANGE = "#FF671F"
ABBEY_GREY = "#505759"
REGAL_BLUE = "#003A70"
LIGHT_BG = "#FDFDFD"
LIGHT_GRAY = "#F0F0F0"
BORDER_COLOR = "#D1D1D1"
TEXT_COLOR = "#2C3E50"

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setFixedSize(450, 320)
        self.settings = QSettings("CavalierRobotics", "LogSync")
        
        is_dark = self.settings.value("dark_mode", "false") == "true"
        bg_color = ABBEY_GREY if is_dark else LIGHT_BG
        txt_color = "white" if is_dark else TEXT_COLOR
        input_bg = "#2b2b2b" if is_dark else "white"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
                color: {txt_color};
            }}
            QLabel {{
                color: {'white' if is_dark else CAVALIER_BLUE};
                font-weight: bold;
                font-size: 13px;
            }}
            QLineEdit {{
                border: 1px solid {BORDER_COLOR if not is_dark else "#606060"};
                border-radius: 6px;
                padding: 8px;
                background-color: {input_bg};
                color: {txt_color};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {CAVALIER_ORANGE};
            }}
            QCheckBox {{
                color: {txt_color};
                font-weight: bold;
            }}
            QPushButton {{
                background-color: {CAVALIER_ORANGE};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Norwester';
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {REGAL_BLUE};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel("PREFERENCES")
        header.setStyleSheet(f"font-family: 'Norwester'; font-size: 18px; color: {CAVALIER_BLUE};")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        form = QFormLayout()
        form.setVerticalSpacing(15)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.ip_input = QLineEdit(self.settings.value("rio_ip", "10.6.19.2"))
        self.path_input = QLineEdit(self.settings.value("save_path", os.path.expanduser("~/Documents/619_Logs")))
        self.dark_mode_check = QCheckBox("Dark Mode")
        self.dark_mode_check.setChecked(self.settings.value("dark_mode", "false") == "true")
        
        form.addRow("RoboRIO IP:", self.ip_input)
        form.addRow("Save Location:", self.path_input)
        form.addRow("", self.dark_mode_check)
        
        layout.addLayout(form)
        layout.addStretch()
        
        save_btn = QPushButton("APPLY")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save)
        layout.addWidget(save_btn)

    def save(self):
        self.settings.setValue("rio_ip", self.ip_input.text())
        self.settings.setValue("save_path", self.path_input.text())
        self.settings.setValue("dark_mode", "true" if self.dark_mode_check.isChecked() else "false")
        self.accept()

class StorageMonitorWorker(QThread):
    status_updated = pyqtSignal(bool, str, str) # connected, usage_percent, raw_stats
    
    def __init__(self, ip):
        super().__init__()
        self.ip = ip
        self.running = True

    def run(self):
        import paramiko
        while self.running:
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(self.ip, username="lvuser", password="", timeout=2)
                
                # Get disk usage for /
                # Output format: Size Used Avail Use% Mounted
                stdin, stdout, stderr = ssh.exec_command("df -h / | tail -1 | awk '{print $2, $3, $5}'")
                stats = stdout.read().decode().strip().split()
                
                ssh.close()
                if len(stats) == 3:
                    total, used, percent = stats
                    self.status_updated.emit(True, percent.replace("%", ""), f"{used} / {total}")
                else:
                    self.status_updated.emit(True, "0", "0 / 0")
            except Exception:
                self.status_updated.emit(False, "0", "-- / --")
            
            # Use smaller increments for sleep to remain responsive to stop signal
            for _ in range(50): 
                if not self.running: break
                self.msleep(100)

    def stop(self):
        self.running = False

class SyncWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, ip, local_dir, delete_after):
        super().__init__()
        self.ip = ip
        self.local_dir = local_dir
        self.delete_after = delete_after

    def run(self):
        import paramiko
        from stat import S_ISREG
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.ip, username="lvuser", password="", timeout=5)
            sftp = ssh.open_sftp()
            
            files = sftp.listdir("/home/lvuser/akitlogs")
            if not os.path.exists(self.local_dir): os.makedirs(self.local_dir)

            count = 0
            for f in files:
                remote_path = f"/home/lvuser/akitlogs/{f}"
                local_path = os.path.join(self.local_dir, f)
                if S_ISREG(sftp.stat(remote_path).st_mode):
                    self.progress.emit(f"Pulling {f}...")
                    sftp.get(remote_path, local_path)
                    if self.delete_after: sftp.remove(remote_path)
                    count += 1
            
            sftp.close()
            ssh.close()
            self.finished.emit(count)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("CavalierRobotics", "LogSync")
        self.monitor_worker = None
        self.init_fonts()
        self.setup_ui()
        self.apply_theme()
        self.start_monitoring()

    def apply_theme(self):
        is_dark = self.settings.value("dark_mode", "false") == "true"
        bg_color = ABBEY_GREY if is_dark else LIGHT_BG
        txt_color = "white" if is_dark else TEXT_COLOR
        panel_bg = "#3E4446" if is_dark else LIGHT_GRAY
        border = "#606060" if is_dark else BORDER_COLOR
        contrast_blue = "#4A90E2" if is_dark else CAVALIER_BLUE
        
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {bg_color};
            }}
            QWidget {{
                color: {txt_color};
                font-family: 'Open Sans', 'Segoe UI', sans-serif;
            }}
            QCheckBox {{
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
        """)
        
        self.console.setStyleSheet(f"""
            QTextEdit {{
                background-color: {"#2b2b2b" if is_dark else "white"};
                border: 1px solid {border};
                border-radius: 10px;
                color: {txt_color};
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                padding: 10px;
            }}
        """)
        
        self.storage_box.setStyleSheet(f"""
            QFrame {{
                background-color: {panel_bg};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        
        self.settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {contrast_blue};
                border: 1px solid {contrast_blue};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {panel_bg}; }}
        """)
        
        self.status_text.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {'#CCCCCC' if is_dark else '#505759'};")
        self.title_lbl.setStyleSheet(f"font-family: 'Norwester'; font-size: 20px; color: {'white' if is_dark else CAVALIER_BLUE}; margin-bottom: 5px;")
        self.console_lbl.setStyleSheet(f"font-weight: bold; color: {'#AAAAAA' if is_dark else ABBEY_GREY}; font-size: 12px; text-transform: uppercase;")
        self.divider_line.setStyleSheet(f"background-color: {border}; height: 1px; border: none;")

    def start_monitoring(self):
        if self.monitor_worker:
            self.monitor_worker.stop()
            self.monitor_worker.wait()
        
        ip = self.settings.value("rio_ip", "10.6.19.2")
        self.monitor_worker = StorageMonitorWorker(ip)
        self.monitor_worker.status_updated.connect(self.update_status_ui)
        self.monitor_worker.start()

    def update_status_ui(self, connected, usage, raw):
        if connected:
            self.status_dot.setStyleSheet("background-color: #27AE60; border-radius: 6px;")
            self.status_text.setText("Connected")
            u_val = int(usage)
            self.storage_bar.setValue(u_val)
            self.usage_lbl.setText(raw)
            # Color change based on usage
            if u_val > 80:
                self.storage_bar.setStyleSheet(self.storage_bar.styleSheet().replace(CAVALIER_BLUE, "#C0392B"))
            else:
                self.storage_bar.setStyleSheet(self.storage_bar.styleSheet().replace("#C0392B", CAVALIER_BLUE))
        else:
            self.status_dot.setStyleSheet("background-color: #C0392B; border-radius: 6px;")
            self.status_text.setText("Offline")
            self.usage_lbl.setText("-- / --")
            self.storage_bar.setValue(0)

    def init_fonts(self):
        # Assumes fonts are in the same folder as the script
        QFontDatabase.addApplicationFont(resource_path("OpenSans-Regular.ttf"))
        QFontDatabase.addApplicationFont(resource_path("Norwester.otf"))

    def setup_ui(self):
        self.setWindowTitle("619 Log Tool")
        self.setWindowIcon(QIcon(resource_path("1024hat.png")))
        self.setMinimumSize(900, 500)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(25)

        # LEFT SIDE: Controls
        left_widget = QWidget()
        left_widget.setFixedWidth(240)
        left_panel = QVBoxLayout(left_widget)
        left_panel.setContentsMargins(0, 0, 0, 0)
        left_panel.setSpacing(15)
        
        # Logo & Header
        logo_container = QVBoxLayout()
        logo_container.setSpacing(5)
        
        self.logo = QLabel()
        logo_img_path = resource_path("3840Wide.png")
        if os.path.exists(logo_img_path):
            self.logo.setPixmap(QPixmap(logo_img_path).scaled(150, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.logo.setText("🛡️")
            self.logo.setStyleSheet("font-size: 40px;")
        
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_container.addWidget(self.logo)
        
        self.title_lbl = QLabel("LOG TOOL")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_lbl.setStyleSheet(f"font-family: 'Norwester'; font-size: 20px; color: {CAVALIER_BLUE}; margin-bottom: 5px;")
        logo_container.addWidget(self.title_lbl)
        
        # Divider - Back below logo and name
        self.divider_line = QFrame()
        self.divider_line.setFrameShape(QFrame.Shape.HLine)
        self.divider_line.setFrameShadow(QFrame.Shadow.Plain)
        logo_container.addWidget(self.divider_line)
        
        left_panel.addLayout(logo_container)

        # Storage Status Section (Simplified)
        self.storage_box = QFrame()
        storage_layout = QVBoxLayout(self.storage_box)
        storage_layout.setContentsMargins(5, 5, 5, 5)
        
        storage_header = QHBoxLayout()
        storage_header.addWidget(QLabel("RIO Storage:"))
        self.usage_lbl = QLabel("0 / 0")
        self.usage_lbl.setStyleSheet("font-size: 11px; font-weight: bold;")
        self.usage_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        storage_header.addWidget(self.usage_lbl)
        storage_layout.addLayout(storage_header)
        
        self.storage_bar = QProgressBar()
        self.storage_bar.setFixedHeight(8)
        self.storage_bar.setTextVisible(False)
        self.storage_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {BORDER_COLOR};
                border-radius: 4px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {CAVALIER_BLUE};
                border-radius: 4px;
            }}
        """)
        storage_layout.addWidget(self.storage_bar)
        left_panel.addWidget(self.storage_box)

        left_panel.addStretch()

        self.sync_btn = QPushButton("SYNC NOW")
        self.sync_btn.setFixedHeight(60)
        self.sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CAVALIER_ORANGE};
                color: white;
                border-radius: 8px;
                font-family: 'Norwester';
                font-size: 18px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{ background-color: {REGAL_BLUE}; }}
            QPushButton:disabled {{ background-color: {ABBEY_GREY}; color: #AAAAAA; }}
        """)
        self.sync_btn.clicked.connect(self.start_sync)
        left_panel.addWidget(self.sync_btn)

        self.del_check = QCheckBox("Clean RIO after sync")
        self.del_check.setChecked(True)
        self.del_check.setStyleSheet("font-size: 13px;")
        left_panel.addWidget(self.del_check)
        
        # Bottom Row: Connection Status (Dot) and Preferences
        bottom_row = QHBoxLayout()
        
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(12, 12)
        self.status_dot.setStyleSheet("background-color: #C0392B; border-radius: 6px;")
        bottom_row.addWidget(self.status_dot)
        
        self.status_text = QLabel("Offline")
        self.status_text.setStyleSheet("font-size: 11px; font-weight: bold; color: #505759;")
        bottom_row.addWidget(self.status_text)
        bottom_row.addStretch()
        
        self.settings_btn = QPushButton("Preferences")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self.open_settings)
        bottom_row.addWidget(self.settings_btn)
        
        left_panel.addLayout(bottom_row)
        
        layout.addWidget(left_widget)

        # RIGHT SIDE: Console
        right_panel = QVBoxLayout()
        self.console_lbl = QLabel("Activity Log")
        self.console_lbl.setStyleSheet(f"font-weight: bold; color: {ABBEY_GREY}; font-size: 12px; text-transform: uppercase;")
        right_panel.addWidget(self.console_lbl)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet(f"""
            QTextEdit {{
                background-color: white;
                border: 1px solid {BORDER_COLOR};
                border-radius: 10px;
                color: {TEXT_COLOR};
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                padding: 10px;
            }}
        """)
        right_panel.addWidget(self.console)
        layout.addLayout(right_panel, 3)

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self.apply_theme()
            self.start_monitoring()

    def start_sync(self):
        self.sync_btn.setEnabled(False)
        self.console.clear()
        self.console.append("<b style='color: #0C2340;'>Initializing connection...</b>")
        
        ip = self.settings.value("rio_ip", "10.6.19.2")
        path = self.settings.value("save_path", "./logs")
        
        self.worker = SyncWorker(ip, path, self.del_check.isChecked())
        self.worker.progress.connect(lambda m: self.console.append(f"<span style='color: #505759;'>• {m}</span>"))
        self.worker.finished.connect(self.on_sync_finished)
        self.worker.error.connect(self.on_sync_error)
        self.worker.start()

    def closeEvent(self, event):
        if self.monitor_worker:
            self.monitor_worker.stop()
            self.monitor_worker.wait()
        event.accept()

    def on_sync_finished(self, count):
        self.console.append(f"\n<b style='color: #27AE60;'>✓ Success: {count} logs synchronized.</b>")
        self.sync_btn.setEnabled(True)

    def on_sync_error(self, error):
        self.console.append(f"\n<b style='color: #C0392B;'>⚠ Error: {error}</b>")
        self.console.append("<span style='color: #E67E22;'>Please check RoboRIO IP and Network settings.</span>")
        self.sync_btn.setEnabled(True)

if __name__ == "__main__":
    # Internal dev test entry point
    import os
    if sys.platform == "darwin":
        import PyQt6
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(os.path.dirname(PyQt6.__file__), 'Qt6', 'plugins', 'platforms')
        
    app = QApplication(sys.argv)
    app.setFont(QFont("Open Sans", 10))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())