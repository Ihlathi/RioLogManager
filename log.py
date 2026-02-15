import os
import sys
import paramiko
from stat import S_ISREG
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTextEdit, QLabel, QCheckBox, QFileDialog, 
                             QFrame, QDialog, QLineEdit, QFormLayout, QProgressBar)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QPropertyAnimation, QEasingCurve, QSettings, QSize, QTimer
from PyQt6.QtGui import QFont, QPixmap, QFontDatabase, QColor

# --- Mac Cocoa Fix ---
# This line prevents the "could not find cocoa" error by forcing the plugin path
import PyQt6
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(os.path.dirname(PyQt6.__file__), 'Qt6', 'plugins', 'platforms')

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
        self.setWindowTitle("Cavalier Sync Settings")
        self.setFixedSize(400, 250)
        self.settings = QSettings("CavalierRobotics", "LogSync")
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {LIGHT_BG};
                color: {TEXT_COLOR};
            }}
            QLabel {{
                color: {TEXT_COLOR};
                font-weight: bold;
            }}
            QLineEdit {{
                border: 1px solid {BORDER_COLOR};
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }}
            QPushButton {{
                background-color: {CAVALIER_BLUE};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {REGAL_BLUE};
            }}
        """)
        
        layout = QFormLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        self.ip_input = QLineEdit(self.settings.value("rio_ip", "10.6.19.2"))
        self.path_input = QLineEdit(self.settings.value("save_path", os.path.expanduser("~/Documents/619_Logs")))
        
        layout.addRow("RoboRIO IP:", self.ip_input)
        layout.addRow("Local Path:", self.path_input)
        
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save)
        layout.addRow(save_btn)

    def save(self):
        self.settings.setValue("rio_ip", self.ip_input.text())
        self.settings.setValue("save_path", self.path_input.text())
        self.accept()

class StorageMonitorWorker(QThread):
    status_updated = pyqtSignal(bool, str, str) # connected, usage_percent, raw_stats
    
    def __init__(self, ip):
        super().__init__()
        self.ip = ip
        self.running = True

    def run(self):
        while self.running:
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(self.ip, username="lvuser", password="", timeout=3)
                
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
            
            self.sleep(5) # Check every 5 seconds

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
        self.start_monitoring()

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
        QFontDatabase.addApplicationFont("OpenSans-Regular.ttf")
        QFontDatabase.addApplicationFont("Norwester.otf")

    def setup_ui(self):
        self.setWindowTitle("619 Log Tool")
        self.setMinimumSize(900, 500)
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {LIGHT_BG};
            }}
            QWidget {{
                color: {TEXT_COLOR};
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
        if os.path.exists("3840Wide.png"):
            self.logo.setPixmap(QPixmap("3840Wide.png").scaled(150, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.logo.setText("🛡️")
            self.logo.setStyleSheet("font-size: 40px;")
        
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_container.addWidget(self.logo)
        
        title_lbl = QLabel("LOG TOOL")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(f"font-family: 'Norwester'; font-size: 20px; color: {CAVALIER_BLUE}; margin-bottom: 5px;")
        logo_container.addWidget(title_lbl)
        
        # Divider - Back below logo and name
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        line.setStyleSheet(f"color: {BORDER_COLOR};")
        logo_container.addWidget(line)
        
        left_panel.addLayout(logo_container)

        # Storage Status Section (Simplified)
        storage_box = QFrame()
        storage_box.setStyleSheet(f"""
            QFrame {{
                background-color: {LIGHT_GRAY};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        storage_layout = QVBoxLayout(storage_box)
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
        status_layout = QVBoxLayout() # Temp layout removed, replaced with storage_layout
        storage_layout.addWidget(self.storage_bar)
        left_panel.addWidget(storage_box)

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
        
        settings_btn = QPushButton("Preferences")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {CAVALIER_BLUE};
                border: 1px solid {CAVALIER_BLUE};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {LIGHT_GRAY}; }}
        """)
        settings_btn.clicked.connect(self.open_settings)
        bottom_row.addWidget(settings_btn)
        
        left_panel.addLayout(bottom_row)
        
        layout.addWidget(left_widget)

        # RIGHT SIDE: Console
        right_panel = QVBoxLayout()
        console_lbl = QLabel("Activity Log")
        console_lbl.setStyleSheet(f"font-weight: bold; color: {ABBEY_GREY}; font-size: 12px; text-transform: uppercase;")
        right_panel.addWidget(console_lbl)

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
    app = QApplication(sys.argv)
    app.setFont(QFont("Open Sans", 10))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())