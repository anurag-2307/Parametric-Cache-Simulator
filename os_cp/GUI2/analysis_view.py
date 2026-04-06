# analysis_view.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTabWidget, QFrame, QGridLayout, 
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, pyqtSignal

class DetailedMetricsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # Summary Label
        self.summary_label = QLabel("Simulation Complete. Review the detailed metrics below.")
        self.summary_label.setStyleSheet("font-size: 16px; color: #A0A0A0; margin-bottom: 10px;")
        layout.addWidget(self.summary_label)

        # Metrics Table (Clean, modern look instead of raw text)
        self.metrics_table = QTableWidget(0, 2)
        self.metrics_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.metrics_table.verticalHeader().setVisible(False)
        self.metrics_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.metrics_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.metrics_table.setStyleSheet("""
            QTableWidget {
                background-color: #1E1E1E;
                border: 1px solid #333333;
                border-radius: 6px;
                gridline-color: #333333;
            }
            QHeaderView::section {
                background-color: #2D2D30;
                padding: 8px;
                border: 1px solid #333333;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 10px;
                border-bottom: 1px solid #2A2A2A;
            }
        """)
        layout.addWidget(self.metrics_table)
        self.setLayout(layout)

    def update_data(self, metrics_dict):
        # Dynamically populate the table when the backend finishes
        self.metrics_table.setRowCount(0)
        for row, (key, value) in enumerate(metrics_dict.items()):
            self.metrics_table.insertRow(row)
            self.metrics_table.setItem(row, 0, QTableWidgetItem(str(key)))
            self.metrics_table.setItem(row, 1, QTableWidgetItem(str(value)))

class VisualMetricsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # Placeholder for graphical elements (Charts, Graphs)
        self.graph_container = QFrame()
        self.graph_container.setStyleSheet("""
            QFrame {
                background-color: #1A1A1A;
                border: 2px dashed #424242;
                border-radius: 8px;
            }
        """)
        graph_layout = QVBoxLayout()
        
        placeholder_label = QLabel("Visual Graphs will render here\n(e.g., L1 vs L2 Hit Rates, Miss Breakdowns)")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setStyleSheet("color: #707070; font-size: 18px;")
        
        graph_layout.addWidget(placeholder_label)
        self.graph_container.setLayout(graph_layout)
        
        layout.addWidget(self.graph_container)
        self.setLayout(layout)

class AnalysisView(QWidget):
    # Signal to tell main.py we want to go back to the settings screen
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)

        # Header with Title and Back Button
        header_layout = QHBoxLayout()
        title = QLabel("Simulation Results")
        title.setObjectName("TitleLabel") # Uses the large styling from style.qss
        
        self.back_btn = QPushButton("← New Simulation")
        self.back_btn.setFixedSize(180, 40)
        self.back_btn.setStyleSheet("background-color: #3E3E42;") # Slightly different color for secondary action
        self.back_btn.clicked.connect(self.back_requested.emit)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.back_btn)
        main_layout.addLayout(header_layout)

        # Tabbed Interface
        self.tabs = QTabWidget()
        
        self.detailed_tab = DetailedMetricsTab()
        self.visual_tab = VisualMetricsTab()

        self.tabs.addTab(self.detailed_tab, "Detailed Metrics")
        self.tabs.addTab(self.visual_tab, "Visual Metrics")
        
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

    def load_results(self, parsed_data):
        # This will be called by main.py once the C++ binary finishes running
        # Example: parsed_data = {"L1 Hits": 4500, "L1 Misses": 120, "AMAT": "1.2 cycles"}
        self.detailed_tab.update_data(parsed_data)
        # Future: Trigger graph updates in visual_tab here as well