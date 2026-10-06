
import pandas as pd
import joblib

from pathlib import Path
from xgboost import XGBRegressor


# PATH
BASE_DIR = Path(__file__).resolve().parents[1]

PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODEL_DIR = BASE_DIR / "models" / "xgboost"
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

# Proporsi data testing
SPLIT_RATIOS = {
    "70_30": 0.30,
    "80_20": 0.20,
}


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
        errors="coerce"
    )

    numeric_columns = [
        TARGET,
        *dataset_info["features"],
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df = df.replace(
        [float("inf"), float("-inf")],
        float("nan")
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
    timestamps = sorted(df["time"].unique())

    if len(timestamps) < 2:
        raise ValueError(
            "Jumlah timestamp tidak cukup untuk split data."
        )

    cutoff_index = int(
        len(timestamps) * (1 - test_size)
    )

    cutoff_index = max(
        1,
        min(cutoff_index, len(timestamps) - 1)
    )

    cutoff_time = timestamps[cutoff_index]

    train_df = df[
        df["time"] < cutoff_time
    ].copy()

    test_df = df[
        df["time"] >= cutoff_time
    ].copy()

    return train_df, test_df


# TRAINING XGBOOST
def train_experiment(
    dataset_name,
    dataset_info,
    split_name,
    test_size,
):
    df = load_dataset(
        dataset_name,
        dataset_info
    )

    train_df, test_df = split_by_time(
        df,
        test_size
    )

    features = dataset_info["features"]

    X_train = train_df[features]
    y_train = train_df[TARGET]

    X_test = test_df[features]
    y_test = test_df[TARGET]

    print("\n" + "=" * 60)
    print("TRAINING XGBOOST")
    print(f"Dataset       : {dataset_name}")
    print(f"Split         : {split_name}")
    print(f"Data training : {len(train_df):,}")
    print(f"Data testing  : {len(test_df):,}")
    print("=" * 60)

    model = XGBRegressor(
        max_depth=2,
        learning_rate=1,
        n_estimators=100,
        random_state=42,
        n_jobs=-1,
        objective="reg:squarederror",
    )

    model.fit(
        X_train,
        y_train
    )

    # Nama eksperimen
    experiment_name = (
        f"xgboost_{dataset_name}_{split_name}"
    )

    # Simpan model
    model_path = (
        MODEL_DIR / f"{experiment_name}.joblib"
    )

    joblib.dump(
        model,
        model_path
    )

    # Prediksi data testing
    y_pred = model.predict(X_test)

    # Simpan hasil prediksi untuk evaluasi
    predictions = test_df[
        ["location_id", "time"]
    ].copy()

    predictions["actual"] = y_test.to_numpy()
    predictions["predicted"] = y_pred
    predictions["algorithm"] = "XGBoost"
    predictions["dataset"] = dataset_name
    predictions["split"] = split_name

    prediction_path = (
        PREDICTION_DIR
        / f"{experiment_name}_predictions.csv"
    )

    predictions.to_csv(
        prediction_path,
        index=False
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
    print("SELURUH TRAINING XGBOOST SELESAI")
    print("=" * 60)

    for result in results:
        print(
            f"{result['experiment']} | "
            f"Train: {result['train_rows']:,} | "
            f"Test: {result['test_rows']:,}"
        )


if __name__ == "__main__":
    main()