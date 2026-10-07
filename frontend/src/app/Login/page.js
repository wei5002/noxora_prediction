"use client";

import { Button, Flex, Input, Text } from "@chakra-ui/react";
import { PasswordInput } from "@/components/ui/password-input";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { PopupMini2 } from "../../components/Popup/popup";

export default function Login() {
  const router = useRouter();

  const API_URL =
    process.env.NEXT_PUBLIC_API_URL || "https://noxora-backend.vercel.app";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showLoginPopup, setShowLoginPopup] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) {
      alert("Email dan password wajib diisi.");
      return;
    }

    try {
      const response = await fetch(`${API_URL}/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        alert(data.message || "Login gagal.");
        return;
      }

      localStorage.setItem("user", JSON.stringify(data.user));
      localStorage.setItem("isLoggedIn", "true");

      window.dispatchEvent(new Event("login"));

      setShowLoginPopup(true);
    } catch (error) {
      console.error("Error:", error);
      alert("Tidak dapat terhubung ke server.");
    }
  };

  return (
    <Flex w="100%" minH="100vh" justify="center" align="center">
      <Flex
        boxShadow="0 4px 12px rgba(0, 0, 0, 0.2)"
        bg={"bg.secondary"}
        w={{ base: "90%", md: "55%", lg: "45%", xl: "35%" }}
        py={"3vh"}
        px={"4vh"}
        direction={"column"}
        gap={"2vh"}
        borderRadius={"2vh"}
        justify={"center"}
      >
        <Flex
          w={"100%"}
          justify={"center"}
          borderBottom={"1px solid #dfdddd"}
          pb={"0.5vh"}
        >
          <Text fontWeight={"bold"} fontSize={"xl"}>
            Login
          </Text>
        </Flex>

        <Flex
          direction={{ base: "column", sm: "row" }}
          align={"center"}
          justify={"space-between"}
        >
          <Text w={{ base: "100%", sm: "30vh" }}>Email</Text>

          <Input
            bg={"bg.input"}
            color={"blackAlpha.800"}
            _placeholder={{ color: "#5f5d5d" }}
            h={"4vh"}
            w={"100%"}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={"Masukkan Email..."}
          />
        </Flex>

        <Flex
          direction={{ base: "column", sm: "row" }}
          align="center"
          justify="space-between"
        >
          <Text w={{ base: "100%", sm: "29vh" }}>Password</Text>

          <PasswordInput
            h="4vh"
            w={"100%"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Masukkan Password..."
            bg={"bg.input"}
            color={"blackAlpha.800"}
            _placeholder={{ color: "#5f5d5d" }}
          />
        </Flex>

        <Flex w="100%" justify="flex-end" mt="-1vh">
          <Text
            fontSize="xs"
            color="text.fouth"
            cursor="pointer"
            _hover={{
              textDecoration: "underline",
            }}
            onClick={() => router.push("/ForgotPassword")}
          >
            Forgot Password?
          </Text>
        </Flex>

        <Flex
          w={"100%"}
          justify={"center"}
          align={"center"}
          direction={"column"}
          gap={"1vh"}
        >
          <Button
            w={"30vh"}
            fontWeight={"bold"}
            bg={"button.primary"}
            _hover={{
              bg: "hover.primary",
            }}
            borderRadius={"4vh"}
            onClick={handleLogin}
          >
            Login
          </Button>

          <Flex direction="row" gap={"1"}>
            <Text fontSize={"xs"} color={"text.thrid"}>
              Don&apos;t have an account?
            </Text>

            <Text
              fontSize="xs"
              color="text.fouth"
              cursor="pointer"
              _hover={{
                textDecoration: "underline",
              }}
              onClick={() => router.push("/Register")}
            >
              Sign up
            </Text>
          </Flex>
        </Flex>
      </Flex>

      {showLoginPopup && (
        <PopupMini2
          title="Login Berhasil"
          message="Login berhasil! Selamat datang di Noxora."
          button1="OK"
          onClick1={() => {
            setShowLoginPopup(false);
            router.push("/");
          }}
        />
      )}
    </Flex>
  );
}
