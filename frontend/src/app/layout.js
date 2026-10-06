import "./globals.css";
import { Flex } from "@chakra-ui/react";
import { Provider } from "@/components/ui/provider";
import { Toaster } from "@/components/ui/toaster";
import Header from "../components/Header";

export const metadata = {
  title: "Noxora",
  description: "Noxora Page",
  manifest: "/manifest.json",
};

export default function RootLayout({ children }) {
  return (
    <html lang="id" suppressHydrationWarning>
      <body>
        <Provider>
          <Flex
            direction="column"
            w="100%"
            minH="100vh"
            align="center"
            bg="bg.primary"
          >
            <Header />

            {children}
          </Flex>

          <Toaster />
        </Provider>
      </body>
    </html>
  );
}
