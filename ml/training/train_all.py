import pandas as pd
import joblib

from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)
from xgboost import XGBRegressor


# 1. KONFIGURASI PATH

# Lokasi file: ml/training/train_all.py
BASE_DIR = Path(__file__).resolve().parents[1]

PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODEL_DIR = BASE_DIR / "models"
RESULT_DIR = BASE_DIR / "results"

DATASETS = {
    "no2": PROCESSED_DIR / "dataset-no2.csv",
    "no2_meteorologi": (
        PROCESSED_DIR / "dataset-no2-meteorologi.csv"
    )
}

TARGET = "nitrogen_dioxide"

FEATURES = {
    "no2": [
        "LAG1",
        "LAG2",
        "LAG3"
    ],
    "no2_meteorologi": [
        "LAG1",
        "LAG2",
        "LAG3",
        "temperature_2m",
        "relative_humidity_2m",
        "rain",
        "wind_speed_10m"
    ]
}

SPLIT_RATIOS = {
    "70_30": 0.30,
    "80_20": 0.20
}

RANDOM_STATE = 42


# 2. MEMBACA DATASET

def load_dataset(dataset_name, file_path):
    print(f"\nMembaca dataset: {dataset_name}")

    if not file_path.exists():
        raise FileNotFoundError(
            f"Dataset tidak ditemukan: {file_path}"
        )

    df = pd.read_csv(file_path)

    required_columns = [
        "location_id",
        "time",
        TARGET,
        *FEATURES[dataset_name]
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

    df["location_id"] = df["location_id"].astype(str)

    # Pastikan seluruh fitur dan target berupa angka
    numeric_columns = [
        TARGET,
        *FEATURES[dataset_name]
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # Ubah nilai tak hingga menjadi missing value
    df = df.replace(
        [float("inf"), float("-inf")],
        float("nan")
    )

    # Hapus baris yang tidak valid
    df = df.dropna(
        subset=[
            "time",
            TARGET,
            *FEATURES[dataset_name]
        ]
    ).copy()

    # Urutkan berdasarkan waktu dan lokasi
    df = df.sort_values(
        ["time", "location_id"]
    ).reset_index(drop=True)

    print(f"Jumlah baris : {len(df):,}")
    print(f"Jumlah lokasi: {df['location_id'].nunique()}")

    return df


# 3. PEMBAGIAN DATA BERDASARKAN WAKTU

def split_by_time(df, test_size):
    timestamps = (
        df["time"]
        .drop_duplicates()
        .sort_values()
        .to_numpy()
    )

    if len(timestamps) < 2:
        raise ValueError(
            "Jumlah timestamp tidak cukup untuk train-test split."
        )

    split_index = int(
        len(timestamps) * (1 - test_size)
    )

    split_index = max(
        1,
        min(split_index, len(timestamps) - 1)
    )

    cutoff_time = timestamps[split_index]

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

    print(f"Batas waktu train: {train_df['time'].max()}")
    print(f"Batas waktu test : {test_df['time'].min()}")
    print(f"Jumlah data train: {len(train_df):,}")
    print(f"Jumlah data test : {len(test_df):,}")

    return train_df, test_df


# 4. MEMBUAT MODEL

def create_model(model_name):
    if model_name == "xgboost":
        return XGBRegressor(
            max_depth=2,
            learning_rate=1,
            n_estimators=100,
            objective="reg:squarederror",
            random_state=RANDOM_STATE,
            n_jobs=-1
        )

    if model_name == "svr":
        return Pipeline([
            ("scaler", StandardScaler()),
            ("svr", SVR(
                kernel="rbf",
                C=100,
                epsilon=0.1,
                gamma=0.1
            ))
        ])

    raise ValueError(
        f"Model tidak dikenal: {model_name}"
    )


# 5. EVALUASI MODEL

def evaluate_model(y_true, y_pred):
    mse = mean_squared_error(
        y_true,
        y_pred
    )

    return {
        "MAE": mean_absolute_error(
            y_true,
            y_pred
        ),
        "MSE": mse,
        "RMSE": mse ** 0.5,
        "R2": r2_score(
            y_true,
            y_pred
        )
    }


# 6. TRAINING DAN EVALUASI

def train_experiment(
    dataset_name,
    df,
    model_name,
    split_name,
    test_size
):
    print("\n" + "=" * 65)
    print(
        f"DATASET: {dataset_name} | "
        f"MODEL: {model_name.upper()} | "
        f"SPLIT: {split_name}"
    )
    print("=" * 65)

    # Bagi data secara kronologis
    train_df, test_df = split_by_time(
        df,
        test_size
    )

    feature_columns = FEATURES[dataset_name]

    # Gunakan seluruh data training dan testing
    X_train = train_df[feature_columns]
    y_train = train_df[TARGET]

    X_test = test_df[feature_columns]
    y_test = test_df[TARGET]

    model = create_model(model_name)

    print(
        f"\nJumlah training yang digunakan: "
        f"{len(X_train):,}"
    )
    print(
        f"Jumlah testing yang digunakan : "
        f"{len(X_test):,}"
    )

    print("\nMelatih model...")
    model.fit(
        X_train,
        y_train
    )

    print("Melakukan prediksi...")
    y_pred = model.predict(X_test)

    # Evaluasi
    metrics = evaluate_model(
        y_test,
        y_pred
    )

    print("\nHasil evaluasi:")
    for metric_name, value in metrics.items():
        print(
            f"{metric_name}: {value:.6f}"
        )

    # Simpan model

    model_subdir = MODEL_DIR / model_name
    model_subdir.mkdir(
        parents=True,
        exist_ok=True
    )

    model_filename = (
        f"{model_name}_{dataset_name}_{split_name}.joblib"
    )

    model_path = model_subdir / model_filename

    joblib.dump(
        model,
        model_path
    )

    print(f"\nModel disimpan: {model_path}")

    # Simpan hasil prediksi
    prediction_dir = RESULT_DIR / "predictions"
    prediction_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    prediction_df = test_df[
        ["location_id", "time", TARGET]
    ].copy()

    prediction_df["predicted_no2"] = y_pred

    prediction_path = prediction_dir / (
        f"predictions_{model_name}_"
        f"{dataset_name}_{split_name}.csv"
    )

    prediction_df.to_csv(
        prediction_path,
        index=False
    )

    print(
        f"Hasil prediksi disimpan: {prediction_path}"
    )

    # Catat hasil eksperimen

    result = {
        "dataset": dataset_name,
        "model": model_name,
        "split": split_name,

        "train_rows": len(train_df),
        "test_rows": len(test_df),

        "train_start": train_df["time"].min(),
        "train_end": train_df["time"].max(),

        "test_start": test_df["time"].min(),
        "test_end": test_df["time"].max(),

        **metrics,

        "model_path": str(model_path),
        "prediction_path": str(prediction_path)
    }

    return result


# 7. MENJALANKAN SELURUH EKSPERIMEN
def main():
    all_results = []

    for dataset_name, file_path in DATASETS.items():

        df = load_dataset(
            dataset_name,
            file_path
        )

        for split_name, test_size in SPLIT_RATIOS.items():

            for model_name in [
                "xgboost",
                "svr"
            ]:

                result = train_experiment(
                    dataset_name=dataset_name,
                    df=df,
                    model_name=model_name,
                    split_name=split_name,
                    test_size=test_size
                )

                all_results.append(result)

    # Simpan seluruh hasil evaluasi

    RESULT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    results_df = pd.DataFrame(
        all_results
    )

    results_path = (
        RESULT_DIR / "evaluation_results.csv"
    )

    results_df.to_csv(
        results_path,
        index=False
    )

    print("\n" + "=" * 65)
    print("SELURUH EKSPERIMEN SELESAI")
    print("=" * 65)

    print("\nRingkasan hasil evaluasi:")

    print(
        results_df[
            [
                "dataset",
                "model",
                "split",
                "train_rows",
                "test_rows",
                "MAE",
                "MSE",
                "RMSE",
                "R2"
            ]
        ].to_string(index=False)
    )

    print(
        f"\nHasil evaluasi disimpan di:\n"
        f"{results_path}"
    )


if __name__ == "__main__":
    main()