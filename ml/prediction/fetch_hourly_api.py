import requests
import pandas as pd

from pathlib import Path


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

AIR_QUALITY_URL = (
    "https://air-quality-api.open-meteo.com/v1/air-quality"
)

WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
)

PAST_HOURS = 3
FORECAST_HOURS = 1


# 2. FUNGSI REQUEST API
def fetch_api(url, params):
    response = requests.get(
        url,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    return response.json()


# 3. AMBIL DATA NO2 PER JAM
def fetch_no2():
    params = {
        "latitude": ",".join(map(str, LATITUDES)),
        "longitude": ",".join(map(str, LONGITUDES)),
        "hourly": "nitrogen_dioxide",
        "past_hours": PAST_HOURS,
        "forecast_hours": FORECAST_HOURS,
        "timezone": "Asia/Jakarta",
    }

    data = fetch_api(AIR_QUALITY_URL, params)

    # Respons banyak lokasi berupa list.
    if isinstance(data, dict):
        data = [data]

    rows = []

    for location_id, item in enumerate(data, start=1):
        hourly = item.get("hourly", {})

        times = hourly.get("time", [])
        values = hourly.get("nitrogen_dioxide", [])

        for time, value in zip(times, values):
            rows.append({
                "location_id": location_id,
                "time": time,
                "nitrogen_dioxide": value,
            })

    return pd.DataFrame(rows)


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
        "timezone": "Asia/Jakarta",
        "wind_speed_unit": "kmh",
    }

    data = fetch_api(WEATHER_URL, params)

    if isinstance(data, dict):
        data = [data]

    rows = []

    for location_id, item in enumerate(data, start=1):
        hourly = item.get("hourly", {})

        times = hourly.get("time", [])
        temperatures = hourly.get("temperature_2m", [])
        humidities = hourly.get("relative_humidity_2m", [])
        rains = hourly.get("rain", [])
        wind_speeds = hourly.get("wind_speed_10m", [])

        for i, time in enumerate(times):
            rows.append({
                "location_id": location_id,
                "time": time,
                "temperature_2m": temperatures[i],
                "relative_humidity_2m": humidities[i],
                "rain": rains[i],
                "wind_speed_10m": wind_speeds[i],
            })

    return pd.DataFrame(rows)


# 5. GABUNGKAN DATA
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
        how="inner"
    )

    df = df.sort_values(
        ["location_id", "time"]
    ).reset_index(drop=True)

    # Simpan hasil secara otomatis.
    ml_dir = Path(__file__).resolve().parents[1]

    output_dir = ml_dir / "data" / "api"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "hourly_api.csv"

    df.to_csv(output_file, index=False)

    print("\nPengambilan data selesai!")
    print(f"Jumlah baris: {len(df)}")
    print(f"Jumlah lokasi: {df['location_id'].nunique()}")
    print(f"File tersimpan: {output_file}")

    print("\nContoh data:")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as error:
        print(f"Gagal mengambil API: {error}")
    except (KeyError, IndexError, TypeError, ValueError) as error:
        print(f"Terjadi kesalahan saat memproses data: {error}")