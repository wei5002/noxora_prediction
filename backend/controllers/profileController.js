import pool from "../db.js";

// PROFILE
export const getProfile = async (req, res) => {
  try {
    const { user_id } = req.params;

    const result = await pool.query(
      `SELECT user_id, username, email, "phoneNumber"
       FROM users
       WHERE user_id = $1`,
      [user_id],
    );

    // User tidak ditemukan
    if (result.rows.length === 0) {
      return res.status(404).json({
        message: "User tidak ditemukan",
      });
    }

    res.status(200).json({
      message: "Data profile berhasil diambil",
      user: result.rows[0],
    });
  } catch (error) {
    console.error(error);

    res.status(500).json({
      message: "Terjadi kesalahan pada server",
    });
  }
};

// UPDATE PROFILE
export const updateProfile = async (req, res) => {
  try {
    const { user_id } = req.params;
    const { username, email, phoneNumber } = req.body;

    // Cek data wajib
    if (!username || !email) {
      return res.status(400).json({
        message: "Username dan email wajib diisi",
      });
    }

    // Cek user
    const userResult = await pool.query(
      `SELECT user_id
       FROM users
       WHERE user_id = $1`,
      [user_id],
    );

    if (userResult.rows.length === 0) {
      return res.status(404).json({
        message: "User tidak ditemukan",
      });
    }

    // Cek username atau email sudah digunakan user lain
    const existingUser = await pool.query(
      `SELECT user_id, username, email
       FROM users
       WHERE (username = $1 OR email = $2)
       AND user_id != $3`,
      [username, email, user_id],
    );

    if (existingUser.rows.length > 0) {
      const user = existingUser.rows[0];

      if (user.username === username) {
        return res.status(409).json({
          message: "Username sudah digunakan",
        });
      }

      if (user.email === email) {
        return res.status(409).json({
          message: "Email sudah digunakan",
        });
      }
    }

    // Update profile
    const result = await pool.query(
      `UPDATE users
       SET username = $1,
           email = $2,
           "phoneNumber" = $3
       WHERE user_id = $4
       RETURNING user_id, username, email, "phoneNumber"`,
      [username, email, phoneNumber || null, user_id],
    );

    res.status(200).json({
      message: "Profile berhasil diperbarui",
      user: result.rows[0],
    });
  } catch (error) {
    console.error(error);

    res.status(500).json({
      message: "Terjadi kesalahan pada server",
    });
  }
};

// DELETE ACCOUNT
export const deleteAccount = async (req, res) => {
  try {
    const { user_id } = req.params;

    // Cek user
    const userResult = await pool.query(
      `SELECT user_id
       FROM users
       WHERE user_id = $1`,
      [user_id],
    );

    if (userResult.rows.length === 0) {
      return res.status(404).json({
        message: "User tidak ditemukan",
      });
    }

    // Hapus user
    await pool.query(
      `DELETE FROM users
       WHERE user_id = $1`,
      [user_id],
    );

    res.status(200).json({
      message: "Akun berhasil dihapus",
    });
  } catch (error) {
    console.error(error);

    res.status(500).json({
      message: "Terjadi kesalahan pada server",
    });
  }
};
