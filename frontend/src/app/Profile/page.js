"use client";

import { Avatar, Button, Flex, Input, Text } from "@chakra-ui/react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PopupMini, PopupMini2 } from "../../components/Popup/popup";

export default function Profile() {
  const router = useRouter();
  const API_URL = process.env.NEXT_PUBLIC_API_URL;

  const [isEditing, setIsEditing] = useState(false);
  const [showDeletePopup, setShowDeletePopup] = useState(false);
  const [showMessagePopup, setShowMessagePopup] = useState(false);

  const [popupTitle, setPopupTitle] = useState("");
  const [popupMessage, setPopupMessage] = useState("");
  const [popupAction, setPopupAction] = useState(() => () => {});

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [telp, setTelp] = useState("");

  const showMessage = (title, message, action = () => {}) => {
    setPopupTitle(title);
    setPopupMessage(message);
    setPopupAction(() => action);
    setShowMessagePopup(true);
  };

  // GET PROFILE
  useEffect(() => {
    const storedUser = localStorage.getItem("user");

    if (!storedUser) {
      router.push("/Login");
      return;
    }

    const user = JSON.parse(storedUser);

    const fetchProfile = async () => {
      try {
        const response = await fetch(`${API_URL}/profile/${user.user_id}`);

        const data = await response.json();

        if (!response.ok) {
          showMessage(
            "Profile",
            data.message || "Failed to retrieve profile data.",
          );
          return;
        }

        setUsername(data.user.username || "");
        setEmail(data.user.email || "");
        setTelp(data.user.phoneNumber || "");

        // Save the latest data to localStorage
        localStorage.setItem("user", JSON.stringify(data.user));
      } catch (error) {
        console.error("Error:", error);

        showMessage("Profile", "Unable to connect to the server.");
      }
    };

    fetchProfile();
  }, [router]);

  // DELETE ACCOUNT
  const handleDeleteAccount = () => {
    setShowDeletePopup(true);
  };

  const confirmDeleteAccount = async () => {
    const storedUser = localStorage.getItem("user");

    if (!storedUser) {
      setShowDeletePopup(false);

      showMessage("Delete Account", "Account data could not be found.");

      return;
    }

    const user = JSON.parse(storedUser);

    try {
      const response = await fetch(`${API_URL}/profile/${user.user_id}`, {
        method: "DELETE",
      });

      const data = await response.json();

      if (!response.ok) {
        setShowDeletePopup(false);

        showMessage(
          "Delete Account",
          data.message || "Failed to delete the account.",
        );

        return;
      }

      // Remove login data from localStorage
      localStorage.removeItem("user");
      localStorage.removeItem("isLoggedIn");

      // Notify other components that the user has logged out
      window.dispatchEvent(new Event("login"));

      setShowDeletePopup(false);

      showMessage("Delete Account", "Account successfully deleted.", () => {
        router.push("/Login");
      });
    } catch (error) {
      console.error("Error:", error);

      setShowDeletePopup(false);

      showMessage("Delete Account", "Unable to connect to the server.");
    }
  };

  // EDIT / SAVE PROFILE
  const handleEdit = async () => {
    // If not editing, enter edit mode
    if (!isEditing) {
      setIsEditing(true);
      return;
    }

    const storedUser = localStorage.getItem("user");

    if (!storedUser) {
      showMessage("Profile", "Account data could not be found.");

      return;
    }

    const user = JSON.parse(storedUser);

    // NORMALIZE DATA
    const normalizedUsername = username.trim().toLowerCase();
    const normalizedEmail = email.trim().toLowerCase();
    const normalizedTelp = telp.trim();

    // VALIDATE USERNAME
    if (!normalizedUsername) {
      showMessage("Profile", "Username is required.");

      return;
    }

    if (normalizedUsername.length < 6) {
      showMessage("Profile", "Username must be at least 6 characters long.");

      return;
    }

    // VALIDATE EMAIL
    if (!normalizedEmail) {
      showMessage("Profile", "Email is required.");

      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailRegex.test(normalizedEmail)) {
      showMessage("Profile", "Invalid email format.");

      return;
    }

    // VALIDATE PHONE NUMBER
    if (normalizedTelp && !/^\d+$/.test(normalizedTelp)) {
      showMessage("Profile", "Phone number can only contain digits.");

      return;
    }

    try {
      const response = await fetch(`${API_URL}/profile/${user.user_id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: normalizedUsername,
          email: normalizedEmail,
          phoneNumber: normalizedTelp || null,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        showMessage("Profile", data.message || "Failed to update profile.");

        return;
      }

      // UPDATE LOCAL STORAGE
      localStorage.setItem("user", JSON.stringify(data.user));

      // UPDATE DISPLAY
      setUsername(data.user.username || "");
      setEmail(data.user.email || "");
      setTelp(data.user.phoneNumber || "");

      setIsEditing(false);

      showMessage("Profile", "Profile successfully updated.");
    } catch (error) {
      console.error("Error:", error);

      showMessage("Profile", "Unable to connect to the server.");
    }
  };

  return (
    <Flex w="100%" minH="100vh" justify="center" align="center" mt="5vh">
      <Flex
        boxShadow="0 4px 12px rgba(0, 0, 0, 0.2)"
        bg="bg.secondary"
        w={{ base: "90%", md: "60%", lg: "50%" }}
        py="3vh"
        px="4vh"
        direction="column"
        gap="2vh"
        borderRadius="2vh"
        justify="center"
      >
        {/* Header */}
        <Flex
          w="100%"
          justify="center"
          borderBottom="1px solid #dfdddd"
          pb="2vh"
          gap="1vh"
          direction={{ base: "column", lg: "row" }}
        >
          <Flex direction="row" gap="2vh" align="center">
            <Avatar.Root w="80px" h="80px">
              <Avatar.Fallback name={username} />
              <Avatar.Image src="" />
            </Avatar.Root>

            <Flex
              w="100%"
              direction="row"
              gap="0.5vh"
              justify="space-between"
              align="center"
            >
              <Flex w="100%" direction="column" gap="3px">
                <Text fontWeight="bold" fontSize="xl">
                  {username}
                </Text>
                <Flex display={{ base: "none", sm: "flex" }} gap="4px">
                  <Flex direction="row" gap="1vh" align="center">
                    <Text color="text.thrid" fontSize="sm" w="50px">
                      Email
                    </Text>

                    <Text color="text.thrid" fontSize="sm">
                      :
                    </Text>
                  </Flex>
                  <Text color="text.thrid" fontSize="sm">
                    {email}
                  </Text>
                </Flex>

                <Flex
                  display={{ base: "none", sm: "flex" }}
                  direction="row"
                  gap="1vh"
                  align="center"
                >
                  <Text color="text.thrid" fontSize="sm" w="50px">
                    Phone
                  </Text>

                  <Text color="text.thrid" fontSize="sm">
                    :
                  </Text>

                  <Text color="text.thrid" fontSize="sm">
                    {telp || "-"}
                  </Text>
                </Flex>
              </Flex>
            </Flex>
          </Flex>

          <Flex
            w="100%"
            direction="column"
            gap="0.5vh"
            justify="center"
            align="end"
          >
            <Button
              h={"35px"}
              w={{ base: "100%", lg: "140px" }}
              fontWeight="bold"
              bg="button.third"
              _hover={{
                bg: "hover.primary",
              }}
              onClick={() => router.push("/ChangePassword")}
              borderRadius="full"
            >
              Change Password
            </Button>
          </Flex>
        </Flex>

        {/* Username */}
        <Flex direction="row" align="center">
          <Text w="170px">Username</Text>

          <Input
            color={"black "}
            bg={isEditing ? "white" : "gray.100"}
            h="24px"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter username..."
            _placeholder={{
              color: "text.thrid",
            }}
            readOnly={!isEditing}
          />
        </Flex>

        {/* Email */}
        <Flex direction="row" align="center">
          <Text w="170px">Email</Text>

          <Input
            bg={isEditing ? "white" : "gray.100"}
            color={"black "}
            h="24px"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter email..."
            _placeholder={{
              color: "text.thrid",
            }}
            readOnly={!isEditing}
          />
        </Flex>

        {/* Phone */}
        <Flex direction="row" align="center">
          <Text w="170px">Phone</Text>

          <Input
            color={"black "}
            bg={isEditing ? "white" : "gray.100"}
            h="24px"
            value={isEditing ? telp : telp || "-"}
            onChange={(e) => {
              const value = e.target.value;

              if (/^\d*$/.test(value)) {
                setTelp(value);
              }
            }}
            placeholder="Enter phone number..."
            _placeholder={{
              color: "text.thrid",
            }}
            readOnly={!isEditing}
          />
        </Flex>

        {/* Buttons */}
        <Flex
          w="100%"
          justify="center"
          direction={{ base: "column", sm: "row" }}
          gap="2vh"
          align="center"
        >
          {/* Delete Account */}
          <Button
            w={"130px"}
            h={"32px"}
            fontWeight="bold"
            bg="button.fouth"
            _hover={{
              bg: "hover.primary",
            }}
            borderRadius="full"
            onClick={handleDeleteAccount}
          >
            Delete Account
          </Button>

          {/* Edit / Save */}
          <Button
            w={"130px"}
            h={"32px"}
            fontWeight="bold"
            bg="button.primary"
            _hover={{
              bg: "hover.primary",
            }}
            borderRadius="full"
            onClick={handleEdit}
          >
            {isEditing ? "Save" : "Edit"}
          </Button>
        </Flex>
      </Flex>

      {showDeletePopup && (
        <PopupMini
          title="Delete Account"
          message="Are you sure you want to delete your account?"
          onClick1={() => setShowDeletePopup(false)}
          onClick2={confirmDeleteAccount}
          button1="Cancel"
          button2="Delete"
        />
      )}

      {showMessagePopup && (
        <PopupMini2
          title={popupTitle}
          message={popupMessage}
          button1="OK"
          onClick1={() => {
            setShowMessagePopup(false);
            popupAction();
          }}
        />
      )}
    </Flex>
  );
}
