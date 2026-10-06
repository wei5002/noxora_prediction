import requests
import pandas as pd

from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from datetime import datetime


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


# 2. URL API
AIR_QUALITY_URL = (
    "https://air-quality-api.open-meteo.com/v1/air-quality"
)

WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
)


# 3. FUNGSI MENGAMBIL DATA API
def fetch_api(url, params):
    response = requests.get(
        url,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    return response.json()


# 4. AMBIL DATA NO2 TERKINI
def fetch_no2():
    params = {
        "latitude": ",".join(map(str, LATITUDES)),
        "longitude": ",".join(map(str, LONGITUDES)),
        "hourly": "nitrogen_dioxide",
        "past_days": 1,
        "forecast_days": 1,
        "timezone": "Asia/Jakarta",
    }

    data = fetch_api(AIR_QUALITY_URL, params)

    if isinstance(data, dict):
        data = [data]

    rows = []

    for i, item in enumerate(data):
        hourly = item.get("hourly", {})

        times = hourly.get("time", [])
        nitrogen_dioxide = hourly.get(
            "nitrogen_dioxide",
            []
        )

        for time, value in zip(
            times,
            nitrogen_dioxide
        ):
            rows.append({
                "location_id": i + 1,
                "time": pd.to_datetime(time),
                "nitrogen_dioxide": value,
            })

    return pd.DataFrame(rows)


# 5. AMBIL DATA METEOROLOGI TERKINI
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
        "timezone": "Asia/Jakarta",
    }

    data = fetch_api(WEATHER_URL, params)

    if isinstance(data, dict):
        data = [data]

    rows = []

    for i, item in enumerate(data):
        current = item.get("current", {})

        rows.append({
            "location_id": i + 1,
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

    return pd.DataFrame(rows)


# 6. JALANKAN PENGAMBILAN DATA
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
        ZoneInfo("Asia/Jakarta")
    )

    realtime_time = pd.Timestamp(
        now.replace(
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=None
        )
    )   

    rows = []

    for location_id in range(
        1,
        len(LATITUDES) + 1
    ):
        location_data = df_no2[
            df_no2["location_id"] == location_id
        ].sort_values("time")

        current_data = location_data[
            location_data["time"] == realtime_time
        ]

        if current_data.empty:
            continue

        current_no2 = current_data.iloc[0][
            "nitrogen_dioxide"
        ]

        lag1_time = (
            realtime_time
            - pd.Timedelta(hours=1)
        )

        lag2_time = (
            realtime_time
            - pd.Timedelta(hours=2)
        )

        lag3_time = (
            realtime_time
            - pd.Timedelta(hours=3)
        )

        lag1_data = location_data[
            location_data["time"] == lag1_time
        ]

        lag2_data = location_data[
            location_data["time"] == lag2_time
        ]

        lag3_data = location_data[
            location_data["time"] == lag3_time
        ]

        lag1 = (
            lag1_data.iloc[0]["nitrogen_dioxide"]
            if not lag1_data.empty
            else None
        )

        lag2 = (
            lag2_data.iloc[0]["nitrogen_dioxide"]
            if not lag2_data.empty
            else None
        )

        lag3 = (
            lag3_data.iloc[0]["nitrogen_dioxide"]
            if not lag3_data.empty
            else None
        )

        weather_data = df_weather[
            df_weather["location_id"]
            == location_id
        ]

        if weather_data.empty:
            continue

        weather = weather_data.iloc[0]

        rows.append({
            "location_id": location_id,
            "time_no2": current_data.iloc[0]["time"],
            "nitrogen_dioxide": current_no2,
            "time_weather": weather["time_weather"],
            "temperature_2m":
                weather["temperature_2m"],
            "relative_humidity_2m":
                weather["relative_humidity_2m"],
            "rain":
                weather["rain"],
            "wind_speed_10m":
                weather["wind_speed_10m"],
            "LAG1": lag1,
            "LAG2": lag2,
            "LAG3": lag3,
        })

    df = pd.DataFrame(rows)

    # Simpan CSV secara otomatis.
    ml_dir = Path(__file__).resolve().parents[1]

    output_dir = ml_dir / "data" / "api"
    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = output_dir / "realtime_api.csv"

    df.to_csv(
        output_file,
        index=False
    )

    print("\nPengambilan data selesai!")
    print(f"Jumlah lokasi: {len(df)}")
    print(f"File tersimpan di: {output_file}")

    print("\nData API:")
    print(df.to_string(index=False))


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as error:
        print(
            f"Gagal mengambil data dari API: {error}"
        )
    except (
        KeyError,
        TypeError,
        ValueError
    ) as error:
        print(
            f"Terjadi kesalahan saat memproses data: {error}"
        )