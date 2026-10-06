import pandas as pd
from pathlib import Path

# 1. KONFIGURASI PATH
BASE_DIR = Path(__file__).resolve().parents[1]

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

NO2_FILE = RAW_DIR / "training_NO2.csv"
OUTPUT_FILE = PROCESSED_DIR / "dataset-no2.csv"


# 2. MEMBACA DATASET NO2
def load_dataset():
    print("Membaca dataset NO2...")

    if not NO2_FILE.exists():
        raise FileNotFoundError(
            f"File dataset NO2 tidak ditemukan: {NO2_FILE}"
        )

    # Lewati 12 baris metadata Open-Meteo
    df = pd.read_csv(NO2_FILE, skiprows=12)

    # Rapikan nama kolom
    df = df.rename(columns={
        "nitrogen_dioxide (μg/m³)": "nitrogen_dioxide"
    })

    return df


# 3. PEMBERSIHAN DATA
def preprocess_dataset(df):
    print("Membersihkan dataset NO2...")

    # Pastikan tipe data konsisten
    df["location_id"] = df["location_id"].astype(str)
    df["time"] = pd.to_datetime(df["time"], errors="coerce")

    df["nitrogen_dioxide"] = pd.to_numeric(
        df["nitrogen_dioxide"],
        errors="coerce"
    )

    # Hapus data dengan lokasi, waktu, atau target kosong
    df = df.dropna(
        subset=["location_id", "time", "nitrogen_dioxide"]
    ).copy()

    # Hapus duplikasi berdasarkan lokasi dan waktu
    df = df.drop_duplicates(
        subset=["location_id", "time"]
    )

    # Urutkan data berdasarkan lokasi dan waktu
    df = df.sort_values(
        by=["location_id", "time"]
    ).reset_index(drop=True)

    return df


# 4. MEMBUAT FITUR LAG
def create_lag_features(df):
    print("Membuat fitur LAG1, LAG2, dan LAG3...")
    grouped_no2 = df.groupby("location_id")["nitrogen_dioxide"]
    df["LAG1"] = grouped_no2.shift(1)
    df["LAG2"] = grouped_no2.shift(2)
    df["LAG3"] = grouped_no2.shift(3)

    return df


# 5. PEMBERSIHAN DATA AKHIR
def clean_dataset(df):
    print("Menghapus baris yang tidak memiliki fitur lag...")
    required_columns = [
        "nitrogen_dioxide",
        "LAG1",
        "LAG2",
        "LAG3"
    ]

    df = df.replace(
        [float("inf"), float("-inf")],
        float("nan")
    )

    df = df.dropna(
        subset=required_columns
    ).copy()

    return df


# 6. MENYIMPAN DATASET
def save_dataset(df):
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(f"\nDataset berhasil disimpan:")
    print(OUTPUT_FILE)


# 7. PROGRAM UTAMA
def main():
    df = load_dataset()
    print(f"Jumlah baris awal: {len(df):,}")
    df = preprocess_dataset(df)
    print(f"Jumlah baris setelah cleaning: {len(df):,}")
    df = create_lag_features(df)
    print(f"Jumlah baris sebelum membuat dataset akhir: {len(df):,}")
    df = clean_dataset(df)

    # Susun kolom
    columns_order = [
        "location_id",
        "time",
        "nitrogen_dioxide",
        "LAG1",
        "LAG2",
        "LAG3"
    ]

    df = df[columns_order]

    save_dataset(df)

    print("\n===== HASIL PREPROCESSING NO2 =====")
    print(f"Jumlah baris akhir : {len(df):,}")
    print(f"Jumlah kolom       : {len(df.columns)}")
    print(f"Jumlah lokasi      : {df['location_id'].nunique()}")

    print("\nLima baris pertama:")
    print(df.head().to_string(index=False))

    print("\nMissing value:")
    print(df.isnull().sum().to_string())

    print("\nPreprocessing NO2 selesai!")


if __name__ == "__main__":
    main()