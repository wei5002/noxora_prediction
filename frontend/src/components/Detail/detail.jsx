import {
  Badge,
  Flex,
  HStack,
  Input,
  InputGroup,
  Stat,
  Text,
} from "@chakra-ui/react";
import { BiSolidBuildingHouse } from "react-icons/bi";
import { FaLocationDot } from "react-icons/fa6";

export const DetailCard = ({ icon, title, keterangan, hasil, satuan }) => {
  return (
    <Flex
      w={"35vh"}
      bg={"card.primary"}
      borderRadius={"1vh"}
      p={"1.5vh"}
      gap={"1.5vh"}
      direction={"column"}>
      <Flex
        w={"100%"}
        align={"center"}
        justify={"center"}
        gap={"1vh"}
        direction={"row"}>
        {icon}
        <Flex
          w={"100%"}
          // align={"center"}
          justify={"center"}
          direction={"column"}>
          <Text fontSize={"2.25vh"} fontWeight={"bold"}>
            {title}
          </Text>
          <Text fontSize={"1.5vh"} color={"text.thrid"}>
            {keterangan}
          </Text>
        </Flex>
      </Flex>
      <Flex gap={"1.5vh"} w={"100%"} align={"center"} justify={"center"}>
        <Text fontWeight={"bold"} fontSize={"4xl"}>
          {hasil}
        </Text>
        <Text fontSize={"2vh"}>{satuan}</Text>
      </Flex>
    </Flex>
  );
};

export const DetailCard2 = ({  title, keterangan, hasil, satuan }) => {
  return (
    <Flex
      w={"100%"}
      bg={"card.primary"}
      borderRadius={"1vh"}
      p={"1.5vh"}
      gap={"1.5vh"}
      direction={"column"}>
      <Flex
        w={"100%"}
        align={"center"}
        justify={"center"}
        gap={"1vh"}
        direction={"row"}>
        <BiSolidBuildingHouse size={"5vh"} color="#89c6f5" />
        <Flex
          w={"100%"}
          // align={"center"}
          justify={"center"}
          direction={"column"}>
          <Text fontSize={"2.25vh"} fontWeight={"bold"}>
            {title}
          </Text>
          <Text fontSize={"1.5vh"} color={"text.thrid"}>
            {keterangan}
          </Text>
        </Flex>
      </Flex>
      <Flex gap={"1.5vh"} w={"100%"} align={"center"} justify={"center"}>
        <Text fontWeight={"bold"} fontSize={"2xl"}>
          {hasil}
        </Text>
        <Text fontSize={"2vh"}>{satuan}</Text>
      </Flex>
    </Flex>
  );
};

export const MiniCard = ({  title, hasil }) => {
  return (
    <Flex
      w={"100%"}
      p={"2.5vh"}
      borderRadius={"2vh"}
      bg={"bg.secondary"}
      // h={"fit-content"}
      direction={"column"}
      boxShadow="0 4px 12px rgba(0, 0, 0, 0.2)">
      <Text fontSize={"xs"} color={"text.thrid"}>
        {title}
      </Text>
      <Text fontWeight={"bold"}>{hasil}</Text>
    </Flex>
  );
};

export const MiniCardLocation = ({
  location,
  hasil,
  lag2,
  onSelect,
}) => {
  const currentValue = Number(hasil);
  const lastHourValue = Number(lag2);

  const isIncreasing =
    !isNaN(currentValue) &&
    !isNaN(lastHourValue) &&
    currentValue > lastHourValue;

  const isDecreasing =
    !isNaN(currentValue) &&
    !isNaN(lastHourValue) &&
    currentValue < lastHourValue;

  return (
    <Flex
      w={"50%"}
      minH={"18vh"}
      py={"2vh"}
      px={"2.5vh"}
      borderRadius={"2vh"}
      direction={"column"}
      justify={"space-between"}
      bg={"bg.secondary"}
      gap={"0.5vh"}
      boxShadow="0 4px 12px rgba(0, 0, 0, 0.2)"
    >
      <Flex
        direction={"row"}
        align={"center"}
        gap={"0.5vh"}
        mb={"0.5vh"}
      >
        <FaLocationDot size={"1.75vh"} />

        <Text fontSize={"1.85vh"}>
          {location}
        </Text>
      </Flex>

      <Flex
        justify={"center"}
        align={"center"}
        flex={"1"}
      >
        <Stat.Root gap={"1vh"} w={"100%"}>
          <HStack justify="center">
            <Stat.ValueText>
              {hasil}{" "}
              <Text fontSize={"sm"}>
                μg/m³
              </Text>
            </Stat.ValueText>
          </HStack>

          <Flex
            justify={"space-between"}
            align={"center"}
            minH={"3vh"}
          >
            <Stat.HelpText>
              Last Hour
            </Stat.HelpText>

            <Badge
              bg="transparent"
              color={
                isIncreasing
                  ? "red.500"
                  : isDecreasing
                  ? "green.500"
                  : "gray.500"
              }
              gap="0"
            >
              {isIncreasing && (
                <Stat.UpIndicator color="red.500" />
              )}

              {isDecreasing && (
                <Stat.DownIndicator color="green.500" />
              )}

              {lag2 !== "-" && lag2 != null
                ? Number(lag2).toFixed(2)
                : "-"}
            </Badge>
          </Flex>
        </Stat.Root>
      </Flex>

      <Flex
        borderTop={"1px solid #eae9e9"}
        pt={"0.75vh"}
        minH={"3vh"}
        direction={"row"}
        justify={"space-between"}
        align={"center"}
        cursor={"pointer"}
        onClick={onSelect}
      >
        <Text
          fontSize={"xs"}
          color={"text.thrid"}
        >
          See More
        </Text>

        <Text
          fontSize={"xs"}
          color={"text.thrid"}
        >
          {">"}
        </Text>
      </Flex>
    </Flex>
  );
};

export const InputPrediction = ({
  title,
  placeholder,
  value,
  onchange,
  satuan,
}) => {
  return (
    <Flex direction={"column"} w={"100%"}>
      <Text w={"100%"} fontSize={"sm"} fontWeight={"bold"}>
        {title}
      </Text>
      <InputGroup endAddon={satuan}>
        <Input
          readOnly
          bg={"whiteAlpha.900"}
          color={"blackAlpha.800"}
          h={"4vh"}
          value={value ?? ""}
          onChange={onchange}
          placeholder={placeholder}
          _placeholder={{ color: "#7d7b7b" }}
        />
      </InputGroup>
    </Flex>
  );
};