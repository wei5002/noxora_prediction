"use client";

import {
  Combobox,
  Portal,
  useFilter,
  useListCollection,
} from "@chakra-ui/react";

import { useState } from "react";

export const LOCATION_OPTIONS = [
  { label: "Jakarta Timur", value: "1" },
  { label: "Kepulauan Seribu", value: "2" },
  { label: "Bekasi", value: "3" },
  { label: "Bogor", value: "4" },
  { label: "Sukabumi", value: "5" },
  { label: "Tangerang", value: "6" },
  { label: "Banten Utara", value: "7" },
  { label: "Bekasi Timur", value: "8" },
  { label: "Karawang", value: "9" },
  { label: "Purwakarta", value: "10" },
];

export const ComboBoxDashboard = ({
  value,
  onValueChange,
  placeholder = "Search Location...",
  ...props
}) => {
  const { contains } = useFilter({
    sensitivity: "base",
  });

  const { collection, filter, reset } = useListCollection({
    initialItems: LOCATION_OPTIONS,
    filter: contains,
  });

  const selectedItem = LOCATION_OPTIONS.find(
    (item) => item.value === String(value ?? ""),
  );

  const [inputValue, setInputValue] = useState(
    selectedItem?.label ?? "",
  );

  const handleInputChange = (details) => {
    setInputValue(details.inputValue);
    filter(details.inputValue);
  };

  const handleValueChange = (details) => {
    const selectedValue = details.value[0] ?? "";

    const selected = LOCATION_OPTIONS.find(
      (item) => item.value === selectedValue,
    );

    setInputValue(selected?.label ?? "");
    reset();

    onValueChange?.(selectedValue);
  };

  return (
    <Combobox.Root
      collection={collection}
      value={value ? [String(value)] : []}
      inputValue={inputValue}
      selectionBehavior="replace"
      onValueChange={handleValueChange}
      onInputValueChange={handleInputChange}
      minH="1vh"
      {...props}
    >
      <Combobox.Control minH="24px">
        <Combobox.Input
          bg="whiteAlpha.900"
          color="blackAlpha.800"
          _placeholder={{
            color: "blackAlpha.800",
            opacity: 1,
          }}
          minH="24px"
          placeholder={placeholder}
        />

        <Combobox.IndicatorGroup minH="24px" color="grey">
          <Combobox.ClearTrigger />
          <Combobox.Trigger />
        </Combobox.IndicatorGroup>
      </Combobox.Control>

      <Portal>
        <Combobox.Positioner color="black">
          <Combobox.Content bg="#f0eded">
            <Combobox.Empty>
              No items found
            </Combobox.Empty>

            {collection.items.map((item) => (
              <Combobox.Item
                key={item.value}
                item={item}
                _highlighted={{
                  bg: "button.fifth",
                  color: "white",
                }}
              >
                {item.label}
                <Combobox.ItemIndicator />
              </Combobox.Item>
            ))}
          </Combobox.Content>
        </Combobox.Positioner>
      </Portal>
    </Combobox.Root>
  );
};