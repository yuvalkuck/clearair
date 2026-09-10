//
// Created by uv on 11/08/2026.
//
#include "stm32f4xx.h"
#include "timestamp.h"
#include "main.h"
#include "event_message.h"
#include "task_mics4514.h"

#include <cmath>

#include "logger.h"
#define MICS4514_NOX_R0 1022	//Reference resistance for the NO2 sensing element
#define MICS4514_RED_R0 1000000	//Reference resistance for the RED sensing element

namespace {
// SGX AN2: boosted-power preheat pulse to bring the OX/NO2 element up to
// temperature quickly, applied on every boot regardless of cold/warm.
constexpr uint32_t MICS4514_BOOST_PREHEAT_MS = 30UL * 1000UL;
// Standard settle time before trusting readings, applied on every boot.
constexpr uint32_t MICS4514_WARMUP_SETTLE_MS = 3UL * 60UL * 1000UL;
// Cold-boot-only continuous soak to reestablish the R0 baseline after the
// sensor has been unpowered for an extended period.
constexpr uint32_t MICS4514_COLD_SOAK_MS = 24UL * 3600UL * 1000UL;
}

extern ADC_HandleTypeDef hadc2;
static CommonMessage msg{};
void SensorCO1NO2::configure(bool isColdBoot) {
    isColdBoot_ = isColdBoot;
    METHODTRACE
}
// reference taken from: https://github.com/paulopereira98/mics4514-stm32-driver
[[noreturn]] void SensorCO1NO2::taskLoop() const {
    METHODTRACE
    HAL_GPIO_WritePin(MICS4514_PREHEAT_GPIO_Port, MICS4514_PREHEAT_Pin, GPIO_PIN_SET);
    vTaskDelay(pdMS_TO_TICKS(MICS4514_BOOST_PREHEAT_MS));
    HAL_GPIO_WritePin(MICS4514_PREHEAT_GPIO_Port, MICS4514_PREHEAT_Pin, GPIO_PIN_RESET);
    if (isColdBoot_) {
        METHODLOGS(info, "MiCS-4514 cold-boot soak: %lums", (unsigned long)MICS4514_COLD_SOAK_MS);
        vTaskDelay(pdMS_TO_TICKS(MICS4514_COLD_SOAK_MS));
}
    vTaskDelay(pdMS_TO_TICKS(MICS4514_WARMUP_SETTLE_MS));
    msg.id = MICS4514CO1NO2;
    double voltage, Rs;

    while (1) {
        auto startTM = getTimestampMs();
        HAL_ADC_Start(&hadc2);
        auto rc = HAL_ADC_PollForConversion(&hadc2, 50);
        if (rc == HAL_OK) {
            auto adc_value = HAL_ADC_GetValue(&hadc2);
            if (adc_value) {
                // NOX
                voltage = (3.3 * adc_value) / 4096;
                Rs = ((5 / (voltage * 2)) - 1) * 19800; //calculate sensing resistance
                msg.payload.co1_no2.no2 = 1000 * std::powf(
                    10, 0.9682f * (logf(Rs / (double)MICS4514_NOX_R0) / logf(10)) - 0.8108f);
                //calculate gas concentration
                // RED
                Rs = ((5 / voltage) - 1) * 47000; //calculate sensing resistance
                msg.payload.co1_no2.co1 = 1000 * powf(
                    10, -1.1859 * (logf(Rs / (double)MICS4514_RED_R0) / logf(10)) + 0.6201);
                //calculate gas concentration
                // send message
                msg.timestamp_ms = getTimestampMs();
                auto qrc = xQueueSend(msgQueue_, &msg, pdMS_TO_TICKS(10));
                if ( qrc != pdPASS ) {
                    METHODLOG(error, "failed to send message to queue");
                }
            }
        } else {
            METHODLOG(warn, "ADC2 timeout");
        }
        HAL_ADC_Stop(&hadc2);
        boundedDelay(getTimestampMs() - startTM);
    }
}
