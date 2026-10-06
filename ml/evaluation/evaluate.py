import pandas as pd
import numpy as np

from pathlib import Path
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

# PATH

BASE_DIR = Path(__file__).resolve().parents[1]
PREDICTION_DIR = (
    BASE_DIR / "results" / "predictions"
)
EVALUATION_DIR = (
    BASE_DIR / "results" / "evaluation"
)
EVALUATION_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

# KOLOM YANG DIBUTUHKAN
REQUIRED_COLUMNS = [
    "actual",
    "predicted",
    "algorithm",
    "dataset",
    "split",
]

# LOAD HASIL PREDIKSI
def load_predictions():

    if not PREDICTION_DIR.exists():
        raise FileNotFoundError(
            f"Folder prediksi tidak ditemukan: "
            f"{PREDICTION_DIR}"
        )
    # Membaca file prediksi eksperimen.
    # File realtime tidak digunakan untuk evaluasi eksperimen.
    prediction_files = sorted(
        file_path
        for file_path in PREDICTION_DIR.glob(
            "*_predictions.csv"
        )
        if file_path.name != "svr_realtime_predictions.csv"
    )

    if not prediction_files:
        raise FileNotFoundError(
            "Tidak ada file prediksi eksperimen. "
            "Jalankan training terlebih dahulu."
        )

    dataframes = []

    for file_path in prediction_files:
        df = pd.read_csv(file_path)
        # Periksa kolom yang dibutuhkan
        missing_columns = [
            col
            for col in REQUIRED_COLUMNS
            if col not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Kolom tidak ditemukan pada "
                f"{file_path.name}: {missing_columns}"
            )

        # Pastikan nilai aktual dan prediksi numerik
        df["actual"] = pd.to_numeric(
            df["actual"],
            errors="coerce",
        )

        df["predicted"] = pd.to_numeric(
            df["predicted"],
            errors="coerce",
        )

        # Hapus nilai kosong dan tak hingga
        df = df.replace(
            [np.inf, -np.inf],
            np.nan,
        )

        df = df.dropna(
            subset=REQUIRED_COLUMNS
        )

        if not df.empty:
            dataframes.append(df)

    if not dataframes:
        raise ValueError(
            "Tidak ada data prediksi valid untuk dievaluasi."
        )

    return pd.concat(
        dataframes,
        ignore_index=True,
    )


# HITUNG METRIK EVALUASI
def evaluate_model(actual, predicted):
    # Mean Absolute Error
    mae = mean_absolute_error(
        actual,
        predicted,
    )
    # Mean Squared Error
    mse = mean_squared_error(
        actual,
        predicted,
    )
    # Root Mean Squared Error
    rmse = np.sqrt(mse)
    # Coefficient of Determination
    if len(actual) >= 2:
        r2 = r2_score(
            actual,
            predicted,
        )
    else:
        r2 = np.nan

    return {
        "MAE": mae,
        "MSE": mse,
        "RMSE": rmse,
        "R2": r2,
    }

# URUTAN HASIL EVALUASI
def sort_evaluation_results(results_df):
    algorithm_order = {
        "XGBoost": 0,
        "SVR": 1,
    }
    dataset_order = {
        "no2": 0,
        "no2_meteorologi": 1,
    }
    split_order = {
        "70_30": 0,
        "80_20": 1,
    }
    results_df = results_df.copy()
    results_df["_algorithm_order"] = (
        results_df["algorithm"].map(
            algorithm_order
        )
    )
    results_df["_dataset_order"] = (
        results_df["dataset"].map(
            dataset_order
        )
    )
    results_df["_split_order"] = (
        results_df["split"].map(
            split_order
        )
    )
    results_df = (
        results_df.sort_values(
            [
                "_algorithm_order",
                "_dataset_order",
                "_split_order",
            ],
            na_position="last",
        )
        .drop(
            columns=[
                "_algorithm_order",
                "_dataset_order",
                "_split_order",
            ]
        )
        .reset_index(drop=True)
    )
    return results_df


# TAMPILKAN TABEL
def display_table(title, dataframe):

    print("\n" )
    print(title)

    if dataframe.empty:
        print("Tidak ada data.")
        return

    print(
        dataframe.to_string(
            index=False,
            float_format=lambda value: f"{value:.6f}",
        )
    )


# EVALUASI SELURUH EKSPERIMEN
def run_evaluation():
    predictions = load_predictions()
    results = []

    # KELOMPOKKAN DATA BERDASARKAN EKSPERIMEN
    grouped = predictions.groupby(
        [
            "algorithm",
            "dataset",
            "split",
        ],
        dropna=False,
    )

    for (
        algorithm,
        dataset,
        split,
    ), group in grouped:
        actual = group["actual"].to_numpy()
        predicted = group["predicted"].to_numpy()
        metrics = evaluate_model(
            actual,
            predicted,
        )
        result = {
            "algorithm": algorithm,
            "dataset": dataset,
            "split": split,
            "total_data": len(group),
            **metrics,
        }

        results.append(result)
    results_df = pd.DataFrame(results)

    if results_df.empty:
        raise ValueError(
            "Tidak ada hasil evaluasi yang dapat ditampilkan."
        )

    results_df = sort_evaluation_results(
        results_df
    )

    # TABEL 1: HASIL EVALUASI XGBOOST
    display_columns = [
        "dataset",
        "split",
        "total_data",
        "MAE",
        "MSE",
        "RMSE",
        "R2",
    ]

    xgboost_results = results_df[
        results_df["algorithm"] == "XGBoost"
    ][display_columns].copy()

    display_table(
        "TABEL 1. HASIL EVALUASI ALGORITMA XGBOOST",
        xgboost_results,
    )

    # Simpan tabel XGBoost
    xgboost_path = (
        EVALUATION_DIR
        / "evaluation_xgboost.csv"
    )

    xgboost_results.to_csv(
        xgboost_path,
        index=False,
    )

    # TABEL 2: HASIL EVALUASI SVR

    svr_results = results_df[
        results_df["algorithm"] == "SVR"
    ][display_columns].copy()

    display_table(
        "TABEL 2. HASIL EVALUASI ALGORITMA SVR",
        svr_results,
    )

    # Simpan tabel SVR
    svr_path = (
        EVALUATION_DIR
        / "evaluation_svr.csv"
    )

    svr_results.to_csv(
        svr_path,
        index=False,
    )

    # TABEL 3: PERINGKAT SPLIT 70:30
    split_70 = results_df[
        results_df["split"] == "70_30"
    ].copy()

    split_70 = split_70.sort_values(
        ["RMSE", "MAE"],
        ascending=[True, True],
    ).reset_index(drop=True)

    split_70.insert(
        0,
        "rank_rmse",
        split_70["RMSE"]
        .rank(
            method="min",
            ascending=True,
        )
        .astype(int),
    )

    comparison_columns = [
        "rank_rmse",
        "algorithm",
        "dataset",
        "split",
        "total_data",
        "MAE",
        "MSE",
        "RMSE",
        "R2",
    ]

    split_70 = split_70[
        comparison_columns
    ]

    display_table(
        "TABEL 3. PERINGKAT HASIL EKSPERIMEN "
        "PEMBAGIAN DATA 70:30",
        split_70,
    )

    # Simpan peringkat 70:30
    split_70_path = (
        EVALUATION_DIR
        / "evaluation_rank_70_30.csv"
    )

    split_70.to_csv(
        split_70_path,
        index=False,
    )

    # TABEL 4: PERINGKAT SPLIT 80:20
    split_80 = results_df[
        results_df["split"] == "80_20"
    ].copy()

    split_80 = split_80.sort_values(
        ["RMSE", "MAE"],
        ascending=[True, True],
    ).reset_index(drop=True)

    split_80.insert(
        0,
        "rank_rmse",
        split_80["RMSE"]
        .rank(
            method="min",
            ascending=True,
        )
        .astype(int),
    )

    split_80 = split_80[
        comparison_columns
    ]

    display_table(
        "TABEL 4. PERINGKAT HASIL EKSPERIMEN "
        "PEMBAGIAN DATA 80:20",
        split_80,
    )

    # Simpan peringkat 80:20
    split_80_path = (
        EVALUATION_DIR
        / "evaluation_rank_80_20.csv"
    )

    split_80.to_csv(
        split_80_path,
        index=False,
    )

    # TABEL 5: HASIL KESELURUHAN + PERINGKAT
    overall_results = results_df.sort_values(
        ["RMSE", "MAE"],
        ascending=[True, True],
    ).reset_index(drop=True)

    overall_results.insert(
        0,
        "rank",
        overall_results["RMSE"]
        .rank(method="min", ascending=True)
        .astype(int),
    )

    overall_results = overall_results[
        [
            "rank",
            "algorithm",
            "dataset",
            "split",
            "total_data",
            "MAE",
            "MSE",
            "RMSE",
            "R2",
        ]
    ]

    display_table(
        "TABEL 5. HASIL EVALUASI KESELURUHAN "
        "(PERINGKAT BERDASARKAN RMSE)",
        overall_results,
    )

    # Simpan peringkat keseluruhan
    overall_path = (
        EVALUATION_DIR
        / "evaluation_rank_overall.csv"
    )

    overall_results.to_csv(
        overall_path,
        index=False,
    )

    # SIMPAN SELURUH HASIL EVALUASI
    output_path = (
        EVALUATION_DIR
        / "evaluation_results.csv"
    )

    results_df.to_csv(
        output_path,
        index=False,
    )

    return (
        results_df,
        xgboost_results,
        svr_results,
        split_70,
        split_80,
    )

# MAIN
if __name__ == "__main__":
    run_evaluation()