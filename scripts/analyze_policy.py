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
CSV_PATH = RESULTS_DIR / "policy_sweep_results.csv"

OUT_DIR = RESULTS_DIR / "analyze_out_policy"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------
# Load data
# -----------------------
POLICY_ORDER = ["LRU", "FIFO", "LFU", "Random"]

df = pd.read_csv(CSV_PATH)
# Clean up types
for col in df.columns:
    if col not in ["trace_file", "policy", "prefetch"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df["trace_file"] = df["trace_file"].astype(str).str.replace(".txt", "", regex=False)

def sorted_policies(policies):
    return [p for p in POLICY_ORDER if p in policies]

def plot_metric_vs_assoc_by_policy(metric, ylabel, title_prefix, file_prefix):
    for trace in sorted(df["trace_file"].dropna().unique()):
        sub_trace = df[df["trace_file"] == trace].copy()
        if sub_trace.empty or metric not in sub_trace.columns:
            continue

        for size in sorted(sub_trace["l1_size"].dropna().unique()):
            temp = sub_trace[sub_trace["l1_size"] == size].copy()
            if temp.empty:
                continue

            plt.figure(figsize=(9, 6))

            for policy in sorted_policies(temp["policy"].dropna().unique()):
                p = temp[temp["policy"] == policy].sort_values("l1_assoc")
                if p.empty:
                    continue
                plt.plot(
                    p["l1_assoc"],
                    p[metric],
                    marker="o",
                    linewidth=2,
                    label=policy
                )

            plt.title(f"{title_prefix} ({trace}, {int(size // 1024)}KB L1)")
            plt.xlabel("Associativity")
            plt.ylabel(ylabel)
            plt.grid(True, alpha=0.3)
            plt.legend(title="Policy")
            plt.tight_layout()
            plt.savefig(OUT_DIR / f"{file_prefix}_{trace}_{int(size // 1024)}KB.png", dpi=200)
            plt.close()

def plot_metric_by_policy_bar(metric, ylabel, title_prefix, file_prefix):
    for trace in sorted(df["trace_file"].dropna().unique()):
        sub = df[df["trace_file"] == trace].copy()
        if sub.empty or metric not in sub.columns:
            continue

        avg = sub.groupby("policy", as_index=True)[metric].mean().reindex(POLICY_ORDER)
        avg = avg.dropna()

        plt.figure(figsize=(8, 5))
        plt.bar(avg.index, avg.values)
        plt.title(f"{title_prefix} ({trace})")
        plt.xlabel("Policy")
        plt.ylabel(ylabel)
        plt.grid(axis="y", alpha=0.3)
        plt.tight_layout()
        plt.savefig(OUT_DIR / f"{file_prefix}_{trace}.png", dpi=200)
        plt.close()

def save_best_policy_tables():
    rows = []
    for trace in sorted(df["trace_file"].dropna().unique()):
        sub_trace = df[df["trace_file"] == trace].copy()
        for size in sorted(sub_trace["l1_size"].dropna().unique()):
            sub_size = sub_trace[sub_trace["l1_size"] == size].copy()
            for assoc in sorted(sub_size["l1_assoc"].dropna().unique()):
                grp = sub_size[sub_size["l1_assoc"] == assoc].copy()
                if grp.empty:
                    continue

                best = grp.sort_values("l1_d_amat", ascending=True).iloc[0].to_dict()
                rows.append({
                    "trace_file": best.get("trace_file"),
                    "l1_size": best.get("l1_size"),
                    "l1_assoc": best.get("l1_assoc"),
                    "best_policy": best.get("policy"),
                    "best_l1_d_amat": best.get("l1_d_amat"),
                    "best_l1_d_hit_rate": best.get("l1_d_hit_rate"),
                    "best_l1_d_miss_rate": best.get("l1_d_miss_rate"),
                    "best_l1_d_write_backs": best.get("l1_d_write_backs"),
                    "l2_amat": best.get("l2_amat"),
                    "l2_hit_rate": best.get("l2_hit_rate"),
                    "l2_miss_rate": best.get("l2_miss_rate"),
                })

    if rows:
        out = pd.DataFrame(rows).sort_values(["trace_file", "l1_size", "l1_assoc"])
        out.to_csv(OUT_DIR / "best_policy_by_setting.csv", index=False)

        win_counts = (
            out.groupby(["trace_file", "best_policy"])
               .size()
               .reset_index(name="wins")
               .sort_values(["trace_file", "wins"], ascending=[True, False])
        )
        win_counts.to_csv(OUT_DIR / "policy_win_counts.csv", index=False)

def save_trace_level_summary():
    rows = []
    for trace in sorted(df["trace_file"].dropna().unique()):
        sub = df[df["trace_file"] == trace].copy()
        if sub.empty:
            continue

        summary = sub.groupby("policy", as_index=False).agg({
            "l1_d_amat": "mean",
            "l1_d_hit_rate": "mean",
            "l1_d_miss_rate": "mean",
            "l1_d_write_backs": "mean",
            "l2_amat": "mean",
            "l2_hit_rate": "mean",
            "l2_miss_rate": "mean",
            "l2_total_accesses": "mean",
        })
        summary.insert(0, "trace_file", trace)
        rows.append(summary)

    if rows:
        out = pd.concat(rows, ignore_index=True)
        out.to_csv(OUT_DIR / "trace_level_policy_summary.csv", index=False)

# Main graphs
plot_metric_vs_assoc_by_policy("l1_d_amat", "AMAT", "D-Cache AMAT vs Policy", "damat_policy")
plot_metric_vs_assoc_by_policy("l1_d_miss_rate", "Miss Rate (%)", "D-Cache Miss Rate vs Policy", "dmiss_policy")
plot_metric_vs_assoc_by_policy("l1_d_hit_rate", "Hit Rate (%)", "D-Cache Hit Rate vs Policy", "dhit_policy")
plot_metric_vs_assoc_by_policy("l1_d_write_backs", "Write Backs", "D-Cache Write Backs vs Policy", "dwb_policy")

# Summary bars
plot_metric_by_policy_bar("l1_d_amat", "Average AMAT", "Average D-Cache AMAT by Policy", "avg_damat_policy")
plot_metric_by_policy_bar("l1_d_miss_rate", "Average Miss Rate (%)", "Average D-Cache Miss Rate by Policy", "avg_dmiss_policy")
plot_metric_by_policy_bar("l1_d_write_backs", "Average Write Backs", "Average D-Cache Write Backs by Policy", "avg_dwb_policy")

# CSV summaries
save_best_policy_tables()
save_trace_level_summary()

print(f"Saved analysis to: {OUT_DIR}")
print("\nTrace-level average AMAT by policy:")
for trace in sorted(df["trace_file"].dropna().unique()):
    sub = df[df["trace_file"] == trace].copy()
    avg = sub.groupby("policy")["l1_d_amat"].mean().reindex(POLICY_ORDER).dropna()
    print(f"\n{trace}:")
    for policy, value in avg.items():
        print(f"  {policy}: {value:.4f}")
