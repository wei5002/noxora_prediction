"use client";

import { Button, Flex, Text } from "@chakra-ui/react";
import { PasswordInput } from "@/components/ui/password-input";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { PopupMini2 } from "../../components/Popup/popup";

export default function ChangePassword() {
  const router = useRouter();
  const API_URL = process.env.NEXT_PUBLIC_API_URL;

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPopup, setShowPopup] = useState(false);
  const [popupTitle, setPopupTitle] = useState("");
  const [popupMessage, setPopupMessage] = useState("");
  const [popupButton1, setPopupButton1] = useState("OK");
  const [popupButton2, setPopupButton2] = useState("");
  const [popupAction, setPopupAction] = useState(() => () => {});

  const showMessage = (title, message, action = () => {}) => {
    setPopupTitle(title);
    setPopupMessage(message);
    setPopupButton1("OK");
    setPopupButton2("");
    setPopupAction(() => action);
    setShowPopup(true);
  };

  const handleChangePassword = async () => {
    const params = new URLSearchParams(window.location.search);
    const resetToken = params.get("token");

    if (!newPassword) {
      showMessage("Change Password", "Password baru harus diisi.");
      return;
    }

    if (newPassword.length < 8) {
      showMessage("Change Password", "Password baru minimal 8 karakter.");
      return;
    }

    if (!confirmPassword) {
      showMessage("Change Password", "Confirm new password harus diisi.");
      return;
    }

    if (newPassword !== confirmPassword) {
      showMessage("Change Password", "Confirm new password tidak sama.");
      return;
    }

    try {
      let response;

      // RESET PASSWORD DARI EMAIL
      if (resetToken) {
        response = await fetch(`${API_URL}/reset-password`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            token: resetToken,
            newPassword,
            confirmPassword,
          }),
        });
      }

      // CHANGE PASSWORD DARI PROFILE
      else {
        const storedUser = localStorage.getItem("user");

        if (!storedUser) {
          showMessage(
            "Change Password",
            "Akun tidak ditemukan. Silakan login terlebih dahulu.",
            () => {
              router.push("/Login");
            },
          );

          return;
        }

        const user = JSON.parse(storedUser);

        response = await fetch(`${API_URL}/change-password/${user.user_id}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            newPassword,
            confirmPassword,
          }),
        });
      }

      const data = await response.json();

      if (!response.ok) {
        showMessage(
          "Change Password",
          data.message || "Gagal mengubah password.",
        );
        return;
      }

      showMessage("Change Password", "Password berhasil diubah.", () => {
        router.push("/Login");
      });
    } catch (error) {
      console.error("Change Password Error:", error);

      showMessage("Change Password", "Tidak dapat terhubung ke server.");
    }
  };

  return (
    <Flex w="100%" minH="100vh" justify="center" align="center">
      <Flex
        boxShadow="0 4px 12px rgba(0, 0, 0, 0.2)"
        bg="bg.secondary"
        w={{
          base: "90%",
          md: "55%",
          lg: "45%",
          xl: "40%",
        }}
        py="3vh"
        px="4vh"
        direction="column"
        gap="2vh"
        borderRadius="2vh"
        justify="center"
      >
        <Flex
          borderBottom="1px solid #d6d1d1"
          pb="0.5vh"
          align="center"
          justify="center"
        >
          <Text fontWeight="bold" fontSize="xl">
            Change Password
          </Text>
        </Flex>

        <Flex direction="column" gap="1.5vh">
          <Flex
            direction={{
              base: "column",
              sm: "row",
            }}
            align="center"
          >
            <Text w="100%">New Password</Text>

            <PasswordInput
              h="4vh"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Masukkan password baru..."
              bg="bg.input"
              color="blackAlpha.800"
              _placeholder={{
                color: "#5f5d5d",
              }}
            />
          </Flex>

          <Flex
            direction={{
              base: "column",
              sm: "row",
            }}
            align="center"
          >
            <Text w="100%">Confirm New Password</Text>

            <PasswordInput
              h="4vh"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Konfirmasi password baru..."
              bg="bg.input"
              color="blackAlpha.800"
              _placeholder={{
                color: "#5f5d5d",
              }}
            />
          </Flex>

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
              onClick={handleChangePassword}
            >
              Save Password
            </Button>
          </Flex>
        </Flex>
      </Flex>

      {showPopup && (
        <PopupMini2
          title={popupTitle}
          message={popupMessage}
          button1={popupButton1}
          button2={popupButton2}
          onClick1={() => {
            setShowPopup(false);
            popupAction();
          }}
          onClick2={() => {
            setShowPopup(false);
          }}
        />
      )}
    </Flex>
  );
}
