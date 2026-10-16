import bcrypt from "bcrypt";
import pool from "../db.js";

// REGISTRATION
export const register = async (req, res) => {
  try {
    const { username, email, phoneNumber, password, confirmPassword } =
      req.body;

    // Normalize input data
    const normalizedUsername = username?.trim().toLowerCase();
    const normalizedEmail = email?.trim().toLowerCase();
    const normalizedPhoneNumber = phoneNumber?.trim();

    // Validate required fields
    if (
      !normalizedUsername ||
      !normalizedEmail ||
      !password ||
      !confirmPassword
    ) {
      return res.status(400).json({
        message: "Registration information is incomplete",
      });
    }

    // Validate minimum username length
    if (normalizedUsername.length < 6) {
      return res.status(400).json({
        message: "Username must be at least 6 characters long",
      });
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailRegex.test(normalizedEmail)) {
      return res.status(400).json({
        message: "Invalid email format",
      });
    }

    // Validate phone number
    if (normalizedPhoneNumber && !/^\d+$/.test(normalizedPhoneNumber)) {
      return res.status(400).json({
        message: "Phone number must contain digits only",
      });
    }

    // Validate minimum password length
    if (password.length < 8) {
      return res.status(400).json({
        message: "Password must be at least 8 characters long",
      });
    }

    // Validate password confirmation
    if (password !== confirmPassword) {
      return res.status(400).json({
        message: "Password and password confirmation do not match",
      });
    }

    // Check whether the username or email is already registered
    const existingUser = await pool.query(
      `SELECT user_id, username, email
       FROM users
       WHERE username = $1 OR email = $2`,
      [normalizedUsername, normalizedEmail],
    );

    if (existingUser.rows.length > 0) {
      const user = existingUser.rows[0];

      if (user.username === normalizedUsername) {
        return res.status(409).json({
          message: "Username is already registered",
        });
      }

      if (user.email === normalizedEmail) {
        return res.status(409).json({
          message: "Email is already registered",
        });
      }
    }

    // Hash the password
    const hashedPassword = await bcrypt.hash(password, 10);

    // Save the new user
    const result = await pool.query(
      `INSERT INTO users
        (username, email, "phoneNumber", password)
       VALUES ($1, $2, $3, $4)
       RETURNING user_id, username, email, "phoneNumber"`,
      [
        normalizedUsername,
        normalizedEmail,
        normalizedPhoneNumber || null,
        hashedPassword,
      ],
    );

    res.status(201).json({
      message: "Registration successful",
      user: result.rows[0],
    });
  } catch (error) {
    console.error(error);

    res.status(500).json({
      message: "An internal server error occurred",
    });
  }
};

// LOGIN
export const login = async (req, res) => {
  try {
    const { email, password } = req.body;

    // Validate required fields
    if (!email || !password) {
      return res.status(400).json({
        message: "Email and password are required",
      });
    }

    // Normalize email
    const normalizedEmail = email.trim().toLowerCase();

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailRegex.test(normalizedEmail)) {
      return res.status(400).json({
        message: "Invalid email format",
      });
    }

    // Find the user by email
    const result = await pool.query(
      `SELECT user_id, username, email, "phoneNumber", password
       FROM users
       WHERE email = $1`,
      [normalizedEmail],
    );

    // Check whether the user exists
    if (result.rows.length === 0) {
      return res.status(401).json({
        message: "Invalid email or password",
      });
    }

    const user = result.rows[0];

    // Validate password
    const isPasswordValid = await bcrypt.compare(password, user.password);

    if (!isPasswordValid) {
      return res.status(401).json({
        message: "Invalid email or password",
      });
    }

    // Login successful
    res.status(200).json({
      message: "Login successful",
      user: {
        user_id: user.user_id,
        username: user.username,
        email: user.email,
        phoneNumber: user.phoneNumber,
      },
    });
  } catch (error) {
    console.error("Login Error:", error);

    res.status(500).json({
      message: "An internal server error occurred",
    });
  }
};
