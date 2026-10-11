
import sys
import time
import tempfile
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

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

EXPECTED_LOCATIONS = set(
    range(1, len(LATITUDES) + 1)
)

REQUIRED_COLUMNS = [
    "location_id",
    "time_no2",
    "nitrogen_dioxide",
    "time_weather",
    "temperature_2m",
    "relative_humidity_2m",
    "rain",
    "wind_speed_10m",
    "LAG1",
    "LAG2",
    "LAG3",
]

ML_DIR = Path(__file__).resolve().parents[1]

OUTPUT_DIR = ML_DIR / "data" / "api"
OUTPUT_FILE = OUTPUT_DIR / "realtime_api.csv"


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
        # Respons satu lokasi.
        if "hourly" in data or "current" in data:
            return [data]

        raise ValueError(
            "Respons API tidak memiliki data hourly/current."
        )

    if not isinstance(data, list):
        raise ValueError("Respons multi-lokasi tidak valid.")

    if len(data) != len(LATITUDES):
        raise ValueError(
            f"API mengembalikan {len(data)} lokasi, "
            f"seharusnya {len(LATITUDES)}."
        )

    return data


# 3. AMBIL DATA NO2 PER JAM

def fetch_no2():
    params = {
        "latitude": ",".join(map(str, LATITUDES)),
        "longitude": ",".join(map(str, LONGITUDES)),
        "hourly": "nitrogen_dioxide",
        "past_days": 1,
        "forecast_days": 1,
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
                f"Data NO2 lokasi {location_id} "
                "kosong atau tidak lengkap."
            )

        for time_value, no2_value in zip(times, values):
            rows.append({
                "location_id": location_id,
                "time": pd.to_datetime(time_value),
                "nitrogen_dioxide": no2_value,
            })

    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError("Data NO2 yang diterima kosong.")

    return df


# 4. AMBIL DATA METEOROLOGI TERKINI

def fetch_weather():
    params = {
        "latitude": ",".join(map(str, LATITUDES)),
        "longitude": ",".join(map(str, LONGITUDES)),
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "rain,"
            "wind_speed_10m"
        ),
        "timezone": TIMEZONE,
    }

    data = normalize_response(
        fetch_api(WEATHER_URL, params)
    )

    rows = []

    for location_id, item in enumerate(data, start=1):
        current = item.get("current", {})

        if not current.get("time"):
            raise ValueError(
                f"Waktu meteorologi lokasi "
                f"{location_id} tidak tersedia."
            )

        rows.append({
            "location_id": location_id,
            "time_weather": current.get("time"),
            "temperature_2m": current.get(
                "temperature_2m"
            ),
            "relative_humidity_2m": current.get(
                "relative_humidity_2m"
            ),
            "rain": current.get("rain"),
            "wind_speed_10m": current.get(
                "wind_speed_10m"
            ),
        })

    df = pd.DataFrame(rows)

    if len(df) != len(LATITUDES):
        raise ValueError(
            "Data meteorologi belum mencakup semua lokasi."
        )

    return df


# 5. VALIDASI DATA SEBELUM DISIMPAN

def validate_data(df):
    if df.empty:
        raise ValueError(
            "Data realtime kosong. CSV lama dipertahankan."
        )

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Kolom tidak lengkap: {missing_columns}"
        )

    location_ids = set(
        pd.to_numeric(
            df["location_id"],
            errors="raise",
        ).astype(int)
    )

    if location_ids != EXPECTED_LOCATIONS:
        raise ValueError(
            "Data tidak mencakup seluruh 10 lokasi. "
            "CSV lama dipertahankan."
        )

    if df["location_id"].duplicated().any():
        raise ValueError(
            "Terdapat lokasi duplikat."
        )

    numeric_columns = [
        "nitrogen_dioxide",
        "temperature_2m",
        "relative_humidity_2m",
        "rain",
        "wind_speed_10m",
        "LAG1",
        "LAG2",
        "LAG3",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    if df[numeric_columns].isna().any().any():
        raise ValueError(
            "Data NO2, lag, atau meteorologi memiliki "
            "nilai kosong/tidak valid. CSV lama "
            "dipertahankan."
        )

    if not df[numeric_columns].apply(
        lambda column: column.map(
            lambda value: pd.notna(value)
            and abs(value) != float("inf")
        )
    ).all().all():
        raise ValueError(
            "Ditemukan nilai numerik tidak valid."
        )

    df["time_no2"] = pd.to_datetime(
        df["time_no2"],
        errors="raise",
    )

    df["time_weather"] = pd.to_datetime(
        df["time_weather"],
        errors="raise",
    )

    df.sort_values(
        "location_id",
        inplace=True,
    )

    df.reset_index(drop=True, inplace=True)

    return df[REQUIRED_COLUMNS]


# 6. SIMPAN CSV DENGAN AMAN

def save_csv_safely(df):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_path = None

    try:
        # File sementara berada di folder yang sama
        # agar penggantian file dapat dilakukan atomik.
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            suffix=".tmp",
            prefix="realtime_api_",
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

        # CSV lama baru diganti setelah data lolos
        # validasi dan penulisan file selesai.
        temp_path.replace(OUTPUT_FILE)

    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


# 7. JALANKAN PENGAMBILAN DATA

def main():
    print("Mengambil data NO2 dari Open-Meteo...")
    df_no2 = fetch_no2()

    print("Mengambil data meteorologi...")
    df_weather = fetch_weather()

    df_no2["time"] = pd.to_datetime(
        df_no2["time"]
    )

    df_weather["time_weather"] = pd.to_datetime(
        df_weather["time_weather"]
    )

    now = datetime.now(
        ZoneInfo(TIMEZONE)
    )

    realtime_time = pd.Timestamp(
        now.replace(
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=None,
        )
    )

    rows = []

    for location_id in range(
        1,
        len(LATITUDES) + 1,
    ):
        location_data = df_no2[
            df_no2["location_id"] == location_id
        ].sort_values("time")

        current_data = location_data[
            location_data["time"] == realtime_time
        ]

        if current_data.empty:
            raise ValueError(
                f"Data NO2 pada jam {realtime_time} "
                f"tidak tersedia untuk lokasi "
                f"{location_id}. CSV lama dipertahankan."
            )

        current_no2 = current_data.iloc[0][
            "nitrogen_dioxide"
        ]

        lag_values = []

        for hours in (1, 2, 3):
            lag_time = (
                realtime_time
                - pd.Timedelta(hours=hours)
            )

            lag_data = location_data[
                location_data["time"] == lag_time
            ]

            if lag_data.empty:
                raise ValueError(
                    f"LAG{hours} lokasi {location_id} "
                    f"pada {lag_time} tidak tersedia. "
                    "CSV lama dipertahankan."
                )

            lag_values.append(
                lag_data.iloc[0]["nitrogen_dioxide"]
            )

        weather_data = df_weather[
            df_weather["location_id"] == location_id
        ]

        if weather_data.empty:
            raise ValueError(
                f"Data meteorologi lokasi "
                f"{location_id} tidak tersedia."
            )

        weather = weather_data.iloc[0]

        rows.append({
            "location_id": location_id,
            "time_no2": current_data.iloc[0]["time"],
            "nitrogen_dioxide": current_no2,
            "time_weather": weather["time_weather"],
            "temperature_2m": weather["temperature_2m"],
            "relative_humidity_2m": (
                weather["relative_humidity_2m"]
            ),
            "rain": weather["rain"],
            "wind_speed_10m": weather["wind_speed_10m"],
            "LAG1": lag_values[0],
            "LAG2": lag_values[1],
            "LAG3": lag_values[2],
        })

    df = pd.DataFrame(rows)

    # Validasi seluruh lokasi sebelum mengganti CSV lama.
    df = validate_data(df)

    # Hanya data valid yang disimpan.
    save_csv_safely(df)

    print("\nPengambilan data realtime berhasil.")
    print(f"Jumlah lokasi: {len(df)}")
    print(f"File tersimpan: {OUTPUT_FILE}")
    print(df.to_string(index=False))


if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        print(
            f"\nGAGAL memperbarui data realtime: {error}",
            file=sys.stderr,
        )

        # Memberi tahu Express bahwa script gagal.
        # CSV lama tidak dihapus oleh script ini.
        sys.exit(1)