// src/theme.js
import { createSystem, defaultConfig, defineConfig } from "@chakra-ui/react";

const config = defineConfig({
  globalCss: {
    "*": {
      boxSizing: "border-box",
      padding: 0,
      margin: 0,
    },
    "html, body": {
      maxWidth: "100vw",
      overflowX: "hidden",
    },
    a: {
      color: "inherit",
      textDecoration: "none",
    },
    "::view-transition-old(root), ::view-transition-new(root)": {
      animation: "none",
      mixBlendMode: "normal",
    },
    "::view-transition-new(root)": {
      zIndex: 9999,
    },
    "::view-transition-old(root)": {
      zIndex: 1,
    },
    "@keyframes fadeInUp": {
      from: { opacity: 0, transform: "translateY(20px)" },
      to: { opacity: 1, transform: "translateY(0)" },
    },
    ".fade-in-up": {
      animation: "fadeInUp 0.4s ease forwards",
    },
    ".loading-overlay": {
      position: "fixed",
      inset: 0,
      background: { base: "#ffffff", _dark: "#353535" },
      zIndex: 99,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    },
    ".sweep-container": {
      position: "relative",
      width: "260px",
    },
    ".sweep-base": {
      width: "100%",
      display: "block",
      filter: "grayscale(100%) opacity(0.3)",
    },
    ".sweep-color": {
      width: "100%",
      display: "block",
    },
    ".sweep-overlay": {
      position: "absolute",
      inset: 0,
      width: "100%",
      animation: "sweepAnim 2s infinite ease-in-out",
    },
    "@keyframes sweepAnim": {
      "0%": { clipPath: "inset(0 100% 0 0)" },
      "50%": { clipPath: "inset(0 0 0 0)" },
      "100%": { clipPath: "inset(0 0 0 100%)" },
    },
  },
  theme: {
    tokens: {
      colors: {
        brand: {
          50: { value: "#ffe5e5" },
          100: { value: "#fbb8b8" },
          200: { value: "#f28a8a" },
          300: { value: "#e85c5c" },
          400: { value: "#e53e3e" },
          500: { value: "#c53030" },
          600: { value: "#9b2c2c" },
          700: { value: "#822727" },
          800: { value: "#63171b" },
          900: { value: "#4a0f13" },
          green: { value: "#129800" },
          blue: { value: "#0057B8" },
          purple: { value: "#942ee3" },
        },
      },
    },
    semanticTokens: {
      colors: {
        "bg.primary": {
          value: { base: "#e7f2f6", _dark: "rgba(20, 25, 24, 1)" },
        },
        "bg.secondary": {
          value: { base: "#ffffff", _dark: "#2f2f2f" },
        },
        "bg.thrid": {
          value: { base: "#f2f2f2", _dark: "#777676" },
        },
        "bg.fouth": {
          value: { base: "#393b47", _dark: "#ebebeb" },
        },
        "bg.input": {
          value: { base: "#fcfbfb", _dark: "rgb(159, 155, 155)" },
        },
        "bg.gradient": {
          value: {
            base: "linear-gradient(180deg,rgb(227, 247, 253) 70%, rgba(255, 255, 255, 1) 100%)",
            _dark:
              "linear-gradient(180deg,rgba(20, 25, 24, 1) 70%, rgb(31, 29, 29) 100%)",
          },
        },

        //_hover
        "hover.primary": {
          value: { base: "#611616", _dark: "#c31c1c" },
        },
        "hover.secondary": {
          value: { base: "#b3aeae", _dark: "#d2d2d2" },
        },

        // text
        "text.primary": {
          value: { base: "#000000", _dark: "#ffff" },
        },
        "text.secondary": {
          value: { base: "#d9f7fa", _dark: "rgba(20, 25, 24, 1)" },
        },
        "text.thrid": {
          value: { base: "#656363", _dark: "rgb(231, 228, 228)" },
        },
        "text.fouth": {
          value: { base: "#358a92", _dark: "#ffffff" },
        },
        "text.fifth": {
          value: { base: "#ffffff", _dark: "#000000" },
        },

        // button
        "button.primary": {
          value: { base: "#30b6d0", _dark: "#ffff" },
        },
        "button.secondary": {
          value: { base: "rgb(61, 64, 65)", _dark: "#ffff" },
        },
        "button.thirth": {
          value: { base: "#000000", _dark: "#ffff" },
        },
        "button.fouth": {
          value: { base: "#fd0a0a", _dark: "#b83a1e" },
        },
        "button.fifth": {
          value: { base: "#30b6d0", _dark: "#0d0d0d" },
        },
        "button.six": {
          value: { base: "#f2d412", _dark: "#f2c912" },
        },

        //hover
        "hover.primary": {
          value: { base: "#d0cece", _dark: "#d8d8d8" },
        },

        "border.primary": {
          value: { base: "#dedbdb", _dark: "#3b3a3a" },
        },

        //card
        "card.primary": {
          value: { base: "#e7f5fa", _dark: "rgba(20, 25, 24, 1)" },
        },

        accent: {
          value: {
            base: "{colors.brand.500}",
            _dark: "{colors.brand.300}",
          },
        },
        "accent.subtle": {
          value: {
            base: "{colors.brand.50}",
            _dark: "{colors.brand.900}",
          },
        },
      },
    },
  },
});

export const system = createSystem(defaultConfig, config);
