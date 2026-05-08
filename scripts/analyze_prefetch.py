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
CSV_PATH = RESULTS_DIR / "prefetch_sweep_results.csv"

OUT_DIR = RESULTS_DIR / "analyze_out_prefetch"
OUT_DIR.mkdir(parents=True, exist_ok=True)
df = pd.read_csv(CSV_PATH)

# Clean up types
for col in df.columns:
    if col not in ["trace_file", "prefetch", "policy"]:
        df[col] = pd.to_numeric(df[col], errors="ignore")

df["trace_file"] = df["trace_file"].astype(str).str.replace(".txt", "", regex=False)

def save_lineplot(metric, ylabel, title_prefix, filename_prefix):
    for trace in sorted(df["trace_file"].dropna().unique()):
        sub = df[df["trace_file"] == trace].copy()
        if sub.empty or metric not in sub.columns:
            continue

        fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
        for ax, prefetch in zip(axes, ["OFF", "ON"]):
            part = sub[sub["prefetch"] == prefetch]
            if part.empty:
                continue

            for size in sorted(part["l1_size"].dropna().unique()):
                temp = part[part["l1_size"] == size].sort_values("l1_assoc")
                ax.plot(
                    temp["l1_assoc"],
                    temp[metric],
                    marker="o",
                    linewidth=2,
                    label=f"{int(size // 1024)}KB"
                )

            ax.set_title(f"{prefetch}")
            ax.set_xlabel("Associativity")
            ax.grid(True, alpha=0.3)
            ax.legend(title="L1 Size")

        axes[0].set_ylabel(ylabel)
        fig.suptitle(f"{title_prefix} ({trace})")
        fig.tight_layout()
        fig.savefig(OUT_DIR / f"{filename_prefix}_{trace}.png", dpi=200)
        plt.close(fig)

def save_delta_heatmap(metric, ylabel, title_prefix, filename_prefix):
    for trace in sorted(df["trace_file"].dropna().unique()):
        sub = df[df["trace_file"] == trace].copy()
        off = sub[sub["prefetch"] == "OFF"][["l1_size", "l1_assoc", metric]].rename(columns={metric: "off"})
        on = sub[sub["prefetch"] == "ON"][["l1_size", "l1_assoc", metric]].rename(columns={metric: "on"})

        merged = pd.merge(off, on, on=["l1_size", "l1_assoc"], how="inner")
        if merged.empty:
            continue

        merged["delta"] = merged["off"] - merged["on"]

        pivot = merged.pivot_table(index="l1_assoc", columns="l1_size", values="delta", aggfunc="mean")
        pivot = pivot.sort_index().sort_index(axis=1)

        fig, ax = plt.subplots(figsize=(8, 5))
        im = ax.imshow(pivot.values, aspect="auto")
        fig.colorbar(im, ax=ax, label=f"OFF - ON ({ylabel})")

        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels([f"{int(c // 1024)}KB" for c in pivot.columns])
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels([str(int(i)) for i in pivot.index])
        ax.set_xlabel("L1 Size")
        ax.set_ylabel("Associativity")
        ax.set_title(f"{title_prefix} Delta Heatmap ({trace})")

        fig.tight_layout()
        fig.savefig(OUT_DIR / f"{filename_prefix}_{trace}.png", dpi=200)
        plt.close(fig)

def save_summary_csv():
    rows = []
    for trace in sorted(df["trace_file"].dropna().unique()):
        sub = df[df["trace_file"] == trace].copy()
        off = sub[sub["prefetch"] == "OFF"]
        on = sub[sub["prefetch"] == "ON"]

        joined = pd.merge(
            off,
            on,
            on=["trace_file", "l1_size", "l1_assoc", "l2_size", "l2_assoc", "policy"],
            suffixes=("_off", "_on"),
            how="inner",
        )

        if joined.empty:
            continue

        joined["amat_delta"] = joined["l1_d_amat_off"] - joined["l1_d_amat_on"]
        joined["amat_improvement_pct"] = (joined["amat_delta"] / joined["l1_d_amat_off"]) * 100.0
        joined["hitrate_delta"] = joined["l1_d_hit_rate_on"] - joined["l1_d_hit_rate_off"]
        joined["missrate_delta"] = joined["l1_d_miss_rate_off"] - joined["l1_d_miss_rate_on"]
        joined["l2_access_delta"] = joined["l2_total_accesses_on"] - joined["l2_total_accesses_off"]

        keep = [
            "trace_file", "l1_size", "l1_assoc", "policy",
            "l1_d_amat_off", "l1_d_amat_on", "amat_delta", "amat_improvement_pct",
            "l1_d_hit_rate_off", "l1_d_hit_rate_on", "hitrate_delta",
            "l1_d_miss_rate_off", "l1_d_miss_rate_on", "missrate_delta",
            "l2_total_accesses_off", "l2_total_accesses_on", "l2_access_delta",
            "l2_amat_off", "l2_amat_on"
        ]
        keep = [c for c in keep if c in joined.columns]
        rows.append(joined[keep])

    if rows:
        out = pd.concat(rows, ignore_index=True)
        out = out.sort_values(["trace_file", "l1_size", "l1_assoc"])
        out.to_csv(OUT_DIR / "prefetch_comparison_summary.csv", index=False)

        best = (
            out.sort_values("amat_delta", ascending=False)
               .groupby("trace_file", as_index=False)
               .head(1)
        )
        best.to_csv(OUT_DIR / "best_prefetch_gain_by_trace.csv", index=False)

def print_summary():
    if "l1_d_amat" not in df.columns:
        return

    print("\nBest average AMAT improvement by trace:")
    for trace in sorted(df["trace_file"].dropna().unique()):
        sub = df[df["trace_file"] == trace].copy()
        off = sub[sub["prefetch"] == "OFF"]
        on = sub[sub["prefetch"] == "ON"]

        joined = pd.merge(
            off,
            on,
            on=["trace_file", "l1_size", "l1_assoc", "l2_size", "l2_assoc", "policy"],
            suffixes=("_off", "_on"),
            how="inner",
        )
        if joined.empty:
            continue

        joined["amat_delta"] = joined["l1_d_amat_off"] - joined["l1_d_amat_on"]
        best = joined.sort_values("amat_delta", ascending=False).iloc[0]

        print(
            f"{trace}: delta={best['amat_delta']:.4f}, "
            f"L1={int(best['l1_size'])}B, assoc={int(best['l1_assoc'])}, "
            f"OFF={best['l1_d_amat_off']:.4f}, ON={best['l1_d_amat_on']:.4f}"
        )

# Core graphs
save_lineplot("l1_d_amat", "AMAT", "D-Cache AMAT vs Prefetch", "damat_prefetch_compare")
save_lineplot("l1_d_hit_rate", "Hit Rate (%)", "D-Cache Hit Rate vs Prefetch", "dhit_prefetch_compare")
save_lineplot("l1_d_miss_rate", "Miss Rate (%)", "D-Cache Miss Rate vs Prefetch", "dmiss_prefetch_compare")
save_lineplot("l2_total_accesses", "L2 Total Accesses", "L2 Traffic vs Prefetch", "l2access_prefetch_compare")
save_lineplot("l2_amat", "AMAT", "L2 AMAT vs Prefetch", "l2amat_prefetch_compare")

# Delta views
save_delta_heatmap("l1_d_amat", "AMAT", "D-Cache AMAT", "damat_delta_heatmap")
save_delta_heatmap("l1_d_hit_rate", "Hit Rate (%)", "D-Cache Hit Rate", "dhit_delta_heatmap")
save_delta_heatmap("l1_d_miss_rate", "Miss Rate (%)", "D-Cache Miss Rate", "dmiss_delta_heatmap")
save_delta_heatmap("l2_total_accesses", "L2 Total Accesses", "L2 Traffic", "l2access_delta_heatmap")

# Summary CSVs
save_summary_csv()
print_summary()

print(f"\nSaved analysis to: {OUT_DIR}")
