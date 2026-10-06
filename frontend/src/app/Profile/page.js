"use client";

import { Avatar, Button, Flex, Input, Text } from "@chakra-ui/react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PopupMini, PopupMini2 } from "../../components/Popup/popup";

export default function Profile() {
  const router = useRouter();

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
        const response = await fetch(
          `http://localhost:5000/profile/${user.user_id}`,
        );

        const data = await response.json();

        if (!response.ok) {
          showMessage(
            "Profile",
            data.message || "Gagal mengambil data profile.",
          );
          return;
        }

        setUsername(data.user.username || "");
        setEmail(data.user.email || "");
        setTelp(data.user.phoneNumber || "");

        // Simpan data terbaru ke localStorage
        localStorage.setItem("user", JSON.stringify(data.user));
      } catch (error) {
        console.error("Error:", error);

        showMessage("Profile", "Tidak dapat terhubung ke server.");
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

      showMessage("Delete Account", "Data akun tidak ditemukan.");

      return;
    }

    const user = JSON.parse(storedUser);

    try {
      const response = await fetch(
        `http://localhost:5000/profile/${user.user_id}`,
        {
          method: "DELETE",
        },
      );

      const data = await response.json();

      if (!response.ok) {
        setShowDeletePopup(false);

        showMessage("Delete Account", data.message || "Gagal menghapus akun.");

        return;
      }

      // Hapus data login dari localStorage
      localStorage.removeItem("user");
      localStorage.removeItem("isLoggedIn");

      // Beritahu component lain bahwa user sudah logout
      window.dispatchEvent(new Event("login"));

      setShowDeletePopup(false);

      showMessage("Delete Account", "Akun berhasil dihapus.", () => {
        router.push("/Login");
      });
    } catch (error) {
      console.error("Error:", error);

      setShowDeletePopup(false);

      showMessage("Delete Account", "Tidak dapat terhubung ke server.");
    }
  };

  // EDIT / SAVE PROFILE
  const handleEdit = async () => {
    // Kalau belum edit → masuk mode edit
    if (!isEditing) {
      setIsEditing(true);
      return;
    }

    const storedUser = localStorage.getItem("user");

    if (!storedUser) {
      showMessage("Profile", "Data akun tidak ditemukan.");

      return;
    }

    const user = JSON.parse(storedUser);

    // NORMALISASI DATA
    const normalizedUsername = username.trim().toLowerCase();
    const normalizedEmail = email.trim().toLowerCase();
    const normalizedTelp = telp.trim();

    // VALIDASI USERNAME
    if (!normalizedUsername) {
      showMessage("Profile", "Username wajib diisi.");

      return;
    }

    if (normalizedUsername.length < 6) {
      showMessage("Profile", "Username minimal 6 karakter.");

      return;
    }

    // VALIDASI EMAIL
    if (!normalizedEmail) {
      showMessage("Profile", "Email wajib diisi.");

      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailRegex.test(normalizedEmail)) {
      showMessage("Profile", "Format email tidak valid.");

      return;
    }

    // VALIDASI NOMOR TELEPON
    if (normalizedTelp && !/^\d+$/.test(normalizedTelp)) {
      showMessage("Profile", "Nomor telepon hanya boleh berisi angka.");

      return;
    }

    try {
      const response = await fetch(
        `http://localhost:5000/profile/${user.user_id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            username: normalizedUsername,
            email: normalizedEmail,
            phoneNumber: normalizedTelp || null,
          }),
        },
      );

      const data = await response.json();

      if (!response.ok) {
        showMessage("Profile", data.message || "Gagal memperbarui profile.");

        return;
      }

      // UPDATE LOCAL STORAGE

      localStorage.setItem("user", JSON.stringify(data.user));

      // UPDATE TAMPILAN

      setUsername(data.user.username || "");
      setEmail(data.user.email || "");
      setTelp(data.user.phoneNumber || "");

      setIsEditing(false);

      showMessage("Profile", "Profile berhasil diperbarui.");
    } catch (error) {
      console.error("Error:", error);

      showMessage("Profile", "Tidak dapat terhubung ke server.");
    }
  };

  return (
    <Flex w="100%" minH="100vh" justify="center" align="center">
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
          direction={{ base: "column", sm: "row" }}
        >
          <Flex direction="row" gap="2vh" align="center">
            <Avatar.Root w="12vh" h="12vh">
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
              <Flex w="100%" direction="column" gap="0.5vh">
                <Text fontWeight="bold" fontSize="xl">
                  {username}
                </Text>

                <Flex direction="row" gap="1vh" align="center">
                  <Text color="text.thrid" fontSize="sm" w="8vh">
                    Email
                  </Text>

                  <Text color="text.thrid" fontSize="sm">
                    :
                  </Text>

                  <Text color="text.thrid" fontSize="sm">
                    {email}
                  </Text>
                </Flex>

                <Flex direction="row" gap="1vh" align="center">
                  <Text color="text.thrid" fontSize="sm" w="8vh">
                    Telp.
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
              w={{ base: "100%", sm: "20vh" }}
              fontWeight="bold"
              bg="button.third"
              _hover={{
                bg: "hover.primary",
              }}
              onClick={() => router.push("/ChangePassword")}
              borderRadius="4vh"
            >
              Change Password
            </Button>
          </Flex>
        </Flex>

        {/* Username */}
        <Flex direction="row" align="center">
          <Text w="30vh">Username</Text>

          <Input
            color={"black "}
            bg={isEditing ? "white" : "gray.100"}
            h="4vh"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Masukkan Username..."
            _placeholder={{
              color: "text.thrid",
            }}
            readOnly={!isEditing}
          />
        </Flex>

        {/* Email */}
        <Flex direction="row" align="center">
          <Text w="30vh">Email</Text>

          <Input
            bg={isEditing ? "white" : "gray.100"}
            color={"black "}
            h="4vh"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Masukkan Email..."
            _placeholder={{
              color: "text.thrid",
            }}
            readOnly={!isEditing}
          />
        </Flex>

        {/* Telp */}
        <Flex direction="row" align="center">
          <Text w="30vh">Telp</Text>

          <Input
            color={"black "}
            bg={isEditing ? "white" : "gray.100"}
            h="4vh"
            value={isEditing ? telp : telp || "-"}
            onChange={(e) => {
              const value = e.target.value;

              if (/^\d*$/.test(value)) {
                setTelp(value);
              }
            }}
            placeholder="Masukkan Nomor Telepon..."
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
        >
          {/* Delete Account */}
          <Button
            w={{ base: "100%", sm: "20vh" }}
            fontWeight="bold"
            bg="button.fouth"
            _hover={{
              bg: "hover.primary",
            }}
            borderRadius="4vh"
            onClick={handleDeleteAccount}
          >
            Delete Account
          </Button>

          {/* Edit / Save */}
          <Button
            w={{ base: "100%", sm: "20vh" }}
            fontWeight="bold"
            bg="button.primary"
            _hover={{
              bg: "hover.primary",
            }}
            borderRadius="4vh"
            onClick={handleEdit}
          >
            {isEditing ? "Save" : "Edit"}
          </Button>
        </Flex>
      </Flex>

      {showDeletePopup && (
        <PopupMini
          title="Delete Account"
          message="Apakah Anda yakin ingin menghapus akun?"
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
