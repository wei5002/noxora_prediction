import express from "express";
import {
  getProfile,
  updateProfile,
  deleteAccount,
} from "../controllers/profileController.js";

const router = express.Router();

router.get("/profile/:user_id", getProfile);

router.put("/profile/:user_id", updateProfile);

router.delete("/profile/:user_id", deleteAccount);

export default router;