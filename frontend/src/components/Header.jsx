// components/Header.jsx
"use client";

import { Button, Flex, Text } from "@chakra-ui/react";
import { ColorModeButton } from "@/components/ui/color-mode";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { RiCloudWindyFill } from "react-icons/ri";
import { PopupMini } from "./Popup/popup";

export default function Header() {
  const router = useRouter();
  const pathname = usePathname();

  const [now, setNow] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [showLogoutPopup, setShowLogoutPopup] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [showInstallButton, setShowInstallButton] = useState(true);

  // CEK STATUS LOGIN
  useEffect(() => {
    const checkLogin = () => {
      const loggedIn = localStorage.getItem("isLoggedIn");

      setIsLoggedIn(loggedIn === "true");
    };

    checkLogin();

    // Perubahan localStorage dari tab/window lain
    window.addEventListener("storage", checkLogin);

    // Perubahan login dari halaman yang sama
    window.addEventListener("login", checkLogin);

    return () => {
      window.removeEventListener("storage", checkLogin);
      window.removeEventListener("login", checkLogin);
    };
  }, []);

  // DATE
  useEffect(() => {
    const updateDate = () => {
      setNow(new Date());
    };

    // Tunggu sampai effect selesai sebelum setState pertama
    const timeout = setTimeout(() => {
      updateDate();
    }, 0);

    // Update setiap 1 detik
    const interval = setInterval(() => {
      updateDate();
    }, 1000);

    return () => {
      clearTimeout(timeout);
      clearInterval(interval);
    };
  }, []);

  // PWA INSTALL
  useEffect(() => {
    const handleBeforeInstallPrompt = (event) => {
      event.preventDefault();

      setDeferredPrompt(event);
      setShowInstallButton(true);
    };

    window.addEventListener(
      "beforeinstallprompt",
      handleBeforeInstallPrompt,
    );

    return () => {
      window.removeEventListener(
        "beforeinstallprompt",
        handleBeforeInstallPrompt,
      );
    };
  }, []);

  // FORMAT DATE
  const formattedDateTime = now
    ? now.toLocaleDateString("en-US", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : "";

  // LOGO
  const handleLogoClick = () => {
    if (pathname === "/") {
      window.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    } else {
      router.push("/");
    }
  };

  // UPLOAD / PREDICTION
  // const handleUploadClick = () => {
  //   if (pathname === "/") {
  //     document.getElementById("uploadImage")?.scrollIntoView({
  //       behavior: "smooth",
  //     });
  //   } else {
  //     sessionStorage.setItem("scrollTarget", "uploadImage");

  //     router.push("/");
  //   }
  // };

  // LOGOUT
  const handleLogout = () => {
    setShowLogoutPopup(true);
  };

  const confirmLogout = () => {
    localStorage.removeItem("isLoggedIn");

    setIsLoggedIn(false);
    setShowLogoutPopup(false);

    router.push("/Login");
  };

  // INSTALL PWA
  const handleInstallApp = async () => {
    if (!deferredPrompt) {
      return;
    }

    deferredPrompt.prompt();

    const { outcome } = await deferredPrompt.userChoice;

    if (outcome === "accepted") {
      setShowInstallButton(false);
    }

    setDeferredPrompt(null);
  };

  return (
    <Flex
      boxShadow="0 4px 12px rgba(0, 0, 0, 0.2)"
      zIndex={10000}
      bg="bg.secondary"
      position="fixed"
      top="3vh"
      left="5%"
      w="90%"
      borderRadius="2vh"
    >
      <Flex
        w="100%"
        align="center"
        flexWrap={{
          base: "wrap",
          md: "nowrap",
        }}
        gap={{
          base: "1vh",
          md: "2vh",
        }}
        px={{
          base: "2vh",
          sm: "3vh",
          md: "3vh",
          lg: "4vh",
        }}
        py={{
          base: "2vh",
          sm: "2.5vh",
          md: "2.5vh",
          lg: "2.5vh",
        }}
      >
        <Flex
          flex="1"
          minW={{
            base: "100%",
            md: "auto",
          }}
          direction="row"
          align="center"
          justify="space-between"
          gap="2vh"
        >
          {/* LOGO */}
          <Flex
            direction="row"
            align="center"
            gap="1vh"
            cursor="pointer"
            flexShrink={0}
            onClick={handleLogoClick}
          >
            <RiCloudWindyFill size="4vh" />

            <Text
              fontWeight="bold"
              fontSize="lg"
            >
              Noxora
            </Text>
          </Flex>

          {/* DATE + COLOR MODE */}
          <Flex
            direction="row"
            align="center"
            gap={{
              base: "1vh",
              md: "2vh",
            }}
            minW={0}
          >
            <Text
              fontSize="sm"
              whiteSpace="nowrap"
              overflow="hidden"
              textOverflow="ellipsis"
            >
              {formattedDateTime}
            </Text>

            <ColorModeButton />
          </Flex>
        </Flex>

        {/* LOGIN + SIGN UP */}
        <Flex
          w={{
            base: "100%",
            md: "auto",
          }}
          justify={{
            base: "center",
            md: "end",
          }}
          direction="row"
          gap={{
            base: "1vh",
            md: "1.5vh",
          }}
          flexShrink={0}
        >
    {showInstallButton && (
      <Button
        w={{
          base: "15vh",
          sm: "16vh",
        }}
        h={{
          base: "4vh",
          sm: "4.5vh",
        }}
        _hover={{
          bg: "hover.primary",
        }}
        fontSize="sm"
        fontWeight="bold"
        bg="button.six"
        borderRadius="10vh"
        onClick={handleInstallApp}
      >
        Add to App
      </Button>
    )}

          {/* LOGIN / PROFILE */}
          {isLoggedIn ? (
            <>
              <Button
                w={{
                  base: "12vh",
                  sm: "13vh",
                }}
                h={{
                  base: "4vh",
                  sm: "4.5vh",
                }}
                _hover={{
                  bg: "hover.primary",
                }}
                fontSize="sm"
                fontWeight="bold"
                bg="button.primary"
                borderRadius="10vh"
                onClick={() => router.push("/Profile")}
              >
                Profile
              </Button>

              <Button
                w={{
                  base: "12vh",
                  sm: "13vh",
                }}
                h={{
                  base: "4vh",
                  sm: "4.5vh",
                }}
                _hover={{
                  bg: "hover.primary",
                }}
                fontSize="sm"
                fontWeight="bold"
                bg="button.thirth"
                borderRadius="10vh"
                onClick={handleLogout}
              >
                Logout
              </Button>
            </>
          ) : (
            <>
              <Button
                w={{
                  base: "12vh",
                  sm: "13vh",
                }}
                h={{
                  base: "4vh",
                  sm: "4.5vh",
                }}
                _hover={{
                  bg: "hover.primary",
                }}
                fontSize="sm"
                fontWeight="bold"
                bg="button.primary"
                borderRadius="10vh"
                onClick={() => router.push("/Login")}
              >
                Login
              </Button>

              <Button
                w={{
                  base: "12vh",
                  sm: "13vh",
                }}
                h={{
                  base: "4vh",
                  sm: "4.5vh",
                }}
                _hover={{
                  bg: "hover.primary",
                }}
                fontSize="sm"
                fontWeight="bold"
                bg="button.thirth"
                borderRadius="10vh"
                onClick={() => router.push("/Register")}
              >
                Sign up
              </Button>
            </>
          )}
        </Flex>
      </Flex>

      {showLogoutPopup && (
        <PopupMini
          title="Logout"
          message="Apakah Anda yakin ingin logout?"
          button1="Batal"
          button2="Logout"
          onClick1={() => setShowLogoutPopup(false)}
          onClick2={confirmLogout}
        />
      )}
    </Flex>
  );
}