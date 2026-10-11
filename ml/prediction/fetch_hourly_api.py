
import sys
import time
import tempfile
from pathlib import Path

import requests
import pandas as pd


# 1. KONFIGURASI LOKASI

LATITUDES = [
    -6.199997,
    -5.7986665,
    -6.002,
    -6.5999985,
    -6.656,
    -6.0606,
    -5.745,
    -6.319,
    -6.402,
    -6.2999954,
]

LONGITUDES = [
    106.899994,
    106.4990656,
    107.002,
    106.5,
    106.844,
    106.4242,
    106.613,
    107.163,
    106.97,
    107.399994,
]

TIMEZONE = "Asia/Jakarta"

AIR_QUALITY_URL = (
    "https://air-quality-api.open-meteo.com/v1/air-quality"
)

WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
)

PAST_HOURS = 3
FORECAST_HOURS = 1

EXPECTED_LOCATIONS = set(
    range(1, len(LATITUDES) + 1)
)

ML_DIR = Path(__file__).resolve().parents[1]

OUTPUT_DIR = ML_DIR / "data" / "api"
OUTPUT_FILE = OUTPUT_DIR / "hourly_api.csv"

REQUIRED_COLUMNS = [
    "location_id",
    "time",
    "nitrogen_dioxide",
    "temperature_2m",
    "relative_humidity_2m",
    "rain",
    "wind_speed_10m",
]


# 2. REQUEST API

def fetch_api(url, params):
    max_attempts = 2

    for attempt in range(max_attempts):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=30,
            )

            # Jika terkena rate limit, jangan retry berkali-kali.
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")

                if retry_after:
                    print(
                        "Open-Meteo membatasi request (429). "
                        f"Retry-After: {retry_after}"
                    )
                else:
                    print(
                        "Open-Meteo membatasi request (429). "
                        "Pengambilan data dihentikan sementara."
                    )

                response.raise_for_status()

            response.raise_for_status()
            data = response.json()

            if not isinstance(data, (dict, list)):
                raise ValueError("Format respons API tidak valid.")

            return data

        except requests.HTTPError as error:
            # Jangan ulangi request jika status 429.
            if (
                error.response is not None
                and error.response.status_code == 429
            ):
                raise

            if attempt == max_attempts - 1:
                raise

            time.sleep(3)

        except requests.RequestException:
            if attempt == max_attempts - 1:
                raise

            time.sleep(3)

    raise RuntimeError("Gagal mengambil data API.")

def normalize_response(data):
    if isinstance(data, dict):
        if "hourly" not in data:
            raise ValueError(
                "Respons API tidak memiliki data hourly."
            )
        data = [data]

    if not isinstance(data, list):
        raise ValueError("Format respons multi-lokasi tidak valid.")

    if len(data) != len(LATITUDES):
        raise ValueError(
            f"API mengembalikan {len(data)} lokasi; "
            f"seharusnya {len(LATITUDES)}."
        )

    return data


# 3. AMBIL DATA NO2 PER JAM

def fetch_no2():
    params = {
        "latitude": ",".join(map(str, LATITUDES)),
        "longitude": ",".join(map(str, LONGITUDES)),
        "hourly": "nitrogen_dioxide",
        "past_hours": PAST_HOURS,
        "forecast_hours": FORECAST_HOURS,
        "timezone": TIMEZONE,
    }

    data = normalize_response(
        fetch_api(AIR_QUALITY_URL, params)
    )

    rows = []

    for location_id, item in enumerate(data, start=1):
        hourly = item.get("hourly", {})

        times = hourly.get("time", [])
        values = hourly.get("nitrogen_dioxide", [])

        if not times or len(times) != len(values):
            raise ValueError(
                f"Data NO2 lokasi {location_id} kosong "
                "atau tidak lengkap."
            )

        for time_value, no2_value in zip(times, values):
            rows.append({
                "location_id": location_id,
                "time": pd.to_datetime(time_value),
                "nitrogen_dioxide": no2_value,
            })

    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError("Data NO2 kosong.")

    return df


# 4. AMBIL DATA METEOROLOGI PER JAM

def fetch_weather():
    params = {
        "latitude": ",".join(map(str, LATITUDES)),
        "longitude": ",".join(map(str, LONGITUDES)),
        "hourly": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "rain,"
            "wind_speed_10m"
        ),
        "past_hours": PAST_HOURS,
        "forecast_hours": FORECAST_HOURS,
        "timezone": TIMEZONE,
        "wind_speed_unit": "kmh",
    }

    data = normalize_response(
        fetch_api(WEATHER_URL, params)
    )

    rows = []

    for location_id, item in enumerate(data, start=1):
        hourly = item.get("hourly", {})

        times = hourly.get("time", [])
        temperatures = hourly.get("temperature_2m", [])
        humidities = hourly.get("relative_humidity_2m", [])
        rains = hourly.get("rain", [])
        wind_speeds = hourly.get("wind_speed_10m", [])

        lengths = {
            len(times),
            len(temperatures),
            len(humidities),
            len(rains),
            len(wind_speeds),
        }

        if not times or len(lengths) != 1:
            raise ValueError(
                f"Data meteorologi lokasi {location_id} "
                "kosong atau panjang kolom tidak sama."
            )

        for i, time_value in enumerate(times):
            rows.append({
                "location_id": location_id,
                "time": pd.to_datetime(time_value),
                "temperature_2m": temperatures[i],
                "relative_humidity_2m": humidities[i],
                "rain": rains[i],
                "wind_speed_10m": wind_speeds[i],
            })

    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError("Data meteorologi kosong.")

    return df


# 5. VALIDASI DAN SIMPAN CSV DENGAN AMAN

def validate_data(df):
    if df.empty:
        raise ValueError(
            "Hasil penggabungan kosong. CSV lama dipertahankan."
        )

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Kolom tidak tersedia: {missing_columns}"
        )

    location_ids = set(
        pd.to_numeric(
            df["location_id"],
            errors="raise",
        ).astype(int)
    )

    if location_ids != EXPECTED_LOCATIONS:
        raise ValueError(
            "Hasil penggabungan tidak mencakup seluruh "
            "10 lokasi. CSV lama dipertahankan."
        )

    if df.duplicated(["location_id", "time"]).any():
        raise ValueError(
            "Ada data duplikat berdasarkan lokasi dan waktu."
        )

    numeric_columns = [
        "nitrogen_dioxide",
        "temperature_2m",
        "relative_humidity_2m",
        "rain",
        "wind_speed_10m",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    if df[numeric_columns].isna().any().any():
        raise ValueError(
            "Data mengandung nilai numerik kosong atau "
            "tidak valid. CSV lama dipertahankan."
        )

    if not df[numeric_columns].map(
        lambda value: pd.notna(value)
        and abs(value) != float("inf")
    ).all().all():
        raise ValueError(
            "Data mengandung nilai tak hingga."
        )

    df["time"] = pd.to_datetime(
        df["time"],
        errors="raise",
    )

    df.sort_values(
        ["location_id", "time"],
        inplace=True,
    )

    df.reset_index(drop=True, inplace=True)

    return df[REQUIRED_COLUMNS]


def save_csv_safely(df):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            suffix=".tmp",
            prefix="hourly_api_",
            dir=OUTPUT_DIR,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

            df.to_csv(
                temp_file,
                index=False,
                lineterminator="\n",
            )

            temp_file.flush()

        # Ganti CSV lama hanya setelah file baru selesai ditulis.
        temp_path.replace(OUTPUT_FILE)

    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


# 6. GABUNGKAN DATA

def main():
    print("Mengambil data NO2 per jam...")
    df_no2 = fetch_no2()

    print("Mengambil data meteorologi per jam...")
    df_weather = fetch_weather()

    print("Menggabungkan data berdasarkan lokasi dan waktu...")

    df = pd.merge(
        df_no2,
        df_weather,
        on=["location_id", "time"],
        how="inner",
        validate="one_to_one",
    )

    # Validasi sebelum mengganti file sebelumnya.
    df = validate_data(df)

    save_csv_safely(df)

    print("\nPengambilan data hourly berhasil.")
    print(f"Jumlah baris: {len(df)}")
    print(f"Jumlah lokasi: {df['location_id'].nunique()}")
    print(f"File tersimpan: {OUTPUT_FILE}")

    print("\nContoh data:")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        print(
            f"\nGAGAL mengambil data hourly: {error}",
            file=sys.stderr,
        )

        # Memberi status gagal kepada Express.
        sys.exit(1)