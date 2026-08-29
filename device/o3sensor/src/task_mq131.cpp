#include "task_mq131.h"

#include "event_message.h"
#include "stm32f4xx.h"
#include "timestamp.h"
#include "main.h"

constexpr uint32_t HEATER_TIME_MS_ON = 60 * 1000;
constexpr uint32_t HEATER_TIME_MS_OFF = 89 * 1000;
extern ADC_HandleTypeDef hadc1;

[[noreturn]] void SensorO3::taskLoop() const {
    CommonMessage msg{};
    msg.id = MQ131CO3;
    HAL_ADC_Start(&hadc1); // Start ADC conversion
    for (;;) {
        // HAL_GPIO_WritePin(MQ7_HEATER_CTRL_GPIO_Port, MQ7_HEATER_CTRL_Pin, GPIO_PIN_RESET); // short R → heater sees ~5V
        // vTaskDelay(pdMS_TO_TICKS(HEATER_TIME_MS_ON));
        // HAL_GPIO_WritePin(MQ7_HEATER_CTRL_GPIO_Port, MQ7_HEATER_CTRL_Pin, GPIO_PIN_SET); // short R → heater sees ~5V
        // vTaskDelay(pdMS_TO_TICKS(HEATER_TIME_MS_OFF));
        // if (HAL_ADC_PollForConversion(&hadc1, 10) == HAL_OK) {
        //     // to prevent long block in case of communication down, wait 10ms
        //     msg.timestamp_ms = getTimestampMs();
        //     msg.payload.uiValue.value = HAL_ADC_GetValue(&hadc1);
        //     xQueueSend(msgQueue_, &msg, pdMS_TO_TICKS(5));
        // }
        vTaskDelay(pdMS_TO_TICKS(60000));
    }
}
