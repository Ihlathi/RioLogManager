import os
import sys
import paramiko
from stat import S_ISREG
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QPushButton, QTextEdit, QLabel, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont

# Configuration
RIO_IP = "10.6.19.2"
USER = "lvuser"
PASS = ""
REMOTE_DIR = "/home/lvuser/akitlogs"
LOCAL_DIR = "./logs"

class LogWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def run(self):
        try:
            if not os.path.exists(LOCAL_DIR):
                os.makedirs(LOCAL_DIR)

            self.progress.emit(f"Connecting to {RIO_IP}...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(RIO_IP, username=USER, password=PASS, timeout=5)
            
            sftp = ssh.open_sftp()
            
            try:
                files = sftp.listdir(REMOTE_DIR)
            except IOError:
                self.error.emit(f"Directory {REMOTE_DIR} not found on Rio.")
                return

            transfer_count = 0
            for f in files:
                remote_path = f"{REMOTE_DIR}/{f}"
                local_path = os.path.join(LOCAL_DIR, f)
                
                # Verify it is a regular file
                if S_ISREG(sftp.stat(remote_path).st_mode):
                    self.progress.emit(f"Downloading: {f}")
                    sftp.get(remote_path, local_path)
                    
                    # Size Verification
                    if os.path.getsize(local_path) == sftp.stat(remote_path).st_size:
                        sftp.remove(remote_path)
                        transfer_count += 1
                    else:
                        self.progress.emit(f"⚠️ Verification failed for {f}")

            sftp.close()
            ssh.close()
            self.finished.emit(transfer_count)

        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("619 Log Scraper")
        self.setMinimumSize(450, 350)

        # Main Layout
        layout = QVBoxLayout()
        
        self.status_label = QLabel("Ready to sync logs.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.btn = QPushButton("🚀 ONE-CLICK LOG SYNC")
        self.btn.setFixedHeight(60)
        self.btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                font-weight: bold;
                font-size: 16px;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.btn.clicked.connect(self.start_transfer)
        layout.addWidget(self.btn)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Courier", 10))
        layout.addWidget(self.console)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def log(self, text):
        self.console.append(text)

    def start_transfer(self):
        self.btn.setEnabled(False)
        self.console.clear()
        self.worker = LogWorker()
        self.worker.progress.connect(self.log)
        self.worker.error.connect(self.handle_error)
        self.worker.finished.connect(self.handle_finish)
        self.worker.start()

    def handle_error(self, err):
        QMessageBox.critical(self, "Connection Error", f"Failed to reach Rio:\n{err}")
        self.btn.setEnabled(True)

    def handle_finish(self, count):
        self.log(f"\n✅ SUCCESS: {count} logs moved to /logs folder.")
        self.btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())