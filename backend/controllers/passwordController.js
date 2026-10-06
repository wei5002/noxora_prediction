import bcrypt from "bcrypt";
import crypto from "crypto";
import pool from "../db.js";
import { sendResetPasswordEmail } from "../emailService.js";

// CHANGE PASSWORD
export const changePassword = async (req, res) => {
  try {
    const { user_id } = req.params;
    const { newPassword, confirmPassword } = req.body;

    // Cek data wajib
    if (!newPassword || !confirmPassword) {
      return res.status(400).json({
        message: "Password baru dan konfirmasi password wajib diisi",
      });
    }

    // Password minimal 8 karakter
    if (newPassword.length < 8) {
      return res.status(400).json({
        message: "Password baru minimal 8 karakter",
      });
    }

    // Cek konfirmasi password
    if (newPassword !== confirmPassword) {
      return res.status(400).json({
        message: "Password baru dan konfirmasi password tidak sama",
      });
    }

    // Ambil password lama dari database
    const result = await pool.query(
      `SELECT password
       FROM users
       WHERE user_id = $1`,
      [user_id],
    );

    if (result.rows.length === 0) {
      return res.status(404).json({
        message: "User tidak ditemukan",
      });
    }

    const user = result.rows[0];

    // Cek apakah password baru sama dengan password sebelumnya
    const isSamePassword = await bcrypt.compare(newPassword, user.password);

    if (isSamePassword) {
      return res.status(400).json({
        message: "Password baru tidak boleh sama dengan password sebelumnya",
      });
    }

    // Hash password baru
    const hashedPassword = await bcrypt.hash(newPassword, 10);

    // Update password
    await pool.query(
      `UPDATE users
       SET password = $1
       WHERE user_id = $2`,
      [hashedPassword, user_id],
    );

    res.status(200).json({
      message: "Password berhasil diubah",
    });
  } catch (error) {
    console.error(error);

    res.status(500).json({
      message: "Terjadi kesalahan pada server",
    });
  }
};

// FORGOT PASSWORD
export const forgotPassword = async (req, res) => {
  try {
    const { email } = req.body;

    // Cek email
    if (!email) {
      return res.status(400).json({
        message: "Email wajib diisi",
      });
    }

    const normalizedEmail = email.trim().toLowerCase();

    // Cari user
    const result = await pool.query(
      `SELECT user_id, email
       FROM users
       WHERE email = $1`,
      [normalizedEmail],
    );

    // Email tidak ditemukan
    if (result.rows.length === 0) {
      return res.status(404).json({
        message: "Email tidak terdaftar",
      });
    }

    const user = result.rows[0];

    // Buat token
    const token = crypto.randomBytes(32).toString("hex");

    // Token berlaku 1 jam
    const expiresAt = new Date(Date.now() + 60 * 60 * 1000);

    // Hapus token lama
    await pool.query(
      `DELETE FROM password_reset_tokens
       WHERE user_id = $1`,
      [user.user_id],
    );

    // Simpan token baru
    await pool.query(
      `INSERT INTO password_reset_tokens
       (user_id, token, expires_at)
       VALUES ($1, $2, $3)`,
      [user.user_id, token, expiresAt],
    );

    // Link reset password
    const resetLink = `http://localhost:3000/ChangePassword?token=${token}`;

    // Kirim email
    await sendResetPasswordEmail(user.email, resetLink);

    res.status(200).json({
      message: "Link reset password berhasil dikirim ke email",
    });
  } catch (error) {
    console.error("Forgot Password Error:", error);

    res.status(500).json({
      message: "Gagal mengirim email reset password",
    });
  }
};

// RESET PASSWORD
export const resetPassword = async (req, res) => {
  try {
    const { token, newPassword, confirmPassword } = req.body;

    // Cek data wajib
    if (!token || !newPassword || !confirmPassword) {
      return res.status(400).json({
        message: "Data reset password belum lengkap",
      });
    }

    // Password minimal 8 karakter
    if (newPassword.length < 8) {
      return res.status(400).json({
        message: "Password minimal 8 karakter",
      });
    }

    // Cek konfirmasi password
    if (newPassword !== confirmPassword) {
      return res.status(400).json({
        message: "Password dan konfirmasi password tidak sama",
      });
    }

    // Cari token
    const result = await pool.query(
      `SELECT id, user_id, expires_at
       FROM password_reset_tokens
       WHERE token = $1`,
      [token],
    );

    // Token tidak ditemukan
    if (result.rows.length === 0) {
      return res.status(400).json({
        message: "Token reset password tidak valid",
      });
    }

    const resetToken = result.rows[0];

    // Cek token expired
    if (new Date() > new Date(resetToken.expires_at)) {
      await pool.query(
        `DELETE FROM password_reset_tokens
         WHERE id = $1`,
        [resetToken.id],
      );

      return res.status(400).json({
        message: "Token reset password sudah kedaluwarsa",
      });
    }

    // Hash password baru
    const hashedPassword = await bcrypt.hash(newPassword, 10);

    // Update password
    await pool.query(
      `UPDATE users
       SET password = $1
       WHERE user_id = $2`,
      [hashedPassword, resetToken.user_id],
    );

    // Hapus token setelah digunakan
    await pool.query(
      `DELETE FROM password_reset_tokens
       WHERE id = $1`,
      [resetToken.id],
    );

    res.status(200).json({
      message: "Password berhasil direset",
    });
  } catch (error) {
    console.error(error);

    res.status(500).json({
      message: "Terjadi kesalahan pada server",
    });
  }
};
