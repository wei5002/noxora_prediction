import { Button, Flex, Text } from "@chakra-ui/react";

export const PopupMini = ({
  title,
  message,
  onClick1,
  onClick2,
  button1,
    button2,
}) => {
  return (
    <Flex
      position="fixed"
      top="0"
      left="0"
      w="100vw"
      h="100vh"
      bg="blackAlpha.600"
      zIndex={20000}
      align="center"
      justify="center"
      px="1vh"
    >
      <Flex
        direction="column"
        bg="bg.secondary"
        w={{
          base: "85%",
          sm: "55vh",
        }}
        borderRadius="2vh"
        p="3vh"
        gap="2vh"
        boxShadow="0 8px 30px rgba(0, 0, 0, 0.3)"
        
      >
        <Flex 
        w="100%" 
        p={"0.25vh"} 
        borderBottom={"1px solid #dfdddd"} 
        justify="center">

        <Text
          fontSize="xl"
          fontWeight="bold"
          textAlign="center"
          >
          {title}
        </Text>
            </Flex>

        <Text
          fontSize="sm"
          textAlign="center"
          color="text.thrid"
        >
          {message}
        </Text>

        <Flex
          justify="center"
          gap="1.5vh"
          mt="1vh"
        >
          <Button
            w="12vh"
            borderRadius="10vh"
            bg="gray.200"
            color="black"
            _hover={{
              bg: "gray.300",
            }}
            onClick={onClick1}
          >
            {button1 || "Cancel"}
          </Button>

          <Button
            w="12vh"
            borderRadius="10vh"
            bg="button.thirth"
            _hover={{
              bg: "hover.primary",
            }}
            onClick={onClick2}
          >
            {button2 || "Confirm"}
          </Button>
        </Flex>
      </Flex>
    </Flex>
  );
};

export const PopupMini2 = ({
  title,
  message,
  onClick1,
  button1,
}) => {
  return (
    <Flex
      position="fixed"
      top="0"
      left="0"
      w="100vw"
      h="100vh"
      bg="blackAlpha.600"
      zIndex={20000}
      align="center"
      justify="center"
      px="1vh"
    >
      <Flex
        direction="column"
        bg="bg.secondary"
        w={{
          base: "85%",
          sm: "55vh",
        }}
        borderRadius="2vh"
        p="3vh"
        gap="2vh"
        boxShadow="0 8px 30px rgba(0, 0, 0, 0.3)"
        
      >
        <Flex 
        w="100%" 
        p={"0.25vh"} 
        borderBottom={"1px solid #dfdddd"} 
        justify="center">

        <Text
          fontSize="xl"
          fontWeight="bold"
          textAlign="center"
          >
          {title}
        </Text>
            </Flex>

        <Text
          fontSize="sm"
          textAlign="center"
          color="text.thrid"
        >
          {message}
        </Text>

        <Flex
          justify="center"
          gap="1.5vh"
          mt="1vh"
        >
          <Button
            w="12vh"
            borderRadius="10vh"
            bg="button.thirth"
            color="text.fifth"
            _hover={{
              bg: "hover.primary",
            }}
            onClick={onClick1}
          >
            {button1 || "Cancel"}
          </Button>

      
        </Flex>
      </Flex>
    </Flex>
  );
};