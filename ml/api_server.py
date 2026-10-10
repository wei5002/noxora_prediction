from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import joblib
import pandas as pd
import requests
from fastapi import FastAPI, HTTPException

app = FastAPI()

ML_DIR = Path(__file__).resolve().parent
MODEL_PATH = ML_DIR / "models" / "svr" / "svr_lag123_no2_meteorologi_80_20.joblib"
TIMEZONE = "Asia/Jakarta"

AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

FEATURES = [
    "LAG1", "LAG2", "LAG3",
    "temperature_2m", "relative_humidity_2m", "rain", "wind_speed_10m",
]

# Koordinat SAMA dengan yang dipakai saat training / script prediksi
LOCATIONS = {
    1: {
        "name": "Jakarta Timur",
        "latitude": -6.221441,
        "longitude": 106.931435,
    },
    2: {
        "name": "Kepulauan Seribu",
        "latitude": -5.7996483,
        "longitude": 106.47254,
    },
    3: {
        "name": "Bekasi",
        "latitude": -6.0808434,
        "longitude": 107.05342,
    },
    4: {
        "name": "Bogor",
        "latitude": -6.5729346,
        "longitude": 106.47356,
    },
    5: {
        "name": "Sukabumi",
        "latitude": -6.6432333,
        "longitude": 106.78992,
    },
    6: {
        "name": "Tangerang",
        "latitude": -6.0808434,
        "longitude": 106.45242,
    },
    7: {
        "name": "Banten Utara",
        "latitude": -5.7293496,
        "longitude": 106.60848,
    },
    8: {
        "name": "Bekasi Timur",
        "latitude": -6.2917395,
        "longitude": 107.17155,
    },
    9: {
        "name": "Karawang",
        "latitude": -6.4323373,
        "longitude": 106.974014,
    },
    10: {
        "name": "Purwakarta",
        "latitude": -6.2917395,
        "longitude": 107.39749,
    },
}

# Model dimuat sekali saat server start
if not MODEL_PATH.exists():
    raise FileNotFoundError(f"Model tidak ditemukan: {MODEL_PATH}")
model = joblib.load(MODEL_PATH)


def fetch_hourly(url, hourly_vars, ids, extra=None):
    params = {
        "latitude": ",".join(str(LOCATIONS[i]["latitude"]) for i in ids),
        "longitude": ",".join(str(LOCATIONS[i]["longitude"]) for i in ids),
        "hourly": hourly_vars,
        "past_days": 1,
        "forecast_days": 1,
        "timezone": TIMEZONE,
    }
    if extra:
        params.update(extra)

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else [data]


def build_rows(ids):
    now = datetime.now(ZoneInfo(TIMEZONE))
    target = now.replace(minute=0, second=0, microsecond=0, tzinfo=None) + timedelta(hours=1)
    key = lambda h: (target - timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M")

    air = fetch_hourly(AIR_QUALITY_URL, "nitrogen_dioxide", ids)
    wx = fetch_hourly(
        WEATHER_URL,
        "temperature_2m,relative_humidity_2m,rain,wind_speed_10m",
        ids,
        {"wind_speed_unit": "kmh"},
    )

    rows = []
    for loc_id, a, w in zip(ids, air, wx):
        no2 = dict(zip(a["hourly"]["time"], a["hourly"]["nitrogen_dioxide"]))
        wh = w["hourly"]
        idx = wh["time"].index(key(1))  # cuaca 1 jam sebelum target (= jam sekarang)

        row = {
            "location_id": loc_id,
            "location_name": LOCATIONS[loc_id]["name"],
            "fetched_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "target_time": target.strftime("%Y-%m-%d %H:%M:%S"),
            "weather_time": (target - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "LAG1": no2.get(key(1)),
            "LAG2": no2.get(key(2)),
            "LAG3": no2.get(key(3)),
            "temperature_2m": wh["temperature_2m"][idx],
            "relative_humidity_2m": wh["relative_humidity_2m"][idx],
            "rain": wh["rain"][idx],
            "wind_speed_10m": wh["wind_speed_10m"][idx],
        }

        if any(row[f] is None for f in FEATURES):
            raise ValueError(f"Data realtime lokasi {loc_id} belum lengkap dari Open-Meteo.")
        rows.append(row)

    return rows


def add_prediction(rows):
    df = pd.DataFrame(rows)
    preds = model.predict(df[FEATURES])  # urutan fitur sama dengan training
    for row, p in zip(rows, preds):
        row["predicted_nitrogen_dioxide"] = float(p)
    return rows


def run(ids, predict):
    try:
        rows = build_rows(ids)
        return add_prediction(rows) if predict else rows
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Gagal mengambil data Open-Meteo: {e}")
    except (ValueError, KeyError, IndexError) as e:
        raise HTTPException(status_code=502, detail=f"Data realtime tidak lengkap: {e}")


# Satu lokasi: data realtime (+ prediksi jika predict=true)
@app.get("/realtime")
def realtime(location_id: int = 1, predict: bool = False):
    if location_id not in LOCATIONS:
        raise HTTPException(status_code=404, detail="Lokasi tidak ditemukan.")
    return run([location_id], predict)[0]


# Semua lokasi: untuk kartu kecil (Jakarta Timur, Bogor, dst.)
@app.get("/realtime-all")
def realtime_all():
    return run(list(LOCATIONS.keys()), predict=False)