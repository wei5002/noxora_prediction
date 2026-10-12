import json
import os
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from zoneinfo import ZoneInfo

import joblib
import pandas as pd
import requests
import psycopg2
from psycopg2.extras import Json, RealDictCursor


# KONFIGURASI

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

CACHE_KEY = "noxora_realtime_prediction"
COOLDOWN_KEY = "noxora_realtime_cooldown"
ADVISORY_LOCK_ID = 742001

REQUEST_TIMEOUT = 15
MAX_ATTEMPTS = 3                     
FAILURE_COOLDOWN_SECONDS = 120      
MIN_COOLDOWN_SECONDS = 60              
DEFAULT_RATE_LIMIT_COOLDOWN = 15 * 60  
MAX_COOLDOWN_SECONDS = 60 * 60


OPEN_METEO_API_KEY = os.getenv("OPEN_METEO_API_KEY")

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "noxora-prediction/1.0"})


class UpstreamUnavailable(Exception):
    """Open-Meteo membatasi (429) atau sedang bermasalah."""

    def __init__(self, message, cooldown_seconds):
        super().__init__(message)
        self.cooldown_seconds = int(cooldown_seconds)


FEATURES_SVR = [
    "LAG1",
    "LAG2",
    "LAG3",
    "temperature_2m",
    "relative_humidity_2m",
    "rain",
    "wind_speed_10m",
]

FEATURES_XGBOOST = [
    "LAG1",
    "LAG2",
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# PATH MODEL

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


# DATABASE NEON
def get_database_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "Environment variable DATABASE_URL belum diatur."
        )

    return psycopg2.connect(
        database_url,
        sslmode="require",
        connect_timeout=10,
    )


def ensure_cache_table():
    connection = get_database_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS
                    realtime_prediction_cache (
                        cache_key VARCHAR(100) PRIMARY KEY,
                        payload JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                            DEFAULT NOW()
                    )
                    """
                )
    finally:
        connection.close()


def load_cache(connection, key=CACHE_KEY):
    with connection.cursor(
        cursor_factory=RealDictCursor
    ) as cursor:
        cursor.execute(
            """
            SELECT payload, updated_at
            FROM realtime_prediction_cache
            WHERE cache_key = %s
            """,
            (key,),
        )

        row = cursor.fetchone()

    if not row:
        return None, None

    payload = row["payload"]

    if isinstance(payload, str):
        payload = json.loads(payload)

    return payload, row["updated_at"]


def save_cache(connection, payload, key=CACHE_KEY):
    # Untuk cache prediksi: hanya dipanggil setelah prediksi berhasil.
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO realtime_prediction_cache (
                    cache_key,
                    payload,
                    updated_at
                )
                VALUES (%s, %s, NOW())
                ON CONFLICT (cache_key)
                DO UPDATE SET
                    payload = EXCLUDED.payload,
                    updated_at = NOW()
                """,
                (key, Json(payload)),
            )


def delete_cache_key(connection, key):
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM realtime_prediction_cache "
                "WHERE cache_key = %s",
                (key,),
            )

def get_cooldown_remaining(connection):
    payload, _ = load_cache(connection, COOLDOWN_KEY)

    if not payload:
        return 0

    try:
        return max(0, int(float(payload["until"]) - time.time()))
    except (KeyError, TypeError, ValueError):
        return 0


def set_cooldown(connection, seconds, reason):
    seconds = max(1, min(int(seconds), MAX_COOLDOWN_SECONDS))

    try:
        connection.rollback()
        save_cache(
            connection,
            {"until": time.time() + seconds, "reason": reason[:300]},
            COOLDOWN_KEY,
        )
    except Exception:
        logger.exception("Gagal menyimpan cooldown.")


def clear_cooldown(connection):
    try:
        delete_cache_key(connection, COOLDOWN_KEY)
    except Exception:
        logger.exception("Gagal menghapus cooldown.")


def is_cache_fresh(payload):
    if not payload:
        return False

    return payload.get("target_time") == format_time(
        get_target_time()
    )


def add_cache_metadata(payload, updated_at):
    result = dict(payload)

    age_seconds = None

    if updated_at is not None:
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        age_seconds = max(
            0,
            int(
                (
                    datetime.now(timezone.utc) - updated_at
                ).total_seconds()
            ),
        )

    result["cache"] = {
        "cached": updated_at is not None,
        "updated_at": (
            updated_at.isoformat() if updated_at else None
        ),
        "age_seconds": age_seconds,
        "stale": not is_cache_fresh(payload),
    }

    return result


# OPEN-METEO
def build_request(url, params):
    if not OPEN_METEO_API_KEY:
        return url, params

    url = url.replace(
        "https://air-quality-api.",
        "https://customer-air-quality-api.",
    ).replace(
        "https://api.",
        "https://customer-api.",
    )

    return url, {**params, "apikey": OPEN_METEO_API_KEY}


def rate_limit_cooldown(response):
    retry_after = response.headers.get("Retry-After")

    if retry_after and retry_after.isdigit():
        return max(int(retry_after), MIN_COOLDOWN_SECONDS)

    try:
        reason = str(response.json().get("reason", "")).lower()
    except ValueError:
        reason = ""

    now = datetime.now(timezone.utc)

    if "minutely" in reason:
        return 90

    if "hourly" in reason:
        next_hour = now.replace(
            minute=0, second=0, microsecond=0
        ) + timedelta(hours=1)
        return max(
            int((next_hour - now).total_seconds()) + 5,
            MIN_COOLDOWN_SECONDS,
        )

    if "daily" in reason:
        return MAX_COOLDOWN_SECONDS  # cek lagi paling cepat tiap 1 jam

    return DEFAULT_RATE_LIMIT_COOLDOWN


def fetch_api(url, params):
    url, params = build_request(url, params)

    last_error = None

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = SESSION.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
        except (requests.Timeout, requests.ConnectionError) as error:
            last_error = error
        else:
            # 429: JANGAN di-retry. Retry hanya memperparah limit.
            if response.status_code == 429:
                raise UpstreamUnavailable(
                    "Open-Meteo membatasi request (429).",
                    rate_limit_cooldown(response),
                )

            if response.status_code >= 500:
                last_error = requests.HTTPError(
                    f"Open-Meteo HTTP {response.status_code}"
                )
            else:
                response.raise_for_status()
                return response.json()

        if attempt < MAX_ATTEMPTS - 1:
            time.sleep(min(2 ** attempt + random.random(), 4))

    raise last_error


def fetch_no2():
    params = {
        "latitude": ",".join(map(str, LATITUDES)),
        "longitude": ",".join(map(str, LONGITUDES)),
        "hourly": "nitrogen_dioxide",
        "past_hours": 3,
        "forecast_hours": 1,
        "timezone": TIMEZONE,
    }

    data = fetch_api(AIR_QUALITY_URL, params)

    if isinstance(data, dict):
        data = [data]

    if len(data) != len(LATITUDES):
        raise ValueError(
            "Jumlah lokasi data NO2 tidak sesuai."
        )

    rows = []

    for location_id, item in enumerate(data, start=1):
        hourly = item.get("hourly", {})
        times = hourly.get("time", [])
        values = hourly.get("nitrogen_dioxide", [])

        if len(times) != len(values):
            raise ValueError(
                f"Panjang data NO2 lokasi {location_id} tidak sesuai."
            )

        for time_value, value in zip(times, values):
            rows.append({
                "location_id": location_id,
                "time": pd.to_datetime(time_value),
                "nitrogen_dioxide": value,
            })

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
        "past_hours": 3,
        "forecast_hours": 1,
        "timezone": TIMEZONE,
        "wind_speed_unit": "kmh",
    }

    data = fetch_api(WEATHER_URL, params)

    if isinstance(data, dict):
        data = [data]

    if len(data) != len(LATITUDES):
        raise ValueError(
            "Jumlah lokasi data meteorologi tidak sesuai."
        )

    rows = []

    for location_id, item in enumerate(data, start=1):
        hourly = item.get("hourly", {})

        times = hourly.get("time", [])
        temperature = hourly.get("temperature_2m", [])
        humidity = hourly.get("relative_humidity_2m", [])
        rain = hourly.get("rain", [])
        wind_speed = hourly.get("wind_speed_10m", [])

        lengths = {
            len(times),
            len(temperature),
            len(humidity),
            len(rain),
            len(wind_speed),
        }

        if len(lengths) != 1:
            raise ValueError(
                "Panjang data meteorologi lokasi "
                f"{location_id} tidak sesuai."
            )

        for i, time_value in enumerate(times):
            rows.append({
                "location_id": location_id,
                "time": pd.to_datetime(time_value),
                "temperature_2m": temperature[i],
                "relative_humidity_2m": humidity[i],
                "rain": rain[i],
                "wind_speed_10m": wind_speed[i],
            })

    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError(
            "Data meteorologi dari Open-Meteo kosong."
        )

    return df


# WAKTU TARGET DAN PERSIAPAN FITUR
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

    return pd.Timestamp(
        target.replace(tzinfo=None)
    )


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
    )

    df = df.sort_values(
        ["location_id", "time"]
    ).reset_index(drop=True)

    rows = []

    lag1_time = target_time - pd.Timedelta(hours=1)
    lag2_time = target_time - pd.Timedelta(hours=2)
    lag3_time = target_time - pd.Timedelta(hours=3)

    weather_time = target_time - pd.Timedelta(hours=1)

    for location_id in range(1, len(LATITUDES) + 1):
        location_data = df[
            df["location_id"] == location_id
        ]

        def get_value(time_value, column):
            matched = location_data[
                location_data["time"] == time_value
            ]

            if matched.empty:
                raise ValueError(
                    f"Data {column} lokasi {location_id} "
                    f"pada {time_value} tidak tersedia."
                )

            value = matched.iloc[0][column]

            if pd.isna(value):
                raise ValueError(
                    f"Data {column} lokasi {location_id} "
                    f"pada {time_value} kosong."
                )

            return float(value)

        lag1 = get_value(
            lag1_time,
            "nitrogen_dioxide",
        )
        lag2 = get_value(
            lag2_time,
            "nitrogen_dioxide",
        )
        lag3 = get_value(
            lag3_time,
            "nitrogen_dioxide",
        )

        temperature = get_value(
            weather_time,
            "temperature_2m",
        )
        humidity = get_value(
            weather_time,
            "relative_humidity_2m",
        )
        rain = get_value(
            weather_time,
            "rain",
        )
        wind_speed = get_value(
            weather_time,
            "wind_speed_10m",
        )

        rows.append({
            "location_id": location_id,
            "target_time": target_time,
            "weather_time": weather_time,
            "LAG1": lag1,
            "LAG2": lag2,
            "LAG3": lag3,
            "temperature_2m": temperature,
            "relative_humidity_2m": humidity,
            "rain": rain,
            "wind_speed_10m": wind_speed,
        })

    return pd.DataFrame(rows)


# MODEL
def load_models():
    if not SVR_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model SVR tidak ditemukan: {SVR_MODEL_PATH}"
        )

    if not XGBOOST_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model XGBoost tidak ditemukan: "
            f"{XGBOOST_MODEL_PATH}"
        )

    return (
        joblib.load(SVR_MODEL_PATH),
        joblib.load(XGBOOST_MODEL_PATH),
    )


def format_time(value):
    if pd.isna(value):
        return None

    return pd.Timestamp(value).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def generate_prediction():
    with ThreadPoolExecutor(max_workers=2) as pool:
        future_no2 = pool.submit(fetch_no2)
        future_weather = pool.submit(fetch_weather)
        df_no2 = future_no2.result()
        df_weather = future_weather.result()

    target_time = get_target_time()

    prediction_data = prepare_prediction_data(
        df_no2,
        df_weather,
        target_time,
    )

    svr_model, xgboost_model = load_models()

    svr_predictions = svr_model.predict(
        prediction_data[FEATURES_SVR]
    )

    xgboost_predictions = xgboost_model.predict(
        prediction_data[FEATURES_XGBOOST]
    )

    results = []

    for i, row in prediction_data.iterrows():
        results.append({
            "location_id": int(row["location_id"]),
            "nitrogen_dioxide": float(row["LAG1"]),
            "time_no2": format_time(
                target_time - pd.Timedelta(hours=1)
            ),
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
                svr_predictions[i]
            ),
            "predicted_nitrogen_dioxide_xgboost": float(
                xgboost_predictions[i]
            ),
        })

    return {
        "success": True,
        "target_time": format_time(target_time),
        "data": results,
    }


# CACHE DAN REFRESH
def stale_result(payload, updated_at, warning, retry_after=None):
    result = add_cache_metadata(payload, updated_at)
    result["warning"] = warning

    if retry_after is not None:
        result["retry_after_seconds"] = retry_after

    return result


def get_cached_prediction():
    ensure_cache_table()

    connection = get_database_connection()

    try:
        cached_payload, updated_at = load_cache(connection)

        if is_cache_fresh(cached_payload):
            return add_cache_metadata(cached_payload, updated_at)

        remaining = get_cooldown_remaining(connection)

        if remaining > 0:
            if cached_payload:
                return stale_result(
                    cached_payload,
                    updated_at,
                    "Sumber data sedang dibatasi. Data terakhir "
                    "yang berhasil tetap ditampilkan.",
                    remaining,
                )

            raise UpstreamUnavailable(
                "Sumber data sedang dibatasi.", remaining
            )

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_try_advisory_lock(%s)",
                (ADVISORY_LOCK_ID,),
            )
            lock_acquired = cursor.fetchone()[0]

        if not lock_acquired:
            if cached_payload:
                return add_cache_metadata(cached_payload, updated_at)

            return {
                "success": False,
                "message": (
                    "Data realtime sedang disiapkan. "
                    "Silakan coba kembali sebentar lagi."
                ),
                "data": [],
            }

        try:
            cached_payload, updated_at = load_cache(connection)

            if is_cache_fresh(cached_payload):
                return add_cache_metadata(cached_payload, updated_at)
            new_payload = generate_prediction()
            if not new_payload.get("success"):
                raise RuntimeError(
                    "Proses prediksi tidak menghasilkan data sukses."
                )

            save_cache(connection, new_payload)
            clear_cooldown(connection)
            _, saved_updated_at = load_cache(connection)
            logger.info("Cache realtime berhasil diperbarui.")
            return add_cache_metadata(new_payload, saved_updated_at)

        except UpstreamUnavailable as error:
            logger.warning("Open-Meteo dibatasi: %s", error)
            set_cooldown(
                connection, error.cooldown_seconds, str(error)
            )

            if cached_payload:
                return stale_result(
                    cached_payload,
                    updated_at,
                    "Sumber data sedang dibatasi. Data terakhir "
                    "yang berhasil tetap ditampilkan.",
                    error.cooldown_seconds,
                )

            raise

        except Exception as error:
            logger.exception("Refresh realtime gagal: %s", error)
            set_cooldown(
                connection, FAILURE_COOLDOWN_SECONDS, str(error)
            )

            if cached_payload:
                return stale_result(
                    cached_payload,
                    updated_at,
                    "Pembaruan data gagal. Data dan prediksi "
                    "terakhir yang berhasil tetap ditampilkan.",
                    FAILURE_COOLDOWN_SECONDS,
                )

            raise

        finally:
            try:
                connection.rollback()
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT pg_advisory_unlock(%s)",
                        (ADVISORY_LOCK_ID,),
                    )
                connection.commit()
            except Exception:
                logger.exception("Gagal melepaskan advisory lock.")

    finally:
        connection.close()


# RESPONS HTTP VERCEL

def send_json(handler, status_code, payload, cacheable=False,
              retry_after=None):
    body = json.dumps(payload, allow_nan=False).encode("utf-8")

    handler.send_response(status_code)
    handler.send_header(
        "Content-Type", "application/json; charset=utf-8"
    )
    handler.send_header("Access-Control-Allow-Origin", "*")

    handler.send_header(
        "Cache-Control",
        (
            "public, s-maxage=60, stale-while-revalidate=300"
            if cacheable
            else "no-store"
        ),
    )

    if retry_after is not None:
        handler.send_header("Retry-After", str(int(retry_after)))

    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization",
        )
        self.end_headers()

    def do_GET(self):
        try:
            result = get_cached_prediction()

            if not result.get("success"):
                send_json(self, 503, result, retry_after=5)
                return

            cacheable = (
                not result.get("warning")
                and not result.get("cache", {}).get("stale")
            )

            send_json(self, 200, result, cacheable=cacheable)

        except UpstreamUnavailable as error:
            send_json(
                self,
                503,
                {
                    "success": False,
                    "message": (
                        "Sumber data cuaca/udara sedang membatasi "
                        "request dan belum ada cache. Coba lagi "
                        "beberapa saat."
                    ),
                    "retry_after_seconds": error.cooldown_seconds,
                    "data": [],
                },
                retry_after=error.cooldown_seconds,
            )

        except requests.RequestException as error:
            logger.exception("Open-Meteo request gagal.")

            send_json(
                self,
                502,
                {
                    "success": False,
                    "message": (
                        "Gagal mengambil data Open-Meteo "
                        "dan cache sebelumnya belum tersedia."
                    ),
                    "error": str(error),
                    "data": [],
                },
            )

        except Exception as error:
            logger.exception("Endpoint realtime gagal.")

            send_json(
                self,
                500,
                {
                    "success": False,
                    "message": (
                        "Terjadi kesalahan pada proses "
                        "prediksi realtime."
                    ),
                    "error": str(error),
                    "data": [],
                },
            )