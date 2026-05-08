from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# -----------------------
# Paths
# -----------------------
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent  # Goes up to Parametric-Cache-Simulator

RESULTS_DIR = ROOT_DIR / "results"

# Point to the CSV inside the results folder
CSV_PATH = RESULTS_DIR / "cache_sweep_results.csv"


OUT_DIR = RESULTS_DIR / "analyze_out_cache_sweep"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------
# Load data
# -----------------------
df = pd.read_csv(CSV_PATH)

# Make trace names cleaner for plots
df["trace_file"] = df["trace_file"].astype(str).str.replace(".txt", "", regex=False)

# Convert useful numeric columns
for col in df.columns:
    if col not in ["trace_file", "prefetch", "policy"]:
        df[col] = pd.to_numeric(df[col], errors="ignore")

# -----------------------
# Helpers
# -----------------------
def plot_metric_vs_assoc(data, metric, ylabel, title_prefix, prefix):
    if metric not in data.columns:
        return

    for trace in data["trace_file"].dropna().unique():
        sub = data[data["trace_file"] == trace]

        plt.figure(figsize=(9, 6))
        for size in sorted(sub["l1_size"].dropna().unique()):
            temp = sub[sub["l1_size"] == size].sort_values("l1_assoc")
            if temp.empty:
                continue
            plt.plot(
                temp["l1_assoc"],
                temp[metric],
                marker="o",
                linewidth=2,
                label=f"{int(size // 1024)}KB"
            )

        plt.title(f"{title_prefix} vs Associativity ({trace})")
        plt.xlabel("Associativity")
        plt.ylabel(ylabel)
        plt.grid(True, alpha=0.3)
        plt.legend(title="L1 Size")
        plt.tight_layout()
        plt.savefig(OUT_DIR / f"{prefix}_{trace}.png", dpi=200)
        plt.close()

def plot_metric_vs_size(data, metric, ylabel, title_prefix, prefix):
    if metric not in data.columns:
        return

    for trace in data["trace_file"].dropna().unique():
        sub = data[data["trace_file"] == trace]

        plt.figure(figsize=(9, 6))
        for assoc in sorted(sub["l1_assoc"].dropna().unique()):
            temp = sub[sub["l1_assoc"] == assoc].sort_values("l1_size")
            if temp.empty:
                continue
            plt.plot(
                temp["l1_size"] / 1024,
                temp[metric],
                marker="o",
                linewidth=2,
                label=f"{int(assoc)}-way"
            )

        plt.title(f"{title_prefix} vs Cache Size ({trace})")
        plt.xlabel("L1 Size (KB)")
        plt.ylabel(ylabel)
        plt.grid(True, alpha=0.3)
        plt.legend(title="Associativity")
        plt.tight_layout()
        plt.savefig(OUT_DIR / f"{prefix}_{trace}.png", dpi=200)
        plt.close()

def plot_heatmap(data, metric, title_prefix, prefix):
    if metric not in data.columns:
        return

    for trace in data["trace_file"].dropna().unique():
        sub = data[data["trace_file"] == trace].copy()
        if sub.empty:
            continue

        pivot = sub.pivot_table(index="l1_assoc", columns="l1_size", values=metric, aggfunc="mean")
        pivot = pivot.sort_index().sort_index(axis=1)

        plt.figure(figsize=(9, 6))
        plt.imshow(pivot.values, aspect="auto")
        plt.colorbar(label=metric)
        plt.xticks(range(len(pivot.columns)), [f"{int(c // 1024)}K" for c in pivot.columns])
        plt.yticks(range(len(pivot.index)), [str(int(i)) for i in pivot.index])
        plt.xlabel("L1 Size")
        plt.ylabel("Associativity")
        plt.title(f"{title_prefix} Heatmap ({trace})")
        plt.tight_layout()
        plt.savefig(OUT_DIR / f"{prefix}_{trace}.png", dpi=200)
        plt.close()

def save_best_configs(data, metric, filename):
    if metric not in data.columns:
        return
    best_rows = []
    for trace in data["trace_file"].dropna().unique():
        sub = data[data["trace_file"] == trace].copy()
        sub = sub.sort_values(metric, ascending=True)
        best = sub.iloc[0].to_dict()
        best_rows.append(best)
    pd.DataFrame(best_rows).to_csv(OUT_DIR / filename, index=False)

def save_grouped_summary(data):
    cols = [
        "trace_file", "l1_size", "l1_assoc",
        "l1_d_hit_rate", "l1_d_miss_rate", "l1_d_amat",
        "l2_hit_rate", "l2_miss_rate", "l2_amat"
    ]
    keep = [c for c in cols if c in data.columns]
    summary = data[keep].copy()
    summary = summary.sort_values(["trace_file", "l1_size", "l1_assoc"])
    summary.to_csv(OUT_DIR / "full_summary_sorted.csv", index=False)

# -----------------------
# Core analysis
# -----------------------
# D-cache analysis
plot_metric_vs_assoc(df, "l1_d_amat", "AMAT", "D-Cache AMAT", "damat_vs_assoc")
plot_metric_vs_size(df, "l1_d_amat", "AMAT", "D-Cache AMAT", "damat_vs_size")
plot_metric_vs_assoc(df, "l1_d_hit_rate", "Hit Rate (%)", "D-Cache Hit Rate", "dhit_vs_assoc")
plot_metric_vs_size(df, "l1_d_hit_rate", "Hit Rate (%)", "D-Cache Hit Rate", "dhit_vs_size")
plot_metric_vs_assoc(df, "l1_d_miss_rate", "Miss Rate (%)", "D-Cache Miss Rate", "dmiss_vs_assoc")
plot_metric_vs_size(df, "l1_d_miss_rate", "Miss Rate (%)", "D-Cache Miss Rate", "dmiss_vs_size")
plot_metric_vs_assoc(df, "l1_d_write_backs", "Write Backs", "D-Cache Write Backs", "dwb_vs_assoc")
plot_metric_vs_size(df, "l1_d_write_backs", "Write Backs", "D-Cache Write Backs", "dwb_vs_size")
plot_heatmap(df, "l1_d_amat", "D-Cache AMAT", "damat_heatmap")

# L2 analysis
plot_metric_vs_assoc(df, "l2_amat", "AMAT", "L2 AMAT", "l2amat_vs_assoc")
plot_metric_vs_size(df, "l2_amat", "AMAT", "L2 AMAT", "l2amat_vs_size")
plot_metric_vs_assoc(df, "l2_hit_rate", "Hit Rate (%)", "L2 Hit Rate", "l2hit_vs_assoc")
plot_metric_vs_size(df, "l2_hit_rate", "Hit Rate (%)", "L2 Hit Rate", "l2hit_vs_size")
plot_metric_vs_assoc(df, "l2_miss_rate", "Miss Rate (%)", "L2 Miss Rate", "l2miss_vs_assoc")
plot_metric_vs_size(df, "l2_miss_rate", "Miss Rate (%)", "L2 Miss Rate", "l2miss_vs_size")
plot_metric_vs_assoc(df, "l2_write_backs", "Write Backs", "L2 Write Backs", "l2wb_vs_assoc")
plot_metric_vs_size(df, "l2_write_backs", "Write Backs", "L2 Write Backs", "l2wb_vs_size")
plot_heatmap(df, "l2_amat", "L2 AMAT", "l2amat_heatmap")

# Best config summaries
save_best_configs(df, "l1_d_amat", "best_configs_dcache_amat.csv")
save_best_configs(df, "l2_amat", "best_configs_l2_amat.csv")
save_grouped_summary(df)

# -----------------------
# Simple printed summary
# -----------------------
print("\nSaved plots and CSV summaries to:", OUT_DIR)
print("\nBest D-cache AMAT per trace:")
if "l1_d_amat" in df.columns:
    for trace in df["trace_file"].dropna().unique():
        sub = df[df["trace_file"] == trace].sort_values("l1_d_amat", ascending=True)
        best = sub.iloc[0]
        print(
            f"{trace}: AMAT={best['l1_d_amat']:.4f}, "
            f"L1={int(best['l1_size'])}B, assoc={int(best['l1_assoc'])}, "
            f"hit_rate={best['l1_d_hit_rate']:.4f}%"
        )
