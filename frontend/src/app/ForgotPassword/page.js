"use client";

import { Button, Flex, Input, Text } from "@chakra-ui/react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { PopupMini2 } from "../../components/Popup/popup";

export default function ForgotPassword() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [showPopup, setShowPopup] = useState(false);
  const [popupTitle, setPopupTitle] = useState("");
  const [popupMessage, setPopupMessage] = useState("");

  const showMessage = (title, message) => {
    setPopupTitle(title);
    setPopupMessage(message);
    setShowPopup(true);
  };

  const handleForgotPassword = async () => {
    // Cek email
    if (!email) {
      showMessage("Forgot Password", "Silakan masukkan email Anda.");
      return;
    }

    // Cek format email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailRegex.test(email)) {
      showMessage("Forgot Password", "Format email tidak valid.");
      return;
    }

    try {
      const response = await fetch("http://localhost:5000/forgot-password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        showMessage(
          "Forgot Password",
          data.message || "Gagal mengirim reset password.",
        );
        return;
      }

      // Tampilkan popup
      showMessage(
        "Email Terkirim",
        "Silakan cek email Anda untuk mendapatkan link reset password.",
      );
    } catch (error) {
      console.error("Error:", error);

      showMessage("Forgot Password", "Tidak dapat terhubung ke server.");
    }
  };

  return (
    <Flex w="100%" minH="100vh" justify="center" align="center">
      <Flex
        boxShadow="0 4px 12px rgba(0, 0, 0, 0.2)"
        bg="bg.secondary"
        w={{ base: "90%", md: "55%", lg: "45%", xl: "30%" }}
        py="3vh"
        px="4vh"
        direction="column"
        gap="2vh"
        borderRadius="2vh"
        justify="center"
      >
        {/* Header */}
        <Flex
          borderBottom="1px solid #d6d1d1"
          pb="0.5vh"
          align="center"
          justify="center"
        >
          <Text fontWeight="bold" fontSize="xl">
            Forgot Password
          </Text>
        </Flex>

        {/* Form */}
        <Flex direction="column" gap="1.5vh">
          <Flex
            direction={{ base: "column", sm: "row" }}
            align={{ base: "stretch", sm: "center" }}
            gap={{ base: "0.5vh", sm: "2vh" }}
          >
            <Text w={{ base: "100%", sm: "25%" }}>Email</Text>

            <Input
              w={{ base: "100%", sm: "75%" }}
              h="4vh"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Masukkan Email Anda..."
              bg={"bg.input"}
              color={"blackAlpha.800"}
              _placeholder={{ color: "#5f5d5d" }}
            />
          </Flex>

          {/* Button */}
          <Flex
            w="100%"
            justify="center"
            align="center"
            direction="column"
            gap="1vh"
            mt="1vh"
          >
            <Button
              w="30vh"
              fontWeight="bold"
              bg="button.primary"
              _hover={{
                bg: "hover.primary",
              }}
              borderRadius="4vh"
              onClick={handleForgotPassword}
            >
              Send Email
            </Button>
          </Flex>
        </Flex>
      </Flex>

      {/* POPUP */}
      {showPopup && (
        <PopupMini2
          title={popupTitle}
          message={popupMessage}
          button1="OK"
          onClick1={() => {
            setShowPopup(false);

            if (popupTitle === "Email Terkirim") {
              router.push("/Login");
            }
          }}
        />
      )}
    </Flex>
  );
}
