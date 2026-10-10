import re
import numpy as np
import pandas as pd

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

# KONFIGURASI EKSPERIMEN
ALGORITHMS = [
    "XGBoost",
    "SVR",
]

LAG_CONFIGURATIONS = [
    "lag1",
    "lag12",
    "lag123",
]

DATASETS = [
    "no2",
    "no2_meteorologi",
]

SPLITS = [
    "70_30",
    "80_20",
]

REQUIRED_COLUMNS = [
    "actual",
    "predicted",
]

# POLA NAMA FILE PREDIKSI
FILENAME_PATTERN = re.compile(
    r"^(xgboost|svr)_"
    r"(?:(lag1|lag12|lag123)_)?"
    r"(no2_meteorologi|no2)_"
    r"(70_30|80_20)_predictions\.csv$",
    re.IGNORECASE,
)

# MEMBACA INFORMASI SKENARIO DARI NAMA FILE
def parse_prediction_filename(file_path):

    match = FILENAME_PATTERN.match(
        file_path.name
    )

    if not match:
        return None

    algorithm, lag, dataset, split = (
        match.groups()
    )

    if lag is None:
        lag = "lag123"

    algorithm = (
        "XGBoost"
        if algorithm.lower() == "xgboost"
        else "SVR"
    )

    return {
        "algorithm": algorithm,
        "lag_configuration": lag.lower(),
        "dataset": dataset.lower(),
        "split": split,
        "prediction_file": file_path.name,
    }

# MEMUAT HASIL PREDIKSI
def load_predictions():

    if not PREDICTION_DIR.exists():
        raise FileNotFoundError(
            f"Folder prediksi tidak ditemukan: "
            f"{PREDICTION_DIR}"
        )

    prediction_files = sorted(
        PREDICTION_DIR.glob(
            "*_predictions.csv"
        )
    )

    if not prediction_files:
        raise FileNotFoundError(
            "Tidak ada file prediksi eksperimen. "
            "Jalankan training terlebih dahulu."
        )

    scenario_files = {}
    ignored_files = []

    for file_path in prediction_files:

        metadata = parse_prediction_filename(
            file_path
        )

        if metadata is None:
            ignored_files.append(
                file_path.name
            )
            continue

        scenario_key = (
            metadata["algorithm"],
            metadata["lag_configuration"],
            metadata["dataset"],
            metadata["split"],
        )

        is_legacy_file = (
            re.match(
                r"^(xgboost|svr)_"
                r"(no2_meteorologi|no2)_"
                r"(70_30|80_20)_predictions\.csv$",
                file_path.name,
                re.IGNORECASE,
            )
            is not None
        )

        if scenario_key not in scenario_files:

            scenario_files[scenario_key] = (
                file_path,
                metadata,
                is_legacy_file,
            )

        elif (
            scenario_files[scenario_key][2]
            and not is_legacy_file
        ):

            scenario_files[scenario_key] = (
                file_path,
                metadata,
                is_legacy_file,
            )

    dataframes = []
    invalid_files = []

    for (
        file_path,
        metadata,
        _,
    ) in scenario_files.values():

        df = pd.read_csv(
            file_path
        )

        missing_columns = [
            column
            for column in REQUIRED_COLUMNS
            if column not in df.columns
        ]

        if missing_columns:
            invalid_files.append(
                f"{file_path.name}: "
                f"kolom tidak ditemukan "
                f"{missing_columns}"
            )
            continue

        # Memastikan nilai aktual dan prediksi numerik.
        df["actual"] = pd.to_numeric(
            df["actual"],
            errors="coerce",
        )

        df["predicted"] = pd.to_numeric(
            df["predicted"],
            errors="coerce",
        )

        # Menghapus nilai kosong dan tak hingga.
        df = df.replace(
            [np.inf, -np.inf],
            np.nan,
        )

        df = df.dropna(
            subset=REQUIRED_COLUMNS
        )

        if df.empty:
            invalid_files.append(
                f"{file_path.name}: "
                "tidak ada data prediksi valid"
            )
            continue

        # Menambahkan metadata skenario.
        for column, value in metadata.items():
            df[column] = value

        dataframes.append(
            df
        )

    if ignored_files:
        print(
            "\nFILE YANG DILEWATI:"
        )

        for filename in ignored_files:
            print(
                f"- {filename}"
            )

    if invalid_files:
        print(
            "\nFILE YANG TIDAK DAPAT DIEVALUASI:"
        )

        for message in invalid_files:
            print(
                f"- {message}"
            )

    if not dataframes:
        raise ValueError(
            "Tidak ada hasil prediksi valid "
            "untuk dievaluasi."
        )

    return pd.concat(
        dataframes,
        ignore_index=True,
    )


# HITUNG METRIK EVALUASI
def evaluate_model(actual, predicted):

    mae = mean_absolute_error(
        actual,
        predicted,
    )

    mse = mean_squared_error(
        actual,
        predicted,
    )

    rmse = np.sqrt(
        mse
    )

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

    results_df = results_df.copy()

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

    lag_order = {
        "lag1": 0,
        "lag12": 1,
        "lag123": 2,
    }

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

    results_df["_lag_order"] = (
        results_df["lag_configuration"].map(
            lag_order
        )
    )

    results_df = results_df.sort_values(
        [
            "_algorithm_order",
            "_dataset_order",
            "_split_order",
            "_lag_order",
        ],
        na_position="last",
    )

    results_df = results_df.drop(
        columns=[
            "_algorithm_order",
            "_dataset_order",
            "_split_order",
            "_lag_order",
        ]
    )

    return results_df.reset_index(
        drop=True
    )

# MENAMPILKAN TABEL
def display_table(title, dataframe):

    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)

    if dataframe.empty:
        print(
            "Tidak ada data."
        )
        return

    print(
        dataframe.to_string(
            index=False,
            float_format=lambda value: (
                f"{value:.6f}"
            ),
        )
    )

# MENYIMPAN TABEL
def save_table(dataframe, filename):

    output_path = (
        EVALUATION_DIR / filename
    )

    dataframe.to_csv(
        output_path,
        index=False,
    )

    print(
        f"\nFile tersimpan: {output_path}"
    )


# MEMERIKSA 24 SKENARIO
def check_scenarios(results_df):

    expected_scenarios = {
        (
            algorithm,
            lag,
            dataset,
            split,
        )
        for algorithm in ALGORITHMS
        for lag in LAG_CONFIGURATIONS
        for dataset in DATASETS
        for split in SPLITS
    }

    actual_scenarios = {
        (
            row.algorithm,
            row.lag_configuration,
            row.dataset,
            row.split,
        )
        for row in results_df.itertuples()
    }

    missing_scenarios = (
        expected_scenarios - actual_scenarios
    )

    print(
        "\nJUMLAH SKENARIO"
    )

    print(
        f"Skenario tersedia: "
        f"{len(actual_scenarios)} / "
        f"{len(expected_scenarios)}"
    )

    if missing_scenarios:

        print(
            "\nSKENARIO YANG BELUM TERSEDIA:"
        )

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

        lag_order = {
            "lag1": 0,
            "lag12": 1,
            "lag123": 2,
        }

        for (
            algorithm,
            lag,
            dataset,
            split,
        ) in sorted(
            missing_scenarios,
            key=lambda item: (
                algorithm_order[item[0]],
                dataset_order[item[2]],
                split_order[item[3]],
                lag_order[item[1]],
            ),
        ):

            print(
                f"- {algorithm} | "
                f"{dataset} | "
                f"{split} | "
                f"{lag}"
            )

    return (
        expected_scenarios,
        actual_scenarios,
        missing_scenarios,
    )


# MEMBUAT PERINGKAT BERDASARKAN RMSE DAN MAE
def create_ranking(dataframe):

    ranked = dataframe.sort_values(
        [
            "RMSE",
            "MAE",
        ],
        ascending=[
            True,
            True,
        ],
        na_position="last",
    ).reset_index(
        drop=True
    )

    ranked.insert(
        0,
        "rank",
        np.arange(
            1,
            len(ranked) + 1,
        ),
    )

    return ranked


# EVALUASI SELURUH EKSPERIMEN
def run_evaluation():
    predictions = load_predictions()
    results = []

    grouped = predictions.groupby(
        [
            "algorithm",
            "lag_configuration",
            "dataset",
            "split",
            "prediction_file",
        ],
        dropna=False,
        sort=False,
    )

    for (
        algorithm,
        lag_configuration,
        dataset,
        split,
        prediction_file,
    ), group in grouped:

        actual = group[
            "actual"
        ].to_numpy()

        predicted = group[
            "predicted"
        ].to_numpy()

        metrics = evaluate_model(
            actual,
            predicted,
        )

        result = {
            "algorithm": algorithm,
            "dataset": dataset,
            "split": split,
            "lag_configuration": (
                lag_configuration
            ),
            "total_data": len(group),
            **metrics,
            "prediction_file": prediction_file,
        }

        results.append(
            result
        )

    results_df = pd.DataFrame(
        results
    )

    if results_df.empty:
        raise ValueError(
            "Tidak ada hasil evaluasi yang dapat ditampilkan."
        )

    results_df = sort_evaluation_results(
        results_df
    )

    # Memeriksa kelengkapan skenario.
    (
        expected_scenarios,
        actual_scenarios,
        missing_scenarios,
    ) = check_scenarios(
        results_df
    )

    # KOLOM TABEL EVALUASI
    display_columns = [
        "dataset",
        "split",
        "lag_configuration",
        "total_data",
        "MAE",
        "MSE",
        "RMSE",
        "R2",
    ]

    # TABEL 1: EVALUASI XGBOOST
    xgboost_results = results_df[
        results_df["algorithm"] == "XGBoost"
    ][display_columns].copy()

    display_table(
        "TABEL 1. HASIL EVALUASI ALGORITMA XGBOOST",
        xgboost_results,
    )

    save_table(
        xgboost_results,
        "evaluation_xgboost.csv",
    )

    # TABEL 2: EVALUASI SVR
    svr_results = results_df[
        results_df["algorithm"] == "SVR"
    ][display_columns].copy()

    display_table(
        "TABEL 2. HASIL EVALUASI ALGORITMA SVR",
        svr_results,
    )

    save_table(
        svr_results,
        "evaluation_svr.csv",
    )

    # KOLOM TABEL PERINGKAT
    comparison_columns = [
        "rank",
        "algorithm",
        "dataset",
        "split",
        "lag_configuration",
        "total_data",
        "MAE",
        "MSE",
        "RMSE",
        "R2",
    ]

    # TABEL 3: PERINGKAT SPLIT 70:30
    split_70 = results_df[
        results_df["split"] == "70_30"
    ].copy()

    split_70 = create_ranking(
        split_70
    )

    split_70 = split_70[
        comparison_columns
    ]

    display_table(
        "TABEL 3. PERINGKAT HASIL EKSPERIMEN "
        "PEMBAGIAN DATA 70:30",
        split_70,
    )

    save_table(
        split_70,
        "evaluation_rank_70_30.csv",
    )

    # TABEL 4: PERINGKAT SPLIT 80:20
    split_80 = results_df[
        results_df["split"] == "80_20"
    ].copy()

    split_80 = create_ranking(
        split_80
    )

    split_80 = split_80[
        comparison_columns
    ]

    display_table(
        "TABEL 4. PERINGKAT HASIL EKSPERIMEN "
        "PEMBAGIAN DATA 80:20",
        split_80,
    )

    save_table(
        split_80,
        "evaluation_rank_80_20.csv",
    )

    # TABEL 5: PERINGKAT KESELURUHAN
    overall_results = create_ranking(
        results_df.copy()
    )

    overall_results = overall_results[
        comparison_columns
    ]

    display_table(
        "TABEL 5. PERINGKAT KESELURUHAN "
        "XGBOOST VS SVR BERDASARKAN RMSE",
        overall_results,
    )

    save_table(
        overall_results,
        "evaluation_rank_overall.csv",
    )

    # SIMPAN SELURUH HASIL EVALUASI
    save_table(
        results_df,
        "evaluation_results.csv",
    )


    if not missing_scenarios:
        print(
            "Seluruh 24 skenario berhasil dievaluasi."
        )

        best_model = overall_results.iloc[0]

    else:
        print(
            "Peringkat di atas hanya berdasarkan skenario yang tersedia."
        )

    return (
        results_df,
        xgboost_results,
        svr_results,
        split_70,
        split_80,
        overall_results,
    )


# MAIN

if __name__ == "__main__":
    run_evaluation()