//
// Created by uv on 21/07/2026.
//

#ifndef CLEARAIR_TELEMETRY_BME680_H
#define CLEARAIR_TELEMETRY_BME680_H
#include "stm32f4xx.h"
#include "stm32f4xx_hal_i2c.h"

namespace bridgeBME680 {
    void init(I2C_HandleTypeDef* hi2c, uint8_t dev_addr_7bit);

    // These match bme68x's required function pointer signatures
    int8_t i2c_read(uint8_t reg_addr, uint8_t* reg_data, uint32_t len, void* intf_ptr);
    int8_t i2c_write(uint8_t reg_addr, const uint8_t* reg_data, uint32_t len, void* intf_ptr);
    void   delay_us(uint32_t period, void* intf_ptr);
};
#endif //CLEARAIR_TELEMETRY_BME680_H
