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

// PATHS
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

const XGBOOST_PREDICTION_CSV = path.join(
  ML_DIR,
  "results",
  "predictions",
  "xgboost_realtime_predictions.csv",
);

const REFRESH_INTERVAL = 5 * 60 * 1000;

// PIPELINE STATUS
let lastMLAttemptAt = 0;
let lastMLSuccessAt = null;
let lastMLError = null;
let mlPipelinePromise = null;

// MIDDLEWARE
app.use(cors());
app.use(express.json());

// HELPER: FORMAT NUMBERS
function toNumber(value) {
  if (value === undefined || value === null || String(value).trim() === "") {
    return null;
  }
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

// HELPER: READ CSV

function readCSV(filePath) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`CSV file not found: ${filePath}`);
  }

  const content = fs.readFileSync(filePath, "utf8");

  if (!content.trim()) {
    return [];
  }

  const lines = content
    .replace(/^\uFEFF/, "")
    .trim()
    .split(/\r?\n/)
    .filter((line) => line.trim() !== "");

  if (lines.length < 2) {
    return [];
  }

  // Simple CSV parser that supports commas inside quoted fields.
  function parseCSVLine(line) {
    const values = [];
    let value = "";
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
      const char = line[i];

      if (char === '"') {
        if (inQuotes && line[i + 1] === '"') {
          value += '"';
          i++;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (char === "," && !inQuotes) {
        values.push(value.trim());
        value = "";
      } else {
        value += char;
      }
    }

    values.push(value.trim());

    return values;
  }

  const headers = parseCSVLine(lines[0]);

  return lines.slice(1).map((line) => {
    const values = parseCSVLine(line);
    const row = {};

    headers.forEach((header, index) => {
      row[header] = values[index] ?? "";
    });

    return row;
  });
}

// HELPER: READ CSV IF AVAILABLE
function readCSVIfExists(filePath) {
  if (!fs.existsSync(filePath)) {
    return [];
  }

  try {
    return readCSV(filePath);
  } catch (error) {
    console.error(`Failed to read ${path.basename(filePath)}:`, error.message);

    return [];
  }
}

// HELPER: FIND DATA BY LOCATION ID
function findByLocation(rows, locationId) {
  return rows.find((row) => Number(row.location_id) === Number(locationId));
}

// HELPER: RUN PYTHON SCRIPT
function runPythonScript(filename) {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(ML_DIR, "prediction", filename);

    if (!fs.existsSync(scriptPath)) {
      reject(new Error(`Python script not found: ${scriptPath}`));
      return;
    }

    const pythonCommand = process.platform === "win32" ? "python" : "python3";

    const python = spawn(pythonCommand, [scriptPath], {
      cwd: ML_DIR,
      shell: false,
    });

    let settled = false;

    python.stdout.on("data", (data) => {
      process.stdout.write(`[${filename}] ${data}`);
    });

    python.stderr.on("data", (data) => {
      process.stderr.write(`[${filename}] ${data}`);
    });

    python.on("error", (error) => {
      if (settled) return;

      settled = true;

      reject(new Error(`${filename} failed to execute: ${error.message}`));
    });

    python.on("close", (code) => {
      if (settled) return;

      settled = true;

      if (code === 0) {
        console.log(`[${filename}] Completed.`);
        resolve();
      } else {
        reject(new Error(`${filename} failed with exit code ${code}.`));
      }
    });
  });
}

// ML PIPELINE

async function runMLPipeline() {
  console.log("Starting Noxora realtime pipeline");

  try {
    await runPythonScript("fetch_hourly_api.py");
    await runPythonScript("fetch_realtime_api.py");
    await runPythonScript("predict_realtime_svr.py");
    await runPythonScript("predict_realtime_xgboost.py");

    lastMLSuccessAt = new Date().toISOString();
    lastMLError = null;

    console.log("Realtime pipeline completed successfully.");
    return true;
  } catch (error) {
    lastMLError = error.message;

    console.error("Realtime pipeline failed:", error.message);

    return false;
  }
}

// REFRESH PIPELINE AT MOST EVERY 5 MINUTES

async function ensureMLPipeline() {
  // Wait for the existing process if it is already running.
  if (mlPipelinePromise) {
    await mlPipelinePromise;
    return;
  }

  const now = Date.now();

  // Prevent repeated API calls.
  if (now - lastMLAttemptAt < REFRESH_INTERVAL) {
    return;
  }

  // Record the attempt before running the pipeline.
  lastMLAttemptAt = now;

  mlPipelinePromise = runMLPipeline();

  try {
    await mlPipelinePromise;
  } finally {
    mlPipelinePromise = null;
  }
}

// HELPER: COMBINE ACTUAL DATA AND PREDICTIONS

function buildRealtimeData() {
  const actualRows = readCSVIfExists(REALTIME_CSV);
  const svrRows = readCSVIfExists(SVR_PREDICTION_CSV);
  const xgbRows = readCSVIfExists(XGBOOST_PREDICTION_CSV);

  return actualRows.map((actual) => {
    const locationId = Number(actual.location_id);

    const svr = findByLocation(svrRows, locationId);
    const xgb = findByLocation(xgbRows, locationId);

    return {
      // Location information
      location_id: locationId,
      location_name:
        actual.location_name ||
        svr?.location_name ||
        xgb?.location_name ||
        null,

      // Actual NO2 data
      time_no2: actual.time_no2 || null,
      nitrogen_dioxide: toNumber(actual.nitrogen_dioxide),

      // Actual meteorological data
      time_weather: actual.time_weather || null,
      temperature_2m: toNumber(actual.temperature_2m),
      relative_humidity_2m: toNumber(actual.relative_humidity_2m),
      rain: toNumber(actual.rain),
      wind_speed_10m: toNumber(actual.wind_speed_10m),

      // Prediction timestamps
      fetched_at: svr?.fetched_at || xgb?.fetched_at || null,
      target_time: svr?.target_time || xgb?.target_time || null,
      weather_time: svr?.weather_time || xgb?.weather_time || null,

      // Lag features for charts and model inputs
      LAG1: toNumber(svr?.LAG1 ?? actual.LAG1),
      LAG2: toNumber(svr?.LAG2 ?? actual.LAG2),
      LAG3: toNumber(svr?.LAG3 ?? actual.LAG3),

      // SVR prediction
      predicted_nitrogen_dioxide: toNumber(svr?.predicted_nitrogen_dioxide),

      // XGBoost prediction
      predicted_nitrogen_dioxide_xgboost: toNumber(
        xgb?.predicted_nitrogen_dioxide,
      ),
    };
  });
}

// BACKEND HEALTH CHECK
app.get("/", (req, res) => {
  res.json({
    success: true,
    message: "Noxora backend is running successfully!",
  });
});

// DATABASE CONNECTION TEST
app.get("/test-db", async (req, res) => {
  try {
    const result = await pool.query("SELECT NOW()");

    res.json({
      success: true,
      message: "Database connection successful!",
      time: result.rows[0],
    });
  } catch (error) {
    console.error("Database error:", error);

    res.status(500).json({
      success: false,
      message: "Database connection failed.",
      error: error.message,
    });
  }
});

// PIPELINE STATUS

app.get("/api/ml/status", (req, res) => {
  res.json({
    success: true,
    refresh_interval_ms: REFRESH_INTERVAL,
    last_attempt_at: lastMLAttemptAt
      ? new Date(lastMLAttemptAt).toISOString()
      : null,
    last_success_at: lastMLSuccessAt,
    last_error: lastMLError,
    is_running: Boolean(mlPipelinePromise),
    has_realtime_file: fs.existsSync(REALTIME_CSV),
    has_svr_file: fs.existsSync(SVR_PREDICTION_CSV),
    has_xgboost_file: fs.existsSync(XGBOOST_PREDICTION_CSV),
  });
});

// REALTIME DATA FOR ALL LOCATIONS
// Returns actual data and lag features

app.get("/api/realtime-all", async (req, res) => {
  try {
    await ensureMLPipeline();

    if (!fs.existsSync(REALTIME_CSV)) {
      return res.status(503).json({
        success: false,
        message: "Realtime data is not available yet.",
        error: lastMLError,
      });
    }

    const data = buildRealtimeData();

    return res.json(data);
  } catch (error) {
    console.error("Failed to read realtime data:", error.message);

    return res.status(500).json({
      success: false,
      message: "Failed to read realtime data.",
      error: error.message,
    });
  }
});

// REALTIME DATA AND PREDICTIONS FOR ALL LOCATIONS
// Endpoint used by the frontend Home page

app.get("/api/ml/realtime", (req, res) => {
  try {
    // Read the most recently saved actual data.
    const actualRows = readCSVIfExists(REALTIME_CSV);

    if (actualRows.length === 0) {
      return res.status(503).json({
        success: false,
        message: "Realtime data is not available yet.",
        error: lastMLError,
      });
    }

    // Prediction files may not be available yet.
    const svrRows = readCSVIfExists(SVR_PREDICTION_CSV);
    const xgbRows = readCSVIfExists(XGBOOST_PREDICTION_CSV);

    const data = actualRows.map((actual) => {
      const locationId = String(actual.location_id);

      const svr = svrRows.find((row) => String(row.location_id) === locationId);

      const xgb = xgbRows.find((row) => String(row.location_id) === locationId);

      return {
        ...actual,

        target_time: svr?.target_time ?? xgb?.target_time ?? null,

        LAG1: svr?.LAG1 ?? actual.LAG1 ?? null,
        LAG2: svr?.LAG2 ?? actual.LAG2 ?? null,
        LAG3: svr?.LAG3 ?? actual.LAG3 ?? null,

        temperature_2m: svr?.temperature_2m ?? actual.temperature_2m ?? null,

        relative_humidity_2m:
          svr?.relative_humidity_2m ?? actual.relative_humidity_2m ?? null,

        rain: svr?.rain ?? actual.rain ?? null,

        wind_speed_10m: svr?.wind_speed_10m ?? actual.wind_speed_10m ?? null,

        predicted_nitrogen_dioxide: svr?.predicted_nitrogen_dioxide ?? null,

        predicted_nitrogen_dioxide_xgboost:
          xgb?.predicted_nitrogen_dioxide_xgboost ??
          xgb?.predicted_nitrogen_dioxide ??
          null,
      };
    });

    return res.json({
      success: true,
      data,
      last_success_at: lastMLSuccessAt,
      last_error: lastMLError,
    });
  } catch (error) {
    console.error("Failed to retrieve combined realtime data:", error.message);

    return res.status(500).json({
      success: false,
      message: "Failed to retrieve realtime data.",
      error: error.message,
    });
  }
});

app.get("/api/realtime", async (req, res) => {
  try {
    const locationId = Number(req.query.location_id);
    const predict = req.query.predict === "true";

    if (!Number.isInteger(locationId) || locationId < 1 || locationId > 10) {
      return res.status(400).json({
        success: false,
        message: "location_id must be a number between 1 and 10.",
      });
    }

    await ensureMLPipeline();

    if (predict) {
      const data = buildRealtimeData();

      const result = findByLocation(data, locationId);

      if (!result) {
        return res.status(404).json({
          success: false,
          message: "Location data not found.",
        });
      }

      return res.json(result);
    }

    if (!fs.existsSync(REALTIME_CSV)) {
      return res.status(503).json({
        success: false,
        message: "Realtime data is not available yet.",
        error: lastMLError,
      });
    }

    const actualRows = readCSV(REALTIME_CSV);
    const result = findByLocation(actualRows, locationId);

    if (!result) {
      return res.status(404).json({
        success: false,
        message: "Realtime data for this location was not found.",
      });
    }

    return res.json(result);
  } catch (error) {
    console.error(
      "Failed to retrieve realtime data/predictions:",
      error.message,
    );

    return res.status(500).json({
      success: false,
      message: "Failed to retrieve realtime data/predictions.",
      error: error.message,
    });
  }
});

// PREDICTIONS FOR ALL LOCATIONS

app.get("/api/predictions", async (req, res) => {
  try {
    await ensureMLPipeline();

    const data = buildRealtimeData();

    if (data.length === 0) {
      return res.status(503).json({
        success: false,
        message: "Prediction data is not available yet.",
        error: lastMLError,
      });
    }

    return res.json(data);
  } catch (error) {
    console.error("Failed to read prediction data:", error.message);

    return res.status(500).json({
      success: false,
      message: "Failed to read prediction data.",
      error: error.message,
    });
  }
});

// AUTHENTICATION, PROFILE, AND PASSWORD ROUTES
app.use("/", authRoutes);
app.use("/", profileRoutes);
app.use("/", passwordRoutes);

// EXPORT APPLICATION
export default app;
