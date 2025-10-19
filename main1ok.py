import sys
import serial
import serial.tools.list_ports
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QComboBox, QMessageBox
)
from PyQt5.QtGui import QTextCursor
from datetime import datetime


# -------------------- Worker Thread --------------------
class SerialReader(QThread):
    data_received = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, ser):
        super().__init__()
        self.ser = ser
        self._running = True

    def run(self):
        buffer = b""
        try:
            while self._running and self.ser.is_open:
                data = self.ser.read_all()
                if data:
                    buffer += data
                    if b"\n" in buffer:
                        parts = buffer.split(b"\n")
                        buffer = parts[-1]
                        for p in parts[:-1]:
                            try:
                                text = p.decode("utf-8", errors="replace")
                            except Exception:
                                text = str(p)
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            self.data_received.emit(f"[{timestamp}] {text}")
        except Exception as e:
            self.error_signal.emit(str(e))

    def stop(self):
        self._running = False
        self.wait(100)


# -------------------- Main GUI --------------------
class SerialGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.ser = None
        self.reader_thread = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Serial Read/Write - PyQt5 Real-Time")
        self.resize(900, 600)
        layout = QVBoxLayout()

        # --- Top controls ---
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        top_bar.addWidget(self.port_combo)

        self.refresh_btn = QPushButton("Refresh COM")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        top_bar.addWidget(self.refresh_btn)

        top_bar.addWidget(QLabel("Baud:"))
        self.baud_edit = QLineEdit("9600")
        self.baud_edit.setFixedWidth(80)
        top_bar.addWidget(self.baud_edit)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_disconnect)
        top_bar.addWidget(self.connect_btn)

        layout.addLayout(top_bar)

        # --- Status ---
        self.status_label = QLabel("Not connected")
        layout.addWidget(self.status_label)

        # --- Read area ---
        layout.addWidget(QLabel("Read (incoming):"))
        self.read_box = QTextEdit()
        self.read_box.setReadOnly(True)
        layout.addWidget(self.read_box)

        # --- Write area ---
        layout.addWidget(QLabel("Write (outgoing):"))
        self.write_box = QTextEdit()
        self.write_box.setFixedHeight(100)
        layout.addWidget(self.write_box)

        write_bar = QHBoxLayout()
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_data)
        write_bar.addWidget(self.send_btn)
        layout.addLayout(write_bar)

        self.setLayout(layout)
        self.refresh_ports()

    # -------------------- Serial Functions --------------------
    def refresh_ports(self):
        self.port_combo.clear()
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo.addItems(ports if ports else ["(no ports)"])

    def connect_disconnect(self):
        if self.ser and self.ser.is_open:
            self.disconnect_serial()
            return

        port = self.port_combo.currentText()
        if port == "(no ports)" or not port:
            QMessageBox.warning(self, "Error", "No COM port selected")
            return

        try:
            baud = int(self.baud_edit.text())
            self.ser = serial.Serial(port, baudrate=baud, timeout=0.05)
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            return

        # Start reader thread
        self.reader_thread = SerialReader(self.ser)
        self.reader_thread.data_received.connect(self.display_data)
        self.reader_thread.error_signal.connect(self.display_error)
        self.reader_thread.start()

        self.connect_btn.setText("Disconnect")
        self.connect_btn.setStyleSheet("background-color: #00cc44; color: white;")
        self.status_label.setText(f"Connected to {port} @ {baud}")

    def disconnect_serial(self):
        if self.reader_thread:
            self.reader_thread.stop()
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.ser = None
        self.connect_btn.setText("Connect")
        self.connect_btn.setStyleSheet("")
        self.status_label.setText("Disconnected")

    def send_data(self):
        if not self.ser or not self.ser.is_open:
            QMessageBox.warning(self, "Error", "Not connected")
            return
        text = self.write_box.toPlainText().strip()
        if not text:
            return
        try:
            self.ser.write((text + "\n").encode("utf-8"))
            self.status_label.setText(f"Sent {len(text)} chars")
        except Exception as e:
            QMessageBox.critical(self, "Write Error", str(e))

    # -------------------- Display --------------------
    def display_data(self, text):
        self.read_box.append(text)
        self.read_box.moveCursor(QTextCursor.End)


    def display_error(self, msg):
        self.status_label.setText("Read error: " + msg)

    # -------------------- Close --------------------
    def closeEvent(self, event):
        self.disconnect_serial()
        event.accept()


# -------------------- Run --------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = SerialGUI()
    gui.show()
    sys.exit(app.exec_())
