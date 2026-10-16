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

  // CHECK LOGIN STATUS
  useEffect(() => {
    const checkLogin = () => {
      const loggedIn = localStorage.getItem("isLoggedIn");

      setIsLoggedIn(loggedIn === "true");
    };

    checkLogin();

    // Listen for localStorage changes from other tabs/windows
    window.addEventListener("storage", checkLogin);

    // Listen for login changes on the same page
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

    // Wait until the effect finishes before the first setState
    const timeout = setTimeout(() => {
      updateDate();
    }, 0);

    // Update every second
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
        px="20px"
        py={{
          base: "13px",
          sm: "13px",
          md: "17px",
          lg: "17px",
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
            gap="8px"
            cursor="pointer"
            flexShrink={0}
            onClick={handleLogoClick}
          >
            <RiCloudWindyFill size="25px" />

            <Text fontWeight="bold" fontSize="lg">
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
                base: "100px",
                sm: "100px",
              }}
              h={{
                base: "32px",
                sm: "32px",
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
                  base: "100px",
                  sm: "100px",
                }}
                h={{
                  base: "32px",
                  sm: "32px",
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
                  base: "100px",
                  sm: "100px",
                }}
                h={{
                  base: "32px",
                  sm: "32px",
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
                  base: "100px",
                  sm: "100px",
                }}
                h={{
                  base: "32px",
                  sm: "32px",
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
                  base: "100px",
                  sm: "100px",
                }}
                h={{
                  base: "32px",
                  sm: "32px",
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
          message="Are you sure you want to log out?"
          button1="Cancel"
          button2="Logout"
          onClick1={() => setShowLogoutPopup(false)}
          onClick2={confirmLogout}
        />
      )}
    </Flex>
  );
}