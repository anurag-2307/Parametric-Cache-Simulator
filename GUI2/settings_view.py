# settings_view.py

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QSpinBox, QPushButton, QFileDialog, QGridLayout, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal

class DropZone(QFrame):
    # Custom widget to handle drag & drop or click-to-browse
    file_dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("DropZone") # Hooks into style.qss
        self.setAcceptDrops(True)
        self.file_path = None

        self.layout = QVBoxLayout()
        self.label = QLabel("Drag & Drop Trace File Here\nor Click to Browse")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.set_file(files[0])

    def mousePressEvent(self, event):
        # Fallback to standard file browser if the user clicks the zone
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Trace File", "", "Text Files (*.txt);;Trace Files (*.trace);;All Files (*)"
        )
        if file_name:
            self.set_file(file_name)

    def set_file(self, path):
        self.file_path = path
        self.label.setText(f"Selected Trace File:\n{os.path.basename(path)}")
        self.file_dropped.emit(path)


class SettingsView(QWidget):
    # Signal that will tell main.py to switch views and execute the command
    run_requested = pyqtSignal(dict) 

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        main_layout.setContentsMargins(40, 60, 40, 40)
        main_layout.setSpacing(40)

        # Title
        title = QLabel("Cache Simulator Configuration")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # Settings Grid (2x4 layout for inputs as per your sketch)
        grid = QGridLayout()
        grid.setHorizontalSpacing(30)
        grid.setVerticalSpacing(20)

        # L1 Cache Settings
        grid.addWidget(QLabel("L1 Size (Bytes):"), 0, 0)
        self.l1_size = QComboBox()
        self.l1_size.addItems(["16384", "32768", "65536", "131072"])
        self.l1_size.setCurrentText("32768")
        grid.addWidget(self.l1_size, 0, 1)

        grid.addWidget(QLabel("L1 Associativity:"), 0, 2)
        self.l1_assoc = QSpinBox()
        self.l1_assoc.setRange(1, 32)
        self.l1_assoc.setValue(8)
        grid.addWidget(self.l1_assoc, 0, 3)

        # L2 Cache Settings
        grid.addWidget(QLabel("L2 Size (Bytes):"), 1, 0)
        self.l2_size = QComboBox()
        self.l2_size.addItems(["524288", "1048576", "2097152", "4194304"])
        self.l2_size.setCurrentText("2097152")
        grid.addWidget(self.l2_size, 1, 1)

        grid.addWidget(QLabel("L2 Associativity:"), 1, 2)
        self.l2_assoc = QSpinBox()
        self.l2_assoc.setRange(1, 64)
        self.l2_assoc.setValue(16)
        grid.addWidget(self.l2_assoc, 1, 3)

        # Other Settings
        grid.addWidget(QLabel("Replacement Policy:"), 2, 0)
        self.policy = QComboBox()
        self.policy.addItems(["LRU", "FIFO"])
        grid.addWidget(self.policy, 2, 1)

        grid.addWidget(QLabel("Prefetching:"), 2, 2)
        self.prefetch = QComboBox()
        self.prefetch.addItems(["ON", "OFF"])
        grid.addWidget(self.prefetch, 2, 3)

        main_layout.addLayout(grid)

        # Drag and Drop Zone
        self.drop_zone = DropZone()
        main_layout.addWidget(self.drop_zone)

        # Run Button
        self.run_btn = QPushButton("Run Simulation")
        self.run_btn.setFixedSize(250, 50)
        self.run_btn.clicked.connect(self.trigger_execution)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.run_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    def trigger_execution(self):
        # Package all user selections into a dictionary and emit it
        # The main.py file will catch this, switch to the analysis screen, and trigger the backend
        config_data = {
            "l1_size": self.l1_size.currentText(),
            "l1_assoc": str(self.l1_assoc.value()),
            "l2_size": self.l2_size.currentText(),
            "l2_assoc": str(self.l2_assoc.value()),
            "policy": self.policy.currentText(),
            "prefetch": self.prefetch.currentText(),
            "trace_file": self.drop_zone.file_path
        }
        self.run_requested.emit(config_data)