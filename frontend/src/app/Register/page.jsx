"use client";

import { Button, Flex, Input, Text } from "@chakra-ui/react";
import { PasswordInput } from "@/components/ui/password-input";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { PopupMini, PopupMini2 } from "../../components/Popup/popup";

export default function Register() {
  const router = useRouter();
  const API_URL = process.env.NEXT_PUBLIC_API_URL;

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [showPopup, setShowPopup] = useState(false);
  const [popupTitle, setPopupTitle] = useState("");
  const [popupMessage, setPopupMessage] = useState("");
  const [popupAction, setPopupAction] = useState(() => () => {});

  const showMessage = (title, message, action = () => {}) => {
    setPopupTitle(title);
    setPopupMessage(message);
    setPopupAction(() => action);
    setShowPopup(true);
  };

  const handleSignUp = async () => {
    if (!username || !email || !password || !confirmPassword) {
      showMessage("Sign Up", "All fields are required.");
      return;
    }

    if (password !== confirmPassword) {
      showMessage(
        "Sign Up",
        "Password and Confirm Password do not match.",
      );
      return;
    }

    if (password !== confirmPassword) {
      showMessage(
        "Sign Up Successful!",
        "Your account has been created successfully. Please log in to continue.",
        () => {
          router.replace("/Login");
        },
      );
      return;
    }

    try {
      const response = await fetch(`${API_URL}/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username,
          email,
          password,
          confirmPassword,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        showMessage(
          "Sign Up",
          data.message || "Registration failed.",
        );
        return;
      }

      showMessage(
        "Sign Up Successful",
        "Your account has been created successfully. Please log in to continue.",
        () => {
          router.push("/Login");
        },
      );
    } catch (error) {
      console.error("Error:", error);

      showMessage(
        "Sign Up",
        "Unable to connect to the server.",
      );
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
            Signup
          </Text>
        </Flex>

        {/* Username */}
        <Flex direction={{ base: "column", sm: "row" }} align={"center"}>
          <Text w={{ base: "100%", sm: "30vh" }}>Username</Text>

          <Input
            h="26px"
            w={"100%"}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder={"Enter username..."}
            bg={"bg.input"}
            color={"blackAlpha.800"}
            _placeholder={{ color: "#5f5d5d" }}
          />
        </Flex>

        {/* Email */}
        <Flex direction={{ base: "column", sm: "row" }} align={"center"}>
          <Text w={{ base: "100%", sm: "30vh" }}>Email</Text>

          <Input
            h="26px"
            w={"100%"}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={"Enter email..."}
            bg={"bg.input"}
            color={"blackAlpha.800"}
            _placeholder={{ color: "#5f5d5d" }}
          />
        </Flex>

        {/* Password */}
        <Flex direction={{ base: "column", sm: "row" }} align={"center"}>
          <Text w={{ base: "100%", sm: "29vh" }}>Password</Text>

          <PasswordInput
            h="26px"
            w={"100%"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={"Enter password..."}
            bg={"bg.input"}
            color={"blackAlpha.800"}
            _placeholder={{ color: "#5f5d5d" }}
          />
        </Flex>

        {/* Confirm Password */}
        <Flex direction={{ base: "column", sm: "row" }} align={"center"}>
          <Text w={{ base: "100%", sm: "29vh" }}>
            Confirm Password
          </Text>

          <PasswordInput
            h="26px"
            w={"100%"}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder={"Re-enter password..."}
            bg={"bg.input"}
            color={"blackAlpha.800"}
            _placeholder={{ color: "#5f5d5d" }}
          />
        </Flex>

        {/* Button */}
        <Flex mt={"1vh"} w={"100%"} justify={"center"}>
          <Button
            w={"100px"}
            h={"32px"}
            fontWeight={"bold"}
            bg={"button.primary"}
            _hover={{ bg: "hover.primary" }}
            borderRadius={"4vh"}
            onClick={handleSignUp}
          >
            Sign Up
          </Button>
        </Flex>
      </Flex>

      {showPopup && (
        <PopupMini2
          title={popupTitle}
          message={popupMessage}
          button1="OK"
          onClick1={() => {
            setShowPopup(false);
            popupAction();
          }}
        />
      )}
    </Flex>
  );
}