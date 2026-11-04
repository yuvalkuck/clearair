//
// Created by uv on 11/08/2026.
//
#include "stm32g4xx.h"
#include "timestamp.h"
#include "main.h"
#include "event_message.h"
#include "task_mics4514.h"

#include <cmath>

#include "logger.h"
#define MICS4514_NOX_R0 1022	//Reference resistance for the NO2 sensing element
#define MICS4514_RED_R0 1000000	//Reference resistance for the RED sensing element

namespace {
    // No boosted preheat: the module's PRE pin is tied to GND. Boosting runs the
    // OX heater near 75 mW, above the datasheet's 50 mW maximum.
    // Standard settle time before trusting readings, applied on every boot.
    constexpr uint32_t MICS4514_WARMUP_SETTLE_MS = 3UL * 60UL * 1000UL;
    // Cold-boot-only continuous soak to reestablish the R0 baseline after the
    // sensor has been unpowered for an extended period.
    constexpr uint32_t MICS4514_COLD_SOAK_MS = 24UL * 3600UL * 1000UL;

    enum AdcRanks : uint8_t {
        RANK_CO1    = 0, // rank 1, ADC_CHANNEL_2,  PA1  MICS_CO1
        RANK_NO2    = 1, // rank 2, ADC_CHANNEL_4,  PA7  MICS_NO2
        RANK_BUTTON = 2, // rank 3, ADC_CHANNEL_14, PB11 BUTTONS_ADC
        MAX_RANKS   = 3, // number of ranks = hadc2.Init.NbrOfConversion
    };
}

extern ADC_HandleTypeDef hadc2;
static CommonMessage msg{};
// static CommonMessage keyMsg{};
static uint32_t adc2Scan[3]; // [0] CO (PA1), [1] NO2 (PA7), [2] buttons (PB11)
static TaskHandle_t adc2Waiter;

void SensorCO1NO2::configure(bool isColdBoot) {
    METHODTRACE
    isColdBoot_ = isColdBoot;
    HAL_ADCEx_Calibration_Start(&hadc2, ADC_SINGLE_ENDED);
}

// reference taken from: https://github.com/paulopereira98/mics4514-stm32-driver
[[noreturn]] void SensorCO1NO2::taskLoop() const {
    METHODTRACE
    if (isColdBoot_) {
        METHODLOGS(info, "MiCS-4514 cold-boot soak: %lums", (unsigned long)MICS4514_COLD_SOAK_MS);
        vTaskDelay(pdMS_TO_TICKS(MICS4514_COLD_SOAK_MS));
    }
    vTaskDelay(pdMS_TO_TICKS(MICS4514_WARMUP_SETTLE_MS));
    msg.id = MICS4514CO1NO2;
    // keyMsg.id = BUTTON_PRESSED;
    double voltage, Rs;
    adc2Waiter = xTaskGetCurrentTaskHandle();
    while (1) {
        auto startTM = getTimestampMs();
        ulTaskNotifyTake(pdTRUE, 0); // drop a stale notification from a late scan
        if (HAL_ADC_Start_DMA(&hadc2, adc2Scan, MAX_RANKS) != HAL_OK) {
            METHODLOG(warn, "ADC2 DMA start failed");
        } else if (ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(50)) == 0) {
            HAL_ADC_Stop_DMA(&hadc2);
            METHODLOG(warn, "ADC2 timeout");
        } else {
            if (adc2Scan[RANK_NO2] && adc2Scan[RANK_CO1]) {
                // NOX
                voltage = (3.3 * adc2Scan[RANK_NO2]) / 4096;
                Rs = ((5 / (voltage * 2)) - 1) * 19800; //calculate sensing resistance
                msg.payload.co1_no2.no2 = 1000 * std::powf(
                    10, 0.9682f * (logf(Rs / (double)MICS4514_NOX_R0) / logf(10)) - 0.8108f);
                //calculate gas concentration
                // RED
                voltage = (3.3 * adc2Scan[RANK_CO1]) / 4096;
                Rs = ((5 / voltage) - 1) * 47000; //calculate sensing resistance
                msg.payload.co1_no2.co1 = 1000 * powf(
                    10, -1.1859 * (logf(Rs / (double)MICS4514_RED_R0) / logf(10)) + 0.6201);
                //calculate gas concentration
                // send message
                msg.timestamp_ms = getTimestampMs();
                if (xQueueSend(msgQueue_, &msg, pdMS_TO_TICKS(10)) != pdPASS) {
                    METHODLOG(error, "failed to send message to queue");
                }
            }
            /* - will be added again with display & button events
            // Buttons on BUTTONS_ADC: none 4095, KEY1 372, KEY2 1016, KEY3 1663,
            // KEY4 2457 (12-bit). Thresholds are the midpoints.
            uint32_t rawKey = adc2Scan[RANK_BUTTON];
            if ( rawKey > 3276) {
                break;
            }
            if (rawKey < 694) {
                keyMsg.payload.button = BUTTON_UP;
            } else if (rawKey < 1340) {
                keyMsg.payload.button = BUTTON_DOWN;
            } else if (rawKey < 2068) {
                keyMsg.payload.button = BUTTON_LEFT;
            } else {
                keyMsg.payload.button = BUTTON_RIGHT;
            }
            keyMsg.timestamp_ms = getTimestampMs();
            if (xQueueSend(msgQueue_, &keyMsg, pdMS_TO_TICKS(10)) != pdPASS) {
                METHODLOG(error, "failed to send message to queue");
            }
            */
        }
        boundedDelay(getTimestampMs() - startTM);
    }
}

// ISR side, DMA transfer-complete for rank values
extern "C" void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef* hadc) {
    if (hadc->Instance == ADC2) {
        BaseType_t woken = pdFALSE;
        vTaskNotifyGiveFromISR(adc2Waiter, &woken);
        portYIELD_FROM_ISR(woken);
    }
}
