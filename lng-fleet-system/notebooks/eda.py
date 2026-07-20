import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import os
import warnings
warnings.filterwarnings("ignore")

sns.set_style("whitegrid")
plt.rcParams["figure.dpi"] = 120

from ml.pipeline.config import DATA_DIR
from ml.data.dataset import generate_synthetic_data, load_dataset

OUTPUT_DIR = os.path.join(DATA_DIR, "eda_plots")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def plot_cii_trend():
    df = load_dataset("cii")
    if df is None:
        df = generate_synthetic_data(2000)["cii"]
    df["date"] = pd.to_datetime(df["date"])
    fig, ax = plt.subplots(figsize=(12, 5))
    for vessel in df["vessel_id"].unique()[:5]:
        vdf = df[df["vessel_id"] == vessel].sort_values("date")
        ax.plot(vdf["date"], vdf["cii_monthly"], label=vessel, alpha=0.8)
    ax.set_xlabel("Date")
    ax.set_ylabel("Monthly CII (gCO2/ton-nm)")
    ax.set_title("CII Trend Over Time by Vessel")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "cii_trend.png"), bbox_inches="tight")
    plt.close(fig)
    print("  Saved cii_trend.png")


def plot_bor_distribution():
    df = load_dataset("bor")
    if df is None:
        df = generate_synthetic_data(2000)["bor"]
    df["season"] = pd.to_datetime(df["date"]).dt.month.map(
        lambda m: "Winter" if m in [12, 1, 2] else "Spring" if m in [3, 4, 5]
        else "Summer" if m in [6, 7, 8] else "Fall"
    )

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for ax, groupby in zip(axes, ["season", "vessel_id"]):
        for key, grp in df.groupby(groupby):
            ax.hist(grp["bor"], bins=30, alpha=0.5, label=str(key))
        ax.set_xlabel("Boil-Off Rate (%)")
        ax.set_ylabel("Frequency")
        ax.set_title(f"BOR Distribution by {groupby.title()}")
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "bor_distribution.png"))
    plt.close(fig)
    print("  Saved bor_distribution.png")


def plot_engine_scatter_matrix():
    df = load_dataset("engine")
    if df is None:
        df = generate_synthetic_data(2000)["engine"]
    cols = ["shaft_power", "sfoc", "exhaust_temp", "rpm"]
    g = sns.PairGrid(df[cols].sample(min(500, len(df))))
    g.map_upper(sns.kdeplot, levels=4, alpha=0.5)
    g.map_lower(sns.scatterplot, s=10, alpha=0.3)
    g.map_diag(sns.histplot, bins=30)
    g.fig.suptitle("Engine Performance Scatter Matrix", y=1.02)
    g.fig.savefig(os.path.join(OUTPUT_DIR, "engine_scatter_matrix.png"),
                  bbox_inches="tight", dpi=100)
    plt.close(g.fig)
    print("  Saved engine_scatter_matrix.png")


def plot_eca_compliance():
    df = load_dataset("cii")
    if df is None:
        df = generate_synthetic_data(2000)["cii"]
    df["rating"] = pd.cut(df["cii_yearly"], bins=[0, 3.5, 5, 7, 9.5, 100],
                          labels=["A", "B", "C", "D", "E"])
    rating_order = ["A", "B", "C", "D", "E"]
    colors = ["#2ecc71", "#27ae60", "#f1c40f", "#e67e22", "#e74c3c"]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    rating_counts = df["rating"].value_counts().reindex(rating_order).fillna(0)
    axes[0].bar(rating_order, rating_counts.values, color=colors, alpha=0.8)
    axes[0].set_xlabel("CII Rating")
    axes[0].set_ylabel("Number of Records")
    axes[0].set_title("CII Rating Distribution")

    vessel_ratings = df.groupby("vessel_id")["rating"].apply(
        lambda x: x.mode().iloc[0] if not x.mode().empty else "C"
    ).reindex(df["vessel_id"].unique()).fillna("C")
    vc = vessel_ratings.value_counts().reindex(rating_order).fillna(0)
    axes[1].bar(rating_order, vc.values, color=colors, alpha=0.8)
    axes[1].set_xlabel("CII Rating")
    axes[1].set_ylabel("Number of Vessels")
    axes[1].set_title("Vessel Primary CII Rating")

    fig.suptitle("ECA Compliance Summary", fontsize=13, y=1.03)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "eca_compliance.png"), bbox_inches="tight")
    plt.close(fig)
    print("  Saved eca_compliance.png")


def plot_correlation_heatmap():
    df = load_dataset("engine")
    if df is None:
        df = generate_synthetic_data(2000)["engine"]
    telemetry_cols = ["shaft_power", "sfoc", "exhaust_temp", "rpm",
                      "turbocharger_speed", "scavenge_air_pressure"]
    corr = df[telemetry_cols].corr()
    fig, ax = plt.subplots(figsize=(8, 6))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r",
                vmin=-1, vmax=1, square=True, cbar_kws={"shrink": 0.8}, ax=ax)
    ax.set_title("Correlation Heatmap of Telemetry Parameters")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "correlation_heatmap.png"))
    plt.close(fig)
    print("  Saved correlation_heatmap.png")


def generate_all_plots():
    print("Generating EDA plots...")
    plot_cii_trend()
    plot_bor_distribution()
    plot_engine_scatter_matrix()
    plot_eca_compliance()
    plot_correlation_heatmap()
    print(f"\nAll plots saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    generate_all_plots()
