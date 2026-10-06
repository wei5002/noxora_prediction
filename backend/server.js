import express from "express";
import dotenv from "dotenv";
import cors from "cors";
import pool from "./db.js";

import path from "path";
import { fileURLToPath } from "url";
import { spawn } from "child_process";
import fs from "fs";

import authRoutes from "./routes/authRoutes.js";
import profileRoutes from "./routes/profileRoutes.js";
import passwordRoutes from "./routes/passwordRoutes.js";

dotenv.config();
const app = express();
const PORT = process.env.PORT || 5000;

// PATH
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const ML_DIR = path.join(__dirname, "..", "ml");
const REALTIME_CSV = path.join(ML_DIR, "data", "api", "realtime_api.csv");

const SVR_PREDICTION_CSV = path.join(
  ML_DIR,
  "results",
  "predictions",
  "svr_realtime_predictions.csv",
);

// Hasil prediksi XGBoost
const XGBOOST_PREDICTION_CSV = path.join(
  ML_DIR,
  "results",
  "predictions",
  "xgboost_realtime_predictions.csv",
);

// MIDDLEWARE
app.use(cors());
app.use(express.json());

// TEST BACKEND
app.get("/", (req, res) => {
  res.json({
    message: "Backend Noxora berhasil berjalan!",
  });
});

// TEST DATABASE
app.get("/test-db", async (req, res) => {
  try {
    const result = await pool.query("SELECT NOW()");

    res.json({
      message: "Database berhasil terhubung!",
      time: result.rows[0],
    });
  } catch (error) {
    console.error("Database error:", error);

    res.status(500).json({
      message: "Database gagal terhubung",
    });
  }
});

// MENJALANKAN PYTHON SCRIPT
function runPythonScript(filename) {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(ML_DIR, "prediction", filename);

    const python = spawn("python", [scriptPath], {
      cwd: ML_DIR,
      shell: false,
    });

    python.stdout.on("data", (data) => {
      process.stdout.write(`[${filename}] ${data}`);
    });

    python.stderr.on("data", (data) => {
      process.stderr.write(`[${filename}] ${data}`);
    });

    python.on("error", (error) => {
      console.error(error);

      reject(error);
    });

    python.on("close", (code) => {
      if (code === 0) {
        // console.log("");
        // console.log(`${filename} selesai dijalankan.`);

        resolve();
      } else {
        const error = new Error(
          `${filename} gagal dijalankan dengan exit code ${code}.`,
        );

        console.error("");
        console.error(`${error.message}`);

        reject(error);
      }
    });
  });
}

// ML PIPELINE

async function runMLPipeline() {
  try {
    await runPythonScript("fetch_hourly_api.py");
    await runPythonScript("fetch_realtime_api.py");
    await runPythonScript("predict_realtime_svr.py");
    await runPythonScript("predict_realtime_xgboost.py");

    return true;
  } catch (error) {
    console.error(error.message);

    return false;
  }
}

let lastMLRunHour = null;
let isMLRunning = false;

function getCurrentHourKey() {
  const now = new Date();

  return new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Asia/Jakarta",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
  })
    .format(now)
    .replace(" ", "T");
}

async function ensureMLPipeline() {
  const currentHour = getCurrentHourKey();

  if (lastMLRunHour === currentHour) {
    return;
  }

  if (isMLRunning) {
    while (isMLRunning) {
      await new Promise((resolve) => setTimeout(resolve, 500));
    }

    return;
  }

  isMLRunning = true;

  try {
    const success = await runMLPipeline();

    if (success) {
      lastMLRunHour = currentHour;
    }
  } finally {
    isMLRunning = false;
  }
}

// MEMBACA FILE CSV
function readCSV(filePath) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`File CSV tidak ditemukan: ${filePath}`);
  }

  const csv = fs.readFileSync(filePath, "utf8");

  const lines = csv
    .trim()
    .split(/\r?\n/)
    .filter((line) => line.trim() !== "");

  if (lines.length === 0) {
    return [];
  }

  const headers = lines[0].split(",").map((header) => header.trim());
  const data = lines.slice(1).map((line) => {
    const values = line.split(",").map((value) => value.trim());
    const row = {};
    headers.forEach((header, index) => {
      row[header] = values[index];
    });

    return row;
  });

  return data;
}

// REALTIME ALL
app.get("/api/realtime-all", async (req, res) => {
  try {
    await ensureMLPipeline();

    if (!fs.existsSync(REALTIME_CSV)) {
      return res.status(404).json({
        message: "Data realtime belum tersedia.",
      });
    }

    if (!fs.existsSync(SVR_PREDICTION_CSV)) {
      return res.status(404).json({
        message: "Data prediksi SVR belum tersedia.",
      });
    }

    const data = readCSV(REALTIME_CSV);
    const svrData = readCSV(SVR_PREDICTION_CSV);

    const result = data.map((item) => {
      const prediction = svrData.find(
        (svr) => Number(svr.location_id) === Number(item.location_id),
      );

      return {
        ...item,
        LAG2: prediction?.LAG2 ?? null,
      };
    });

    return res.json(result);
  } catch (error) {
    console.error("Gagal membaca data realtime:", error);

    return res.status(500).json({
      message: "Gagal membaca data realtime.",
      error: error.message,
    });
  }
});

// REALTIME BERDASARKAN LOCATION
app.get("/api/realtime", async (req, res) => {
  try {
    const locationId = Number(req.query.location_id);
    const predict = req.query.predict === "true";

    // VALIDASI LOCATION ID
    if (!locationId) {
      return res.status(400).json({
        message: "location_id wajib diisi.",
      });
    }

    await ensureMLPipeline();

    // JIKA MEMINTA DATA PREDIKSI
    if (predict) {
      // CEK FILE SVR

      if (!fs.existsSync(SVR_PREDICTION_CSV)) {
        return res.status(404).json({
          message: "Data prediksi SVR belum tersedia.",
        });
      }

      // CEK FILE XGBOOST
      if (!fs.existsSync(XGBOOST_PREDICTION_CSV)) {
        return res.status(404).json({
          message: "Data prediksi XGBoost belum tersedia.",
        });
      }

      const svrData = readCSV(SVR_PREDICTION_CSV);
      const xgboostData = readCSV(XGBOOST_PREDICTION_CSV);

      const svrResult = svrData.find(
        (item) => Number(item.location_id) === locationId,
      );

      const xgboostResult = xgboostData.find(
        (item) => Number(item.location_id) === locationId,
      );

      // CEK DATA SVR
      if (!svrResult) {
        return res.status(404).json({
          message: "Data prediksi SVR untuk lokasi tidak ditemukan.",
        });
      }

      // CEK DATA XGBOOST
      if (!xgboostResult) {
        return res.status(404).json({
          message: "Data prediksi XGBoost untuk lokasi tidak ditemukan.",
        });
      }

      // GABUNGKAN HASIL
      const result = {
        // Informasi lokasi
        location_id: locationId,
        location_name: svrResult.location_name || xgboostResult.location_name,

        // Waktu prediksi
        fetched_at: svrResult.fetched_at || xgboostResult.fetched_at,
        target_time: svrResult.target_time || xgboostResult.target_time,
        weather_time: svrResult.weather_time || xgboostResult.weather_time,

        // DATA LAG
        LAG1: svrResult.LAG1,
        LAG2: svrResult.LAG2,
        LAG3: svrResult.LAG3,

        // DATA METEOROLOGI
        temperature_2m: svrResult.temperature_2m,
        relative_humidity_2m: svrResult.relative_humidity_2m,
        rain: svrResult.rain,
        wind_speed_10m: svrResult.wind_speed_10m,

        // HASIL PREDIKSI SVR
        predicted_nitrogen_dioxide: Number(
          svrResult.predicted_nitrogen_dioxide,
        ),

        // HASIL PREDIKSI XGBOOST
        predicted_nitrogen_dioxide_xgboost: Number(
          xgboostResult.predicted_nitrogen_dioxide,
        ),
      };

      return res.json(result);
    }

    // JIKA HANYA MEMINTA DATA REALTIME
    if (!fs.existsSync(REALTIME_CSV)) {
      return res.status(404).json({
        message: "Data realtime belum tersedia.",
      });
    }

    const data = readCSV(REALTIME_CSV);

    const result = data.find((item) => Number(item.location_id) === locationId);

    if (!result) {
      return res.status(404).json({
        message: "Data realtime untuk lokasi tidak ditemukan.",
      });
    }

    return res.json(result);
  } catch (error) {
    console.error("Gagal mengambil data realtime/prediksi:", error);

    return res.status(500).json({
      message: "Gagal mengambil data realtime/prediksi.",
      error: error.message,
    });
  }
});

// PREDICTIONS
app.get("/api/predictions", async (req, res) => {
  try {
    await ensureMLPipeline();

    // CEK SVR
    if (!fs.existsSync(SVR_PREDICTION_CSV)) {
      return res.status(404).json({
        message: "Data prediksi SVR belum tersedia.",
      });
    }

    // CEK XGBOOST
    if (!fs.existsSync(XGBOOST_PREDICTION_CSV)) {
      return res.status(404).json({
        message: "Data prediksi XGBoost belum tersedia.",
      });
    }

    // BACA DATA
    const svrData = readCSV(SVR_PREDICTION_CSV);
    const xgboostData = readCSV(XGBOOST_PREDICTION_CSV);

    // GABUNGKAN DATA
    const result = svrData.map((svr) => {
      const xgboost = xgboostData.find(
        (item) => Number(item.location_id) === Number(svr.location_id),
      );

      return {
        location_id: Number(svr.location_id),
        location_name: svr.location_name || xgboost?.location_name,
        fetched_at: svr.fetched_at || xgboost?.fetched_at,
        target_time: svr.target_time || xgboost?.target_time,
        weather_time: svr.weather_time || xgboost?.weather_time,
        LAG1: svr.LAG1,
        LAG2: svr.LAG2,
        LAG3: svr.LAG3,
        temperature_2m: svr.temperature_2m,
        relative_humidity_2m: svr.relative_humidity_2m,
        rain: svr.rain,
        wind_speed_10m: svr.wind_speed_10m,
        // SVR
        predicted_nitrogen_dioxide: Number(svr.predicted_nitrogen_dioxide),
        // XGBoost
        predicted_nitrogen_dioxide_xgboost: xgboost
          ? Number(xgboost.predicted_nitrogen_dioxide)
          : null,
      };
    });

    return res.json(result);
  } catch (error) {
    console.error("Gagal membaca data prediksi:", error);

    return res.status(500).json({
      message: "Gagal membaca data prediksi.",
      error: error.message,
    });
  }
});

// ROUTES
app.use("/", authRoutes);
app.use("/", profileRoutes);
app.use("/", passwordRoutes);

// START SERVER
app.listen(PORT, async () => {
  // console.log("");
  // console.log("========================================");
  console.log(`Backend berjalan di http://localhost:${PORT}`);
  // console.log("========================================");

  const currentHour = getCurrentHourKey();
  const success = await runMLPipeline();

  if (success) {
    lastMLRunHour = currentHour;
  }
});