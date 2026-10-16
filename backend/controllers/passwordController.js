import bcrypt from "bcrypt";
import crypto from "crypto";
import pool from "../db.js";
import { sendResetPasswordEmail } from "../emailService.js";

// CHANGE PASSWORD
export const changePassword = async (req, res) => {
  try {
    const { user_id } = req.params;
    const { newPassword, confirmPassword } = req.body;

    // Validate required fields
    if (!newPassword || !confirmPassword) {
      return res.status(400).json({
        message: "New password and password confirmation are required",
      });
    }

    // Validate minimum password length
    if (newPassword.length < 8) {
      return res.status(400).json({
        message: "New password must be at least 8 characters long",
      });
    }

    // Validate password confirmation
    if (newPassword !== confirmPassword) {
      return res.status(400).json({
        message: "New password and password confirmation do not match",
      });
    }

    // Retrieve the current password from the database
    const result = await pool.query(
      `SELECT password
       FROM users
       WHERE user_id = $1`,
      [user_id],
    );

    if (result.rows.length === 0) {
      return res.status(404).json({
        message: "User not found",
      });
    }

    const user = result.rows[0];

    // Check whether the new password matches the current password
    const isSamePassword = await bcrypt.compare(newPassword, user.password);

    if (isSamePassword) {
      return res.status(400).json({
        message: "New password must be different from the current password",
      });
    }

    // Hash the new password
    const hashedPassword = await bcrypt.hash(newPassword, 10);

    // Update the password
    await pool.query(
      `UPDATE users
       SET password = $1
       WHERE user_id = $2`,
      [hashedPassword, user_id],
    );

    res.status(200).json({
      message: "Password changed successfully",
    });
  } catch (error) {
    console.error(error);

    res.status(500).json({
      message: "An internal server error occurred",
    });
  }
};

// FORGOT PASSWORD
export const forgotPassword = async (req, res) => {
  try {
    const { email } = req.body;

    // Validate email
    if (!email) {
      return res.status(400).json({
        message: "Email is required",
      });
    }

    const normalizedEmail = email.trim().toLowerCase();

    // Find the user
    const result = await pool.query(
      `SELECT user_id, email
       FROM users
       WHERE email = $1`,
      [normalizedEmail],
    );

    // Check whether the email exists
    if (result.rows.length === 0) {
      return res.status(404).json({
        message: "Email address is not registered",
      });
    }

    const user = result.rows[0];

    // Generate a reset token
    const token = crypto.randomBytes(32).toString("hex");

    // Set the token expiration time to one hour
    const expiresAt = new Date(Date.now() + 60 * 60 * 1000);

    // Delete any existing reset tokens
    await pool.query(
      `DELETE FROM password_reset_tokens
       WHERE user_id = $1`,
      [user.user_id],
    );

    // Store the new reset token
    await pool.query(
      `INSERT INTO password_reset_tokens
       (user_id, token, expires_at)
       VALUES ($1, $2, $3)`,
      [user.user_id, token, expiresAt],
    );

    // Generate the password reset link
    const resetLink = `${process.env.FRONTEND_URL}/ChangePassword?token=${token}`;

    // Send the password reset email
    await sendResetPasswordEmail(user.email, resetLink);

    res.status(200).json({
      message: "Password reset link has been sent to your email",
    });
  } catch (error) {
    console.error("FORGOT PASSWORD ERROR:", error);

    return res.status(500).json({
      success: false,
      message: "Failed to process the password reset request",
    });
  }
};

// RESET PASSWORD
export const resetPassword = async (req, res) => {
  try {
    const { token, newPassword, confirmPassword } = req.body;

    // Validate required fields
    if (!token || !newPassword || !confirmPassword) {
      return res.status(400).json({
        message: "Required password reset information is incomplete",
      });
    }

    // Validate minimum password length
    if (newPassword.length < 8) {
      return res.status(400).json({
        message: "Password must be at least 8 characters long",
      });
    }

    // Validate password confirmation
    if (newPassword !== confirmPassword) {
      return res.status(400).json({
        message: "Password and password confirmation do not match",
      });
    }

    // Find the reset token
    const result = await pool.query(
      `SELECT id, user_id, expires_at
       FROM password_reset_tokens
       WHERE token = $1`,
      [token],
    );

    // Check whether the token exists
    if (result.rows.length === 0) {
      return res.status(400).json({
        message: "Invalid password reset token",
      });
    }

    const resetToken = result.rows[0];

    // Check whether the token has expired
    if (new Date() > new Date(resetToken.expires_at)) {
      await pool.query(
        `DELETE FROM password_reset_tokens
         WHERE id = $1`,
        [resetToken.id],
      );

      return res.status(400).json({
        message: "Password reset token has expired",
      });
    }

    // Hash the new password
    const hashedPassword = await bcrypt.hash(newPassword, 10);

    // Update the user's password
    await pool.query(
      `UPDATE users
       SET password = $1
       WHERE user_id = $2`,
      [hashedPassword, resetToken.user_id],
    );

    // Delete the token after it has been used
    await pool.query(
      `DELETE FROM password_reset_tokens
       WHERE id = $1`,
      [resetToken.id],
    );

    res.status(200).json({
      message: "Password has been reset successfully",
    });
  } catch (error) {
    console.error(error);

    res.status(500).json({
      message: "An internal server error occurred",
    });
  }
};
