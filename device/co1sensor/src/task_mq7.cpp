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

constexpr uint8_t HEATER_TIME_SEC_ON = 60;
constexpr uint8_t HEATER_TIME_SEC_OFF = 90;
extern ADC_HandleTypeDef hadc1;

[[noreturn]] void SensorCO1::taskLoop() const {
    CommonMessage msg{};
    msg.id = MQ7CO1;
    HAL_ADC_Start(&hadc1); // Start ADC conversion
    for (;;) {
        // turn on Heater

        HAL_GPIO_WritePin(MQ7_HEATER_CTRL_GPIO_Port, MQ7_HEATER_CTRL_Pin, GPIO_PIN_SET);
        vTaskDelay(pdMS_TO_TICKS(HEATER_TIME_SEC_ON));
        HAL_GPIO_WritePin(MQ7_HEATER_CTRL_GPIO_Port, MQ7_HEATER_CTRL_Pin, GPIO_PIN_RESET);
        vTaskDelay(pdMS_TO_TICKS(HEATER_TIME_SEC_ON-1));
        if (HAL_ADC_PollForConversion(&hadc1, 1000) == HAL_OK) {
            msg.timestamp_ms = getTimestampMs();
            msg.payload.uiValue.value = HAL_ADC_GetValue(&hadc1);
            xQueueSend(msgQueue_, &msg, pdMS_TO_TICKS(5));
        }
    }
}
