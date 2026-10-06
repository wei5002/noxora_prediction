import pandas as pd
from pathlib import Path

# KONFIGURASI PATH
BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"

NO2_FILE = RAW_DIR / "training_NO2.csv"
WEATHER_FILE = RAW_DIR / "training_meteorologi.csv"


# FUNGSI PEMERIKSAAN DATASET
def inspect_dataset(file_path, dataset_name):

    print(f"DATASET {dataset_name}")

    # Periksa apakah file tersedia
    if not file_path.exists():
        print(f"ERROR: File tidak ditemukan: {file_path}")
        return

    # Baca CSV dengan melewati 12 baris metadata
    try:
        df = pd.read_csv(
            file_path,
            skiprows=12,
            low_memory=False
        )
    except Exception as e:
        print(f"Gagal membaca CSV: {e}")
        return

    # 1. UKURAN DATASET
    print("\n[1] UKURAN DATASET")
    print(f"Jumlah baris : {df.shape[0]:,}")
    print(f"Jumlah kolom : {df.shape[1]}")

    # 2. NAMA KOLOM
    print("\n[2] NAMA KOLOM")
    print(df.columns.tolist())

    # 3. LIMA BARIS PERTAMA
    print("\n[3] LIMA BARIS PERTAMA")
    print(df.head().to_string(index=False))

    # 4. TIPE DATA
    print("\n[4] TIPE DATA")
    print(df.dtypes.to_string())

    # 5. MISSING VALUE
    print("\n[5] MISSING VALUE")
    missing_values = df.isnull().sum()
    print(missing_values.to_string())
    print(f"Total missing value: {missing_values.sum():,}")

    # 6. DUPLIKAT
    print("\n[6] JUMLAH BARIS DUPLIKAT")
    print(f"{df.duplicated().sum():,}")

    # 7. 20 BARIS ASLI CSV
    print("\n[7] 20 BARIS ASLI FILE CSV")

    try:
        with open(
            file_path,
            "r",
            encoding="utf-8-sig",
            errors="replace"
        ) as file:

            for i in range(20):
                line = file.readline()

                if not line:
                    break

                print(f"Baris {i + 1}: {line.rstrip()}")

    except Exception as e:
        print(f"Gagal membaca isi asli file: {e}")


# JALANKAN PEMERIKSAAN
inspect_dataset(NO2_FILE, "NO2")

inspect_dataset(WEATHER_FILE, "METEOROLOGI")

print("\nPemeriksaan dataset selesai.")