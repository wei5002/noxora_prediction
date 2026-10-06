import pandas as pd
from pathlib import Path

# 1. KONFIGURASI PATH
BASE_DIR = Path(__file__).resolve().parents[1]

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

NO2_FILE = RAW_DIR / "training_NO2.csv"
WEATHER_FILE = RAW_DIR / "training_meteorologi.csv"

OUTPUT_FILE = PROCESSED_DIR / "dataset-no2-meteorologi.csv"


# 2. MEMBACA DATASET
def load_dataset():
    print("Membaca dataset NO2 dan meteorologi...")

    # Lewati 12 baris metadata di awal file Open-Meteo
    df_no2 = pd.read_csv(NO2_FILE, skiprows=12)
    df_weather = pd.read_csv(WEATHER_FILE, skiprows=12)

    # Rapikan nama kolom
    df_no2 = df_no2.rename(columns={
        "nitrogen_dioxide (μg/m³)": "nitrogen_dioxide"
    })

    df_weather = df_weather.rename(columns={
        "temperature_2m (°C)": "temperature_2m",
        "relative_humidity_2m (%)": "relative_humidity_2m",
        "rain (mm)": "rain",
        "wind_speed_10m (km/h)": "wind_speed_10m"
    })

    return df_no2, df_weather


# 3. PREPROCESSING DAN PENGGABUNGAN DATA
def preprocess_dataset(df_no2, df_weather):
    print("Membersihkan dan menggabungkan dataset...")

    # Samakan tipe data kolom lokasi
    df_no2["location_id"] = df_no2["location_id"].astype(str)
    df_weather["location_id"] = df_weather["location_id"].astype(str)

    # Konversi waktu ke datetime
    df_no2["time"] = pd.to_datetime(df_no2["time"])
    df_weather["time"] = pd.to_datetime(df_weather["time"])

    # Pastikan data numerik
    no2_columns = ["nitrogen_dioxide"]
    weather_columns = [
        "temperature_2m",
        "relative_humidity_2m",
        "rain",
        "wind_speed_10m"
    ]

    for column in no2_columns:
        df_no2[column] = pd.to_numeric(
            df_no2[column], errors="coerce"
        )

    for column in weather_columns:
        df_weather[column] = pd.to_numeric(
            df_weather[column], errors="coerce"
        )

    # Periksa duplikasi sebelum penggabungan
    df_no2 = df_no2.drop_duplicates(
        subset=["location_id", "time"]
    )

    df_weather = df_weather.drop_duplicates(
        subset=["location_id", "time"]
    )

    # Gabungkan berdasarkan lokasi dan waktu
    df = pd.merge(
        df_no2,
        df_weather,
        on=["location_id", "time"],
        how="inner",
        validate="one_to_one"
    )

    # Urutkan berdasarkan lokasi dan waktu
    df = df.sort_values(
        by=["location_id", "time"]
    ).reset_index(drop=True)

    return df


# 4. MEMBUAT FITUR LAG
def create_lag_features(df):
    print("Membuat fitur LAG1, LAG2, dan LAG3...")

    # Ambil nilai NO2 dari waktu sebelumnya
    grouped_no2 = df.groupby("location_id")["nitrogen_dioxide"]

    df["LAG1"] = grouped_no2.shift(1)
    df["LAG2"] = grouped_no2.shift(2)
    df["LAG3"] = grouped_no2.shift(3)

    return df


# 5. PEMBERSIHAN DATA AKHIR
def clean_dataset(df):
    print("Membersihkan missing value...")

    # Hapus baris yang tidak memiliki target,
    # fitur lag, atau fitur meteorologi
    required_columns = [
        "nitrogen_dioxide",
        "LAG1",
        "LAG2",
        "LAG3",
        "temperature_2m",
        "relative_humidity_2m",
        "rain",
        "wind_speed_10m"
    ]

    df = df.dropna(subset=required_columns).copy()

    # Hapus nilai tak hingga jika ada
    df = df.replace([float("inf"), float("-inf")], pd.NA)
    df = df.dropna(subset=required_columns)

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
    df_no2, df_weather = load_dataset()

    print(f"Jumlah baris NO2         : {len(df_no2):,}")
    print(f"Jumlah baris meteorologi : {len(df_weather):,}")

    df = preprocess_dataset(df_no2, df_weather)

    print(f"Jumlah baris setelah merge: {len(df):,}")

    df = create_lag_features(df)

    print(f"Jumlah baris sebelum cleaning: {len(df):,}")

    df = clean_dataset(df)

    # Susun kolom agar mudah dibaca
    columns_order = [
        "location_id",
        "time",
        "nitrogen_dioxide",
        "LAG1",
        "LAG2",
        "LAG3",
        "temperature_2m",
        "relative_humidity_2m",
        "rain",
        "wind_speed_10m"
    ]

    df = df[columns_order]

    save_dataset(df)

    print("\n===== HASIL PREPROCESSING =====")
    print(f"Jumlah baris akhir : {len(df):,}")
    print(f"Jumlah kolom       : {len(df.columns)}")

    print("\nLima baris pertama:")
    print(df.head().to_string(index=False))

    print("\nMissing value:")
    print(df.isnull().sum().to_string())

    print("\nJumlah lokasi:")
    print(df["location_id"].nunique())

    print("\nPreprocessing selesai!")


if __name__ == "__main__":
    main()