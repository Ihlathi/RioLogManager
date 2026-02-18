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
                             QFrame, QDialog, QLineEdit, QFormLayout, QProgressBar,
                             QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView, QMenu, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QPropertyAnimation, QEasingCurve, QSettings, QSize, QTimer, QDateTime
from PyQt6.QtGui import QFont, QPixmap, QFontDatabase, QColor, QIcon, QAction
import subprocess

class SortableTableWidgetItem(QTableWidgetItem):
    def __init__(self, text, sort_key):
        super().__init__(text)
        self.sort_key = sort_key

    def __lt__(self, other):
        if isinstance(other, SortableTableWidgetItem):
            return self.sort_key < other.sort_key
        return super().__lt__(other)

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
        self.setFixedSize(450, 420)
        self.settings = QSettings("CavalierRobotics", "LogSync")
        
        is_dark = self.settings.value("dark_mode", "false") == "true"
        bg_color = ABBEY_GREY if is_dark else LIGHT_BG
        txt_color = "white" if is_dark else TEXT_COLOR
        input_bg = "#2b2b2b" if is_dark else "white"
        panel_bg = "#3E4446" if is_dark else LIGHT_GRAY
        border = "#606060" if is_dark else BORDER_COLOR
        
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
            #browse_btn {{
                background-color: {panel_bg};
                color: {txt_color};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 12px;
                font-family: 'Open Sans';
                font-size: 11px;
                font-weight: bold;
                min-width: 60px;
            }}
            #browse_btn:hover {{
                background-color: {CAVALIER_ORANGE};
                color: white;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        header = QLabel("PREFERENCES")
        header.setStyleSheet(f"font-family: 'Norwester'; font-size: 18px; color: {CAVALIER_BLUE};")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        form = QFormLayout()
        form.setVerticalSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.ip_input = QLineEdit(self.settings.value("rio_ip", "10.6.19.2"))
        
        # Save Path with Browse
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit(self.settings.value("save_path", os.path.expanduser("~/Documents/619_Logs")))
        browse_path_btn = QPushButton("Browse")
        browse_path_btn.setObjectName("browse_btn")
        browse_path_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_path_btn.clicked.connect(self.select_save_path)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(browse_path_btn)
        
        self.robot_path_input = QLineEdit(self.settings.value("robot_path", "/home/lvuser/akitlogs"))
        
        # AS Path with Browse
        as_path_layout = QHBoxLayout()
        as_default = "AdvantageScope" if sys.platform == "darwin" else "AdvantageScope.exe"
        self.as_path_input = QLineEdit(self.settings.value("as_path", as_default))
        self.as_path_input.setPlaceholderText("Path to AdvantageScope")
        browse_as_btn = QPushButton("Browse")
        browse_as_btn.setObjectName("browse_btn")
        browse_as_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_as_btn.clicked.connect(self.select_as_path)
        as_path_layout.addWidget(self.as_path_input)
        as_path_layout.addWidget(browse_as_btn)
        
        self.dark_mode_check = QCheckBox("Dark Mode")
        self.dark_mode_check.setChecked(self.settings.value("dark_mode", "false") == "true")
        
        form.addRow("RoboRIO IP:", self.ip_input)
        form.addRow("Save Location:", path_layout)
        form.addRow("Robot Logs:", self.robot_path_input)
        form.addRow("AdvantageScope Path:", as_path_layout)
        form.addRow("", self.dark_mode_check)
        
        layout.addLayout(form)
        layout.addStretch()
        
        save_btn = QPushButton("APPLY")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save)
        layout.addWidget(save_btn)

    def select_save_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Save Location", self.path_input.text())
        if path:
            self.path_input.setText(path)

    def select_as_path(self):
        if sys.platform == "darwin":
            path, _ = QFileDialog.getOpenFileName(self, "Select AdvantageScope", "/Applications", "Applications (*.app)")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Select AdvantageScope", "C:\\", "Executables (*.exe)")
        
        if path:
            self.as_path_input.setText(path)

    def save(self):
        self.settings.setValue("rio_ip", self.ip_input.text())
        self.settings.setValue("save_path", self.path_input.text())
        self.settings.setValue("robot_path", self.robot_path_input.text())
        self.settings.setValue("as_path", self.as_path_input.text())
        self.settings.setValue("dark_mode", "true" if self.dark_mode_check.isChecked() else "false")
        self.accept()

class StorageMonitorWorker(QThread):
    status_updated = pyqtSignal(bool, str, str) # connected, usage_percent, raw_stats
    
    def __init__(self, ip, robot_path):
        super().__init__()
        self.ip = ip
        self.robot_path = robot_path
        self.running = True

    def run(self):
        import paramiko
        while self.running:
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(self.ip, username="lvuser", password="", timeout=2)
                
                # Get disk usage for the configured log path
                # Output format: Size Used Avail Use% Mounted
                cmd = f"df -h '{self.robot_path}' | tail -1 | awk '{{print $2, $3, $5}}'"
                stdin, stdout, stderr = ssh.exec_command(cmd)
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

    def __init__(self, ip, local_dir, robot_dir, delete_after, selected_files=None):
        super().__init__()
        self.ip = ip
        self.local_dir = local_dir
        self.robot_dir = robot_dir
        self.delete_after = delete_after
        self.selected_files = selected_files

    def run(self):
        import paramiko
        from stat import S_ISREG
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.ip, username="lvuser", password="", timeout=5)
            sftp = ssh.open_sftp()
            
            if self.selected_files:
                files = self.selected_files
            else:
                try:
                    files = sftp.listdir(self.robot_dir)
                except IOError:
                    files = []
            
            if not os.path.exists(self.local_dir): os.makedirs(self.local_dir)

            count = 0
            for f in files:
                # remote_path = f"{self.robot_dir}/{f}" if self.robot_dir.endswith('/') else f"{self.robot_dir}/{f}"
                # Better safe than sorry with path joining for remote
                remote_path = os.path.join(self.robot_dir, f).replace("\\", "/") # Ensure forward slashes for Linux
                local_path = os.path.join(self.local_dir, f)
                try:
                    stats = sftp.stat(remote_path)
                    if S_ISREG(stats.st_mode):
                        self.progress.emit(f"Pulling {f}...")
                        sftp.get(remote_path, local_path)
                        if self.delete_after: sftp.remove(remote_path)
                        count += 1
                except Exception as e:
                    self.progress.emit(f"Error pulling {f}: {str(e)}")
            
            sftp.close()
            ssh.close()
            self.finished.emit(count)
        except Exception as e:
            self.error.emit(str(e))

class RemoteListWorker(QThread):
    files_listed = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, ip, robot_dir):
        super().__init__()
        self.ip = ip
        self.robot_dir = robot_dir

    def run(self):
        import paramiko
        from stat import S_ISREG
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.ip, username="lvuser", password="", timeout=5)
            sftp = ssh.open_sftp()
            
            file_list = []
            try:
                files = sftp.listdir_attr(self.robot_dir)
                for f in files:
                    if S_ISREG(f.st_mode):
                        # size in KB, mtime as timestamp
                        file_list.append({
                            'name': f.filename,
                            'size': f.st_size,
                            'mtime': f.st_mtime
                        })
            except IOError:
                # Directory might not exist yet
                pass
            
            sftp.close()
            ssh.close()
            self.files_listed.emit(file_list)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("CavalierRobotics", "LogSync")
        self.monitor_worker = None
        self.was_connected = False
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
        contrast_blue = REGAL_BLUE if is_dark else CAVALIER_BLUE
        
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
            QMenu {{
                background-color: {panel_bg};
                color: {txt_color};
                border: 1px solid {border};
            }}
            QMenu::item:selected {{
                background-color: {CAVALIER_ORANGE};
                color: white;
            }}
            QMessageBox {{
                background-color: {bg_color};
            }}
            QMessageBox QLabel {{
                color: {txt_color};
                font-size: 13px;
            }}
            QMessageBox QPushButton {{
                background-color: {CAVALIER_ORANGE};
                color: white;
                border-radius: 4px;
                padding: 6px 15px;
                min-width: 80px;
                font-weight: bold;
            }}
        """)
        
        self.console.setStyleSheet(f"""
            QTextEdit {{
                background-color: {"#2b2b2b" if is_dark else "white"};
                border: 1px solid {border};
                border-radius: 10px;
                color: {txt_color};
                font-family: 'Courier New', 'Monaco', monospace;
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
                font-weight: bold;
            }}
            QPushButton:hover {{ 
                background-color: {contrast_blue}; 
                color: white;
            }}
        """)
        
        self.status_text.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {'#CCCCCC' if is_dark else '#505759'};")
        self.title_lbl.setStyleSheet(f"font-family: 'Norwester'; font-size: 20px; color: {'white' if is_dark else CAVALIER_BLUE}; margin-bottom: 5px;")
        self.console_lbl.setStyleSheet(f"font-weight: bold; color: {'#AAAAAA' if is_dark else ABBEY_GREY}; font-size: 12px; text-transform: uppercase;")
        self.divider_line.setStyleSheet(f"background-color: {border}; height: 1px; border: none;")

        # Tab & Table Styling
        tab_bg = "#2b2b2b" if is_dark else "white"
        header_bg = "#3E4446" if is_dark else LIGHT_GRAY
        
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {border}; border-radius: 8px; background: {bg_color}; }}
            QTabBar::tab {{
                background: {panel_bg};
                color: {txt_color};
                padding: 10px 20px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{ background: {CAVALIER_ORANGE}; color: white; }}
        """)

        table_style = f"""
            QTableWidget {{
                background-color: {tab_bg};
                alternate-background-color: {"#333333" if is_dark else "#F9F9F9"};
                gridline-color: {border};
                border: 1px solid {border};
                border-radius: 4px;
                outline: none;
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {txt_color};
                padding: 6px;
                border: none;
                border-right: 1px solid {border};
                border-bottom: 1px solid {border};
                font-weight: bold;
            }}
            QHeaderView::section:last {{
                border-right: none;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {bg_color};
                width: 10px;
            }}
            QScrollBar::handle:vertical {{
                background: {ABBEY_GREY};
                min-height: 20px;
                border-radius: 5px;
            }}
        """
        self.local_table.setStyleSheet(table_style)
        self.remote_table.setStyleSheet(table_style)
        self.local_table.setAlternatingRowColors(True)
        self.remote_table.setAlternatingRowColors(True)
        
        # Hide vertical headers completely
        self.local_table.verticalHeader().setVisible(False)
        self.remote_table.verticalHeader().setVisible(False)

        input_style = f"""
            QLineEdit {{
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px;
                background-color: {tab_bg};
                color: {txt_color};
            }}
        """
        self.local_search.setStyleSheet(input_style)
        self.remote_search.setStyleSheet(input_style)
        
        button_style = f"""
            QPushButton {{
                background-color: {contrast_blue};
                color: white;
                border-radius: 6px;
                padding: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {CAVALIER_ORANGE}; }}
        """
        self.refresh_local_btn.setStyleSheet(button_style)
        self.refresh_remote_btn.setStyleSheet(button_style)

    def start_monitoring(self):
        if self.monitor_worker:
            self.monitor_worker.stop()
            self.monitor_worker.wait()
        
        ip = self.settings.value("rio_ip", "10.6.19.2")
        robot_path = self.settings.value("robot_path", "/home/lvuser/akitlogs")
        self.monitor_worker = StorageMonitorWorker(ip, robot_path)
        self.monitor_worker.status_updated.connect(self.update_status_ui)
        self.monitor_worker.start()

    def update_status_ui(self, connected, usage, raw):
        if connected:
            if not self.was_connected:
                self.refresh_remote_logs()
            self.was_connected = True
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

        # RIGHT SIDE: Tabs
        self.tabs = QTabWidget()
        
        # Tab 1: Activity Log
        self.activity_tab = QWidget()
        activity_layout = QVBoxLayout(self.activity_tab)
        self.console_lbl = QLabel("Activity Log")
        self.console_lbl.setStyleSheet(f"font-weight: bold; color: {ABBEY_GREY}; font-size: 12px; text-transform: uppercase;")
        activity_layout.addWidget(self.console_lbl)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        activity_layout.addWidget(self.console)
        self.tabs.addTab(self.activity_tab, "Sync Status")

        # Tab 2: Local Logs
        self.local_tab = QWidget()
        local_layout = QVBoxLayout(self.local_tab)
        
        local_tools = QHBoxLayout()
        self.local_search = QLineEdit()
        self.local_search.setPlaceholderText("Search local logs...")
        self.local_search.textChanged.connect(self.filter_local_logs)
        local_tools.addWidget(self.local_search)
        
        self.refresh_local_btn = QPushButton("Refresh")
        self.refresh_local_btn.setFixedWidth(80)
        self.refresh_local_btn.clicked.connect(self.refresh_local_logs)
        local_tools.addWidget(self.refresh_local_btn)
        local_layout.addLayout(local_tools)

        self.local_table = QTableWidget(0, 3)
        self.local_table.setHorizontalHeaderLabels(["Name", "Size", "Date Modified"])
        local_header = self.local_table.horizontalHeader()
        local_header.setMinimumSectionSize(20)
        local_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        local_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.local_table.setColumnWidth(1, 60)
        local_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.local_table.setColumnWidth(2, 120)
        local_header.setSectionsMovable(False)
        self.local_table.verticalHeader().setVisible(False)
        self.local_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.local_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.local_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.local_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.local_table.customContextMenuRequested.connect(self.show_local_context_menu)
        self.local_table.setSortingEnabled(True)
        self.local_table.sortByColumn(2, Qt.SortOrder.DescendingOrder)
        local_layout.addWidget(self.local_table)
        self.tabs.addTab(self.local_tab, "Local Logs")

        # Tab 3: Remote Logs
        self.remote_tab = QWidget()
        remote_layout = QVBoxLayout(self.remote_tab)
        
        remote_tools = QHBoxLayout()
        self.remote_search = QLineEdit()
        self.remote_search.setPlaceholderText("Search remote logs...")
        self.remote_search.textChanged.connect(self.filter_remote_logs)
        remote_tools.addWidget(self.remote_search)
        
        self.refresh_remote_btn = QPushButton("Scan RIO")
        self.refresh_remote_btn.setFixedWidth(80)
        self.refresh_remote_btn.clicked.connect(self.refresh_remote_logs)
        remote_tools.addWidget(self.refresh_remote_btn)
        remote_layout.addLayout(remote_tools)

        self.remote_table = QTableWidget(0, 3)
        self.remote_table.setHorizontalHeaderLabels(["Name", "Size", "Date Modified"])
        remote_header = self.remote_table.horizontalHeader()
        remote_header.setMinimumSectionSize(20)
        remote_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        remote_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.remote_table.setColumnWidth(1, 60)
        remote_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.remote_table.setColumnWidth(2, 120)
        remote_header.setSectionsMovable(False)
        self.remote_table.verticalHeader().setVisible(False)
        self.remote_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.remote_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.remote_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.remote_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.remote_table.customContextMenuRequested.connect(self.show_remote_context_menu)
        self.remote_table.setSortingEnabled(True)
        self.remote_table.sortByColumn(2, Qt.SortOrder.DescendingOrder)
        remote_layout.addWidget(self.remote_table)
        self.tabs.addTab(self.remote_tab, "Remote Logs")

        layout.addWidget(self.tabs, 3)
        
        # Shortcuts
        from PyQt6.QtGui import QKeySequence
        self.settings_shortcut = QAction(self)
        self.settings_shortcut.setShortcut(QKeySequence(QKeySequence.StandardKey.Preferences))
        self.settings_shortcut.triggered.connect(self.open_settings)
        self.addAction(self.settings_shortcut)

        self.last_remote_files = []
        self.last_local_files = []
        self.refresh_local_logs()

    def refresh_local_logs(self):
        self.local_table.setRowCount(0)
        self.last_local_files = []
        path = self.settings.value("save_path", os.path.expanduser("~/Documents/619_Logs"))
        if not os.path.exists(path):
            return
            
        for f in os.listdir(path):
            if f.endswith(".wpilog"):
                f_path = os.path.join(path, f)
                stat = os.stat(f_path)
                data = {
                    'name': f,
                    'size': stat.st_size,
                    'mtime': stat.st_mtime
                }
                self.last_local_files.append(data)
        
        self.update_local_table(self.last_local_files)

    def update_local_table(self, files):
        self.local_table.setSortingEnabled(False)
        self.local_table.setRowCount(len(files))
        for i, f in enumerate(sorted(files, key=lambda x: x['mtime'], reverse=True)):
            self.local_table.setItem(i, 0, SortableTableWidgetItem(f['name'], f['name']))
            
            size_mb = f['size'] / (1024 * 1024)
            size_item = SortableTableWidgetItem(f"{size_mb:.2f} MB", f['size'])
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.local_table.setItem(i, 1, size_item)
            
            date = QDateTime.fromSecsSinceEpoch(int(f['mtime'])).toString("yyyy-MM-dd HH:mm:ss")
            date_item = SortableTableWidgetItem(date, f['mtime'])
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.local_table.setItem(i, 2, date_item)
        self.local_table.setSortingEnabled(True)

    def filter_local_logs(self):
        search = self.local_search.text().lower()
        filtered = [f for f in self.last_local_files if search in f['name'].lower()]
        self.update_local_table(filtered)

    def show_local_context_menu(self, pos):
        selected_rows = self.local_table.selectionModel().selectedRows()
        if not selected_rows: return
        
        filenames = [self.local_table.item(row.row(), 0).text() for row in selected_rows]
        count = len(filenames)
        
        menu = QMenu()
        open_action = menu.addAction(f"Open in AdvantageScope ({count})" if count > 1 else "Open in AdvantageScope")
        reveal_action = menu.addAction("Reveal in Finder" if sys.platform == "darwin" else "Reveal in Explorer")
        delete_action = menu.addAction(f"Delete {count} Files" if count > 1 else "Delete File")
        
        action = menu.exec(self.local_table.viewport().mapToGlobal(pos))
        
        path = self.settings.value("save_path", os.path.expanduser("~/Documents/619_Logs"))
        
        if action == open_action:
            as_path = self.settings.value("as_path", "AdvantageScope" if sys.platform == "darwin" else "AdvantageScope.exe")
            for filename in filenames:
                full_path = os.path.join(path, filename)
                try:
                    if sys.platform == "darwin":
                        subprocess.run(["open", "-a", as_path, full_path], check=True)
                    else:
                        subprocess.Popen([as_path, full_path])
                except Exception as e:
                    QMessageBox.critical(self, "Launch Error", 
                                    f"Failed to launch AdvantageScope for {filename}.\n\nPath: {as_path}\nError: {str(e)}")
                    break
        elif action == reveal_action:
            for filename in filenames:
                full_path = os.path.join(path, filename)
                if sys.platform == "darwin":
                    subprocess.run(["open", "-R", full_path])
                else:
                    subprocess.run(["explorer", "/select,", os.path.normpath(full_path)])
        elif action == delete_action:
            msg = f"Are you sure you want to delete {count} files?" if count > 1 else f"Are you sure you want to delete {filenames[0]}?"
            ans = QMessageBox.question(self, "Delete", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ans == QMessageBox.StandardButton.Yes:
                for filename in filenames:
                    try:
                        os.remove(os.path.join(path, filename))
                    except Exception as e:
                        QMessageBox.warning(self, "Error", f"Failed to delete {filename}: {e}")
                self.refresh_local_logs()

    def refresh_remote_logs(self):
        ip = self.settings.value("rio_ip", "10.6.19.2")
        robot_path = self.settings.value("robot_path", "/home/lvuser/akitlogs")
        self.remote_worker = RemoteListWorker(ip, robot_path)
        self.remote_worker.files_listed.connect(self.on_remote_files_listed)
        self.remote_worker.error.connect(lambda e: self.console.append(f"<span style='color: #C0392B;'>Failed to list remote files: {e}</span>"))
        self.remote_worker.start()

    def on_remote_files_listed(self, files):
        self.last_remote_files = [f for f in files if f['name'].endswith(".wpilog")]
        self.update_remote_table(self.last_remote_files)

    def update_remote_table(self, files):
        self.remote_table.setSortingEnabled(False)
        self.remote_table.setRowCount(len(files))
        for i, f in enumerate(sorted(files, key=lambda x: x['mtime'], reverse=True)):
            self.remote_table.setItem(i, 0, SortableTableWidgetItem(f['name'], f['name']))
            
            size_mb = f['size'] / (1024 * 1024)
            size_item = SortableTableWidgetItem(f"{size_mb:.2f} MB", f['size'])
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.remote_table.setItem(i, 1, size_item)
            
            date = QDateTime.fromSecsSinceEpoch(int(f['mtime'])).toString("yyyy-MM-dd HH:mm:ss")
            date_item = SortableTableWidgetItem(date, f['mtime'])
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.remote_table.setItem(i, 2, date_item)
        self.remote_table.setSortingEnabled(True)

    def filter_remote_logs(self):
        search = self.remote_search.text().lower()
        filtered = [f for f in self.last_remote_files if search in f['name'].lower()]
        self.update_remote_table(filtered)

    def show_remote_context_menu(self, pos):
        selected_rows = self.remote_table.selectionModel().selectedRows()
        if not selected_rows: return
        
        filenames = [self.remote_table.item(row.row(), 0).text() for row in selected_rows]
        count = len(filenames)
        
        menu = QMenu()
        sync_action = menu.addAction(f"Sync {count} files" if count > 1 else "Sync this file")
        delete_action = menu.addAction(f"Delete {count} from RIO" if count > 1 else "Delete from RIO")
        
        action = menu.exec(self.remote_table.viewport().mapToGlobal(pos))
        
        ip = self.settings.value("rio_ip", "10.6.19.2")
        robot_path = self.settings.value("robot_path", "/home/lvuser/akitlogs")
        
        if action == sync_action:
            self.tabs.setCurrentIndex(0) # Switch to status tab
            self.start_sync(file_list=filenames)
        elif action == delete_action:
            msg = f"Delete {count} logs from RoboRIO?" if count > 1 else f"Delete {filenames[0]} from RoboRIO?"
            ans = QMessageBox.question(self, "Delete", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ans == QMessageBox.StandardButton.Yes:
                import paramiko
                try:
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(ip, username="lvuser", password="", timeout=5)
                    sftp = ssh.open_sftp()
                    for filename in filenames:
                        remote_file = os.path.join(robot_path, filename).replace("\\", "/")
                        sftp.remove(remote_file)
                    sftp.close()
                    ssh.close()
                    self.refresh_remote_logs()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to delete: {e}")

    def delete_remote_file(self, ip, path):
        import paramiko
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username="lvuser", password="", timeout=5)
            sftp = ssh.open_sftp()
            sftp.remove(path)
            sftp.close()
            ssh.close()
            self.refresh_remote_logs()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete: {e}")

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self.apply_theme()
            self.start_monitoring()

    def start_sync(self, file_list=None):
        self.sync_btn.setEnabled(False)
        self.sync_btn.setText("SYNCING...")
        self.console.clear()
        self.console.append("<b style='color: #0C2340;'>Initializing connection...</b>")
        
        ip = self.settings.value("rio_ip", "10.6.19.2")
        path = self.settings.value("save_path", os.path.expanduser("~/Documents/619_Logs"))
        robot_path = self.settings.value("robot_path", "/home/lvuser/akitlogs")
        
        # Only delete after sync if we are doing a full sync (list is None) AND the checkbox is checked
        # Note: clicked signal passes a bool, so we check if it's specifically a list
        is_partial_sync = isinstance(file_list, list)
        delete_after = self.del_check.isChecked() if not is_partial_sync else False
        
        # Ensure we pass None if it's just the clicked signal's boolean
        worker_file_list = file_list if is_partial_sync else None
        
        self.worker = SyncWorker(ip, path, robot_path, delete_after, selected_files=worker_file_list)
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
        self.sync_btn.setText("SYNC NOW")
        self.sync_btn.setEnabled(True)
        self.refresh_local_logs()
        self.refresh_remote_logs()

    def on_sync_error(self, error):
        self.console.append(f"\n<b style='color: #C0392B;'>⚠ Error: {error}</b>")
        self.console.append("<span style='color: #E67E22;'>Please check RoboRIO IP and Network settings.</span>")
        self.sync_btn.setText("SYNC NOW")
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