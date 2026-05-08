from pathlib import Path
import subprocess

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
BINARY = ROOT_DIR / "src" / "cs1op"
TRACE_DIR = ROOT_DIR / "traces"

def run_sim(l1_size, l1_assoc, trace_file):
    trace_path = TRACE_DIR / trace_file

    if not BINARY.exists():
        raise FileNotFoundError(f"Binary not found: {BINARY}")
    if not trace_path.exists():
        raise FileNotFoundError(f"Trace file not found: {trace_path}")

    cmd = [
        str(BINARY),
        "--l1-size", str(l1_size),
        "--l1-assoc", str(l1_assoc),
        "--l2-size", str(L2_SIZE), # Make sure L2_SIZE, L2_ASSOC, PREFETCH, POLICY are defined if you use this standalone
        "--l2-assoc", str(L2_ASSOC),
        "--prefetch", PREFETCH,
        "--policy", POLICY,
        "--trace", trace_file,  
    ]

    print("CMD:", " ".join(cmd))

    result = subprocess.run(
        cmd,
        cwd=str(TRACE_DIR), # Run from the trace dir so it finds the file
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Run failed for {trace_file} | L1={l1_size}, assoc={l1_assoc}\n"
            f"STDERR:\n{result.stderr}\n"
            f"STDOUT:\n{result.stdout}"
        )

    return result.stdout