# simulator_backend.py

import subprocess
import os
from PyQt6.QtCore import QThread, pyqtSignal

class SimulatorWorker(QThread):
    # Signals to communicate back to the main GUI thread safely
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        try:
            # 1. Construct the Path
            # Assuming main.py is run from the project root, and the executable is inside the 'cs1' folder
            executable_path = os.path.join(".", "cs1", "cs1op") 
            
            # Add .exe extension if running on Windows
            if os.name == 'nt' and not executable_path.endswith('.exe'):
                executable_path += '.exe'

            trace_file = self.config.get("trace_file")
            if not trace_file:
                self.error.emit("Error: No trace file was selected!")
                return

            # 2. Build the Command Array exactly as you specified
            cmd = [
                executable_path,
                "--l1-size", self.config["l1_size"],
                "--l1-assoc", self.config["l1_assoc"],
                "--l2-size", self.config["l2_size"],
                "--l2-assoc", self.config["l2_assoc"],
                "--policy", self.config["policy"].upper(),
                "--prefetch", self.config["prefetch"].upper(),
                "--trace", trace_file
            ]

            # 3. Execute Silently
            # CREATE_NO_WINDOW ensures no terminal popups on Windows
            creation_flags = 0
            if os.name == 'nt':
                creation_flags = subprocess.CREATE_NO_WINDOW

            process = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                creationflags=creation_flags
            )

            if process.returncode != 0:
                # If your C++ code crashes or throws an error, we catch it here
                self.error.emit(f"Execution failed with error:\n{process.stderr}")
                return

            # 4. Parse the standard output from the C++ file
            parsed_results = self.parse_output(process.stdout)
            
            # Emit the clean dictionary back to the GUI to update the tables/graphs
            self.finished.emit(parsed_results)

        except Exception as e:
            self.error.emit(f"A system error occurred: {str(e)}")

    def parse_output(self, stdout):
        """
        Parses the raw text output (cout) from your C++ program into a dictionary.
        *NOTE*: You may need to tweak this logic to match your exact C++ print format.
        """
        results = {}
        
        # Split output line by line
        lines = stdout.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Basic parser: looks for "Key: Value" or "Key = Value"
            if ":" in line:
                key, val = line.split(":", 1)
                results[key.strip()] = val.strip()
            elif "=" in line:
                key, val = line.split("=", 1)
                results[key.strip()] = val.strip()
            else:
                # If it's an unformatted string, just save it sequentially
                results[f"Log_{len(results)}"] = line

        # Fallback to make sure our sidebar logic doesn't break if 'Trace Count' isn't printed
        if "Trace Count" not in results:
             # Just a placeholder, you can calculate real trace lines here if needed
            results["Trace Count"] = "Simulation Finished"

        return results