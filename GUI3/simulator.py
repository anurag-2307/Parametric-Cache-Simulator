# simulator.py
# ─────────────────────────────────────────────────────────────────────────────
# Builds the ./cs1op command, runs it in a subprocess, captures stdout,
# and parses every metric into a clean structured dict.
# ─────────────────────────────────────────────────────────────────────────────

import os
import re
import time
import subprocess
from typing import Optional
from dataclasses import dataclass, field, asdict


# ── Config dataclass ──────────────────────────────────────────────────────────
@dataclass
class SimConfig:
    l1_size:    int   = 32768
    l1_assoc:   int   = 8
    l2_size:    int   = 2097152
    l2_assoc:   int   = 16
    policy:     str   = "LRU"
    prefetch:   str   = "ON"
    binary:     str   = "./cs1op"
    trace_path: str   = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ── Per-cache metric block ────────────────────────────────────────────────────
@dataclass
class CacheMetrics:
    name:              str   = ""
    total_accesses:    int   = 0
    reads:             int   = 0
    writes:            int   = 0
    cache_hits:        int   = 0
    cache_misses:      int   = 0
    write_backs:       int   = 0
    hit_rate:          float = 0.0   # percentage
    miss_rate:         float = 0.0   # percentage
    amat:              float = 0.0
    split_accesses:    int   = 0
    replacement_policy: str  = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ── Full simulation result ────────────────────────────────────────────────────
@dataclass
class SimResult:
    config:               SimConfig      = field(default_factory=SimConfig)
    command:              str            = ""
    raw_output:           str            = ""
    duration_s:           float          = 0.0
    status:               str            = "success"  # "success" | "error"
    error_message:        str            = ""

    i_cache:              CacheMetrics   = field(default_factory=CacheMetrics)
    d_cache:              CacheMetrics   = field(default_factory=CacheMetrics)
    l2_cache:             CacheMetrics   = field(default_factory=CacheMetrics)
    modified_instructions: int           = 0

    def to_metrics_dict(self) -> dict:
        """Flat dict suitable for JSON storage in DB."""
        return {
            "i_cache":               self.i_cache.to_dict(),
            "d_cache":               self.d_cache.to_dict(),
            "l2_cache":              self.l2_cache.to_dict(),
            "modified_instructions": self.modified_instructions,
        }

    def to_config_dict(self) -> dict:
        return {
            "l1_size":   self.config.l1_size,
            "l1_assoc":  self.config.l1_assoc,
            "l2_size":   self.config.l2_size,
            "l2_assoc":  self.config.l2_assoc,
            "policy":    self.config.policy,
            "prefetch":  self.config.prefetch,
        }


# ── Command builder ───────────────────────────────────────────────────────────
def build_command(cfg: SimConfig) -> str:
    """
    Returns the full shell command string, e.g.:
    ./cs1op --l1-size 32768 --l1-assoc 8 --l2-size 2097152 --l2-assoc 16
            --prefetch ON --policy LRU --trace ../trace_rd.txt
    """
    parts = [
        cfg.binary,
        "--l1-size",   str(cfg.l1_size),
        "--l1-assoc",  str(cfg.l1_assoc),
        "--l2-size",   str(cfg.l2_size),
        "--l2-assoc",  str(cfg.l2_assoc),
        "--prefetch",  cfg.prefetch,
        "--policy",    cfg.policy,
        "--trace",     cfg.trace_path,
    ]
    return " ".join(parts)


def _compile_runtime_binary() -> tuple[bool, str, str]:
    """
    Compile the simulator binary in cs1/ at runtime.
    Returns (ok, binary_path, error_message).
    """
    gui3_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.abspath(os.path.join(gui3_dir, ".."))
    cs1_dir = os.path.join(workspace_root, "cs1")
    binary_path = os.path.join(cs1_dir, "cs1op")

    if not os.path.isdir(cs1_dir):
        return False, "", f"Compilation folder not found: '{cs1_dir}'"

    compile_cmd = [
        "g++",
        "main.cpp",
        "Cache.cpp",
        "CacheSet.cpp",
        "-o",
        "cs1op",
    ]

    try:
        proc = subprocess.run(
            compile_cmd,
            cwd=cs1_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        _ = proc  # keep shape explicit; stdout/stderr are not needed on success
        return True, binary_path, ""
    except FileNotFoundError:
        return False, "", "Compiler not found: g++ is not installed or not in PATH."
    except subprocess.CalledProcessError as e:
        err = e.stderr.strip() or e.stdout.strip() or "Unknown compile error"
        return False, "", f"Compilation failed:\n{err}"


# ── Output parser ─────────────────────────────────────────────────────────────
def _parse_int(value: str) -> int:
    try:
        return int(value.replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0


def _parse_float(value: str) -> float:
    try:
        return float(value.replace("%", "").replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0.0


def _parse_cache_block(block: str, name: str) -> CacheMetrics:
    """
    Parse one cache section (I-Cache, D-Cache, or L2) from the raw text block.
    Handles both '  :  value' and ':value' spacing variants.
    """
    m = CacheMetrics(name=name)

    for line in block.splitlines():
        if ":" not in line:
            continue

        key_raw, value_raw = line.split(":", 1)
        key = " ".join(key_raw.strip().lower().split())
        value = value_raw.strip()

        if key == "total accesses":
            m.total_accesses = _parse_int(value)
        elif key == "reads":
            m.reads = _parse_int(value)
        elif key == "writes":
            m.writes = _parse_int(value)
        elif key == "cache hits":
            m.cache_hits = _parse_int(value)
        elif key == "cache misses":
            m.cache_misses = _parse_int(value)
        elif key == "write backs":
            m.write_backs = _parse_int(value)
        elif key == "hit rate":
            m.hit_rate = _parse_float(value)
        elif key == "miss rate":
            m.miss_rate = _parse_float(value)
        elif key == "amat":
            m.amat = _parse_float(value)
        elif key == "split accesses":
            m.split_accesses = _parse_int(value)
        elif key == "replacement policy used":
            m.replacement_policy = value.split()[0] if value else ""

    return m


def parse_output(raw: str) -> tuple[CacheMetrics, CacheMetrics, CacheMetrics, int]:
    """
    Splits the raw simulator stdout into the three cache sections and parses each.
    Returns (i_cache, d_cache, l2_cache, modified_instructions).
    """

    # ── Split into sections using the separator lines ─────────────────────────
    # The output uses lines of '=' as dividers between sections.
    # We find the three named sections by header keywords.

    lines = raw.splitlines()

    sections: dict[str, list[str]] = {
        "icache": [],
        "dcache": [],
        "l2":     [],
    }

    current = None
    for line in lines:
        stripped = line.strip()

        # Detect section headers
        if re.search(r"Instruction Cache\s*\(I.Cache\)", stripped, re.IGNORECASE):
            current = "icache"
            continue
        elif re.search(r"Data Cache\s*\(D.Cache\)", stripped, re.IGNORECASE):
            current = "dcache"
            continue
        elif re.search(r"Unified L2 Cache", stripped, re.IGNORECASE):
            current = "l2"
            continue

        # Stop accumulating at separator lines (all '=' chars)
        if re.match(r"^=+$", stripped) and current is not None:
            # Don't reset — let the next header line switch the section
            pass

        if current is not None:
            sections[current].append(line)

    i_text  = "\n".join(sections["icache"])
    d_text  = "\n".join(sections["dcache"])
    l2_text = "\n".join(sections["l2"])

    i_cache  = _parse_cache_block(i_text,  "I-Cache")
    d_cache  = _parse_cache_block(d_text,  "D-Cache")
    l2_cache = _parse_cache_block(l2_text, "L2 Cache")

    # ── Modified Instructions ─────────────────────────────────────────────────
    mod_instr = 0
    for line in raw.splitlines():
        if "MODIFIED" not in line.upper():
            continue
        nums = re.findall(r"[0-9,]+", line)
        if nums:
            mod_instr = _parse_int(nums[-1])
            break

    return i_cache, d_cache, l2_cache, mod_instr


# ── Main runner ───────────────────────────────────────────────────────────────
def run_simulation(cfg: SimConfig, timeout: int = 120) -> SimResult:
    """
    Execute the simulator binary with the given config.
    Returns a fully populated SimResult.

    Raises no exceptions — all errors are captured in SimResult.status / error_message.
    """
    result = SimResult(config=cfg)

    # Validate inputs before running
    if not cfg.trace_path or not os.path.isfile(cfg.trace_path):
        result.status        = "error"
        result.error_message = f"Trace file not found: '{cfg.trace_path}'"
        return result

    # Compile simulator binary at runtime for each Run Simulation action.
    ok, binary_path, compile_err = _compile_runtime_binary()
    if not ok:
        result.status = "error"
        result.error_message = compile_err
        return result

    # Build command
    cmd = build_command(SimConfig(
        l1_size=cfg.l1_size, l1_assoc=cfg.l1_assoc,
        l2_size=cfg.l2_size, l2_assoc=cfg.l2_assoc,
        policy=cfg.policy,   prefetch=cfg.prefetch,
        binary=binary_path,
        trace_path=cfg.trace_path,
    ))
    result.command = cmd

    # Run
    t_start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.dirname(os.path.abspath(cfg.trace_path)),
        )
        t_end = time.perf_counter()
        result.duration_s = round(t_end - t_start, 3)

        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        result.raw_output = stdout + ("\n" + stderr if stderr.strip() else "")

        if proc.returncode != 0:
            result.status        = "error"
            result.error_message = (
                f"Simulator exited with code {proc.returncode}.\n"
                f"{stderr.strip() or 'No error message from binary.'}"
            )
            return result

        # Parse
        i_cache, d_cache, l2_cache, mod_instr = parse_output(stdout)
        result.i_cache               = i_cache
        result.d_cache               = d_cache
        result.l2_cache              = l2_cache
        result.modified_instructions = mod_instr
        result.status                = "success"

    except subprocess.TimeoutExpired:
        result.status        = "error"
        result.error_message = f"Simulation timed out after {timeout} seconds."

    
    except Exception as e:
        result.status        = "error"
        result.error_message = f"Unexpected error: {type(e).__name__}: {e}"

    return result


# ── Smoke test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    SAMPLE_OUTPUT = """
================================================================================

Instruction Cache (I-Cache) :
---- Cache Simulation Results : L1 cache ----
Total Accesses : 2077327
Reads          : 2077327
Writes         : 0
Cache Hits     : 2061245
Cache Misses   : 16082
Write Backs    : 0
Hit Rate       : 99.2258 %
Miss Rate      : 0.774168 %
AMAT           : 4.23955
Split Accesses : 107303

Replacement Policy used : LRU
================================================================================

Data Cache (D-Cache) :
---- Cache Simulation Results : L1 cache ----
Total Accesses : 729824
Reads          : 533156
Writes         : 196668
Cache Hits     : 629723
Cache Misses   : 100101
Write Backs    : 34673
Hit Rate       : 86.2842 %
Miss Rate      : 13.7158 %
AMAT           : 7.50155
Split Accesses : 148

Replacement Policy used : LRU
================================================================================

Unified L2 Cache :
---- Cache Simulation Results : L2 cache ----
Total Accesses : 236028
Reads          : 201355
Writes         : 34673
Cache Hits     : 221845
Cache Misses   : 14183
Write Backs    : 1588
Hit Rate       : 93.991 %
Miss Rate      : 6.00903 %
AMAT           : 27.0181
Split Accesses : 0

Replacement Policy used : LRU
================================================================================

MODIFIED INSTRUCTIONS : 10194
"""
    i, d, l2, mod = parse_output(SAMPLE_OUTPUT)
    print("=== I-Cache ===")
    for k, v in i.to_dict().items():
        print(f"  {k:25s}: {v}")
    print("\n=== D-Cache ===")
    for k, v in d.to_dict().items():
        print(f"  {k:25s}: {v}")
    print("\n=== L2 Cache ===")
    for k, v in l2.to_dict().items():
        print(f"  {k:25s}: {v}")
    print(f"\n  Modified Instructions  : {mod}")