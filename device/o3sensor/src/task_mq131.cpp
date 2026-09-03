#include "task_mq131.h"

#include "event_message.h"
#include "logger.h"
#include "stm32f4xx.h"
#include "timestamp.h"
#include "main.h"

extern ADC_HandleTypeDef hadc1;

bool SensorO3::configure() const {
    METHODTRACE

    uint32_t value = 0;
    for (auto limit = 5; limit > 0; --limit) {
        HAL_ADC_Start(&hadc1); // Start ADC conversion
        auto rc= HAL_ADC_PollForConversion(&hadc1, 10);
        if (rc == HAL_OK) {
            value = HAL_ADC_GetValue(&hadc1);
        } else {
            vTaskDelay(pdMS_TO_TICKS(1));
        }
        HAL_ADC_Stop(&hadc1); // Start ADC conversion
        if (value > 0) {
            break;
        }
    }
    return (value > 0 ? true : false);
}
static CommonMessage msg{};
[[noreturn]] void SensorO3::taskLoop() const {
    METHODTRACE
    msg.id = MQ131CO3;
    for (;;) {
        for (auto limit = 5; limit > 0; --limit) {
            HAL_ADC_Start(&hadc1); // Start ADC conversion
            auto rc = HAL_ADC_PollForConversion(&hadc1, 50);
            if (rc == HAL_OK) {
                msg.timestamp_ms = getTimestampMs();
                msg.payload.uiValue.value = HAL_ADC_GetValue(&hadc1);
                xQueueSend(msgQueue_, &msg, pdMS_TO_TICKS(5));
            } else {
                METHODLOGF(warn, "ADC1 timeout:{}", limit);
            }
            HAL_ADC_Stop(&hadc1); // Start ADC conversion
            if (rc == HAL_OK) {
                break;
            }
        }
        vTaskDelay(pdMS_TO_TICKS(60000));
    }
}
