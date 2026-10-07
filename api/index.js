import express from "express";
import cors from "cors";
import pool from "../backend/db.js";

import authRoutes from "../backend/routes/authRoutes.js";
import profileRoutes from "../backend/routes/profileRoutes.js";
import passwordRoutes from "../backend/routes/passwordRoutes.js";

const app = express();

// MIDDLEWARE
app.use(cors());
app.use(express.json());

// TEST BACKEND
app.get("/", (req, res) => {
  res.json({
    message: "Backend Noxora berhasil berjalan di Vercel!",
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
      error: error.message,
    });
  }
});

// ROUTES
app.use("/", authRoutes);
app.use("/", profileRoutes);
app.use("/", passwordRoutes);

// EXPORT
export default app;
