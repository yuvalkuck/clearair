// //
// // Created by uv on 22/07/2026.
// //
//
#include "stm32f4xx.h"
#include "task_particle.h"

#include <stdio.h>
#include "bridge_particle.h"
#include "sps30_i2c.h"
#include "sensirion_i2c_hal.h"
#include "timestamp.h"
#include "event_message.h"

// #include "timestamp.h"

// static uint8_t work_buffer[BSEC_MAX_WORKBUFFER_SIZE];
// static bme68x_dev commBridgeCfg = {0};
// static constexpr uint32_t BSEC_TASK_MAX_WAIT_MS     = 2000; // BME68x max heater dur
// #define BSEC_REQUESTED_OUTPUTS 6
//
// static auto applyBsecSensorSettings(const bsec_bme_settings_t& settings) {
//     bme68x_conf conf{};
//     bme68x_heatr_conf heatr_conf{};
//
//     auto rc = bme68x_get_conf(&conf, &commBridgeCfg);
//     if (rc != BME68X_OK) { return rc; }
//
//     conf.os_hum = settings.humidity_oversampling;
//     conf.os_temp = settings.temperature_oversampling;
//     conf.os_pres = settings.pressure_oversampling;
//     rc = bme68x_set_conf(&conf, &commBridgeCfg);
//     if (rc != BME68X_OK) { return rc; }
//
//     heatr_conf.enable = BME68X_ENABLE;
//     heatr_conf.heatr_temp = settings.heater_temperature;
//     heatr_conf.heatr_dur = settings.heater_duration;
//     rc = bme68x_set_heatr_conf(BME68X_FORCED_MODE, &heatr_conf, &commBridgeCfg);
//     if (rc != BME68X_OK) { return rc; }
//
//     rc = bme68x_set_op_mode(BME68X_FORCED_MODE, &commBridgeCfg);
//     return rc;
// }
//
bool TaskParticle::configure(I2C_HandleTypeDef* hi2c) {
    initBridgeParticle(hi2c, SPS30_I2C_ADDR_69);
    sps30_init(SPS30_I2C_ADDR_69);
    auto rc = sps30_stop_measurement();
    // int8_t serial_number[32] = {0};
    // int8_t product_type[8] = {0};
    // rc = sps30_read_serial_number(serial_number, 32);
    // printf("serial_number: %p\n", serial_number);
    // rc = sps30_read_product_type(product_type, 8);
    // printf("product_type: %p\n", product_type);

    return (rc == 0);
}

//
constexpr auto PARTICAL_CYCLE_TIME_MS = 60 * 1000;
constexpr auto PARTICAL_ONERROR_CYCLE_MS = 10 * 1000;

void TaskParticle::taskLoop() {
    CommonMessage msg{};
    msg.id = SPS30Particle;
    auto& payload = msg.payload.particle;
    auto rc = sps30_start_measurement(SPS30_OUTPUT_FORMAT_OUTPUT_FORMAT_FLOAT);
    sensirion_i2c_hal_sleep_usec(10000);
    uint16_t data_ready_flag = 0;
    for (;;) {
        rc = sps30_read_data_ready_flag(&data_ready_flag);
        if (rc != 0) {
            printf("error executing read_data_ready_flag(): %i\n", rc);
            vTaskDelay(pdMS_TO_TICKS(PARTICAL_ONERROR_CYCLE_MS));
            continue;
        }
        rc = sps30_read_measurement_values_float(
            &payload.mc_1p0, &payload.mc_2p5, &payload.mc_4p0, &payload.mc_10p0, &payload.nc_0p5,
            &payload.nc_1p0, &payload.nc_2p5,
            &payload.nc_4p0, &payload.nc_10p0, &payload.typical_particle_size);
        if (rc != 0) {
            printf("rc executing read_measurement_values_uint16(): %i\n",
                   rc);
            vTaskDelay(pdMS_TO_TICKS(PARTICAL_ONERROR_CYCLE_MS));
            continue;
        }
        msg.timestamp_ms = getTimestampMs();
        xQueueSend(msgQueue_, &msg, pdMS_TO_TICKS(5));
        vTaskDelay(pdMS_TO_TICKS(PARTICAL_CYCLE_TIME_MS));
    }
}
