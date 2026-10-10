import pandas as pd
import joblib

from pathlib import Path
from xgboost import XGBRegressor

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


# PATH
BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)

MODEL_DIR = (
    BASE_DIR
    / "models"
    / "xgboost"
)

PREDICTION_DIR = (
    BASE_DIR
    / "results"
    / "predictions"
)

EVALUATION_DIR = (
    BASE_DIR
    / "results"
    / "evaluation"
)

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)

PREDICTION_DIR.mkdir(
    parents=True,
    exist_ok=True
)

EVALUATION_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# DATASET
DATASETS = {
    "no2": {
        "path": (
            PROCESSED_DIR
            / "dataset-no2.csv"
        ),
        "features": [
            "LAG1"
        ],
    },
    "no2_meteorologi": {
        "path": (
            PROCESSED_DIR
            / "dataset-no2-meteorologi.csv"
        ),
        "features": [
            "LAG1",
            "temperature_2m",
            "relative_humidity_2m",
            "rain",
            "wind_speed_10m",
        ],
    },
}

TARGET = "nitrogen_dioxide"


# SPLIT DATA
SPLIT_RATIOS = {
    "70_30": 0.30,
    "80_20": 0.20,
}


# LOAD DATASET
def load_dataset(
    dataset_name,
    dataset_info
):
    file_path = dataset_info["path"]

    if not file_path.exists():
        raise FileNotFoundError(
            f"Dataset tidak ditemukan: {file_path}"
        )

    df = pd.read_csv(
        file_path
    )

    required_columns = [
        "location_id",
        "time",
        TARGET,
        *dataset_info["features"],
    ]

    missing_columns = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Kolom tidak ditemukan pada "
            f"{dataset_name}: "
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
        [
            float("inf"),
            float("-inf")
        ],
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
        [
            "time",
            "location_id"
        ]
    ).reset_index(
        drop=True
    )

    print(
        f"\nDataset: {dataset_name}"
    )

    print(
        f"Jumlah data: {len(df):,}"
    )

    return df


# SPLIT DATA BERDASARKAN WAKTU
def split_by_time(
    df,
    test_size
):
    timestamps = sorted(
        df["time"].unique()
    )

    if len(timestamps) < 2:
        raise ValueError(
            "Jumlah timestamp tidak cukup "
            "untuk split data."
        )

    cutoff_index = int(
        len(timestamps)
        * (1 - test_size)
    )

    cutoff_index = max(
        1,
        min(
            cutoff_index,
            len(timestamps) - 1
        )
    )

    cutoff_time = timestamps[
        cutoff_index
    ]

    train_df = df[
        df["time"] < cutoff_time
    ].copy()

    test_df = df[
        df["time"] >= cutoff_time
    ].copy()

    return (
        train_df,
        test_df
    )


# TRAINING XGBOOST
def train_experiment(
    dataset_name,
    dataset_info,
    split_name,
    test_size
):
    df = load_dataset(
        dataset_name,
        dataset_info
    )

    train_df, test_df = (
        split_by_time(
            df,
            test_size
        )
    )

    features = (
        dataset_info["features"]
    )

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
        f"\nTraining XGBoost | "
        f"LAG1 | "
        f"{dataset_name} | "
        f"{split_name}"
    )

    print(
        f"Data training: "
        f"{len(train_df):,}"
    )

    print(
        f"Data testing: "
        f"{len(test_df):,}"
    )


    # CREATE MODEL
    model = XGBRegressor(
        max_depth=2,
        learning_rate=1,
        n_estimators=100,
        random_state=42,
        n_jobs=-1,
        objective="reg:squarederror"
    )


    # TRAIN MODEL
    print("Mulai training...")

    model.fit(
        X_train,
        y_train
    )

    print(
        "Training selesai."
    )


    # MODEL NAME
    experiment_name = (
        f"xgboost_lag1_"
        f"{dataset_name}_"
        f"{split_name}"
    )


    # SAVE MODEL
    model_path = (
        MODEL_DIR
        / f"{experiment_name}.joblib"
    )

    joblib.dump(
        model,
        model_path
    )

    print(
        f"Model disimpan: "
        f"{model_path}"
    )


    # PREDICTION
    print(
        "Melakukan prediksi..."
    )

    y_pred = model.predict(
        X_test
    )


    # EVALUATION
    mae = mean_absolute_error(
        y_test,
        y_pred
    )

    mse = mean_squared_error(
        y_test,
        y_pred
    )

    rmse = mse ** 0.5

    r2 = r2_score(
        y_test,
        y_pred
    )

    print(
        f"MAE: {mae:.6f}"
    )

    print(
        f"MSE: {mse:.6f}"
    )

    print(
        f"RMSE: {rmse:.6f}"
    )

    print(
        f"R2: {r2:.6f}"
    )


    # SAVE PREDICTIONS
    predictions = test_df[
        [
            "location_id",
            "time"
        ]
    ].copy()

    predictions[
        "actual"
    ] = y_test.to_numpy()

    predictions[
        "predicted"
    ] = y_pred

    predictions[
        "algorithm"
    ] = "XGBoost"

    predictions[
        "lag_configuration"
    ] = "LAG1"

    predictions[
        "dataset"
    ] = dataset_name

    predictions[
        "split"
    ] = split_name

    prediction_path = (
        PREDICTION_DIR
        / f"{experiment_name}_predictions.csv"
    )

    predictions.to_csv(
        prediction_path,
        index=False
    )

    print(
        f"Prediksi disimpan: "
        f"{prediction_path}"
    )


    # SAVE EVALUATION
    return {
        "algorithm": "XGBoost",
        "lag_configuration": "LAG1",
        "dataset": dataset_name,
        "split": split_name,
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "MAE": mae,
        "MSE": mse,
        "RMSE": rmse,
        "R2": r2
    }


# MAIN
def main():
    results = []

    for dataset_name, dataset_info in (
        DATASETS.items()
    ):

        for split_name, test_size in (
            SPLIT_RATIOS.items()
        ):

            result = train_experiment(
                dataset_name=dataset_name,
                dataset_info=dataset_info,
                split_name=split_name,
                test_size=test_size
            )

            results.append(
                result
            )


    # SAVE EVALUATION
    results_df = pd.DataFrame(
        results
    )

    evaluation_path = (
        EVALUATION_DIR
        / "xgboost_lag1.csv"
    )

    results_df.to_csv(
        evaluation_path,
        index=False
    )


    # DISPLAY RESULTS
    print(
        "\nHasil XGBoost LAG1:"
    )

    print(
        results_df.to_string(
            index=False
        )
    )

    print(
        f"\nEvaluasi disimpan: "
        f"{evaluation_path}"
    )


if __name__ == "__main__":
    main()