//
// Created by uv on 21/07/2026.
//

#ifndef CLEARAIR_TELEMETRY_BME680_H
#define CLEARAIR_TELEMETRY_BME680_H
#include "stm32f4xx_hal_i2c.h"
#include "bme68x_defs.h"


    int initBridgeBME68x(I2C_HandleTypeDef* hi2c,bme68x_dev &commBridgeCfg, uint8_t dev_addr_7bit = 0x76);

    // These match bme68x's required function pointer signatures

#endif //CLEARAIR_TELEMETRY_BME680_H
