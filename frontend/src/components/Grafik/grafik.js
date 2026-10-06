"use client";

import { Flex, Text } from "@chakra-ui/react";
import dynamic from "next/dynamic";
import { useColorModeValue } from "@/components/ui/color-mode";

const Chart = dynamic(() => import("react-apexcharts"), {
  ssr: false,
});

export default function PredictionChart({ data }) {
  const textPrimary = useColorModeValue("#464646", "#ffffff");

  const hasData =
    Boolean(data?.chartCategories?.length) &&
    Boolean(data?.svrChartSeries?.length) &&
    Boolean(data?.xgboostChartSeries?.length);

  const options = {
    chart: {
      height: 210,
      type: "line",
      toolbar: {
        show: false,
      },
      zoom: {
        enabled: false,
      },
    },

    dataLabels: {
      enabled: false,
    },

    stroke: {
      curve: "smooth",
      width: 3,
    },

    xaxis: {
      categories: data?.chartCategories ?? [],

      labels: {
        style: {
          colors: textPrimary,
          fontSize: "12px",
        },
      },
    },

    yaxis: {
      labels: {
        formatter: (value) => Number(value).toFixed(2),

        style: {
          colors: textPrimary,
          fontSize: "12px",
        },
      },
    },

    tooltip: {
      y: {
        formatter: (value) => `${Number(value).toFixed(2)} μg/m³`,
      },
    },

    legend: {
      position: "bottom",
      horizontalAlign: "center",
    },

    grid: {
      borderColor: "#e7e7e7",
    },

    markers: {
      size: 4,
      discrete: [
        {
          seriesIndex: 0,
          dataPointIndex: 3,
          size: 6,
        },
        {
          seriesIndex: 1,
          dataPointIndex: 3,
          size: 6,
        },
      ],
    },
  };

  // 2 GARIS

  const series = [
    {
      name: "SVR",
      data: data?.svrChartSeries ?? [],
    },
    {
      name: "XGBoost",
      data: data?.xgboostChartSeries ?? [],
    },
  ];

  return (
    <>
      <style jsx global>{`
        .apexcharts-xaxis-label {
          font-size: 12px !important;
        }

        .apexcharts-yaxis-label {
          font-size: 12px !important;
        }
      `}</style>

      <Flex
        w={{ base: "100%", md: "100%" }}
        direction="column"
        p={"2.5vh"}
        boxShadow="0 4px 12px rgba(0, 0, 0, 0.2)"
        borderRadius={"2vh"}
        bg={"bg.secondary"}
        gap={"2vh"}
      >
        <Flex pb={"0.5vh"} borderBottom={"1px solid #dfdddd"}>
          <Text fontWeight={"bold"} color={"text.fouth"}>
            Prediction Graph
          </Text>
        </Flex>

        {hasData ? (
          <Flex mt={{ base: "-2.5vh", lg: "-1vh" }} position="relative">
            <Flex w={"100%"} direction={"column"} gap={"2vh"} h={"27vh"}>
              <Chart
                width="100%"
                options={options}
                series={series}
                type="line"
                height={"110%"}
              />
            </Flex>
          </Flex>
        ) : (
          <Flex h="260px" align="center" justify="center">
            <Text fontSize="sm" color="text.thrid">
              Pilih lokasi dan tekan Send untuk melihat prediksi.
            </Text>
          </Flex>
        )}
      </Flex>
    </>
  );
}
