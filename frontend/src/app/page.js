"use client";

import { Button, Flex, Grid, Text } from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FaCloudSun, FaLocationDot } from "react-icons/fa6";
import {
  InputPrediction,
  MiniCard,
  MiniCardLocation,
} from "../components/Detail/detail";
import { ComboBoxDashboard } from "../components/ComboBox/comboBox";
import PredictionChart from "../components/Grafik/grafik";
import { RiCloudWindyFill } from "react-icons/ri";
import { PopupMini } from "../components/Popup/popup";

export default function Home() {
  const router = useRouter();

  const [predictionData, setPredictionData] = useState(null);
  const [selectedLocation, setSelectedLocation] = useState("1");
  const [selectedPredictionLocation, setSelectedPredictionLocation] =
    useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showPredictionPopup, setShowPredictionPopup] = useState(false);
  // const [currentLocationData, setCurrentLocationData] = useState(null);
  const [allLocations, setAllLocations] = useState([]);

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

  const currentLocationData =
    allLocations.find(
      (row) => String(row.location_id) === String(selectedLocation),
    ) ?? null;

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
    setSelectedLocation(String(locationId));
  };

  const handleSendPrediction = () => {
    const isLoggedIn = localStorage.getItem("isLoggedIn");

    if (isLoggedIn !== "true") {
      setShowPredictionPopup(true);
      return;
    }

    if (!selectedPredictionLocation) {
      setError("Please select a location first.");
      return;
    }

    try {
      setLoading(true);
      setError("");

      // Use data already loaded by useEffect.
      // Do not call Open-Meteo again when the Send button is clicked.
      const selectedData = allLocations.find(
        (row) => String(row.location_id) === String(selectedPredictionLocation),
      );

      if (!selectedData) {
        throw new Error(
          "Location data is not available yet. Please wait for the real-time data to finish loading.",
        );
      }

      const predictedSVR = Number(selectedData.predicted_nitrogen_dioxide);

      const predictedXGBoost = Number(
        selectedData.predicted_nitrogen_dioxide_xgboost,
      );

      if (
        selectedData.predicted_nitrogen_dioxide == null ||
        !Number.isFinite(predictedSVR)
      ) {
        throw new Error("SVR prediction data is not available.");
      }

      if (
        selectedData.predicted_nitrogen_dioxide_xgboost == null ||
        !Number.isFinite(predictedXGBoost)
      ) {
        throw new Error("XGBoost prediction data is not available.");
      }

      const lagValues = [
        selectedData.LAG3,
        selectedData.LAG2,
        selectedData.LAG1,
      ].map(Number);

      if (!lagValues.every(Number.isFinite)) {
        throw new Error("Historical NO₂ data (LAG1–LAG3) is incomplete.");
      }

      // Prediction target time from the Python endpoint.
      const targetTimeValue = String(selectedData.target_time || "");

      const targetTimeMatch = targetTimeValue.match(
        /T(\d{2}:\d{2})| (\d{2}:\d{2})/,
      );

      const targetTime = targetTimeMatch
        ? targetTimeMatch[1] || targetTimeMatch[2]
        : "";

      if (!targetTime) {
        throw new Error("Prediction time is not available.");
      }

      // Chart order: LAG3, LAG2, LAG1, prediction result.
      const svrChartSeries = [...lagValues, predictedSVR].map((value) =>
        Number(value.toFixed(2)),
      );

      const xgboostChartSeries = [...lagValues, predictedXGBoost].map((value) =>
        Number(value.toFixed(2)),
      );

      const [hour, minute] = targetTime.split(":").map(Number);
      const targetMinutes = hour * 60 + minute;

      const chartCategories = [-180, -120, -60, 0].map((offset) => {
        const totalMinutes = (targetMinutes + offset + 1440) % 1440;

        const h = String(Math.floor(totalMinutes / 60)).padStart(2, "0");

        const m = String(totalMinutes % 60).padStart(2, "0");

        return `${h}:${m}`;
      });

      setPredictionData({
        location_id: selectedData.location_id,
        target_time: selectedData.target_time,

        svrValue: predictedSVR,
        xgboostValue: predictedXGBoost,
        time: targetTime,

        temperature_2m: selectedData.temperature_2m,
        wind_speed_10m: selectedData.wind_speed_10m,
        rain: selectedData.rain,
        relative_humidity_2m: selectedData.relative_humidity_2m,

        svrChartSeries,
        xgboostChartSeries,
        chartCategories,
      });
    } catch (err) {
      console.error("Failed to display prediction:", err);

      setError(
        err.message || "An error occurred while displaying the prediction.",
      );
    } finally {
      setLoading(false);
    }
  };

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

        if (!result?.success || !Array.isArray(result.data)) {
          throw new Error("Real-time data is not available.");
        }

        if (cancelled) return;

        setAllLocations(result.data);
      } catch (err) {
        if (cancelled || err.name === "AbortError") return;

        console.error("Failed to update real-time data:", err);
      } finally {
        isLoading = false;
      }
    };

    load();

    const timer = setInterval(load, 5 * 60 * 1000);

    return () => {
      cancelled = true;
      clearInterval(timer);
      controller?.abort();
    };
  }, []);

  return (
    <Flex
      direction={"column"}
      w={"100%"}
      minH={"100vh"}
      bg={"bg.gradient"}
      align={"center"}
    >
      <Flex
        direction={"column"}
        w={"100%"}
        align={"center"}
        gap={{ base: "20px", lg: "20px" }}
        py={"4vh"}
      >
        <Flex
          direction={{
            base: "column",
            sm: "column",
            md: "column",
            lg: "column",
            xl: "row",
          }}
          w="90%"
          mt={{
            base: "110px",
            sm: "110px",
            md: "80px",
            lg: "80px",
            xl: "80px",
          }}
          gap="17px"
          align="stretch"
        >
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
          >
            <Flex
              w={"100%"}
              p={"20px"}
              borderRadius={"2vh"}
              bg={"bg.secondary"}
              boxShadow={"0 4px 12px rgba(0, 0, 0, 0.2)"}
              direction={"column"}
              gap="17px"
              justify="space-between"
            >
              <Flex direction="column">
                <Flex justify="space-between" align="center">
                  <Text fontSize="sm" color="text.thrid">
                    Current Weather
                  </Text>

                  <Flex w="200px" direction="row" gap="1vh" align="center">
                    <FaLocationDot />

                    <ComboBoxDashboard
                      value={selectedLocation}
                      onValueChange={setSelectedLocation}
                    />
                  </Flex>
                </Flex>

                <Text fontWeight="bold">
                  {new Date().toLocaleTimeString("en-US", {
                    hour: "2-digit",
                    minute: "2-digit",
                    hour12: false,
                    timeZone: "Asia/Jakarta",
                  })}
                </Text>
              </Flex>

              <Flex direction="row" gap="17px" align="center">
                <FaCloudSun size="50px" />

                <Text fontSize="xl">
                  {currentLocationData?.nitrogen_dioxide != null
                    ? `${Number(currentLocationData.nitrogen_dioxide).toFixed(
                        2,
                      )} μg/m³`
                    : "-"}
                </Text>
              </Flex>

              <Text fontSize="sm">
                Latest actual data: {currentLocationData?.time_no2 ?? "-"}
              </Text>
            </Flex>

            <Grid
              w="100%"
              templateColumns={{
                base: "repeat(2, 1fr)",
                sm: "repeat(2, 1fr)",
                md: "repeat(3, 1fr)",
              }}
              gap="17px"
            >
              <MiniCard
                title="Location"
                hasil={locationNames[selectedLocation] ?? "-"}
              />

              <MiniCard
                title="Nitrogen Dioxide"
                hasil={
                  currentLocationData?.nitrogen_dioxide != null
                    ? `${Number(currentLocationData.nitrogen_dioxide).toFixed(
                        2,
                      )} μg/m³`
                    : "-"
                }
              />

              <MiniCard
                title="Temperature"
                hasil={
                  currentLocationData?.temperature_2m != null
                    ? `${Number(currentLocationData.temperature_2m).toFixed(
                        2,
                      )} °C`
                    : "-"
                }
              />

              <MiniCard
                title="Wind Speed"
                hasil={
                  currentLocationData?.wind_speed_10m != null
                    ? `${Number(currentLocationData.wind_speed_10m).toFixed(
                        2,
                      )} km/h`
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
                    ? `${Number(
                        currentLocationData.relative_humidity_2m,
                      ).toFixed(2)}%`
                    : "-"
                }
              />
            </Grid>

            <Flex
              w="100%"
              gap="17px"
              flex="1"
              align="stretch"
              direction={{
                base: "column",
                sm: "column",
                md: "row",
                lg: "row",
                xl: "row",
              }}
            >
              <Flex w="100%" direction="row" gap="17px">
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
              </Flex>

              <Flex w="100%" direction="row" gap="17px">
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
              </Flex>
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
              px={"20px"}
              py={"18px"}
              boxShadow={"0 4px 12px rgba(0, 0, 0, 0.2)"}
              borderRadius="2vh"
              bg="bg.secondary"
              gap="17px"
              direction="column"
            >
              <Flex pb="0.5vh" borderBottom="1px solid #dfdddd">
                <Text fontWeight="bold" color="text.fouth">
                  Nitrogen Dioxide Prediction
                </Text>
              </Flex>

              <Flex
                direction={{
                  base: "column",
                  md: "row",
                }}
                gap="17px"
                justify="space-between"
              >
                <Flex
                  direction="column"
                  w={{
                    base: "100%",
                    md: "45%",
                  }}
                >
                  <Text w="20vh" fontSize="sm" fontWeight="bold">
                    Location
                  </Text>

                  <ComboBoxDashboard
                    w="100%"
                    value={selectedPredictionLocation}
                    onValueChange={setSelectedPredictionLocation}
                  />
                </Flex>

                <Flex w="100%" gap="17px">
                  <InputPrediction
                    title="Temperature"
                    placeholder="Temperature..."
                    value={
                      predictionData?.temperature_2m != null
                        ? Number(predictionData.temperature_2m).toFixed(2)
                        : "-"
                    }
                    satuan="°C"
                  />

                  <InputPrediction
                    title="Wind Speed"
                    placeholder="Wind Speed..."
                    value={
                      predictionData?.wind_speed_10m != null
                        ? Number(predictionData.wind_speed_10m).toFixed(2)
                        : "-"
                    }
                    satuan="km/h"
                  />
                </Flex>
              </Flex>

              <Flex direction="row" gap="17px" justify="space-between">
                <InputPrediction
                  title="Rainfall"
                  placeholder="Rainfall..."
                  value={
                    predictionData?.rain != null
                      ? Number(predictionData.rain).toFixed(2)
                      : "-"
                  }
                  satuan="mm"
                />

                <InputPrediction
                  title="Relative Humidity"
                  placeholder="Relative Humidity..."
                  value={
                    predictionData?.relative_humidity_2m != null
                      ? Number(predictionData.relative_humidity_2m).toFixed(2)
                      : "-"
                  }
                  satuan="%"
                />
              </Flex>

              <Flex
                justify="center"
                align="center"
                direction="column"
                gap="5px"
              >
                <Button
                  w="120px"
                  h="32px"
                  borderRadius="4vh"
                  bg="button.primary"
                  onClick={handleSendPrediction}
                  loading={loading}
                  _hover={{
                    bg: "hover.primary",
                  }}
                >
                  Send
                </Button>

                {error && (
                  <Text color="red.500" fontSize="sm" textAlign="center">
                    {error}
                  </Text>
                )}
              </Flex>
            </Flex>

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
                    Prediction Results
                  </Text>
                </Flex>

                <Flex w="100%" direction="column" gap="5px">
                  <Flex
                    direction={{
                      base: "column",
                      sm: "column",
                      md: "row",
                    }}
                    gap="5px"
                    align={{
                      base: "flex-start",
                      md: "center",
                    }}
                  >
                    <Text fontSize="sm" color="text.thrid">
                      NO₂ Prediction Time:
                    </Text>

                    <Text fontSize="lg" color="text.thrid" fontWeight="bold">
                      {predictionData ? predictionData.time : "-"}
                    </Text>
                  </Flex>

                  <Flex w="100%" direction="column" gap="17px" mt="1.5vh">
                    <Flex
                      w="100%"
                      flex="1"
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
                        direction="row"
                      >
                        <Text
                          fontSize="md"
                          textAlign="center"
                          fontWeight="bold"
                        >
                          SVR
                        </Text>

                        <Flex
                          direction="row"
                          gap="5px"
                          align="center"
                          justify="center"
                        >
                          <Text
                            fontSize={{
                              base: "xl",
                              md: "2xl",
                            }}
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

                    <Flex
                      w="100%"
                      flex="1"
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
                        direction="row"
                      >
                        <Text
                          fontSize="md"
                          textAlign="center"
                          fontWeight="bold"
                        >
                          XGBoost
                        </Text>

                        <Flex
                          direction="row"
                          gap="5px"
                          align="center"
                          justify="center"
                        >
                          <Text
                            fontSize={{
                              base: "xl",
                              md: "2xl",
                            }}
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

      {showPredictionPopup && (
        <PopupMini
          title="Prediction"
          message="Please log in first to make a prediction."
          button1="Cancel"
          button2="Login"
          onClick1={() => setShowPredictionPopup(false)}
          onClick2={() => {
            setShowPredictionPopup(false);
            router.push("/Login");
          }}
        />
      )}
    </Flex>
  );
}
