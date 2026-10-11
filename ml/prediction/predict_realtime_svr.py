
import os
import sys
import time
import tempfile
import requests
import pandas as pd
import numpy as np
import joblib

from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# 1. KONFIGURASI

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

AIR_QUALITY_URL = (
    "https://air-quality-api.open-meteo.com/v1/air-quality"
)

WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
)

TIMEZONE = "Asia/Jakarta"
MAX_ATTEMPTS = 3
REQUEST_TIMEOUT = 30

SVR_FEATURES = [
    "LAG1",
    "LAG2",
    "LAG3",
    "temperature_2m",
    "relative_humidity_2m",
    "rain",
    "wind_speed_10m",
]

ML_DIR = Path(__file__).resolve().parents[1]

MODEL_PATH = (
    ML_DIR
    / "models"
    / "svr"
    / "svr_lag123_no2_meteorologi_80_20.joblib"
)

OUTPUT_DIR = (
    ML_DIR
    / "results"
    / "predictions"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "svr_realtime_predictions.csv"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# 2. REQUEST API DENGAN RETRY

def fetch_api(url, params):
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 429:
                if attempt == MAX_ATTEMPTS - 1:
                    response.raise_for_status()

                retry_after = response.headers.get(
                    "Retry-After"
                )

                try:
                    wait_seconds = float(retry_after)
                except (TypeError, ValueError):
                    wait_seconds = 5 * (attempt + 1)

                wait_seconds = max(
                    1,
                    min(wait_seconds, 30),
                )

                print(
                    f"API terkena batas request (429). "
                    f"Mencoba kembali dalam {wait_seconds:g} detik..."
                )

                time.sleep(wait_seconds)
                continue

            response.raise_for_status()

            data = response.json()

            if isinstance(data, dict) and data.get("error"):
                raise ValueError(
                    f"Open-Meteo mengembalikan error: "
                    f"{data.get('reason', data['error'])}"
                )

            return data

        except requests.RequestException:
            if attempt == MAX_ATTEMPTS - 1:
                raise

            wait_seconds = 3 * (attempt + 1)

            print(
                f"Request API gagal. "
                f"Mencoba kembali dalam {wait_seconds} detik..."
            )

            time.sleep(wait_seconds)

    raise RuntimeError("Gagal mengambil data dari Open-Meteo.")


# 3. VALIDASI JUMLAH LOKASI

def normalize_response(data):
    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list):
        raise ValueError(
            "Format respons Open-Meteo tidak valid."
        )

    if len(data) != len(LATITUDES):
        raise ValueError(
            f"Jumlah lokasi tidak sesuai. "
            f"Diharapkan {len(LATITUDES)}, "
            f"tetapi menerima {len(data)}."
        )

    return data


# 4. AMBIL DATA NO2 HOURLY

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
        hourly = item.get("hourly") or {}

        times = hourly.get("time") or []
        values = hourly.get("nitrogen_dioxide") or []

        if len(times) != len(values):
            raise ValueError(
                f"Jumlah data waktu dan NO2 tidak sesuai "
                f"pada lokasi {location_id}."
            )

        for timestamp, value in zip(times, values):
            rows.append({
                "location_id": location_id,
                "time": pd.to_datetime(timestamp),
                "nitrogen_dioxide": value,
            })

    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError("Data NO2 dari API kosong.")

    return df


# 5. AMBIL DATA METEOROLOGI HOURLY

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
        "past_days": 1,
        "forecast_days": 1,
        "timezone": TIMEZONE,
        "wind_speed_unit": "kmh",
    }

    data = normalize_response(
        fetch_api(WEATHER_URL, params)
    )

    rows = []

    weather_columns = [
        "temperature_2m",
        "relative_humidity_2m",
        "rain",
        "wind_speed_10m",
    ]

    for location_id, item in enumerate(data, start=1):
        hourly = item.get("hourly") or {}
        times = hourly.get("time") or []

        for column in weather_columns:
            if len(hourly.get(column) or []) != len(times):
                raise ValueError(
                    f"Jumlah data {column} tidak sesuai "
                    f"pada lokasi {location_id}."
                )

        for i, timestamp in enumerate(times):
            rows.append({
                "location_id": location_id,
                "time": pd.to_datetime(timestamp),
                "temperature_2m":
                    hourly["temperature_2m"][i],
                "relative_humidity_2m":
                    hourly["relative_humidity_2m"][i],
                "rain":
                    hourly["rain"][i],
                "wind_speed_10m":
                    hourly["wind_speed_10m"][i],
            })

    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError(
            "Data meteorologi dari API kosong."
        )

    return df


# 6. TENTUKAN WAKTU PREDIKSI

def get_target_time():
    now = datetime.now(ZoneInfo(TIMEZONE))

    target = now.replace(
        minute=0,
        second=0,
        microsecond=0,
    ) + timedelta(hours=1)

    # Timestamp API menggunakan waktu lokal tanpa timezone.
    return pd.Timestamp(target.replace(tzinfo=None))


# 7. SIAPKAN FITUR PREDIKSI

def prepare_prediction_data(
    df_no2,
    df_weather,
    target_time,
):
    df = pd.merge(
        df_no2,
        df_weather,
        on=["location_id", "time"],
        how="inner",
        validate="one_to_one",
    )

    df = df.sort_values(
        ["location_id", "time"]
    ).reset_index(drop=True)

    if df.empty:
        raise ValueError(
            "Data NO2 dan meteorologi tidak memiliki "
            "waktu yang cocok."
        )

    rows = []

    for location_id in range(1, len(LATITUDES) + 1):
        location_data = df[
            df["location_id"] == location_id
        ].sort_values("time")

        lag_times = [
            target_time - pd.Timedelta(hours=1),
            target_time - pd.Timedelta(hours=2),
            target_time - pd.Timedelta(hours=3),
        ]

        lag_values = []

        for lag_time in lag_times:
            previous = location_data[
                location_data["time"] == lag_time
            ]

            if previous.empty:
                raise ValueError(
                    f"Data NO2 lokasi {location_id} "
                    f"pada {lag_time} tidak tersedia."
                )

            lag_values.append(
                previous.iloc[0]["nitrogen_dioxide"]
            )

        weather_time = (
            target_time - pd.Timedelta(hours=1)
        )

        target_weather = location_data[
            location_data["time"] == weather_time
        ]

        if target_weather.empty:
            raise ValueError(
                f"Data meteorologi lokasi {location_id} "
                f"pada {weather_time} tidak tersedia."
            )

        weather = target_weather.iloc[0]

        rows.append({
            "location_id": location_id,
            "target_time": target_time,
            "weather_time": weather_time,
            "LAG1": lag_values[0],
            "LAG2": lag_values[1],
            "LAG3": lag_values[2],
            "temperature_2m": weather["temperature_2m"],
            "relative_humidity_2m":
                weather["relative_humidity_2m"],
            "rain": weather["rain"],
            "wind_speed_10m": weather["wind_speed_10m"],
        })

    result = pd.DataFrame(rows)

    numeric_columns = SVR_FEATURES

    result[numeric_columns] = result[
        numeric_columns
    ].apply(pd.to_numeric, errors="coerce")

    if result[numeric_columns].isna().any().any():
        raise ValueError(
            "Fitur prediksi mengandung nilai kosong "
            "atau bukan angka."
        )

    if not np.isfinite(
        result[numeric_columns].to_numpy(dtype=float)
    ).all():
        raise ValueError(
            "Fitur prediksi mengandung nilai tidak valid."
        )

    if len(result) != len(LATITUDES):
        raise ValueError(
            "Jumlah hasil fitur tidak sesuai dengan jumlah lokasi."
        )

    return result


# 8. SIMPAN CSV DENGAN AMAN

def save_csv_safely(df, output_file):
    """
    File lama tidak diganti sampai CSV baru selesai ditulis.
    Jika proses penulisan gagal, file lama tetap dipertahankan.
    """
    output_file.parent.mkdir(
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
            prefix="svr_realtime_",
            dir=output_file.parent,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

            df.to_csv(
                temp_file,
                index=False,
                lineterminator="\n",
            )

            temp_file.flush()
            os.fsync(temp_file.fileno())

        # Mengganti file lama setelah penulisan selesai.
        temp_path.replace(output_file)
        temp_path = None

    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


# 9. PREDIKSI SVR

def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model SVR tidak ditemukan: {MODEL_PATH}"
        )

    print("Memuat model SVR RBF...")

    model = joblib.load(MODEL_PATH)

    print("Model SVR berhasil dimuat.")

    print("\nMengambil data NO2...")
    df_no2 = fetch_no2()

    print("Mengambil data meteorologi...")
    df_weather = fetch_weather()

    target_time = get_target_time()

    print(
        f"\nTarget prediksi: "
        f"{target_time.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    X = prepare_prediction_data(
        df_no2,
        df_weather,
        target_time,
    )

    print("\nMenjalankan prediksi SVR...")

    predictions = model.predict(X[SVR_FEATURES])

    if len(predictions) != len(X):
        raise ValueError(
            "Jumlah prediksi tidak sesuai dengan jumlah lokasi."
        )

    if not np.isfinite(predictions).all():
        raise ValueError(
            "Hasil prediksi mengandung nilai tidak valid."
        )

    X["predicted_nitrogen_dioxide"] = predictions

    X["target_time"] = X["target_time"].dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    X["weather_time"] = X["weather_time"].dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # CSV baru disimpan hanya setelah seluruh langkah berhasil.
    save_csv_safely(X, OUTPUT_FILE)

    print("\nPrediksi SVR selesai!")

    print(X.to_string(index=False))

    print(f"\nHasil tersimpan di: {OUTPUT_FILE}")


# 10. JALANKAN PROGRAM

if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        print(
            f"\nPrediksi SVR gagal: {error}",
            file=sys.stderr,
        )

        # Agar server.js mengetahui bahwa proses gagal.
        sys.exit(1)