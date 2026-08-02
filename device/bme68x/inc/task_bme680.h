//
// Created by uv on 22/07/2026.
//

#ifndef CLEARAIR_TASK_BME680_H
#define CLEARAIR_TASK_BME680_H
#include "cmsis_os.h"
#include "stm32f4xx_hal_i2c.h"
#include "bme68x_defs.h"
#include "bsec_datatypes.h"
#include "FreeRTOS.h"
#include "queue.h"
/**
 * the class use the BSEC lib, so get new data will invoke the run() method every X seconds
 * and if there is a new data the lib will asynchronicity send back to the message queue.
 * " Calling .run(), If the internal sampling interval X seconds has not elapsed,
 * .run() does nothing and exits immediately."
 */
class TaskBme680 {
    QueueHandle_t msgQueue_;
    void readAndSendToQueue(const bsec_bme_settings_t& s, int64_t timestamp_ns);
public:
    TaskBme680() = default;

    bool configure(
        osMessageQueueId_t output_queue,
        I2C_HandleTypeDef* hi2c,
        uint8_t i2c_addr8 = BME68X_I2C_ADDR_LOW
    );
    void run();
    [[noreturn]] void taskLoop();
};
#endif //CLEARAIR_TASK_BME680_H
