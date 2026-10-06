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
    subject: "Reset Password Noxora",
    html: `
      <h2>Reset Password Noxora</h2>
      <p>Silakan klik link berikut untuk reset password:</p>
      <a href="${resetLink}">Reset Password</a>
      <p>Link berlaku selama 1 jam.</p>
    `,
  });
};
