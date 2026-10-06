import pandas as pd
import joblib
import sys
import threading
import itertools
import time

from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR


# PATH
BASE_DIR = Path(__file__).resolve().parents[1]

PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODEL_DIR = BASE_DIR / "models" / "svr"
PREDICTION_DIR = BASE_DIR / "results" / "predictions"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
PREDICTION_DIR.mkdir(parents=True, exist_ok=True)


# DATASET
DATASETS = {
    "no2": {
        "path": PROCESSED_DIR / "dataset-no2.csv",
        "features": [
            "LAG1",
            "LAG2",
            "LAG3",
        ],
    },
    "no2_meteorologi": {
        "path": PROCESSED_DIR / "dataset-no2-meteorologi.csv",
        "features": [
            "LAG1",
            "LAG2",
            "LAG3",
            "temperature_2m",
            "relative_humidity_2m",
            "rain",
            "wind_speed_10m",
        ],
    },
}

TARGET = "nitrogen_dioxide"

SPLIT_RATIOS = {
    "70_30": 0.30,
    "80_20": 0.20,
}


# PROGRESS BAR
def show_progress(message, percent, spinner=""):
    bar_length = 30

    filled_length = int(
        bar_length * percent / 100
    )

    bar = (
        "█" * filled_length
        + "░" * (bar_length - filled_length)
    )

    sys.stdout.write(
        f"\r{message} [{bar}] {percent:3d}% {spinner}   "
    )
    sys.stdout.flush()

    if percent >= 100:
        sys.stdout.write("\n")
        sys.stdout.flush()


# LOADING ANIMATION
def start_loading(message, percent):
    stop_event = threading.Event()

    def animate():
        spinner = itertools.cycle(
            ["|", "/", "-", "\\"]
        )

        while not stop_event.is_set():
            show_progress(
                message,
                percent,
                next(spinner),
            )

            # Kecepatan animasi
            time.sleep(0.1)

    thread = threading.Thread(
        target=animate,
        daemon=True,
    )

    thread.start()

    return stop_event, thread


def stop_loading(stop_event, thread):
    stop_event.set()
    thread.join()


# LOAD DATASET
def load_dataset(dataset_name, dataset_info):
    file_path = dataset_info["path"]

    if not file_path.exists():
        raise FileNotFoundError(
            f"Dataset tidak ditemukan: {file_path}"
        )

    df = pd.read_csv(file_path)

    required_columns = [
        "location_id",
        "time",
        TARGET,
        *dataset_info["features"],
    ]

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Kolom tidak ditemukan pada {dataset_name}: "
            f"{missing_columns}"
        )

    df["time"] = pd.to_datetime(
        df["time"],
        errors="coerce",
    )

    numeric_columns = [
        TARGET,
        *dataset_info["features"],
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    df = df.replace(
        [float("inf"), float("-inf")],
        float("nan"),
    )

    df = df.dropna(
        subset=[
            "location_id",
            "time",
            TARGET,
            *dataset_info["features"],
        ]
    )

    df = df.sort_values(
        ["time", "location_id"]
    ).reset_index(drop=True)

    print(f"\nDataset: {dataset_name}")
    print(f"Jumlah data: {len(df):,}")

    return df


# SPLIT DATA BERDASARKAN WAKTU
def split_by_time(df, test_size):
    timestamps = sorted(
        df["time"].unique()
    )

    if len(timestamps) < 2:
        raise ValueError(
            "Jumlah timestamp tidak cukup untuk split data."
        )

    cutoff_index = int(
        len(timestamps) * (1 - test_size)
    )

    cutoff_index = max(
        1,
        min(cutoff_index, len(timestamps) - 1),
    )

    cutoff_time = timestamps[cutoff_index]

    train_df = df[
        df["time"] < cutoff_time
    ].copy()

    test_df = df[
        df["time"] >= cutoff_time
    ].copy()

    return train_df, test_df


# TRAINING SVR
def train_experiment(
    dataset_name,
    dataset_info,
    split_name,
    test_size,
):
    df = load_dataset(
        dataset_name,
        dataset_info,
    )

    train_df, test_df = split_by_time(
        df,
        test_size,
    )

    features = dataset_info["features"]

    X_train = train_df[features]
    y_train = train_df[TARGET]

    X_test = test_df[features]
    y_test = test_df[TARGET]

    print("\n" + "=" * 60)
    print("TRAINING SVR")
    print(f"Dataset       : {dataset_name}")
    print(f"Split         : {split_name}")
    print(f"Data training : {len(train_df):,}")
    print(f"Data testing  : {len(test_df):,}")
    print("=" * 60)

    progress_message = (
        f"SVR [{dataset_name} - {split_name}]"
    )

    # Inisialisasi model
    model = Pipeline([
        ("scaler", StandardScaler()),
        (
            "svr",
            SVR(
                kernel="rbf",
                C=100,
                epsilon=0.1,
                gamma=0.1,
            ),
        ),
    ])

    # Persiapan training
    show_progress(
        progress_message,
        0,
    )

    # Training dimulai dengan animasi
    stop_event, loading_thread = start_loading(
        progress_message,
        10,
    )

    try:
        model.fit(
            X_train,
            y_train,
        )
    finally:
        # Hentikan animasi setelah fit selesai
        stop_loading(
            stop_event,
            loading_thread,
        )

    # Training selesai
    show_progress(
        progress_message,
        80,
    )

    # Nama eksperimen
    experiment_name = (
        f"svr_{dataset_name}_{split_name}"
    )

    # Simpan model
    model_path = (
        MODEL_DIR / f"{experiment_name}.joblib"
    )

    joblib.dump(
        model,
        model_path,
    )

    show_progress(
        progress_message,
        85,
    )

    # Prediksi data testing
    y_pred = model.predict(
        X_test,
    )

    show_progress(
        progress_message,
        95,
    )

    # Simpan hasil prediksi untuk evaluasi
    predictions = test_df[
        ["location_id", "time"]
    ].copy()

    predictions["actual"] = y_test.to_numpy()
    predictions["predicted"] = y_pred
    predictions["algorithm"] = "SVR"
    predictions["dataset"] = dataset_name
    predictions["split"] = split_name

    prediction_path = (
        PREDICTION_DIR
        / f"{experiment_name}_predictions.csv"
    )

    predictions.to_csv(
        prediction_path,
        index=False,
    )

    show_progress(
        progress_message,
        100,
    )

    print(f"Model disimpan     : {model_path}")
    print(f"Prediksi disimpan  : {prediction_path}")
    print("Training selesai.")

    return {
        "experiment": experiment_name,
        "train_rows": len(train_df),
        "test_rows": len(test_df),
    }


# MAIN
def main():
    results = []

    for dataset_name, dataset_info in DATASETS.items():
        for split_name, test_size in SPLIT_RATIOS.items():
            result = train_experiment(
                dataset_name=dataset_name,
                dataset_info=dataset_info,
                split_name=split_name,
                test_size=test_size,
            )

            results.append(result)

    print("\n" + "=" * 60)
    print("SELURUH TRAINING SVR SELESAI")
    print("=" * 60)

    for result in results:
        print(
            f"{result['experiment']} | "
            f"Train: {result['train_rows']:,} | "
            f"Test: {result['test_rows']:,}"
        )


if __name__ == "__main__":
    main()