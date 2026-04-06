# core/simulator.py
import subprocess
import os


class SimulatorRunner:
    def __init__(self):
        gui_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.workspace_root = os.path.abspath(os.path.join(gui_root, ".."))
        self.cs1_dir = os.path.join(self.workspace_root, "cs1")
        self.executable_path = os.path.join(self.cs1_dir, "cs1op")

    def compile_code(self):
        """Compiles simulator sources inside cs1 directory."""
        if not os.path.isdir(self.cs1_dir):
            return False, f"Compilation folder not found: {self.cs1_dir}"

        compile_command = [
            "g++",
            "main.cpp",
            "Cache.cpp",
            "CacheSet.cpp",
            "-o",
            "cs1op",
        ]

        try:
            subprocess.run(
                compile_command,
                cwd=self.cs1_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            return True, "Compilation successful."
        except subprocess.CalledProcessError as e:
            error_text = e.stderr.strip() or e.stdout.strip() or "Unknown compile error"
            return False, f"Compilation failed:\n{error_text}"

    def run_simulation(self, config):
        """Runs the compiled binary."""
        trace_file = config.get("trace_file")
        if not trace_file or not os.path.exists(trace_file):
            return False, "Error: Trace file not found."
        if not os.path.exists(self.executable_path):
            return False, "Executable not found. Compilation likely failed."

        trace_file_abs = os.path.abspath(trace_file)

        command = [
            self.executable_path,
            "--l1-size", config["l1_size"],
            "--l1-assoc", config["l1_assoc"],
            "--l2-size", config["l2_size"],
            "--l2-assoc", config["l2_assoc"],
            "--prefetch", config["prefetch"],
            "--policy", config["policy"],
            "--trace", trace_file_abs,
        ]

        try:
            result = subprocess.run(
                command,
                cwd=self.cs1_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            error_text = e.stderr.strip() or e.stdout.strip() or "Unknown runtime error"
            return False, f"Simulation crashed:\n{error_text}"
        except FileNotFoundError:
            return False, "Executable not found. Compilation likely failed."