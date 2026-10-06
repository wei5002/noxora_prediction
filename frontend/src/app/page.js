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

  // STATE
  const [predictionData, setPredictionData] = useState(null);
  const [selectedLocation, setSelectedLocation] = useState("1");
  const [selectedPredictionLocation, setSelectedPredictionLocation] =
    useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showPredictionPopup, setShowPredictionPopup] = useState(false);
  const [currentLocationData, setCurrentLocationData] = useState(null);
  const [allLocations, setAllLocations] = useState([]);

  // NAMA LOKASI
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

  // AMBIL DATA NO2 PER LOKASI
  const getLocationNO2 = (locationId) => {
    const item = allLocations.find(
      (row) => String(row.location_id) === String(locationId),
    );

    return item?.nitrogen_dioxide != null
      ? Number(item.nitrogen_dioxide).toFixed(2)
      : "-";
  };

  // AMBIL LAG2 PER LOKASI
  const getLocationLAG2 = (locationId) => {
    const item = allLocations.find(
      (row) => String(row.location_id) === String(locationId),
    );

    return item?.LAG2 != null ? Number(item.LAG2).toFixed(2) : "-";
  };

  const handleSelectLocation = (locationId) => {
    setSelectedLocation(String(locationId));
  };

  // HANDLE PREDICTION
  const handleSendPrediction = async () => {
    const isLoggedIn = localStorage.getItem("isLoggedIn");

    // CEK LOGIN
    if (isLoggedIn !== "true") {
      setShowPredictionPopup(true);
      return;
    }

    // CEK LOKASI
    if (!selectedPredictionLocation) {
      setError("Silakan pilih lokasi terlebih dahulu.");
      return;
    }

    try {
      setLoading(true);
      setError("");

      // REQUEST KE BACKEND
      const response = await fetch(
        `http://localhost:5000/api/realtime?location_id=${selectedPredictionLocation}&predict=true`,
      );

      const result = await response.json();
      console.log("HASIL PREDIKSI DARI BACKEND:", result);
      if (!response.ok) {
        throw new Error(result.message || "Gagal mengambil data prediksi.");
      }

      const predictedSVR = Number(result.predicted_nitrogen_dioxide);
      const predictedXGBoost = Number(
        result.predicted_nitrogen_dioxide_xgboost,
      );

      // VALIDASI HASIL SVR
      if (
        result.predicted_nitrogen_dioxide == null ||
        Number.isNaN(predictedSVR)
      ) {
        throw new Error("Data prediksi SVR tidak tersedia.");
      }

      // VALIDASI HASIL XGBOOST
      if (
        result.predicted_nitrogen_dioxide_xgboost == null ||
        Number.isNaN(predictedXGBoost)
      ) {
        throw new Error("Data prediksi XGBoost tidak tersedia.");
      }

      // AMBIL TARGET TIME
      const targetTimeValue = String(result.target_time || "");
      const targetTime = targetTimeValue.includes("T")
        ? targetTimeValue.split("T")[1]?.slice(0, 5)
        : targetTimeValue.split(" ")[1]?.slice(0, 5);

      if (!targetTime) {
        throw new Error("Waktu prediksi tidak tersedia.");
      }

      const svrChartSeries = [
        Number(result.LAG3),
        Number(result.LAG2),
        Number(result.LAG1),
        predictedSVR,
      ].map((value) => Number(value.toFixed(2)));

      const xgboostChartSeries = [
        Number(result.LAG3),
        Number(result.LAG2),
        Number(result.LAG1),
        predictedXGBoost,
      ].map((value) => Number(value.toFixed(2)));

      // WAKTU GRAFIK
      const [hour, minute] = targetTime.split(":").map(Number);
      const targetMinutes = hour * 60 + minute;
      const chartCategories = [-180, -120, -60, 0].map((offset) => {
        const totalMinutes = (targetMinutes + offset + 1440) % 1440;
        const h = String(Math.floor(totalMinutes / 60)).padStart(2, "0");
        const m = String(totalMinutes % 60).padStart(2, "0");
        return `${h}:${m}`;
      });

      // SIMPAN DATA PREDIKSI
      setPredictionData({
        location_id: result.location_id,
        target_time: result.target_time,

        // Nilai prediksi
        svrValue: predictedSVR,
        xgboostValue: predictedXGBoost,

        // Waktu prediksi
        time: targetTime,
        // Data cuaca
        temperature_2m: result.temperature_2m,
        wind_speed_10m: result.wind_speed_10m,
        rain: result.rain,
        relative_humidity_2m: result.relative_humidity_2m,

        // Data grafik
        svrChartSeries,
        xgboostChartSeries,
        chartCategories,
      });
    } catch (error) {
      console.error("Gagal mendapatkan prediksi:", error);
      setError(error.message || "Terjadi kesalahan saat mengambil prediksi.");
      setPredictionData(null);
    } finally {
      setLoading(false);
    }
  };

  // SCROLL TARGET

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

  // DATA REALTIME LOKASI TERPILIH
  // CURRENT WEATHER

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch(
          `http://localhost:5000/api/realtime?location_id=${selectedLocation}`,
        );
        if (!res.ok) {
          throw new Error("Gagal mengambil data realtime.");
        }
        const data = await res.json();
        console.log("DATA CURRENT WEATHER:", data);
        setCurrentLocationData(data);
      } catch (err) {
        console.error(err);
        setCurrentLocationData(null);
      }
    };

    load();
    const timer = setInterval(load, 5 * 60 * 1000);
    return () => clearInterval(timer);
  }, [selectedLocation]);

  // DATA REALTIME SEMUA LOKASI

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch("http://localhost:5000/api/realtime-all");
        if (!res.ok) return;
        const data = await res.json();
        setAllLocations(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error(err);
      }
    };

    load();
    const timer = setInterval(load, 5 * 60 * 1000);
    return () => clearInterval(timer);
  }, []);

  // RETURN
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
        gap={{ base: "4vh", lg: "5vh" }}
        py={"4vh"}
      >
        {/* CURRENT WEATHER + PREDICTION */}
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
            base: "16vh",
            sm: "16vh",
            md: "12vh",
            lg: "12vh",
            xl: "12vh",
          }}
          gap="3vh"
          align="stretch"
        >
          {/* CURRENT WEATHER */}
          <Flex
            w={{
              base: "100%",
              sm: "100%",
              md: "100%",
              lg: "100%",
              xl: "50%",
            }}
            direction="column"
            gap="2vh"
          >
            {/* CURRENT WEATHER CARD */}
            <Flex
              w={"100%"}
              p={"2.5vh"}
              borderRadius={"2vh"}
              bg={"bg.secondary"}
              boxShadow={"0 4px 12px rgba(0, 0, 0, 0.2)"}
              direction={"column"}
              gap="2vh"
              justify="space-between"
            >
              <Flex direction="column">
                <Flex justify="space-between" align="center">
                  <Text fontSize="sm" color="text.thrid">
                    Current Weather
                  </Text>

                  <Flex w="30vh" direction="row" gap="1vh" align="center">
                    <FaLocationDot />

                    <ComboBoxDashboard
                      value={selectedLocation}
                      onValueChange={setSelectedLocation}
                    />
                  </Flex>
                </Flex>

                <Text fontWeight="bold">
                  {new Date().toLocaleTimeString("id-ID", {
                    hour: "2-digit",
                    minute: "2-digit",
                    hour12: false,
                    timeZone: "Asia/Jakarta",
                  })}
                </Text>
              </Flex>

              <Flex direction="row" gap="2vh" align="center">
                <FaCloudSun size="8vh" />

                <Text fontSize="xl">
                  {currentLocationData?.nitrogen_dioxide != null
                    ? `${Number(currentLocationData.nitrogen_dioxide).toFixed(
                        2,
                      )} μg/m³`
                    : "-"}
                </Text>
              </Flex>

              <Text fontSize="sm">
                Data aktual terakhir: {currentLocationData?.time_no2 ?? "-"}
              </Text>
            </Flex>
            {/* MINI CARDS */}
            <Grid
              w="100%"
              templateColumns={{
                base: "repeat(2, 1fr)",
                sm: "repeat(2, 1fr)",
                md: "repeat(3, 1fr)",
              }}
              gap="2vh"
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
                title="Rain"
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
            {/* LOCATION CARDS */}
            <Flex
              w="100%"
              gap="2vh"
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
              <Flex w="100%" direction="row" gap="2vh">
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

              <Flex w="100%" direction="row" gap="2vh">
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
          {/* PREDICTION */}
          <Flex
            w={{
              base: "100%",
              sm: "100%",
              md: "100%",
              lg: "100%",
              xl: "50%",
            }}
            direction="column"
            gap="2vh"
            minW="0"
          >
            {/* PREDICTION INPUT */}
            <Flex
              w="100%"
              p="2.5vh"
              boxShadow={"0 4px 12px rgba(0, 0, 0, 0.2)"}
              borderRadius="2vh"
              bg="bg.secondary"
              gap="2vh"
              direction="column"
            >
              <Flex pb="0.5vh" borderBottom="1px solid #dfdddd">
                <Text fontWeight="bold" color="text.fouth">
                  Prediction Nitrogen Dioxide
                </Text>
              </Flex>

              <Flex
                direction={{
                  base: "column",
                  md: "row",
                }}
                gap="2vh"
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

                <Flex w="100%" gap="2vh">
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

              <Flex direction="row" gap="2vh" justify="space-between">
                <InputPrediction
                  title="Rain"
                  placeholder="Rain..."
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
                gap="1vh"
              >
                <Button
                  w="15vh"
                  h="4.5vh"
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

            {/* GRAPH + RESULT */}
            <Flex
              w="100%"
              flex="1"
              direction={{
                base: "column",
                sm: "column",
                md: "row",
              }}
              gap="2vh"
              align="stretch"
              minW="0"
            >
              {/* GRAPH */}
              <Flex
                flex="1"
                minW="0"
                w="100%"
                h={"40vh"}
                // minH={{
                //   base: "40vh",
                //   md: "40vh",
                // }}
              >
                <PredictionChart data={predictionData} />
              </Flex>

              {/* RESULT */}
              <Flex
                w={{
                  base: "100%",
                  md: "42%",
                }}
                minW="0"
                // minH={{
                //   base: "40vh",
                //   md: "40vh",
                // }}
                direction="column"
                p="2.5vh"
                boxShadow={"0 4px 12px rgba(0, 0, 0, 0.2)"}
                borderRadius="2vh"
                bg="bg.secondary"
                gap="2vh"
              >
                <Flex pb="0.5vh" borderBottom="1px solid #dfdddd">
                  <Text fontWeight="bold" color="text.fouth">
                    Prediction Result
                  </Text>
                </Flex>

                <Flex w="100%" direction="column" gap="1vh">
                  <Flex
                    direction={{
                      base: "column",
                      sm: "column",
                      md: "row",
                    }}
                    gap="1vh"
                    align={{
                      base: "flex-start",
                      md: "center",
                    }}
                  >
                    <Text fontSize="sm" color="text.thrid">
                      Prediksi NO₂ Jam:
                    </Text>

                    <Text fontSize="lg" color="text.thrid" fontWeight="bold">
                      {predictionData ? predictionData.time : "-"}
                    </Text>
                  </Flex>

                  <Flex w="100%" direction="column" gap="2vh" mt="1.5vh">
                    {/* SVR */}
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
                        gap="1vh"
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
                          gap="1vh"
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

                    {/* XGBOOST */}
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
                        gap="1vh"
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
                          gap="1vh"
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
        {/* ABOUT NOXORA */}
        <Flex
          w={{
            base: "90%",
            lg: "60%",
          }}
          py="4vh"
          px="4vh"
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
              Noxora adalah aplikasi berbasis Progressive Web App (PWA) yang
              membantu pengguna memprediksi konsentrasi nitrogen dioksida (NO₂)
              dan memantau kualitas udara di wilayah Jabodetabek. Aplikasi ini
              menggunakan algoritma XGBoost dan Support Vector Regression (SVR)
              untuk menghasilkan prediksi konsentrasi NO₂ berdasarkan kondisi
              lingkungan.
            </Text>

            <Text fontSize="md" textAlign="justify" color="text.thrid">
              Pengguna dapat memasukkan parameter lingkungan seperti lokasi,
              temperatur, kecepatan angin, curah hujan, dan kelembapan relatif.
              Hasil prediksi kemudian ditampilkan dalam bentuk nilai konsentrasi
              NO₂ dan grafik sehingga lebih mudah dipahami.
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
            <RiCloudWindyFill size="30vh" />
          </Flex>
        </Flex>
      </Flex>

      {/* FOOTER */}
      <Flex
        w="100%"
        mt="2vh"
        py="3vh"
        px="6vh"
        bg="bg.secondary"
        direction="column"
        align="center"
        gap="1vh"
        borderTop="1px solid #e7e7e7"
      >
        <Text fontSize="xl" fontWeight="bold" color="text.fouth">
          Noxora
        </Text>

        <Text fontSize="sm" color="text.thrid" textAlign="center">
          Prediksi Konsentrasi Nitrogen Dioksida (NO₂)
          <br />
          Menggunakan XGBoost dan Support Vector Regression
        </Text>

        <Text fontSize="xs" color="text.thrid" mt="1vh">
          © 2026 Shirley 535230024. All rights reserved.
        </Text>
      </Flex>

      {showPredictionPopup && (
        <PopupMini
          title="Prediction"
          message="Silakan login terlebih dahulu untuk melakukan prediksi."
          button1="Batal"
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
