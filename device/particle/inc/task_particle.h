//
// Created by uv on 02/08/2026.
//

#ifndef CLEARAIR_TASK_PARTICLE_H
#define CLEARAIR_TASK_PARTICLE_H

#include "stm32f4xx_hal_i2c.h"
#include "base_device_task.h"


class SensorParticle : public BaseDeviceTask {

public:
    SensorParticle() = default;
    bool configure(
        I2C_HandleTypeDef* hi2c);

    void taskLoop();
};

#endif //CLEARAIR_TASK_PARTICLE_H
