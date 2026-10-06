import express from "express";

import {
  changePassword,
  forgotPassword,
  resetPassword,
} from "../controllers/passwordController.js";

const router = express.Router();

router.put("/change-password/:user_id", changePassword);

router.post("/forgot-password", forgotPassword);

router.post("/reset-password", resetPassword);

export default router;
