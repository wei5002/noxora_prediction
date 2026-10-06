import { Button, FileUpload, Icon, Text } from "@chakra-ui/react";
import { FaRegImage } from "react-icons/fa";

export const UploadImage = ({ onFileChange }) => {
  return (
    <FileUpload.Root
      accept={["image/png"]}
      borderRadius={"1vh"}
      onFileChange={(details) => {
        const file = details.acceptedFiles[0];
        if (file) {
          onFileChange(file);
        }
      }}>
      <FileUpload.HiddenInput />
      <FileUpload.Trigger asChild>
        <Button size="sm" w={"full"} bg={"bg.fouth"} _hover={{ bg: "#b4b2b2" }}>
          <Icon as={FaRegImage} color={"text.fifth"} />
          <Text fontSize={"sm"} color={"text.fifth"}>
            Use your image
          </Text>
        </Button>
      </FileUpload.Trigger>
      {/* <FileUpload.List /> */}
    </FileUpload.Root>
  );
};
