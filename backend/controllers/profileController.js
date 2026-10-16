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

    // Check whether the user exists
    if (result.rows.length === 0) {
      return res.status(404).json({
        message: "User not found",
      });
    }

    res.status(200).json({
      message: "Profile data retrieved successfully",
      user: result.rows[0],
    });
  } catch (error) {
    console.error(error);

    res.status(500).json({
      message: "An internal server error occurred",
    });
  }
};

// UPDATE PROFILE
export const updateProfile = async (req, res) => {
  try {
    const { user_id } = req.params;
    const { username, email, phoneNumber } = req.body;

    // Validate required fields
    if (!username || !email) {
      return res.status(400).json({
        message: "Username and email are required",
      });
    }

    // Check whether the user exists
    const userResult = await pool.query(
      `SELECT user_id
       FROM users
       WHERE user_id = $1`,
      [user_id],
    );

    if (userResult.rows.length === 0) {
      return res.status(404).json({
        message: "User not found",
      });
    }

    // Check whether the username or email is already used by another user
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
          message: "Username is already taken",
        });
      }

      if (user.email === email) {
        return res.status(409).json({
          message: "Email is already in use",
        });
      }
    }

    // Update the profile
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
      message: "Profile updated successfully",
      user: result.rows[0],
    });
  } catch (error) {
    console.error(error);

    res.status(500).json({
      message: "An internal server error occurred",
    });
  }
};

// DELETE ACCOUNT
export const deleteAccount = async (req, res) => {
  try {
    const { user_id } = req.params;

    // Check whether the user exists
    const userResult = await pool.query(
      `SELECT user_id
       FROM users
       WHERE user_id = $1`,
      [user_id],
    );

    if (userResult.rows.length === 0) {
      return res.status(404).json({
        message: "User not found",
      });
    }

    // Delete the user account
    await pool.query(
      `DELETE FROM users
       WHERE user_id = $1`,
      [user_id],
    );

    res.status(200).json({
      message: "Account deleted successfully",
    });
  } catch (error) {
    console.error(error);

    res.status(500).json({
      message: "An internal server error occurred",
    });
  }
};
