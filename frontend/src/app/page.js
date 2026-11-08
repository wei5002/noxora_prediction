"use client";

import { Flex, Grid, Text } from "@chakra-ui/react";

import { useEffect, useMemo, useState } from "react";

import { FaCloudSun, FaLocationDot } from "react-icons/fa6";

import { MiniCard, MiniCardLocation } from "../components/Detail/detail";

import { ComboBoxDashboard } from "../components/ComboBox/comboBox";

import PredictionChart from "../components/Grafik/grafik";

import { RiCloudWindyFill } from "react-icons/ri";

// Dipindah ke luar komponen supaya tidak dibuat ulang di setiap render
const STORAGE_KEYS = {
  locations: "noxora_last_locations",
  weatherLocation: "noxora_selected_weather_location",
};

const locationNames = {
  1: "Jakarta Timur",
  2: "Kepulauan Seribu",
  3: "Bekasi",
  4: "Bogor",
  5: "Sukabumi",
  6: "Tangerang",
  7: "Banten Utara",
  8: "Bekasi Timur",
  9: "Karawang",
  10: "Purwakarta",
};

// Field baru yang null/undefined tidak boleh menimpa nilai lama yang valid
const mergeLocations = (prev, next) => {
  const prevMap = new Map(prev.map((row) => [String(row.location_id), row]));

  return next.map((row) => {
    const old = prevMap.get(String(row.location_id));
    if (!old) return row;

    const merged = { ...row };
    for (const key of Object.keys(old)) {
      if (merged[key] == null && old[key] != null) {
        merged[key] = old[key];
      }
    }
    return merged;
  });
};

const getNo2Category = (value) => {
  if (value == null || !Number.isFinite(Number(value))) {
    return {
      label: "No Data",
      description: "Prediction data unavailable",
      color: "#64748b",
      bg: "#f1f5f9",
    };
  }

  const concentration = Number(value);

  if (concentration <= 80) {
    return {
      label: "Baik",
      description: "Good air quality",
      color: "#1d5e35",
      bg: "#b6fbce",
    };
  }

  if (concentration <= 200) {
    return {
      label: "Sedang",
      description: "Moderate air quality",
      color: "#1d4ed8",
      bg: "#bbd5f7",
    };
  }

  if (concentration <= 1130) {
    return {
      label: "Tidak Sehat",
      description: "Unhealthy air quality",
      color: "#a16207",
      bg: "#fef9c3",
    };
  }

  if (concentration <= 2260) {
    return {
      label: "Sangat Tidak Sehat",
      description: "Very unhealthy air quality",
      color: "#b91c1c",
      bg: "#fee2e2",
    };
  }

  return {
    label: "Berbahaya",
    description: "Hazardous air quality",
    color: "#ffffff",
    bg: "#6e2121",
  };
};

export default function Home() {
  const [selectedLocation, setSelectedLocation] = useState("1");
  const [allLocations, setAllLocations] = useState([]);
  const [cacheRestored, setCacheRestored] = useState(false);
  const [currentTime, setCurrentTime] = useState("");

  // 1. Restore cache saat pertama kali mount
  useEffect(() => {
    try {
      const savedLocations = localStorage.getItem(STORAGE_KEYS.locations);
      const savedWeatherLocation = localStorage.getItem(
        STORAGE_KEYS.weatherLocation,
      );

      if (savedLocations) {
        const parsedLocations = JSON.parse(savedLocations);
        if (Array.isArray(parsedLocations)) {
          setAllLocations(parsedLocations);
        }
      }

      if (savedWeatherLocation) {
        setSelectedLocation(savedWeatherLocation);
      }
    } catch (err) {
      console.error("Failed to restore Noxora data:", err);
    } finally {
      setCacheRestored(true);
    }
  }, []);

  // 2. Simpan data lokasi ke cache setiap berubah (hanya setelah restore selesai)
  useEffect(() => {
    if (!cacheRestored || allLocations.length === 0) return;

    try {
      localStorage.setItem(
        STORAGE_KEYS.locations,
        JSON.stringify(allLocations),
      );
    } catch (err) {
      console.error("Failed to save real-time data:", err);
    }
  }, [cacheRestored, allLocations]);

  const currentLocationData = useMemo(
    () =>
      allLocations.find(
        (row) => String(row.location_id) === String(selectedLocation),
      ) ?? null,
    [allLocations, selectedLocation],
  );

  const formattedDateTime = currentLocationData?.time_no2
    ? new Date(
        currentLocationData.time_no2.replace(" ", "T") + "+07:00",
      ).toLocaleString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZone: "Asia/Jakarta",
      })
    : "-";

  console.log("Current location data:", currentLocationData);

  // 3. Prediksi dihitung langsung dari data lokasi terpilih (bukan state)
  const { predictionData, error } = useMemo(() => {
    if (!currentLocationData) {
      return { predictionData: null, error: "" };
    }

    try {
      const d = currentLocationData;
      const predictedSVR = Number(d.predicted_nitrogen_dioxide);
      const predictedXGBoost = Number(d.predicted_nitrogen_dioxide_xgboost);

      if (
        d.predicted_nitrogen_dioxide == null ||
        !Number.isFinite(predictedSVR)
      ) {
        throw new Error("SVR prediction data is not available.");
      }

      if (
        d.predicted_nitrogen_dioxide_xgboost == null ||
        !Number.isFinite(predictedXGBoost)
      ) {
        throw new Error("XGBoost prediction data is not available.");
      }

      const lagValues = [d.LAG3, d.LAG2, d.LAG1].map(Number);

      if (!lagValues.every(Number.isFinite)) {
        throw new Error("Historical NO₂ data (LAG1–LAG3) is incomplete.");
      }

      const targetTimeMatch = String(d.target_time || "").match(
        /T(\d{2}:\d{2})| (\d{2}:\d{2})/,
      );
      const targetTime = targetTimeMatch
        ? targetTimeMatch[1] || targetTimeMatch[2]
        : "";

      if (!targetTime) {
        throw new Error("Prediction time is not available.");
      }

      const round = (value) => Number(value.toFixed(2));

      const [hour, minute] = targetTime.split(":").map(Number);
      const targetMinutes = hour * 60 + minute;
      const chartCategories = [-180, -120, -60, 0].map((offset) => {
        const totalMinutes = (targetMinutes + offset + 1440) % 1440;
        const h = String(Math.floor(totalMinutes / 60)).padStart(2, "0");
        const m = String(totalMinutes % 60).padStart(2, "0");
        return `${h}:${m}`;
      });

      return {
        error: "",
        predictionData: {
          location_id: d.location_id,
          target_time: d.target_time,
          svrValue: predictedSVR,
          xgboostValue: predictedXGBoost,
          time: targetTime,
          temperature_2m: d.temperature_2m,
          wind_speed_10m: d.wind_speed_10m,
          rain: d.rain,
          relative_humidity_2m: d.relative_humidity_2m,
          svrChartSeries: [...lagValues, predictedSVR].map(round),
          xgboostChartSeries: [...lagValues, predictedXGBoost].map(round),
          chartCategories,
        },
      };
    } catch (err) {
      return {
        predictionData: null,
        error: err.message || "Unable to display prediction results.",
      };
    }
  }, [currentLocationData]);

  const getLocationNO2 = (locationId) => {
    const item = allLocations.find(
      (row) => String(row.location_id) === String(locationId),
    );

    return item?.nitrogen_dioxide != null
      ? Number(item.nitrogen_dioxide).toFixed(2)
      : "-";
  };

  const getLocationLAG2 = (locationId) => {
    const item = allLocations.find(
      (row) => String(row.location_id) === String(locationId),
    );

    return item?.LAG2 != null ? Number(item.LAG2).toFixed(2) : "-";
  };

  const handleSelectLocation = (locationId) => {
    const value = String(locationId);

    setSelectedLocation(value);

    try {
      localStorage.setItem(STORAGE_KEYS.weatherLocation, value);
    } catch (err) {
      console.error("Failed to save selected weather location:", err);
    }
  };

  // Menampilkan waktu WIB setelah komponen dimuat agar tidak terjadi hydration mismatch
  useEffect(() => {
    const updateTime = () => {
      setCurrentTime(
        new Date().toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
          timeZone: "Asia/Jakarta",
        }),
      );
    };

    updateTime();
    const timer = setInterval(updateTime, 60 * 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const target = sessionStorage.getItem("scrollTarget");

    if (target) {
      sessionStorage.removeItem("scrollTarget");

      setTimeout(() => {
        document.getElementById(target)?.scrollIntoView({
          behavior: "smooth",
        });
      }, 100);
    }
  }, []);

  // 4. Fetch real-time: MERGE dengan data lama, jangan menimpa
  useEffect(() => {
    let cancelled = false;
    let isLoading = false;
    let controller = null;

    const load = async () => {
      if (isLoading || cancelled) return;

      const API_URL = process.env.NEXT_PUBLIC_API_URL;

      if (!API_URL) {
        console.error("NEXT_PUBLIC_API_URL is not configured.");
        return;
      }

      isLoading = true;
      controller = new AbortController();

      try {
        const response = await fetch(`${API_URL}/api/ml/realtime`, {
          cache: "no-store",
          signal: controller.signal,
        });

        const result = await response.json().catch(() => null);

        if (!response.ok) {
          throw new Error(
            result?.message ||
              result?.error ||
              `Failed to fetch real-time data. HTTP ${response.status}`,
          );
        }

        if (
          !result?.success ||
          !Array.isArray(result.data) ||
          result.data.length === 0
        ) {
          throw new Error("Real-time data is not available.");
        }

        if (cancelled) return;

        setAllLocations((prev) => mergeLocations(prev, result.data));
      } catch (err) {
        if (cancelled || err.name === "AbortError") return;

        console.error("Failed to update real-time data:", err);
      } finally {
        isLoading = false;
      }
    };

    load();

    const timer = setInterval(load, 60 * 60 * 1000);

    return () => {
      cancelled = true;
      clearInterval(timer);
      controller?.abort();
    };
  }, []);

  const svrCategory = getNo2Category(predictionData?.svrValue);

  const xgboostCategory = getNo2Category(predictionData?.xgboostValue);

  return (
    <Flex
      direction={"column"}
      w={"100%"}
      minH={"100vh"}
      bg={"bg.gradient"}
      align={"center"}
    >
      <Flex
        direction="column"
        w="100%"
        maxW="1600px"
        align="center"
        gap={{ base: "20px", lg: "24px" }}
        px={{ base: "4%", md: "5%" }}
        pt={{ base: "110px", md: "100px", xl: "105px" }}
        pb="32px"
      >
        <Flex w="100%" direction="column" gap="20px">
          {/* bagian atas  */}
          <Flex
            w="100%"
            p={{ base: "18px", md: "24px", xl: "20px" }}
            borderRadius="2xl"
            bg="bg.secondary"
            boxShadow="0 8px 28px rgba(0, 0, 0, 0.09)"
            direction="column"
            gap="12px"
            border="1px solid"
            borderColor="border.subtle"
            // justify="space-between"
          >
            <Flex
              justify="space-between"
              align={{ base: "flex-start", md: "center" }}
              direction={{ base: "column", md: "row" }}
            >
              <Flex direction="column" w="100%" h="100%" justify="center">
                <Flex
                  direction="row"
                  w="100%"
                  justify="space-between"
                  align="center"
                  gap="5px"
                >
                  <Text fontSize="sm" color="text.thrid">
                    Current NO₂ Concentration
                  </Text>

                  <Flex
                    w={{ base: "180px", md: "240px" }}
                    flexShrink={0}
                    direction="row"
                    gap="10px"
                    align="center"
                    borderRadius="xl"
                  >
                    <FaLocationDot />
                    <Flex justify="end" minW="0" flex="1">
                      <ComboBoxDashboard
                        value={selectedLocation}
                        onValueChange={handleSelectLocation}
                      />
                    </Flex>
                  </Flex>
                </Flex>

                <Text fontSize="md" color="text.primary" fontWeight="bold">
                  {currentTime || "--:--"}
                </Text>
              </Flex>
            </Flex>

            <Grid
              w="100%"
              templateColumns={{ base: "1fr", md: "1fr 1fr" }}
              gap="14px"
            >
              {/* // prediksi */}
              <Flex
                direction="column"
                justify="space-between"
                h="100%"
                minH="150px"
                borderRadius="xl"
                // gap="12px"
              >
                <Flex align="center" gap="20px" wrap="wrap" flex="1">
                  <FaCloudSun size="50px" />

                  <Flex
                    fontSize={{ base: "3xl", md: "xl" }}
                    direction="row"
                    gap="5px"
                    align="center"
                    wrap="wrap"
                  >
                    <Text color="text.primary" lineHeight="1">
                      {currentLocationData?.nitrogen_dioxide != null
                        ? Number(currentLocationData.nitrogen_dioxide).toFixed(
                            2,
                          )
                        : "-"}
                    </Text>

                    <Text color="text.primary">μg/m³</Text>
                  </Flex>
                </Flex>

                <Text fontSize="sm" color="text.primary">
                  Latest actual data:{" "}
                  <Text as="span" fontWeight="bold">
                    {formattedDateTime}
                  </Text>
                </Text>
              </Flex>

              <Flex
                direction="column"
                justify="space-between"
                px={{ base: "18px", md: "22px" }}
                borderLeft="1px solid"
                borderColor="border.primary"
                gap="10px"
              >
                <Flex justify="space-between" align="center" gap="5px">
                  <Text
                    fontSize="sm"
                    color="text.primary"
                    fontWeight="semibold"
                  >
                    Predicted NO₂ concentration
                  </Text>

                  <Text fontSize="sm" color="text.thrid" fontWeight="semibold">
                    {predictionData?.time
                      ? `At ${predictionData.time}`
                      : "Prediction time: -"}
                  </Text>
                </Flex>

                <Flex direction="column" gap="10px">
                  {/* SVR */}
                  <Flex
                    w="100%"
                    align="center"
                    bg="card.primary"
                    py="2vh"
                    px="1.25vh"
                    borderRadius="2vh"
                  >
                    <Flex
                      w="100%"
                      justify="space-between"
                      align="center"
                      gap="5px"
                    >
                      <Flex align="center" gap="10px">
                        <Text fontSize="md" fontWeight="bold">
                          SVR
                        </Text>

                        <Flex
                          // border="1px solid"
                          // borderColor="border.primary"
                          px="10px"
                          py="2px"
                          borderRadius="xl"
                          bg={svrCategory.bg}
                        >
                          <Text
                            fontSize="xs"
                            fontWeight="bold"
                            color={svrCategory.color}
                          >
                            {svrCategory.label}
                          </Text>
                        </Flex>
                      </Flex>

                      <Flex align="center" gap="5px">
                        <Text
                          fontSize={{ base: "xl", md: "2xl" }}
                          fontWeight="bold"
                          color="text.fouth"
                        >
                          {predictionData
                            ? Number(predictionData.svrValue).toFixed(2)
                            : "-"}
                        </Text>

                        {predictionData && (
                          <Text fontSize="sm" color="text.thrid">
                            μg/m³
                          </Text>
                        )}
                      </Flex>
                    </Flex>
                  </Flex>

                  {/* XGBoost */}
                  <Flex
                    w="100%"
                    align="center"
                    bg="card.primary"
                    py="2vh"
                    px="1.25vh"
                    borderRadius="2vh"
                  >
                    <Flex
                      w="100%"
                      justify="space-between"
                      align="center"
                      gap="5px"
                    >
                      <Flex align="center" gap="10px">
                        <Text fontSize="md" fontWeight="bold">
                          XGBoost
                        </Text>

                        <Flex
                          // border="1px solid"
                          // borderColor="border.primary"
                          px="10px"
                          py="2px"
                          borderRadius="xl"
                          bg={xgboostCategory.bg}
                        >
                          <Text
                            fontSize="xs"
                            fontWeight="bold"
                            color={xgboostCategory.color}
                          >
                            {xgboostCategory.label}
                          </Text>
                        </Flex>
                      </Flex>

                      <Flex align="center" gap="5px">
                        <Text
                          fontSize={{ base: "xl", md: "2xl" }}
                          fontWeight="bold"
                          color="text.fouth"
                        >
                          {predictionData
                            ? Number(predictionData.xgboostValue).toFixed(2)
                            : "-"}
                        </Text>

                        {predictionData && (
                          <Text fontSize="sm" color="text.thrid">
                            μg/m³
                          </Text>
                        )}
                      </Flex>
                    </Flex>
                  </Flex>
                </Flex>
              </Flex>
            </Grid>
            {error && (
              <Text color="red.500" fontSize="sm">
                {error}
              </Text>
            )}
          </Flex>

          <Flex w={"100%"} direction={"row"} gap={"15px"}>
            <Flex w={"50%"} direction={"column"} gap={"15px"}>
              <Grid
                w="100%"
                templateColumns={{
                  base: "repeat(2, minmax(0, 1fr))",
                  md: "repeat(3, minmax(0, 1fr))",
                }}
                gap={{ base: "10px", md: "16px" }}
              >
                <MiniCard
                  title="Location"
                  hasil={locationNames[selectedLocation] ?? "-"}
                />

                <MiniCard
                  title="Nitrogen Dioxide"
                  hasil={
                    currentLocationData?.nitrogen_dioxide != null
                      ? `${Number(currentLocationData.nitrogen_dioxide).toFixed(2)} μg/m³`
                      : "-"
                  }
                />

                <MiniCard
                  title="Temperature"
                  hasil={
                    currentLocationData?.temperature_2m != null
                      ? `${Number(currentLocationData.temperature_2m).toFixed(2)} °C`
                      : "-"
                  }
                />

                <MiniCard
                  title="Wind Speed"
                  hasil={
                    currentLocationData?.wind_speed_10m != null
                      ? `${Number(currentLocationData.wind_speed_10m).toFixed(2)} km/h`
                      : "-"
                  }
                />

                <MiniCard
                  title="Rainfall"
                  hasil={
                    currentLocationData?.rain != null
                      ? `${Number(currentLocationData.rain).toFixed(2)} mm`
                      : "-"
                  }
                />

                <MiniCard
                  title="Relative Humidity"
                  hasil={
                    currentLocationData?.relative_humidity_2m != null
                      ? `${Number(currentLocationData.relative_humidity_2m).toFixed(2)}%`
                      : "-"
                  }
                />
              </Grid>

              <Flex
                w="100%"
                gap="14px"
                align="stretch"
                direction={{ base: "column", lg: "row" }}
              >
                <Grid
                  w="100%"
                  templateColumns="repeat(2, minmax(0, 1fr))"
                  gap="14px"
                >
                  <MiniCardLocation
                    location="Jakarta Timur"
                    hasil={getLocationNO2(1)}
                    lag2={getLocationLAG2(1)}
                    onSelect={() => handleSelectLocation("1")}
                  />

                  <MiniCardLocation
                    location="Bogor"
                    hasil={getLocationNO2(4)}
                    lag2={getLocationLAG2(4)}
                    onSelect={() => handleSelectLocation("4")}
                  />
                </Grid>

                <Grid
                  w="100%"
                  templateColumns="repeat(2, minmax(0, 1fr))"
                  gap="14px"
                >
                  <MiniCardLocation
                    location="Tangerang"
                    hasil={getLocationNO2(6)}
                    lag2={getLocationLAG2(6)}
                    onSelect={() => handleSelectLocation("6")}
                  />

                  <MiniCardLocation
                    location="Bekasi"
                    hasil={getLocationNO2(3)}
                    lag2={getLocationLAG2(3)}
                    onSelect={() => handleSelectLocation("3")}
                  />
                </Grid>
              </Flex>
            </Flex>

            <Flex
              w={{
                base: "100%",
                sm: "100%",
                md: "100%",
                lg: "100%",
                xl: "50%",
              }}
              direction="column"
              gap="17px"
              minW="0"
            >
              <Flex
                w="100%"
                flex="1"
                direction={{
                  base: "column",
                  sm: "column",
                  md: "row",
                }}
                gap="17px"
                align="stretch"
                minW="0"
              >
                <Flex flex="1" minW="0" minH="40vh">
                  <PredictionChart data={predictionData} />
                </Flex>

                <Flex
                  w={{
                    base: "100%",
                    md: "42%",
                  }}
                  minW="0"
                  direction="column"
                  p="20px"
                  boxShadow={"0 4px 12px rgba(0, 0, 0, 0.2)"}
                  borderRadius="2vh"
                  bg="bg.secondary"
                  gap="17px"
                >
                  <Flex pb="0.5vh" borderBottom="1px solid #dfdddd">
                    <Text fontWeight="bold" color="text.fouth">
                      NO₂ Category
                    </Text>
                  </Flex>

                  <Flex
                    w="100%"
                    direction="column"
                    gap="5px"
                    justify="space-between"
                  >
                    {/* Baik */}
                    <Flex
                      bg="bg.primary"
                      p="7px 10px"
                      borderRadius="sm"
                      direction="row"
                      gap="5px"
                      align="center"
                      justify="space-between"
                    >
                      <Text fontSize="sm" color="text.thrid">
                        Baik
                      </Text>
                      <Text fontSize="sm" color="text.thrid" fontWeight="bold">
                        0 – 50
                      </Text>
                    </Flex>

                    {/* Sedang */}
                    <Flex
                      bg="bg.primary"
                      p="7px 10px"
                      borderRadius="sm"
                      direction="row"
                      gap="5px"
                      align="center"
                      justify="space-between"
                    >
                      <Text fontSize="sm" color="text.thrid">
                        Sedang
                      </Text>
                      <Text fontSize="sm" color="text.thrid" fontWeight="bold">
                        51 – 100
                      </Text>
                    </Flex>

                    {/* Tidak Sehat */}
                    <Flex
                      bg="bg.primary"
                      p="7px 10px"
                      borderRadius="sm"
                      direction="row"
                      gap="5px"
                      align="center"
                      justify="space-between"
                    >
                      <Text fontSize="sm" color="text.thrid">
                        Tidak Sehat
                      </Text>
                      <Text fontSize="sm" color="text.thrid" fontWeight="bold">
                        101 – 199
                      </Text>
                    </Flex>

                    {/* Sangat Tidak Sehat */}
                    <Flex
                      bg="bg.primary"
                      p="7px 10px"
                      borderRadius="sm"
                      direction="row"
                      gap="5px"
                      align="center"
                      justify="space-between"
                    >
                      <Text fontSize="sm" color="text.thrid">
                        Sangat Tidak Sehat
                      </Text>
                      <Text fontSize="sm" color="text.thrid" fontWeight="bold">
                        200 – 299
                      </Text>
                    </Flex>

                    {/* Berbahaya */}
                    <Flex
                      bg="bg.primary"
                      p="7px 10px"
                      borderRadius="sm"
                      direction="row"
                      gap="5px"
                      align="center"
                      justify="space-between"
                    >
                      <Text fontSize="sm" color="text.thrid">
                        Berbahaya
                      </Text>
                      <Text fontSize="sm" color="text.thrid" fontWeight="bold">
                        300 – 500
                      </Text>
                    </Flex>
                  </Flex>
                </Flex>
              </Flex>
            </Flex>
          </Flex>
        </Flex>

        <Flex
          w={{
            base: "90%",
            lg: "60%",
          }}
          py="20px"
          px="20px"
          gap={{
            base: "2vh",
            md: "3vh",
          }}
          bg="bg.secondary"
          direction={{
            base: "column",
            md: "row",
          }}
          borderRadius="2vh"
          boxShadow={"0 4px 12px rgba(0, 0, 0, 0.2)"}
        >
          <Flex
            w={{
              base: "100%",
              lg: "65%",
            }}
            direction="column"
            gap="1.5vh"
          >
            <Text
              fontSize="xl"
              fontWeight="bold"
              textAlign={{
                base: "center",
                md: "start",
              }}
            >
              Noxora
            </Text>

            <Text fontSize="md" textAlign="justify" color="text.thrid">
              Noxora is a Progressive Web App (PWA) that helps users predict
              nitrogen dioxide (NO₂) concentrations and monitor air quality
              across the Greater Jakarta area. The application uses the XGBoost
              and Support Vector Regression (SVR) algorithms to predict NO₂
              concentrations based on environmental conditions.
            </Text>

            <Text fontSize="md" textAlign="justify" color="text.thrid">
              Users can select environmental parameters such as location,
              temperature, wind speed, rainfall, and relative humidity. The
              prediction results are then displayed as NO₂ concentration values
              and charts, making them easier to understand.
            </Text>
          </Flex>

          <Flex
            w={{
              base: "100%",
              md: "35%",
            }}
            direction="column"
            gap="1.5vh"
            align="center"
            justify="center"
          >
            <RiCloudWindyFill size={"200px"} />
          </Flex>
        </Flex>
      </Flex>

      <Flex
        w="100%"
        mt="2vh"
        py="3vh"
        px="6vh"
        bg="bg.secondary"
        direction="column"
        align="center"
        gap="5px"
        borderTop="1px solid #e7e7e7"
      >
        <Text fontSize="xl" fontWeight="bold" color="text.fouth">
          Noxora
        </Text>

        <Text fontSize="sm" color="text.thrid" textAlign="center">
          Nitrogen Dioxide (NO₂) Concentration Prediction
          <br />
          Using XGBoost and Support Vector Regression
        </Text>

        <Text fontSize="xs" color="text.thrid" mt="1vh">
          © 2026 Shirley 535230024. All rights reserved.
        </Text>
      </Flex>
    </Flex>
  );
}
