
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


# 2. KONFIGURASI LOKASI MODEL
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


# 3. MENGAMBIL DATA DARI API

def fetch_api(url, params):
    response = requests.get(
        url,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


# 4. MENGAMBIL DATA NO2

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

    # Jika respons hanya berupa dictionary (satu lokasi)
    # ubah menjadi list agar dapat diproses dengan perulangan
    if isinstance(data, dict):
        data = [data]

    rows = []

    # Mengulang setiap respons lokasi.
    # enumerate(start=1) memberikan nomor lokasi mulai dari 1.
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
            "NO2 data from Open-Meteo is empty."
        )

    return df


# 5. MENGAMBIL DATA METEOROLOGI

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

    # Jika respons hanya berupa dictionary,
    # ubah menjadi list agar formatnya seragam.
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
            "Weather data from Open-Meteo is empty."
        )

    return df


# 6. MENENTUKAN WAKTU TARGET PREDIKSI
def get_target_time():
    # Mengambil waktu saat ini berdasarkan zona waktu Jakarta.
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

    # Menghapus informasi timezone agar format waktu
    # sesuai dengan waktu pada DataFrame hasil API.
    return pd.Timestamp(
        target.replace(
            tzinfo=None
        )
    )


# 7. MENYIAPKAN DATA UNTUK PREDIKSI

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
                    f"NO2 data for location {location_id} "
                    f"at {lag_time} is unavailable."
                )

            # Mengambil nilai NO2 dari baris pertama hasil pencarian.
            value = previous.iloc[0][
                "nitrogen_dioxide"
            ]

            # Memastikan nilai NO2 tidak kosong.
            if pd.isna(value):
                raise ValueError(
                    f"NO2 data for location {location_id} "
                    f"at {lag_time} is empty."
                )

            # Mengubah nilai NO2 menjadi float,
            # kemudian memasukkannya ke dalam list lag_values.
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
                f"Weather data for location {location_id} "
                f"at {weather_time} is unavailable."
            )

        # Mengambil baris pertama yang sesuai dengan waktu meteorologi.
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


# 8. MEMUAT MODEL MACHINE LEARNING
def load_models():
    if not SVR_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"SVR model not found: "
            f"{SVR_MODEL_PATH}"
        )

    if not XGBOOST_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"XGBoost model not found: "
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


# 9. MEMFORMAT DATA WAKTU
def format_time(value):
    # Jika nilai waktu kosong, kembalikan None.
    # None nantinya akan diubah menjadi null dalam JSON.
    if pd.isna(value):
        return None

    # Tahun-Bulan-Tanggal Jam:Menit:Detik.
    return pd.Timestamp(value).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# 10. MENJALANKAN PROSES PREDIKSI
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


# 11. VERCEL FUNCTION / HTTP HANDLER
# BaseHTTPRequestHandler digunakan untuk menangani HTTP request.
# Class handler ini menjadi pintu masuk ketika endpoint dipanggil.
class handler(BaseHTTPRequestHandler):
    # Fungsi ini dijalankan ketika endpoint menerima HTTP GET request.
    def do_GET(self):
        try:
            # Menjalankan seluruh proses pengambilan data
            # hingga menghasilkan prediksi NO2.
            result = generate_prediction()

            # Mengubah dictionary Python menjadi JSON.
            body = json.dumps(
                result
            ).encode("utf-8")

            self.send_response(200)

            # Memberi tahu client bahwa respons berformat JSON.
            self.send_header(
                "Content-Type",
                "application/json",
            )

            # Mengizinkan request dari berbagai origin.
            # Header ini berkaitan dengan aturan CORS.
            self.send_header(
                "Access-Control-Allow-Origin",
                "*",
            )

            # Mengirim ukuran respons dalam satuan byte.
            self.send_header(
                "Content-Length",
                str(len(body)),
            )

            # Menandakan bagian header HTTP sudah selesai.
            self.end_headers()

            # Mengirim isi respons JSON kepada client.
            self.wfile.write(body)

        # Menangani error yang berkaitan dengan request ke API.
        # Contohnya koneksi gagal atau respons HTTP tidak berhasil.
        except requests.RequestException as error:

            # Menyiapkan pesan error dalam format JSON.
            body = json.dumps(
                {
                    "success": False,
                    "message": (
                        "Failed to retrieve data "
                        "from Open-Meteo."
                    ),
                    "error": str(error),
                }
            ).encode("utf-8")

            # Status 502 menunjukkan masalah saat menerima
            # respons dari layanan eksternal.
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

            # Mengirim informasi error kepada client.
            self.wfile.write(body)

        # Menangani error lain yang tidak termasuk RequestException.
        # Contohnya model tidak ditemukan atau data input tidak lengkap.
        except Exception as error:
            # Menyiapkan informasi error dalam format JSON.
            body = json.dumps(
                {
                    "success": False,
                    "message": (
                        "An error occurred during "
                        "the prediction process."
                    ),
                    "error": str(error),
                }
            ).encode("utf-8")

            # Status 500 menunjukkan terjadi kesalahan pada server.
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