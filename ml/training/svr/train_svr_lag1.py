import time
import threading
import itertools
import sys

import joblib
import numpy as np
import pandas as pd

from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR


# PATH

BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = (
    BASE_DIR / "data" / "processed"
)

MODEL_DIR = (
    BASE_DIR / "models" / "svr"
)

PREDICTION_DIR = (
    BASE_DIR / "results" / "predictions"
)

EVALUATION_DIR = (
    BASE_DIR / "results" / "evaluation"
)

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

PREDICTION_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

EVALUATION_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# KONFIGURASI TRAINING

DATASETS = {
    "no2": {
        "file": "dataset-no2.csv",
        "features": [
            "LAG1",
        ],
    },
    "no2_meteorologi": {
        "file": "dataset-no2-meteorologi.csv",
        "features": [
            "LAG1",
            "temperature_2m",
            "relative_humidity_2m",
            "rain",
            "wind_speed_10m",
        ],
    },
}

SPLITS = {
    "70_30": 0.70,
    "80_20": 0.80,
}

TARGET = "nitrogen_dioxide"

LAG_CONFIGURATION = "lag1"

MODEL_PARAMS = {
    "kernel": "rbf",
    "C": 100,
    "gamma": 0.1,
    "epsilon": 0.1,
}


# ANIMASI PROSES

def show_progress(stop_event, message):

    spinner = itertools.cycle(
        ["|", "/", "-", "\\"]
    )

    while not stop_event.is_set():
        sys.stdout.write(
            f"\r{message} {next(spinner)}"
        )
        sys.stdout.flush()
        time.sleep(0.2)

    sys.stdout.write(
        f"\r{message} selesai.       \n"
    )
    sys.stdout.flush()


# MEMUAT DATASET

def load_dataset(dataset_name, config):

    file_path = (
        PROCESSED_DIR / config["file"]
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Dataset tidak ditemukan: {file_path}"
        )

    print(
        f"\nMemuat dataset: {file_path.name}"
    )

    df = pd.read_csv(
        file_path
    )

    required_columns = [
        "time",
        TARGET,
        *config["features"],
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Kolom tidak ditemukan pada "
            f"{file_path.name}: {missing_columns}"
        )

    # Mengubah waktu menjadi datetime.

    df["time"] = pd.to_datetime(
        df["time"],
        errors="coerce",
    )

    # Memastikan target dan fitur numerik.

    numeric_columns = [
        TARGET,
        *config["features"],
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    # Menghapus nilai kosong dan tak hingga.

    df = df.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    df = df.dropna(
        subset=[
            "time",
            *numeric_columns,
        ]
    )

    # Mengurutkan berdasarkan waktu.

    df = df.sort_values(
        "time"
    ).reset_index(
        drop=True
    )

    if df.empty:
        raise ValueError(
            f"Dataset {dataset_name} tidak memiliki "
            f"data valid setelah preprocessing."
        )

    print(
        f"Jumlah data valid: {len(df):,}"
    )

    print(
        f"Jumlah fitur: {len(config['features'])}"
    )

    print(
        f"Fitur: {config['features']}"
    )

    return df


# MEMBAGI DATA BERDASARKAN WAKTU

def split_by_time(df, train_ratio):

    # Memisahkan berdasarkan timestamp unik,
    # bukan mengacak baris data.

    unique_times = np.sort(
        df["time"].unique()
    )

    if len(unique_times) < 2:
        raise ValueError(
            "Jumlah timestamp tidak cukup "
            "untuk pembagian training dan testing."
        )

    cutoff_index = int(
        len(unique_times) * train_ratio
    )

    cutoff_index = min(
        max(cutoff_index, 1),
        len(unique_times) - 1,
    )

    cutoff_time = unique_times[
        cutoff_index
    ]

    train_df = df[
        df["time"] < cutoff_time
    ].copy()

    test_df = df[
        df["time"] >= cutoff_time
    ].copy()

    if train_df.empty or test_df.empty:
        raise ValueError(
            "Data training atau testing kosong."
        )

    return (
        train_df,
        test_df,
        pd.Timestamp(cutoff_time),
    )


# MEMBUAT MODEL SVR

def create_model():

    model = Pipeline(
        steps=[
            (
                "scaler",
                StandardScaler(),
            ),
            (
                "svr",
                SVR(
                    **MODEL_PARAMS
                ),
            ),
        ]
    )

    return model


# TRAINING DAN PREDIKSI

def train_scenario(
    dataset_name,
    config,
    split_name,
    train_ratio,
):

    print(
        "\n" + "=" * 80
    )

    print(
        f"ALGORITMA       : SVR"
    )

    print(
        f"DATASET         : {dataset_name}"
    )

    print(
        f"KONFIGURASI LAG : {LAG_CONFIGURATION}"
    )

    print(
        f"SPLIT           : {split_name}"
    )

    print(
        "=" * 80
    )

    df = load_dataset(
        dataset_name,
        config,
    )

    train_df, test_df, cutoff_time = (
        split_by_time(
            df,
            train_ratio,
        )
    )

    features = config["features"]

    X_train = train_df[
        features
    ]

    y_train = train_df[
        TARGET
    ]

    X_test = test_df[
        features
    ]

    y_test = test_df[
        TARGET
    ]

    print(
        f"\nBatas waktu training : {cutoff_time}"
    )

    print(
        f"Data training        : {len(X_train):,}"
    )

    print(
        f"Data testing         : {len(X_test):,}"
    )

    print(
        f"Rasio training       : {train_ratio:.0%}"
    )

    print(
        f"Rasio testing        : {1 - train_ratio:.0%}"
    )

    # Membuat model.

    model = create_model()

    # Menjalankan animasi selama proses training.

    stop_event = threading.Event()

    progress_thread = threading.Thread(
        target=show_progress,
        args=(
            stop_event,
            (
                f"Training SVR {dataset_name} "
                f"{split_name}"
            ),
        ),
        daemon=True,
    )

    progress_thread.start()

    start_time = time.time()

    try:
        model.fit(
            X_train,
            y_train,
        )
    finally:
        stop_event.set()
        progress_thread.join()

    training_duration = (
        time.time() - start_time
    )

    print(
        f"Waktu training: "
        f"{training_duration / 60:.2f} menit"
    )

    # Membuat prediksi pada data testing.

    print(
        "Menghasilkan prediksi testing..."
    )

    predicted = model.predict(
        X_test
    )

    # MENYIMPAN MODEL

    model_filename = (
        f"svr_{LAG_CONFIGURATION}_"
        f"{dataset_name}_{split_name}.joblib"
    )

    model_path = (
        MODEL_DIR / model_filename
    )

    joblib.dump(
        model,
        model_path,
    )

    print(
        f"Model tersimpan: {model_path}"
    )

    # MENYIMPAN HASIL PREDIKSI

    prediction_df = pd.DataFrame(
        {
            "actual": y_test.to_numpy(),
            "predicted": predicted,
        }
    )

    prediction_df.insert(
        0,
        "time",
        test_df["time"].to_numpy(),
    )

    if "location_id" in test_df.columns:
        prediction_df.insert(
            0,
            "location_id",
            test_df["location_id"].to_numpy(),
        )

    prediction_df["algorithm"] = "SVR"

    prediction_df["lag_configuration"] = (
        LAG_CONFIGURATION
    )

    prediction_df["dataset"] = (
        dataset_name
    )

    prediction_df["split"] = (
        split_name
    )

    prediction_filename = (
        f"svr_{LAG_CONFIGURATION}_"
        f"{dataset_name}_{split_name}_"
        f"predictions.csv"
    )

    prediction_path = (
        PREDICTION_DIR
        / prediction_filename
    )

    prediction_df.to_csv(
        prediction_path,
        index=False,
    )

    print(
        f"Prediksi tersimpan: {prediction_path}"
    )

    print(
        f"Jumlah prediksi: {len(prediction_df):,}"
    )

    print(
        f"Training selesai: "
        f"{dataset_name} | {split_name}"
    )

    return {
        "algorithm": "SVR",
        "lag_configuration": LAG_CONFIGURATION,
        "dataset": dataset_name,
        "split": split_name,
        "train_data": len(train_df),
        "test_data": len(test_df),
        "training_minutes": (
            training_duration / 60
        ),
        "model_file": model_filename,
        "prediction_file": prediction_filename,
    }


# MENJALANKAN SELURUH SKENARIO LAG1

def main():

    print(
        "\n" + "=" * 80
    )

    print(
        "TRAINING SVR - LAG1"
    )

    print(
        "Total skenario: 4"
    )

    print(
        "=" * 80
    )

    scenario_results = []

    total_scenarios = (
        len(DATASETS) * len(SPLITS)
    )

    current_scenario = 0

    for dataset_name, config in DATASETS.items():

        for split_name, train_ratio in SPLITS.items():

            current_scenario += 1

            print(
                f"\nSkenario "
                f"{current_scenario}/{total_scenarios}"
            )

            result = train_scenario(
                dataset_name=dataset_name,
                config=config,
                split_name=split_name,
                train_ratio=train_ratio,
            )

            scenario_results.append(
                result
            )

    # MENYIMPAN RINGKASAN TRAINING

    summary_df = pd.DataFrame(
        scenario_results
    )

    summary_path = (
        EVALUATION_DIR
        / "training_summary_svr_lag1.csv"
    )

    summary_df.to_csv(
        summary_path,
        index=False,
    )

    print(
        "\n" + "=" * 80
    )

    print(
        "SELURUH TRAINING SVR LAG1 SELESAI"
    )

    print(
        "=" * 80
    )

    print(
        summary_df.to_string(
            index=False
        )
    )

    print(
        f"\nRingkasan training tersimpan: "
        f"{summary_path}"
    )


# MAIN

if __name__ == "__main__":
    main()