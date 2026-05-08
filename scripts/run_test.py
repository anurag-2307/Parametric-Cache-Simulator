from pathlib import Path
import csv
import itertools
import subprocess
import re
import sys

# -----------------------
# Paths
# -----------------------
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

TRACE_DIR = ROOT_DIR / "traces"
BINARY = ROOT_DIR / "src" / "cs1op"
OUT_CSV = ROOT_DIR / "results" / "cache_sweep_results.csv"
# Sweep grid for associativity-vs-size
L1_SIZES = [8192, 16384, 32768]
L1_ASSOCS = [1, 2, 4, 8]

# Keep these fixed for this experiment
L2_SIZE = 1048576
L2_ASSOC = 8
PREFETCH = "OFF"
POLICY = "LRU"

TRACE_FILES = [
    "trace_rd.txt",
    "trace_sq.txt",
    "trace_str.txt",
]

SECTION_ALIASES = {
    "Instruction Cache (I-Cache) :": "l1_i",
    "Data Cache (D-Cache) :": "l1_d",
    "Unified L2 Cache :": "l2",
}

INT_KEYS = {
    "Total Accesses",
    "Reads",
    "Writes",
    "Cache Hits",
    "Cache Misses",
    "Write Backs",
    "Split Accesses",
}

FLOAT_KEYS = {
    "Hit Rate",
    "Miss Rate",
    "AMAT",
}

def parse_output(stdout: str) -> dict:
    data = {
        "l1_i_total_accesses": None,
        "l1_i_reads": None,
        "l1_i_writes": None,
        "l1_i_hits": None,
        "l1_i_misses": None,
        "l1_i_write_backs": None,
        "l1_i_hit_rate": None,
        "l1_i_miss_rate": None,
        "l1_i_amat": None,
        "l1_i_split_accesses": None,

        "l1_d_total_accesses": None,
        "l1_d_reads": None,
        "l1_d_writes": None,
        "l1_d_hits": None,
        "l1_d_misses": None,
        "l1_d_write_backs": None,
        "l1_d_hit_rate": None,
        "l1_d_miss_rate": None,
        "l1_d_amat": None,
        "l1_d_split_accesses": None,

        "l2_total_accesses": None,
        "l2_reads": None,
        "l2_writes": None,
        "l2_hits": None,
        "l2_misses": None,
        "l2_write_backs": None,
        "l2_hit_rate": None,
        "l2_miss_rate": None,
        "l2_amat": None,
        "l2_split_accesses": None,
    }

    current_section = None

    for raw_line in stdout.splitlines():
        line = raw_line.strip()

        if line in SECTION_ALIASES:
            current_section = SECTION_ALIASES[line]
            continue

        if current_section is None:
            continue

        if ":" not in line:
            continue

        key, value = [x.strip() for x in line.split(":", 1)]

        if key not in INT_KEYS and key not in FLOAT_KEYS:
            continue

        if key in INT_KEYS:
            try:
                parsed = int(float(value.replace(",", "")))
            except ValueError:
                continue
        else:
            try:
                parsed = float(value.replace("%", "").strip())
            except ValueError:
                continue

        prefix = current_section
        if key == "Total Accesses":
            data[f"{prefix}_total_accesses"] = parsed
        elif key == "Reads":
            data[f"{prefix}_reads"] = parsed
        elif key == "Writes":
            data[f"{prefix}_writes"] = parsed
        elif key == "Cache Hits":
            data[f"{prefix}_hits"] = parsed
        elif key == "Cache Misses":
            data[f"{prefix}_misses"] = parsed
        elif key == "Write Backs":
            data[f"{prefix}_write_backs"] = parsed
        elif key == "Hit Rate":
            data[f"{prefix}_hit_rate"] = parsed
        elif key == "Miss Rate":
            data[f"{prefix}_miss_rate"] = parsed
        elif key == "AMAT":
            data[f"{prefix}_amat"] = parsed
        elif key == "Split Accesses":
            data[f"{prefix}_split_accesses"] = parsed

    return data

def run_sim(trace_file: str, l1_size: int, l1_assoc: int) -> str:
    binary = str(BINARY.resolve())
    trace_path = TRACE_DIR / trace_file

    if not BINARY.exists():
        raise FileNotFoundError(f"Binary not found: {BINARY}")
    if not trace_path.exists():
        raise FileNotFoundError(f"Trace file not found: {trace_path}")

    cmd = [
        binary,
        "--l1-size", str(l1_size),
        "--l1-assoc", str(l1_assoc),
        "--l2-size", str(L2_SIZE),
        "--l2-assoc", str(L2_ASSOC),
        "--prefetch", PREFETCH,
        "--policy", POLICY,
        "--trace", trace_file,   # keep this as filename; cwd is TRACE_DIR
    ]

    result = subprocess.run(
        cmd,
        cwd=str(TRACE_DIR),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Run failed for trace={trace_file}, L1={l1_size}, assoc={l1_assoc}\n"
            f"STDERR:\n{result.stderr}\n"
            f"STDOUT:\n{result.stdout}"
        )

    return result.stdout

def write_row(csv_path: Path, row: dict):
    file_exists = csv_path.exists()
    with csv_path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def main():
    if not BINARY.exists():
        print(f"Missing binary: {BINARY}", file=sys.stderr)
        sys.exit(1)

    for trace_file, l1_size, l1_assoc in itertools.product(TRACE_FILES, L1_SIZES, L1_ASSOCS):
        print(f"Running trace={trace_file}, L1 size={l1_size}, assoc={l1_assoc}")
        stdout = run_sim(trace_file, l1_size, l1_assoc)
        metrics = parse_output(stdout)

        row = {
            "trace_file": trace_file,
            "l1_size": l1_size,
            "l1_assoc": l1_assoc,
            "l2_size": L2_SIZE,
            "l2_assoc": L2_ASSOC,
            "prefetch": PREFETCH,
            "policy": POLICY,
            **metrics,
        }

        write_row(OUT_CSV, row)

    print(f"Saved results to {OUT_CSV}")

if __name__ == "__main__":
    main()
