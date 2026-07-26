//
// Created by uv on 22/07/2026.
//

#ifndef CLEARAIR_TASK_BME680_H
#define CLEARAIR_TASK_BME680_H
#include "cmsis_os2.h"
#include "stm32f4xx_hal_i2c.h"
// #include "fixed_queue.h"
// #include "bme68x_defs.h"

/**
 * the class use the BSEC lib, so get new data will invoke the run() method every X seconds
 * and if there is a new data the lib will asynchronicity send back to the message queue.
 * " Calling .run(), If the internal sampling interval X seconds has not elapsed,
 * .run() does nothing and exits immediately."
 */
class TaskBme680 {
    I2C_HandleTypeDef* hi2c_;
    uint8_t i2c_addr8_;
    osMessageQueueId_t & msgQueue_;

public:
    TaskBme680(
        I2C_HandleTypeDef* hi2c,
        osMessageQueueId_t* output_queue,
        uint8_t i2c_addr8 = 0x76 // 7-bit address
        );

    bool load();
    bool start();
};
#endif //CLEARAIR_TASK_BME680_H
