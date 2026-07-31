#include "task_mq7.h"

#include "event_message.h"
#include "stm32f4xx.h"
#include "timestamp.h"
#include "main.h"

extern osThreadId_t co1SensorTaskHandle;

bool SensorCO1::configure(osMessageQueueId_t output_queue) {
    msgQueue_ = static_cast<QueueHandle_t>(output_queue);
    return true;
}

void SensorCO1::run() {
    osThreadResume(co1SensorTaskHandle);
}

constexpr uint32_t HEATER_TIME_MS_ON = 60 * 1000;
constexpr uint32_t HEATER_TIME_MS_OFF = 89 * 1000;
extern ADC_HandleTypeDef hadc1;
extern TIM_HandleTypeDef htim5;
constexpr uint32_t TIM_CHANNEL = TIM_CHANNEL_2;

[[noreturn]] void SensorCO1::taskLoop() const {
    const uint32_t PwmPeriod5v = __HAL_TIM_GET_AUTORELOAD(&htim5);
    const uint32_t PwmPeriod1v4 = (PwmPeriod5v * 28) / 100; // ~28% Duty
    CommonMessage msg{};
    msg.id = MQ7CO1;
    HAL_ADC_Start(&hadc1); // Start ADC conversion
    for (;;) {
        // turn on Heater
        __HAL_TIM_SET_COMPARE(&htim5, TIM_CHANNEL, PwmPeriod5v);
        vTaskDelay(pdMS_TO_TICKS(HEATER_TIME_MS_ON));
        __HAL_TIM_SET_COMPARE(&htim5, TIM_CHANNEL, PwmPeriod1v4);
        vTaskDelay(pdMS_TO_TICKS(HEATER_TIME_MS_OFF));
        if (HAL_ADC_PollForConversion(&hadc1, 10) == HAL_OK) {
            msg.timestamp_ms = getTimestampMs();
            msg.payload.uiValue.value = HAL_ADC_GetValue(&hadc1);
            xQueueSend(msgQueue_, &msg, pdMS_TO_TICKS(5));
        }
        vTaskDelay(1);
    }
}
