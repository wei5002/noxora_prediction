"use client";

import {
  Combobox,
  Portal,
  useFilter,
  useListCollection,
} from "@chakra-ui/react";

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
}) => {
  const { contains } = useFilter({
    sensitivity: "base",
  });

  const { collection, filter, reset } = useListCollection({
    initialItems: LOCATION_OPTIONS,
    filter: contains,
  });

  const handleInputChange = (details) => {
    filter(details.inputValue);
  };

  const handleValueChange = (details) => {
    const selectedValue = details.value[0] ?? "";

    reset();
    onValueChange?.(selectedValue);
  };

  const selectedItem = LOCATION_OPTIONS.find(
    (item) => item.value === String(value),
  );

  return (
    <Combobox.Root
      collection={collection}
      value={value ? [String(value)] : []}
      selectionBehavior="replace"
      onValueChange={handleValueChange}
      onInputValueChange={handleInputChange}
      minH="1vh"
    >
      <Combobox.Control minH="2vh">
        <Combobox.Input
          bg="whiteAlpha.900"
          color="blackAlpha.800"
           _placeholder={{
            color: "blackAlpha.800",
            opacity: 1,
          }}
          minH="4vh"
          placeholder={selectedItem?.label ?? placeholder}
        />

        <Combobox.IndicatorGroup minH="2vh" color="grey">
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