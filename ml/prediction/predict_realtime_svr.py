import requests
import pandas as pd
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
OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# 3. REQUEST API
def fetch_api(url, params):
    response = requests.get(
        url,
        params=params,
        timeout=60
    )

    response.raise_for_status()
    return response.json()


# 4. AMBIL DATA NO2 HOURLY
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
        params
    )

    if isinstance(data, dict):
        data = [data]

    rows = []

    for location_id, item in enumerate(
        data,
        start=1
    ):

        hourly = item.get(
            "hourly",
            {}
        )

        for time, value in zip(
            hourly.get("time", []),
            hourly.get(
                "nitrogen_dioxide",
                []
            )
        ):

            rows.append({
                "location_id": location_id,
                "time": pd.to_datetime(time),
                "nitrogen_dioxide": value,
            })

    return pd.DataFrame(rows)


# 5. AMBIL DATA METEOROLOGI HOURLY
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
        params
    )

    if isinstance(data, dict):
        data = [data]

    rows = []

    for location_id, item in enumerate(
        data,
        start=1
    ):

        hourly = item.get(
            "hourly",
            {}
        )

        times = hourly.get(
            "time",
            []
        )

        for i, time in enumerate(times):

            rows.append({
                "location_id": location_id,
                "time": pd.to_datetime(time),
                "temperature_2m":
                    hourly["temperature_2m"][i],
                "relative_humidity_2m":
                    hourly["relative_humidity_2m"][i],
                "rain":
                    hourly["rain"][i],
                "wind_speed_10m":
                    hourly["wind_speed_10m"][i],
            })

    return pd.DataFrame(rows)


# 6. TENTUKAN WAKTU PREDIKSI
def get_target_time():

    now = datetime.now(
        ZoneInfo(TIMEZONE)
    )

    target = now.replace(
        minute=0,
        second=0,
        microsecond=0
    ) + timedelta(hours=1)

    # Hilangkan timezone
    target = target.replace(
        tzinfo=None
    )

    return pd.Timestamp(target)


# 7. SIAPKAN FITUR PREDIKSI
def prepare_prediction_data(
    df_no2,
    df_weather,
    target_time
):

    df = pd.merge(

        df_no2,

        df_weather,

        on=[
            "location_id",
            "time"
        ],

        how="inner"
    )

    df = df.sort_values(
        [
            "location_id",
            "time"
        ]
    ).reset_index(
        drop=True
    )

    rows = []

    for location_id in range(
        1,
        len(LATITUDES) + 1
    ):

        location_data = df[
            df["location_id"]
            == location_id
        ].sort_values(
            "time"
        )

        # LAG 1, LAG 2, LAG 3
        lag_times = [

            target_time
            - pd.Timedelta(hours=1),

            target_time
            - pd.Timedelta(hours=2),

            target_time
            - pd.Timedelta(hours=3),

        ]

        lag_values = []
        for lag_time in lag_times:
            previous = location_data[
                location_data["time"]
                == lag_time
            ]
            if previous.empty:
                raise ValueError(

                    f"Data NO2 untuk lokasi "
                    f"{location_id} pada "
                    f"{lag_time} tidak tersedia."

                )
            lag_values.append(

                previous.iloc[0][
                    "nitrogen_dioxide"
                ]

            )

        # DATA METEOROLOGI
        weather_time = (
            target_time
            - pd.Timedelta(hours=1)
        )
        target_weather = location_data[
            location_data["time"]
            == weather_time
        ]

        if target_weather.empty:

            raise ValueError(

                f"Data meteorologi lokasi "
                f"{location_id} pada "
                f"{weather_time} tidak tersedia."

            )

        weather = target_weather.iloc[0]

        # SIMPAN DATA
        rows.append({
            "location_id": location_id,
            "target_time": target_time,
            "weather_time": weather_time,
            "LAG1": lag_values[0],
            "LAG2": lag_values[1],
            "LAG3": lag_values[2],
            "temperature_2m":
                weather["temperature_2m"],
            "relative_humidity_2m":
                weather["relative_humidity_2m"],
            "rain":
                weather["rain"],
            "wind_speed_10m":
                weather["wind_speed_10m"],
        })
    return pd.DataFrame(rows)


# 8. PREDIKSI SVR
def main():

    # CEK MODEL
    if not MODEL_PATH.exists():

        raise FileNotFoundError(

            f"Model SVR tidak ditemukan: "
            f"{MODEL_PATH}"

        )
    print(
        "Memuat model SVR RBF..."
    )
    model = joblib.load(
        MODEL_PATH
    )
    print(
        "Model SVR berhasil dimuat."
    )
    # AMBIL DATA NO2
    print(
        "\nMengambil data NO2..."
    )
    df_no2 = fetch_no2()
    # AMBIL DATA METEOROLOGI
    print(
        "Mengambil data meteorologi..."
    )
    df_weather = fetch_weather()

    # WAKTU TARGET
    target_time = get_target_time()
    print(
        f"\nTarget prediksi: "
        f"{target_time.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    # SIAPKAN FITUR
    X = prepare_prediction_data(
        df_no2,
        df_weather,
        target_time

    )

    # PREDIKSI
    predictions = model.predict(
        X[SVR_FEATURES]
    )

    X[
        "predicted_nitrogen_dioxide"
    ] = predictions

    # FORMAT WAKTU
    X["target_time"] = X[
        "target_time"
    ].apply(

        lambda x:
        x.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    )

    X["weather_time"] = X[
        "weather_time"
    ].apply(

        lambda x:
        x.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    )

    # SIMPAN CSV
    output_file = (
        OUTPUT_DIR
        / "svr_realtime_predictions.csv"
    )

    X.to_csv(
        output_file,
        index=False,
        lineterminator="\n"

    )

    # HASIL
    print(
        "\nPrediksi SVR selesai!"
    )

    print(
        X.to_string(
            index=False
        )
    )

    print(
        f"\nHasil tersimpan di: "
        f"{output_file}"
    )


# 9. JALANKAN PROGRAM
if __name__ == "__main__":
    try:

        main()
    except requests.RequestException as error:
        print(
            f"Gagal mengambil API: {error}"
        )
    except (
        ValueError,
        KeyError,
        IndexError
    ) as error:

        print(
            f"Terjadi kesalahan: {error}"
        )