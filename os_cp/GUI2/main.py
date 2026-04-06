# main.py

import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                             QStackedWidget, QMessageBox)
from PyQt6.QtCore import Qt

# Import our custom modular components
from settings_view import SettingsView
from analysis_view import AnalysisView
from sidebar import HistorySidebar
from simulator_backend import SimulatorWorker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cache Simulator - Professional Edition")
        
        # Default to maximized window as requested
        self.showMaximized() 
        
        # Keep track of the background worker so it doesn't get garbage collected
        self.worker = None 
        
        self.init_ui()
        self.load_stylesheet()

    def init_ui(self):
        # The central widget holds everything
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout is horizontal: Left side for views, Right side for history
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. The Stacked Widget (handles switching between Settings and Analysis)
        self.view_stack = QStackedWidget()
        
        self.settings_view = SettingsView()
        self.analysis_view = AnalysisView()
        
        self.view_stack.addWidget(self.settings_view)
        self.view_stack.addWidget(self.analysis_view)

        # 2. The Persistent Sidebar
        self.sidebar = HistorySidebar()

        # Add to main layout (stretch factor 1 for main view, 0 for fixed sidebar)
        main_layout.addWidget(self.view_stack, 1)
        main_layout.addWidget(self.sidebar, 0)

        central_widget.setLayout(main_layout)

        # --- Signal Connections ---
        
        # When "Run Simulation" is clicked
        self.settings_view.run_requested.connect(self.start_simulation)
        
        # When "<- New Simulation" is clicked in Analysis View
        self.analysis_view.back_requested.connect(self.show_settings)
        
        # When a past run is clicked in the Sidebar
        self.sidebar.run_selected.connect(self.load_past_run)

    def load_stylesheet(self):
        """Loads the central style.qss file to give it the million-dollar look."""
        style_path = os.path.join(os.path.dirname(__file__), "style.qss")
        if os.path.exists(style_path):
            with open(style_path, "r") as f:
                self.setStyleSheet(f.read())
        else:
            print("Warning: style.qss not found. Running with default OS styles.")

    def start_simulation(self, config_data):
        """Triggered by the SettingsView. Starts the C++ backend silently."""
        
        # Change the button text to show it's loading
        self.settings_view.run_btn.setText("Simulating...")
        self.settings_view.run_btn.setEnabled(False)

        # Initialize and start the background thread
        self.worker = SimulatorWorker(config_data)
        self.worker.finished.connect(lambda results: self.on_simulation_finished(config_data, results))
        self.worker.error.connect(self.on_simulation_error)
        self.worker.start()

    def on_simulation_finished(self, config_data, results_data):
        """Triggered when the C++ backend completes successfully."""
        
        # Reset the run button
        self.settings_view.run_btn.setText("Run Simulation")
        self.settings_view.run_btn.setEnabled(True)

        # 1. Pass data to the Analysis View
        self.analysis_view.load_results(results_data)
        
        # 2. Add this run to the persistent History Sidebar
        self.sidebar.add_run_to_history(config_data, results_data)
        
        # 3. Switch the screen to the Analysis View dynamically
        self.view_stack.setCurrentWidget(self.analysis_view)

    def on_simulation_error(self, error_message):
        """Triggered if the C++ binary crashes or fails to execute."""
        self.settings_view.run_btn.setText("Run Simulation")
        self.settings_view.run_btn.setEnabled(True)
        
        QMessageBox.critical(self, "Execution Error", error_message)

    def show_settings(self):
        """Switches the view back to the configuration screen."""
        self.view_stack.setCurrentWidget(self.settings_view)

    def load_past_run(self, run_data):
        """Triggered when a user clicks a history item in the sidebar."""
        # run_data contains both 'config' and 'results'
        self.analysis_view.load_results(run_data["results"])
        self.view_stack.setCurrentWidget(self.analysis_view)


if __name__ == "__main__":
    # The application entry point
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())