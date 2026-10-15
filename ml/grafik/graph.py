from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# KONFIGURASI
BASE_DIR = Path(__file__).resolve().parents[1]
PREDICTION_DIR = BASE_DIR / "results" / "predictions"
OUTPUT_DIR = BASE_DIR / "results" / "graphs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SVR_FILE = PREDICTION_DIR / "svr_lag123_no2_meteorologi_80_20_predictions.csv"
XGBOOST_FILE = PREDICTION_DIR / "xgboost_lag12_no2_80_20_predictions.csv"
LOCATION_ID = None
DETAIL_DAYS = 7
SAVE_OVERVIEW = False
DPI = 220

# MEMBACA DATA
def read_prediction_csv(file_path, prediction_column):
    """Baca CSV prediksi dan periksa kolom yang dibutuhkan."""
    if not file_path.exists():
        raise FileNotFoundError(
            f"File tidak ditemukan:\n{file_path}\n\n"
            "Pastikan file prediksi ada di folder results/predictions."
        )

    df = pd.read_csv(file_path)

    required = {"location_id", "time", "actual", "predicted"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Kolom pada {file_path.name} belum lengkap. "
            f"Kolom yang hilang: {sorted(missing)}"
        )

    df = df[["location_id", "time", "actual", "predicted"]].copy()
    df["time"] = pd.to_datetime(df["time"], errors="coerce")

    for col in ["location_id", "actual", "predicted"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["location_id", "time", "actual", "predicted"])

    if df.duplicated(["location_id", "time"]).any():
        raise ValueError(
            f"Ada data duplikat location_id dan time di {file_path.name}."
        )

    return df.rename(columns={"predicted": prediction_column})


def load_comparison_data():
    """Gabungkan data SVR dan XGBoost berdasarkan lokasi serta waktu."""
    svr = read_prediction_csv(SVR_FILE, "svr_prediction")
    xgb = read_prediction_csv(XGBOOST_FILE, "xgboost_prediction")

    svr = svr.rename(columns={"actual": "actual_svr"})
    xgb = xgb.rename(columns={"actual": "actual_xgboost"})

    data = svr.merge(
        xgb,
        on=["location_id", "time"],
        how="inner",
        validate="one_to_one",
    )

    if data.empty:
        raise ValueError(
            "Tidak ada waktu/lokasi yang cocok antara file SVR dan XGBoost."
        )

    same_actual = np.isclose(
        data["actual_svr"],
        data["actual_xgboost"],
        rtol=1e-6,
        atol=1e-8,
    )
    if not same_actual.all():
        raise ValueError(
            "Nilai aktual di kedua file tidak sama. "
            "Periksa kembali file prediksi sebelum membandingkan model."
        )

    data["actual"] = data["actual_svr"]
    data = data[
        [
            "location_id",
            "time",
            "actual",
            "svr_prediction",
            "xgboost_prediction",
        ]
    ].sort_values(["location_id", "time"])

    if LOCATION_ID is not None:
        data = data[data["location_id"] == LOCATION_ID]
        if data.empty:
            raise ValueError(
                f"Location ID {LOCATION_ID} tidak ditemukan di file prediksi."
            )

    return data.reset_index(drop=True)


# FUNGSI UNTUK MEMBUAT GRAFIK YANG LEBIH JELAS
def draw_three_lines(ax, data, title, date_format="%d %b"):
    """Gambar tiga garis dengan label, grid, dan sumbu waktu yang mudah dibaca."""
    data = data.sort_values("time")

    ax.plot(
        data["time"],
        data["actual"],
        label="Aktual",
        color="#222222",
        linewidth=1.8,
        alpha=0.95,
    )
    ax.plot(
        data["time"],
        data["svr_prediction"],
        label="Prediksi SVR terbaik",
        color="#007f7b",
        linewidth=1.5,
        alpha=0.9,
    )
    ax.plot(
        data["time"],
        data["xgboost_prediction"],
        label="Prediksi XGBoost terbaik",
        color="#d97706",
        linewidth=1.4,
        alpha=0.9,
    )

    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Waktu pengamatan", fontsize=10)
    ax.set_ylabel("Konsentrasi NO₂", fontsize=10)
    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.3)
    ax.legend(loc="upper right", frameon=True, fontsize=9)
    ax.tick_params(axis="both", labelsize=9)

    # Kurangi jumlah label tanggal supaya tidak bertumpuk.
    ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
    ax.margins(x=0.01)


def save_per_location_graphs(data):
    """Simpan grafik seluruh periode dan grafik detail per lokasi."""
    location_ids = sorted(data["location_id"].unique())

    for location_id in location_ids:
        location_data = (
            data[data["location_id"] == location_id]
            .sort_values("time")
            .copy()
        )
        location_label = str(int(location_id))

        # 1. Grafik seluruh periode testing untuk satu lokasi.
        fig, ax = plt.subplots(figsize=(16, 7))
        draw_three_lines(
            ax,
            location_data,
            title=(
                f"Nilai Aktual vs Prediksi NO₂ — Lokasi {location_label}\n"
                "SVR terbaik dan XGBoost terbaik | Seluruh periode testing"
            ),
            date_format="%b %Y",
        )
        fig.tight_layout()

        full_path = OUTPUT_DIR / f"grafik_lokasi_{location_label}_full.png"
        fig.savefig(full_path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)

        # 2. Grafik detail beberapa hari terakhir agar pola garis lebih terlihat.
        last_time = location_data["time"].max()
        start_time = last_time - pd.Timedelta(days=DETAIL_DAYS)
        detail = location_data[location_data["time"] >= start_time]

        fig, ax = plt.subplots(figsize=(16, 7))
        draw_three_lines(
            ax,
            detail,
            title=(
                f"Detail Aktual vs Prediksi NO₂ — Lokasi {location_label}\n"
                f"{start_time:%d %b %Y} sampai {last_time:%d %b %Y}"
            ),
            date_format="%d %b\n%H:%M",
        )
        # Pada grafik detail, tampilkan label waktu lebih sering.
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=10))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b\n%H:%M"))
        fig.tight_layout()

        detail_path = OUTPUT_DIR / f"grafik_lokasi_{location_label}_detail_{DETAIL_DAYS}_hari.png"
        fig.savefig(detail_path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)

        print(f"Lokasi {location_label}:")
        print(f"  Grafik seluruh periode : {full_path}")
        print(f"  Grafik detail {DETAIL_DAYS} hari : {detail_path}")

    return location_ids


def save_overview_graph(data, location_ids):
    """Opsional: simpan ringkasan banyak lokasi dalam satu gambar."""
    if not SAVE_OVERVIEW or len(location_ids) < 2:
        return

    ncols = 2
    nrows = int(np.ceil(len(location_ids) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(16, 4.5 * nrows))
    axes = np.asarray(axes).reshape(-1)

    for ax, location_id in zip(axes, location_ids):
        subset = data[data["location_id"] == location_id]
        draw_three_lines(
            ax,
            subset,
            title=f"Lokasi {int(location_id)}",
            date_format="%b %Y",
        )

    for ax in axes[len(location_ids):]:
        ax.set_visible(False)

    fig.suptitle(
        "Ringkasan Perbandingan Aktual, SVR, dan XGBoost",
        fontsize=15,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    path = OUTPUT_DIR / "grafik_ringkasan_semua_lokasi.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Grafik ringkasan: {path}")


def main():
    data = load_comparison_data()

    # Simpan data hasil pencocokan agar bisa diperiksa kembali.
    combined_csv = OUTPUT_DIR / "data_perbandingan_aktual_svr_xgboost.csv"
    data.to_csv(combined_csv, index=False)

    print("=" * 65)
    print("GRAFIK PERBANDINGAN AKTUAL, SVR, DAN XGBOOST")
    print("=" * 65)
    print(f"Data yang cocok : {len(data):,} baris")
    print(f"Jumlah lokasi   : {data['location_id'].nunique()}")
    print(f"Periode         : {data['time'].min()} s.d. {data['time'].max()}")
    print(f"Folder output   : {OUTPUT_DIR}")
    print()

    location_ids = save_per_location_graphs(data)
    save_overview_graph(data, location_ids)

    print("\nSelesai. Buka file PNG per lokasi di folder results/graphs.")


if __name__ == "__main__":
    main()
