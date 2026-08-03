// //
// // Created by uv on 22/07/2026.
// //
//
#include "stm32f4xx.h"
#include "task_particle.h"

#include "bridge_particle.h"
#include "sps30_i2c.h"
#include "cmsis_os.h"
#include "event_message.h"
#include "queue.h"
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
//     rc = bsec_init();
//     if (rc != BSEC_OK) {
//         return false;
//     }
//
//     rc = bsec_set_configuration(bsec_config_iaq, sizeof(bsec_config_iaq),
//                                 work_buffer, sizeof(work_buffer));
//     if (rc != BSEC_OK) {
//         return false;
//     }
//
//     bsec_sensor_configuration_t requestedOutputs[BSEC_REQUESTED_OUTPUTS];
//     uint8_t nRequested = 0;
//
//     requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_LP, BSEC_OUTPUT_IAQ};
//     requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_LP, BSEC_OUTPUT_STATIC_IAQ};
//     requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_LP, BSEC_OUTPUT_CO2_EQUIVALENT};
//     requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_LP, BSEC_OUTPUT_BREATH_VOC_EQUIVALENT};
//     requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_LP, BSEC_OUTPUT_RAW_TEMPERATURE};
//     requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_LP, BSEC_OUTPUT_RAW_HUMIDITY};
//
//     bsec_sensor_configuration_t requiredSensorSettings[BSEC_MAX_PHYSICAL_SENSOR];
//     uint8_t nRequired = BSEC_MAX_PHYSICAL_SENSOR;
//
//     rc = bsec_update_subscription(requestedOutputs, nRequested,
//                                   requiredSensorSettings, &nRequired);
//
//     return (rc == BSEC_OK);
    return true;
}
//
void TaskParticle::taskLoop() {
     for (;;) {
//         int64_t timestamp_ns = getTimestampNs();
//
//         bsec_bme_settings_t bme_settings;
//         bsec_sensor_control(timestamp_ns, &bme_settings);
//
//         if (bme_settings.trigger_measurement) {
//             applyBsecSensorSettings(bme_settings);
//
//             uint32_t wait_ms = 10;
//             if (bme_settings.run_gas && bme_settings.heater_duration > 0) {
//                 wait_ms = (uint32_t)bme_settings.heater_duration + 10;
//                 if (wait_ms > BSEC_TASK_MAX_WAIT_MS)   // critical fix #2: hard cap
//                     wait_ms = BSEC_TASK_MAX_WAIT_MS;
//             }
//             vTaskDelay(pdMS_TO_TICKS(wait_ms));
//
//             readAndSendToQueue(bme_settings, timestamp_ns);
//         }
//
//         int64_t next_call_ns = bme_settings.next_call - timestamp_ns;
//         uint32_t delay_ms = (next_call_ns > 0) ? (uint32_t)(next_call_ns / 1000000) : 1;
//         vTaskDelay(pdMS_TO_TICKS(delay_ms));
     }
}
