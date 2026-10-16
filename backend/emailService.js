import nodemailer from "nodemailer";
import dotenv from "dotenv";

dotenv.config();

console.log("GMAIL USER:", process.env.GMAIL_USER);
console.log("APP PASSWORD LENGTH:", process.env.GMAIL_APP_PASSWORD?.length);

const transporter = nodemailer.createTransport({
  service: "gmail",
  auth: {
    user: process.env.GMAIL_USER,
    pass: process.env.GMAIL_APP_PASSWORD,
  },
});

export const sendResetPasswordEmail = async (email, resetLink) => {
  await transporter.sendMail({
    from: `"Noxora" <${process.env.GMAIL_USER}>`,
    to: email,
    subject: "Reset Your Noxora Password",
    html: `
      <h2>Reset Your Noxora Password</h2>
      <p>Please click the link below to reset your password:</p>
      <a href="${resetLink}">Reset Password</a>
      <p>This link will expire in 1 hour.</p>
    `,
  });
};
