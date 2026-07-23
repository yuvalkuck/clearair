//
// Created by uv on 22/07/2026.
//
#include "bridge_bme680.h"
#include "bme68x.h"
#include "task_bme680.h"
#include "bsec_interface.h"

static bme68x_dev sensorCfg;

TaskBme680::TaskBme680(I2C_HandleTypeDef* hi2c,
                       uint8_t i2c_addr8, // 8-bit shifted address
                       MessageQueue& output_queue) : hi2c_(hi2c), i2c_addr8_(i2c_addr8), msgQueue_(output_queue) {}

bool TaskBme680::load() {
    bridgeBME680::init(hi2c_, i2c_addr8_);

    sensorCfg.intf = BME68X_I2C_INTF;
    sensorCfg.read = bridgeBME680::i2c_read;
    sensorCfg.write = bridgeBME680::i2c_write;
    sensorCfg.delay_us = bridgeBME680::delay_us;
    sensorCfg.intf_ptr = &i2c_addr8_;
    sensorCfg.amb_temp = 25;

    // bsec_sensor_control()
    if (bme68x_init(&sensorCfg) != BME68X_OK) {
        return false;
    }

    if ( bsec_init() != BME68X_OK ) {
        return false;
    }
    return true;
}

bool TaskBme680::start() {
    return false;
}
