#include "task_mq131.h"

#include "event_message.h"
#include "logger.h"
#include "stm32f4xx.h"
#include "timestamp.h"
#include "main.h"

extern ADC_HandleTypeDef hadc1;

namespace {
// MQ131 datasheet: preheat time over 48h on a genuine cold start;
// 3 minutes is used as the settle time on a warm restart.
constexpr uint32_t MQ131_WARMUP_COLD_MS = 48UL * 3600UL * 1000UL;
constexpr uint32_t MQ131_WARMUP_WARM_MS = 3UL * 60UL * 1000UL;
}

bool SensorO3::configure(bool isColdBoot) {
    isColdBoot_ = isColdBoot;
    METHODTRACE

    uint32_t value = 0;
    for (auto limit = 5; limit > 0; --limit) {
        HAL_ADC_Start(&hadc1); // Start ADC conversion
        auto rc = HAL_ADC_PollForConversion(&hadc1, 10);
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
    auto warmupMs = isColdBoot_ ? MQ131_WARMUP_COLD_MS : MQ131_WARMUP_WARM_MS;
    METHODLOGS(info, "MQ131 warm-up: %lums (%s)", (unsigned long)warmupMs, isColdBoot_ ? "cold" : "warm");
    vTaskDelay(pdMS_TO_TICKS(warmupMs));
    msg.id = MQ131CO3;
    for (;;) {
        auto startTM = getTimestampMs();
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
        boundedDelay(getTimestampMs() - startTM);
    }
}
