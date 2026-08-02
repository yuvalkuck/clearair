//
// Created by uv on 02/08/2026.
//

#ifndef CLEARAIR_TASK_PARTICLE_H
#define CLEARAIR_TASK_PARTICLE_H
#include "cmsis_os.h"
#include "stm32f4xx_hal_i2c.h"
#include "FreeRTOS.h"
#include "queue.h"


class TaskParticle {
    QueueHandle_t msgQueue_;
public:
    TaskParticle() = default;

    bool configure(
        osMessageQueueId_t output_queue,
        I2C_HandleTypeDef* hi2c,
        uint8_t i2c_addr8 = 0x69
    );
    void run();
    [[noreturn]] void taskLoop();
};

#endif //CLEARAIR_TASK_PARTICLE_H
