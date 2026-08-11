//
// Created by uv on 11/08/2026.
//
#include "stm32f4xx.h"
#include "timestamp.h"
#include "main.h"
#include "event_message.h"
#include "task_mics4514.h"

[[noreturn]] void SensorCO1NO2::taskLoop() const {
    CommonMessage msg{};
    msg.id = MICS4514CO1NO2;
    while (1) {
        vTaskDelay(1);
    }
}
