
import json
import os
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from threading import Lock
from zoneinfo import ZoneInfo

import joblib
import pandas as pd
import psycopg2
import requests


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
CACHE_KEY = "python_realtime"
CACHE_SECONDS = 1800
STALE_CACHE_MAX_SECONDS = 86400
REQUEST_TIMEOUT = 15
MAX_RETRIES = 2

_memory_cache = None
_memory_cache_at = 0
_prediction_lock = Lock()

SVR_FEATURES = [
    "LAG1",
    "LAG2",
    "LAG3",
    "temperature_2m",
    "relative_humidity_2m",
    "rain",
    "wind_speed_10m",
]

XGBOOST_FEATURES = [
    "LAG1",
    "LAG2",
]

BASE_DIR = Path(__file__).resolve().parents[2]

SVR_MODEL_PATH = (
    BASE_DIR
    / "ml"
    / "models"
    / "svr"
    / "svr_lag123_no2_meteorologi_80_20.joblib"
)

XGBOOST_MODEL_PATH = (
    BASE_DIR
    / "ml"
    / "models"
    / "xgboost"
    / "xgboost_lag12_no2_80_20.joblib"
)


def get_database_connection():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "Environment variable DATABASE_URL belum diatur."
        )

    return psycopg2.connect(
        database_url,
        connect_timeout=5,
        sslmode="require",
    )


def ensure_cache_table():
    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS realtime_prediction_cache (
                    cache_key VARCHAR(50) PRIMARY KEY,
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )


def save_persistent_cache(payload):
    try:
        ensure_cache_table()

        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO realtime_prediction_cache
                        (cache_key, payload, updated_at)
                    VALUES (%s, %s::jsonb, NOW())
                    ON CONFLICT (cache_key)
                    DO UPDATE SET
                        payload = EXCLUDED.payload,
                        updated_at = NOW()
                    """,
                    (
                        CACHE_KEY,
                        json.dumps(payload, allow_nan=False),
                    ),
                )

        return True

    except Exception as error:
        print(f"Gagal menyimpan cache PostgreSQL: {error}")
        return False


def load_persistent_cache():
    try:
        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT payload, updated_at
                    FROM realtime_prediction_cache
                    WHERE cache_key = %s
                    """,
                    (CACHE_KEY,),
                )

                row = cursor.fetchone()

        if not row:
            return None, None

        payload, updated_at = row

        if isinstance(payload, str):
            payload = json.loads(payload)

        return payload, updated_at

    except Exception as error:
        print(f"Gagal membaca cache PostgreSQL: {error}")
        return None, None


def cache_age_seconds(updated_at):
    if updated_at is None:
        return None

    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)

    return max(
        0,
        (
            datetime.now(timezone.utc) - updated_at
        ).total_seconds(),
    )


def is_cache_usable(updated_at):
    age = cache_age_seconds(updated_at)

    return (
        age is not None
        and age <= STALE_CACHE_MAX_SECONDS
    )

def add_cache_metadata(payload, updated_at=None, stale=False):
    result = dict(payload)
    result["cached"] = True

    if updated_at is not None:
        if updated_at.tzinfo is not None:
            result["cache_updated_at"] = (
                updated_at.astimezone(timezone.utc).isoformat()
            )
        else:
            result["cache_updated_at"] = updated_at.isoformat()

    if stale:
        result["cache_warning"] = (
            "Open-Meteo gagal diakses. Data yang ditampilkan "
            "berasal dari prediksi terakhir yang berhasil disimpan "
            "dan mungkin bukan data terbaru."
        )

    return result


def fetch_api(url, params):
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )

            # Jangan mengulang request 429 secara langsung.
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")

                raise requests.HTTPError(
                    "Open-Meteo membatasi permintaan (HTTP 429). "
                    f"Retry-After: {retry_after or 'tidak tersedia'}",
                    response=response,
                )

            response.raise_for_status()
            return response.json()

        except requests.HTTPError as error:
            last_error = error

            status = (
                error.response.status_code
                if error.response is not None
                else None
            )

            # Error 429 ditangani dengan cache, bukan retry langsung.
            if status == 429:
                raise

            # Error 4xx lainnya tidak perlu diulang.
            if status is not None and 400 <= status < 500:
                raise

        except requests.RequestException as error:
            last_error = error

        if attempt < MAX_RETRIES - 1:
            time.sleep(2)

    raise last_error or RuntimeError(
        "Permintaan Open-Meteo gagal."
    )

def fetch_no2():
    params = {
        "latitude": ",".join(map(str, LATITUDES)),
        "longitude": ",".join(map(str, LONGITUDES)),
        "hourly": "nitrogen_dioxide",
        "past_days": 1,
        "forecast_days": 1,
        "timezone": TIMEZONE,
    }

    data = fetch_api(AIR_QUALITY_URL, params)

    if isinstance(data, dict):
        data = [data]

    if len(data) != len(LATITUDES):
        raise ValueError(
            "Jumlah respons data NO2 tidak sesuai dengan jumlah lokasi."
        )

    rows = []

    for location_id, item in enumerate(data, start=1):
        hourly = item.get("hourly", {})
        times = hourly.get("time", [])
        values = hourly.get("nitrogen_dioxide", [])

        for time_value, value in zip(times, values):
            rows.append(
                {
                    "location_id": location_id,
                    "time": pd.to_datetime(time_value),
                    "nitrogen_dioxide": value,
                }
            )

    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError("Data NO2 dari Open-Meteo kosong.")

    return df


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

    data = fetch_api(WEATHER_URL, params)

    if isinstance(data, dict):
        data = [data]

    if len(data) != len(LATITUDES):
        raise ValueError(
            "Jumlah respons meteorologi tidak sesuai dengan jumlah lokasi."
        )

    rows = []

    for location_id, item in enumerate(data, start=1):
        hourly = item.get("hourly", {})

        times = hourly.get("time", [])
        temperature = hourly.get("temperature_2m", [])
        humidity = hourly.get("relative_humidity_2m", [])
        rain = hourly.get("rain", [])
        wind_speed = hourly.get("wind_speed_10m", [])

        lengths = [
            len(times),
            len(temperature),
            len(humidity),
            len(rain),
            len(wind_speed),
        ]

        if len(set(lengths)) != 1:
            raise ValueError(
                f"Panjang data meteorologi lokasi {location_id} "
                "tidak konsisten."
            )

        for index, time_value in enumerate(times):
            rows.append(
                {
                    "location_id": location_id,
                    "time": pd.to_datetime(time_value),
                    "temperature_2m": temperature[index],
                    "relative_humidity_2m": humidity[index],
                    "rain": rain[index],
                    "wind_speed_10m": wind_speed[index],
                }
            )

    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError("Data meteorologi dari Open-Meteo kosong.")

    return df


def get_target_time():
    now = datetime.now(ZoneInfo(TIMEZONE))

    target = (
        now.replace(
            minute=0,
            second=0,
            microsecond=0,
        )
        + timedelta(hours=1)
    )

    return pd.Timestamp(target.replace(tzinfo=None))


def prepare_prediction_data(df_no2, df_weather, target_time):
    df = pd.merge(
        df_no2,
        df_weather,
        on=["location_id", "time"],
        how="inner",
    )

    df = df.sort_values(
        ["location_id", "time"]
    ).reset_index(drop=True)

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
                    f"Data NO2 lokasi {location_id} pada "
                    f"{lag_time} tidak tersedia."
                )

            value = previous.iloc[0]["nitrogen_dioxide"]

            if pd.isna(value):
                raise ValueError(
                    f"Data NO2 lokasi {location_id} pada "
                    f"{lag_time} kosong."
                )

            lag_values.append(float(value))

        weather_time = target_time - pd.Timedelta(hours=1)

        target_weather = location_data[
            location_data["time"] == weather_time
        ]

        if target_weather.empty:
            raise ValueError(
                f"Data meteorologi lokasi {location_id} pada "
                f"{weather_time} tidak tersedia."
            )

        weather = target_weather.iloc[0]

        weather_values = [
            weather["temperature_2m"],
            weather["relative_humidity_2m"],
            weather["rain"],
            weather["wind_speed_10m"],
        ]

        if any(pd.isna(value) for value in weather_values):
            raise ValueError(
                f"Data meteorologi lokasi {location_id} "
                "memiliki nilai kosong."
            )

        rows.append(
            {
                "location_id": location_id,
                "target_time": target_time,
                "weather_time": weather_time,
                "LAG1": lag_values[0],
                "LAG2": lag_values[1],
                "LAG3": lag_values[2],
                "temperature_2m": float(weather["temperature_2m"]),
                "relative_humidity_2m": float(
                    weather["relative_humidity_2m"]
                ),
                "rain": float(weather["rain"]),
                "wind_speed_10m": float(weather["wind_speed_10m"]),
            }
        )

    return pd.DataFrame(rows)


def load_models():
    if not SVR_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model SVR tidak ditemukan: {SVR_MODEL_PATH}"
        )

    if not XGBOOST_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model XGBoost tidak ditemukan: {XGBOOST_MODEL_PATH}"
        )

    svr_model = joblib.load(SVR_MODEL_PATH)
    xgboost_model = joblib.load(XGBOOST_MODEL_PATH)

    return svr_model, xgboost_model


def format_time(value):
    if pd.isna(value):
        return None

    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def generate_prediction():
    svr_model, xgboost_model = load_models()

    df_no2 = fetch_no2()
    df_weather = fetch_weather()

    target_time = get_target_time()

    prediction_data = prepare_prediction_data(
        df_no2,
        df_weather,
        target_time,
    )

    svr_predictions = svr_model.predict(
        prediction_data[SVR_FEATURES]
    )

    xgboost_predictions = xgboost_model.predict(
        prediction_data[XGBOOST_FEATURES]
    )

    results = []

    time_no2 = target_time - pd.Timedelta(hours=1)

    for index, row in prediction_data.iterrows():
        results.append(
            {
                "location_id": int(row["location_id"]),
                "nitrogen_dioxide": float(row["LAG1"]),
                "time_no2": format_time(time_no2),
                "target_time": format_time(row["target_time"]),
                "weather_time": format_time(row["weather_time"]),
                "LAG1": float(row["LAG1"]),
                "LAG2": float(row["LAG2"]),
                "LAG3": float(row["LAG3"]),
                "temperature_2m": float(row["temperature_2m"]),
                "relative_humidity_2m": float(
                    row["relative_humidity_2m"]
                ),
                "rain": float(row["rain"]),
                "wind_speed_10m": float(row["wind_speed_10m"]),
                "predicted_nitrogen_dioxide": float(
                    svr_predictions[index]
                ),
                "predicted_nitrogen_dioxide_xgboost": float(
                    xgboost_predictions[index]
                ),
            }
        )

    return {
        "success": True,
        "target_time": format_time(target_time),
        "data": results,
    }



def get_cached_prediction():
    global _memory_cache
    global _memory_cache_at

    connection = None
    lock_acquired = False
    last_payload = None
    last_updated_at = None

    # 1. Gunakan cache di memory jika tersedia.
    if _memory_cache is not None:
        age = time.time() - _memory_cache_at

        if age < CACHE_SECONDS:
            response = dict(_memory_cache)
            response["cached"] = True
            response["realtime_available"] = True
            return response

    try:
        # 2. Baca cache terakhir dari PostgreSQL.
        connection = get_database_connection()

        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS realtime_prediction_cache (
                    cache_key VARCHAR(50) PRIMARY KEY,
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)

            cursor.execute("""
                SELECT payload, updated_at
                FROM realtime_prediction_cache
                WHERE cache_key = %s
            """, (CACHE_KEY,))

            row = cursor.fetchone()

        connection.commit()

        if row:
            last_payload, last_updated_at = row

            if isinstance(last_payload, str):
                last_payload = json.loads(last_payload)

        # 3. Jika cache masih baru, langsung gunakan.
        age = cache_age_seconds(last_updated_at)

        print("CACHE STATUS:", {
            "found": last_payload is not None,
            "age_seconds": age,
            "cache_seconds": CACHE_SECONDS
        })

        if (
            last_payload is not None
            and age is not None
            and age < CACHE_SECONDS
        ):
            _memory_cache = last_payload
            _memory_cache_at = time.time()

            response = dict(last_payload)
            response["cached"] = True
            response["realtime_available"] = True
            return response

        # 4. Coba memperoleh lock agar tidak ada beberapa
        # request yang memperbarui prediksi secara bersamaan.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_try_advisory_lock(%s)",
                (742001,)
            )
            lock_acquired = cursor.fetchone()[0]

        # Jika request lain sedang memperbarui data,
        # gunakan cache lama jika tersedia.
        if not lock_acquired:
            if last_payload is not None:
                return add_cache_metadata(
                    last_payload,
                    last_updated_at,
                    stale=True
                )

            raise RuntimeError(
                "Prediksi sedang diproses dan cache belum tersedia."
            )

        # 5. Ambil data terbaru hanya ketika cache perlu diperbarui.
        print("CACHE MISS: mengambil data terbaru dari Open-Meteo.")

        result = generate_prediction()

        # 6. Simpan hasil baru hanya jika prediksi berhasil.
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO realtime_prediction_cache
                    (cache_key, payload, updated_at)
                VALUES (%s, %s::jsonb, NOW())
                ON CONFLICT (cache_key)
                DO UPDATE SET
                    payload = EXCLUDED.payload,
                    updated_at = NOW()
            """, (
                CACHE_KEY,
                json.dumps(result, allow_nan=False)
            ))

        connection.commit()

        _memory_cache = result
        _memory_cache_at = time.time()

        response = dict(result)
        response["cached"] = False
        response["realtime_available"] = True
        response["cache_warning"] = None

        return response

    except Exception as error:
        print(f"Gagal mengambil data terbaru: {error}")

        # 7. Jika API gagal, kembalikan prediksi terakhir.
        if last_payload is not None:
            print("CACHE FALLBACK: menggunakan prediksi terakhir.")

            _memory_cache = last_payload
            _memory_cache_at = time.time()

            response = dict(last_payload)
            response["cached"] = True
            response["realtime_available"] = False
            response["cache_warning"] = (
                "Data realtime tidak tersedia. "
                "Menampilkan prediksi terakhir yang tersimpan."
            )

            return response

        # Belum ada cache sama sekali.
        raise

    finally:
        if connection is not None:
            try:
                if lock_acquired:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT pg_advisory_unlock(%s)",
                            (742001,)
                        )
                    connection.commit()
            except Exception as error:
                print(f"Gagal melepas lock: {error}")
            finally:
                connection.close()
                
class handler(BaseHTTPRequestHandler):
    def send_json(self, status_code, payload):
        body = json.dumps(
            payload,
            allow_nan=False,
        ).encode("utf-8")

        self.send_response(status_code)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, OPTIONS",
        )
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization",
        )
        self.end_headers()

            
    def do_GET(self):
        try:
            result = get_cached_prediction()
            self.send_json(200, result)

        except requests.RequestException as error:
            print(f"Error Open-Meteo: {error}")
            self.send_json(
                502,
                {
                    "success": False,
                    "message": (
                        "Gagal mengambil data dari Open-Meteo "
                        "dan cache sebelumnya tidak tersedia."
                    ),
                    "error": str(error),
                },
            )

        except RuntimeError as error:
            message = str(error)
            print(f"Error runtime: {message}")

            if "Pembaruan prediksi sedang berlangsung" in message:
                self.send_json(
                    503,
                    {
                        "success": False,
                        "message": message,
                    },
                )
            else:
                self.send_json(
                    500,
                    {
                        "success": False,
                        "message": (
                            "Terjadi kesalahan pada backend Noxora."
                        ),
                        "error": message,
                    },
                )

        except Exception as error:
            print(f"Error endpoint realtime: {error}")
            self.send_json(
                500,
                {
                    "success": False,
                    "message": (
                        "Terjadi kesalahan pada proses prediksi "
                        "dan cache sebelumnya tidak tersedia."
                    ),
                    "error": str(error),
                },
            )