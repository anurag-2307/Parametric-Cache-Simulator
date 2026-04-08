# sidebar.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt, pyqtSignal

class HistorySidebar(QWidget):
    # Emit a signal when a user clicks a past run, passing the run's ID or data
    run_selected = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setObjectName("SidebarWidget") # Hooks into style.qss
        self.setFixedWidth(250) # Fixed width so it doesn't crush the main views
        self.history_data = [] # In-memory list to store run dictionaries
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar Title
        title = QLabel("History")
        title.setObjectName("SidebarTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # List Widget for past runs
        self.history_list = QListWidget()
        self.history_list.setObjectName("HistoryList")
        self.history_list.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.history_list)

        self.setLayout(layout)

    def add_run_to_history(self, config_data, results_data):
        """
        Takes the configuration and results of a finished run, formats a 
        clean display string, and adds it to the sidebar.
        """
        # Store the full data for later retrieval/comparison
        run_record = {
            "config": config_data,
            "results": results_data
        }
        self.history_data.append(run_record)
        run_index = len(self.history_data) - 1

        # Format the display string (e.g., L1: 32K | 27L traces)
        # Assuming we can calculate the trace count in the backend and pass it here
        trace_count_str = results_data.get("Trace Count", "Unknown traces")
        
        display_text = f"Run #{run_index + 1}\nL1: {config_data['l1_size']} | {trace_count_str}"
        
        item = QListWidgetItem(display_text)
        # Store the index inside the UI item so we know which data to pull when clicked
        item.setData(Qt.ItemDataRole.UserRole, run_index) 
        
        self.history_list.insertItem(0, item) # Add newest to the top

    def on_item_clicked(self, item):
        # Retrieve the index we stored in the item
        run_index = item.data(Qt.ItemDataRole.UserRole)
        selected_run = self.history_data[run_index]
        
        # Emit the selected run's data so main.py can display it or compare it
        self.run_selected.emit(selected_run)