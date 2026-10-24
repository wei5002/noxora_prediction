import json
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from zoneinfo import ZoneInfo

import joblib
import pandas as pd
import requests


# Konfigurasi lokasi

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

FEATURES = [
    "LAG1",
    "LAG2",
    "LAG3",
    "temperature_2m",
    "relative_humidity_2m",
    "rain",
    "wind_speed_10m",
]


# Path model

BASE_DIR = Path(__file__).resolve().parents[2]

SVR_MODEL_PATH = (
    BASE_DIR
    / "ml"
    / "models"
    / "svr"
    / "svr_no2_meteorologi_80_20.joblib"
)

XGBOOST_MODEL_PATH = (
    BASE_DIR
    / "ml"
    / "models"
    / "xgboost"
    / "xgboost_no2_meteorologi_80_20.joblib"
)


# Request API

def fetch_api(url, params):
    response = requests.get(
        url,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


# Ambil data NO2

def fetch_no2():
    params = {
        "latitude": ",".join(
            map(str, LATITUDES)
        ),
        "longitude": ",".join(
            map(str, LONGITUDES)
        ),
        "hourly": "nitrogen_dioxide",
        "past_days": 1,
        "forecast_days": 1,
        "timezone": TIMEZONE,
    }

    data = fetch_api(
        AIR_QUALITY_URL,
        params,
    )

    if isinstance(data, dict):
        data = [data]

    rows = []

    for location_id, item in enumerate(
        data,
        start=1,
    ):
        hourly = item.get(
            "hourly",
            {},
        )

        times = hourly.get(
            "time",
            [],
        )

        values = hourly.get(
            "nitrogen_dioxide",
            [],
        )

        for time, value in zip(
            times,
            values,
        ):
            rows.append(
                {
                    "location_id": location_id,
                    "time": pd.to_datetime(time),
                    "nitrogen_dioxide": value,
                }
            )

    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError(
            "Data NO2 dari Open-Meteo kosong."
        )

    return df


# Ambil data meteorologi

def fetch_weather():
    params = {
        "latitude": ",".join(
            map(str, LATITUDES)
        ),
        "longitude": ",".join(
            map(str, LONGITUDES)
        ),
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

    data = fetch_api(
        WEATHER_URL,
        params,
    )

    if isinstance(data, dict):
        data = [data]

    rows = []

    for location_id, item in enumerate(
        data,
        start=1,
    ):
        hourly = item.get(
            "hourly",
            {},
        )

        times = hourly.get(
            "time",
            [],
        )

        temperature = hourly.get(
            "temperature_2m",
            [],
        )

        humidity = hourly.get(
            "relative_humidity_2m",
            [],
        )

        rain = hourly.get(
            "rain",
            [],
        )

        wind_speed = hourly.get(
            "wind_speed_10m",
            [],
        )

        for i, time in enumerate(times):
            rows.append(
                {
                    "location_id": location_id,
                    "time": pd.to_datetime(time),
                    "temperature_2m": temperature[i],
                    "relative_humidity_2m": humidity[i],
                    "rain": rain[i],
                    "wind_speed_10m": wind_speed[i],
                }
            )

    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError(
            "Data meteorologi dari Open-Meteo kosong."
        )

    return df


# Tentukan waktu prediksi

def get_target_time():
    now = datetime.now(
        ZoneInfo(TIMEZONE)
    )

    target = (
        now.replace(
            minute=0,
            second=0,
            microsecond=0,
        )
        + timedelta(hours=1)
    )

    return pd.Timestamp(
        target.replace(
            tzinfo=None
        )
    )


# Siapkan data prediksi

def prepare_prediction_data(
    df_no2,
    df_weather,
    target_time,
):
    df = pd.merge(
        df_no2,
        df_weather,
        on=[
            "location_id",
            "time",
        ],
        how="inner",
    )

    df = df.sort_values(
        [
            "location_id",
            "time",
        ]
    ).reset_index(
        drop=True
    )

    rows = []

    for location_id in range(
        1,
        len(LATITUDES) + 1,
    ):
        location_data = df[
            df["location_id"] == location_id
        ].sort_values(
            "time"
        )

        lag1_time = (
            target_time
            - pd.Timedelta(hours=1)
        )

        lag2_time = (
            target_time
            - pd.Timedelta(hours=2)
        )

        lag3_time = (
            target_time
            - pd.Timedelta(hours=3)
        )

        lag_times = [
            lag1_time,
            lag2_time,
            lag3_time,
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

            value = previous.iloc[0][
                "nitrogen_dioxide"
            ]

            if pd.isna(value):
                raise ValueError(
                    f"Data NO2 lokasi {location_id} "
                    f"pada {lag_time} kosong."
                )

            lag_values.append(
                float(value)
            )

        weather_time = (
            target_time
            - pd.Timedelta(hours=1)
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

        rows.append(
            {
                "location_id": location_id,
                "target_time": target_time,
                "weather_time": weather_time,
                "LAG1": lag_values[0],
                "LAG2": lag_values[1],
                "LAG3": lag_values[2],
                "temperature_2m": float(
                    weather["temperature_2m"]
                ),
                "relative_humidity_2m": float(
                    weather["relative_humidity_2m"]
                ),
                "rain": float(
                    weather["rain"]
                ),
                "wind_speed_10m": float(
                    weather["wind_speed_10m"]
                ),
            }
        )

    return pd.DataFrame(rows)


# Load model

def load_models():
    if not SVR_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model SVR tidak ditemukan: "
            f"{SVR_MODEL_PATH}"
        )

    if not XGBOOST_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model XGBoost tidak ditemukan: "
            f"{XGBOOST_MODEL_PATH}"
        )

    svr_model = joblib.load(
        SVR_MODEL_PATH
    )

    xgboost_model = joblib.load(
        XGBOOST_MODEL_PATH
    )

    return (
        svr_model,
        xgboost_model,
    )


# Format waktu

def format_time(value):
    if pd.isna(value):
        return None

    return pd.Timestamp(value).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# Generate prediction

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
        prediction_data[FEATURES]
    )

    xgboost_predictions = (
        xgboost_model.predict(
            prediction_data[FEATURES]
        )
    )

    results = []

    for i, row in prediction_data.iterrows():
        location_id = int(
            row["location_id"]
        )

        current_no2 = float(
            row["LAG1"]
        )

        time_no2 = (
            target_time
            - pd.Timedelta(hours=1)
        )

        results.append(
            {
                "location_id": location_id,
                "nitrogen_dioxide": current_no2,
                "time_no2": format_time(
                    time_no2
                ),
                "target_time": format_time(
                    row["target_time"]
                ),
                "weather_time": format_time(
                    row["weather_time"]
                ),
                "LAG1": float(
                    row["LAG1"]
                ),
                "LAG2": float(
                    row["LAG2"]
                ),
                "LAG3": float(
                    row["LAG3"]
                ),
                "temperature_2m": float(
                    row["temperature_2m"]
                ),
                "relative_humidity_2m": float(
                    row["relative_humidity_2m"]
                ),
                "rain": float(
                    row["rain"]
                ),
                "wind_speed_10m": float(
                    row["wind_speed_10m"]
                ),
                "predicted_nitrogen_dioxide": float(
                    svr_predictions[i]
                ),
                "predicted_nitrogen_dioxide_xgboost": float(
                    xgboost_predictions[i]
                ),
            }
        )

    return {
        "success": True,
        "target_time": format_time(
            target_time
        ),
        "data": results,
    }

# Vercel Function
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            result = generate_prediction()

            body = json.dumps(
                result
            ).encode("utf-8")

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/json",
            )
            self.send_header(
                "Access-Control-Allow-Origin",
                "*",
            )
            self.send_header(
                "Content-Length",
                str(len(body)),
            )
            self.end_headers()

            self.wfile.write(body)

        except requests.RequestException as error:
            body = json.dumps(
                {
                    "success": False,
                    "message": (
                        "Gagal mengambil data "
                        "dari Open-Meteo."
                    ),
                    "error": str(error),
                }
            ).encode("utf-8")

            self.send_response(502)
            self.send_header(
                "Content-Type",
                "application/json",
            )
            self.send_header(
                "Access-Control-Allow-Origin",
                "*",
            )
            self.send_header(
                "Content-Length",
                str(len(body)),
            )
            self.end_headers()

            self.wfile.write(body)

        except Exception as error:
            body = json.dumps(
                {
                    "success": False,
                    "message": (
                        "Terjadi kesalahan "
                        "pada proses prediksi."
                    ),
                    "error": str(error),
                }
            ).encode("utf-8")

            self.send_response(500)
            self.send_header(
                "Content-Type",
                "application/json",
            )
            self.send_header(
                "Access-Control-Allow-Origin",
                "*",
            )
            self.send_header(
                "Content-Length",
                str(len(body)),
            )
            self.end_headers()

            self.wfile.write(body)