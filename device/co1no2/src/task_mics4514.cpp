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
#define MICS4514_NOX_PREHEAT 1	//seconds for preheating the NO2 sensing element
#define MICS4514_NOX_R0 1022	//Reference resistance for the NO2 sensing element
#define MICS4514_RED_R0 1000000	//Reference resistance for the RED sensing element

extern ADC_HandleTypeDef hadc2;
static CommonMessage msg{};
// reference taken from: https://github.com/paulopereira98/mics4514-stm32-driver
[[noreturn]] void SensorCO1NO2::taskLoop() const {
    METHODTRACE
    msg.id = MICS4514CO1NO2;
    HAL_GPIO_WritePin(MICS4514_PREHEAT_GPIO_Port, MICS4514_PREHEAT_Pin, GPIO_PIN_SET);
    HAL_Delay(MICS4514_NOX_PREHEAT * 1000);
    HAL_GPIO_WritePin(MICS4514_PREHEAT_GPIO_Port, MICS4514_PREHEAT_Pin, GPIO_PIN_RESET);
    double voltage, Rs;

    while (1) {
        HAL_ADC_Start(&hadc2);
        auto rc = HAL_ADC_PollForConversion(&hadc2, 50);
        if (rc == HAL_OK) {
            auto adc_value = HAL_ADC_GetValue(&hadc2);
            HAL_ADC_Stop(&hadc2);
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
                xQueueSend(msgQueue_, &msg, pdMS_TO_TICKS(5));
            }
        } else {
            METHODLOG(warn, "ADC2 timeout");
        }
        vTaskDelay(30000);
    }
}
