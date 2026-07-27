//
// Created by uv on 21/07/2026
//
#include "stm32f4xx_hal.h"
#include "bme68x.h"
#include "bridge_bme680.h"
#include "cmsis_os.h"

namespace {
    constexpr uint32_t I2C_TIMEOUT_MS = 100;
    I2C_HandleTypeDef* i2cH;
    uint8_t dev_addr_ = 0x76 << 1;
}

/*
*    int8_t i2c_read(uint8_t reg_addr, uint8_t* reg_data, uint32_t len, void* intf_ptr);
    int8_t i2c_write(uint8_t reg_addr, const uint8_t* reg_data, uint32_t len, void* intf_ptr);
    void   delay_us(uint32_t period, void* intf_ptr);

 */


static int8_t i2c_read(uint8_t reg_addr, uint8_t* reg_data, uint32_t len, void* intf_ptr) {
    uint8_t addr8 = *static_cast<uint8_t*>(intf_ptr); // 8-bit addr stored in intf_ptr
    HAL_StatusTypeDef st = HAL_I2C_Mem_Read(
        i2cH, addr8, reg_addr, I2C_MEMADD_SIZE_8BIT,
        reg_data, len, I2C_TIMEOUT_MS);
    return (st == HAL_OK) ? 0 : -1;
}

static int8_t i2c_write(uint8_t reg_addr, const uint8_t* reg_data, uint32_t len, void* intf_ptr) {
    uint8_t addr8 = *static_cast<uint8_t*>(intf_ptr);
    HAL_StatusTypeDef st = HAL_I2C_Mem_Write(
        i2cH, addr8, reg_addr, I2C_MEMADD_SIZE_8BIT,
        const_cast<uint8_t*>(reg_data), len, I2C_TIMEOUT_MS);
    return (st == HAL_OK) ? 0 : -1;
}

static void delay_us(uint32_t period, void* /*intf_ptr*/) {
    // For short delays under RTOS, busy-wait; for longer, prefer vTaskDelay in caller context.
    // bme68x calls this with small values (µs), so a tight loop using DWT cycle counter
    // is common, or HAL_Delay-based approximation if µs precision isn't critical.
    uint32_t us = period;
    if (us < 1000) {
        volatile uint32_t cycles = (SystemCoreClock / 1000000U) * us / 5U;
        while (cycles--) { __NOP(); }
    }
    else {
        vTaskDelay(pdMS_TO_TICKS(us));
    }
}

static bme68x_dev sensorCfg = {0};


int initBridgeBME680(I2C_HandleTypeDef* hi2c, uint8_t dev_addr_7bit) {
    i2cH = hi2c;
    dev_addr_ = dev_addr_7bit << 1;

    sensorCfg.intf = BME68X_I2C_INTF;
    sensorCfg.read = i2c_read;
    sensorCfg.write = i2c_write;
    sensorCfg.delay_us = delay_us;
    sensorCfg.intf_ptr = &dev_addr_;
    sensorCfg.amb_temp = 25;

    // bsec_sensor_control()
    return  bme68x_init(&sensorCfg);
}
