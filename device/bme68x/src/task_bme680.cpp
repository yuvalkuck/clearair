//
// Created by uv on 22/07/2026.
//

#include "stm32f4xx.h"
#include "bridge_bme680.h"
#include "task_bme680.h"
#include "bme68x.h"
#include "bsec_interface.h"
#include "bsec_iaq.h"
#include "event_message.h"
#include "timestamp.h"
#include <cstring>
#include "logger.h"
static uint8_t work_buffer[BSEC_MAX_WORKBUFFER_SIZE];
static bme68x_dev commBridgeCfg = {0};
static constexpr uint32_t BSEC_TASK_MAX_WAIT_MS = 2000; // BME68x max heater dur
#define BSEC_REQUESTED_OUTPUTS 3
static bme68x_conf conf{};
static bme68x_heatr_conf heatr_conf{};

static auto applyBsecSensorSettings(const bsec_bme_settings_t& settings) {
    METHODTRACE
    memset(&conf, 0, sizeof(bme68x_conf));
    memset(&heatr_conf, 0, sizeof(heatr_conf));
    auto rc = bme68x_get_conf(&conf, &commBridgeCfg);
    if (rc != BME68X_OK) { return rc; }

    conf.os_hum = settings.humidity_oversampling;
    conf.os_temp = settings.temperature_oversampling;
    conf.os_pres = settings.pressure_oversampling;
    rc = bme68x_set_conf(&conf, &commBridgeCfg);
    if (rc != BME68X_OK) { return rc; }

    heatr_conf.enable = BME68X_ENABLE;
    heatr_conf.heatr_temp = settings.heater_temperature;
    heatr_conf.heatr_dur = settings.heater_duration;
    rc = bme68x_set_heatr_conf(BME68X_FORCED_MODE, &heatr_conf, &commBridgeCfg);
    if (rc != BME68X_OK) { return rc; }

    rc = bme68x_set_op_mode(BME68X_FORCED_MODE, &commBridgeCfg);
    return rc;
}

bool SensorBme68x::configure(I2C_HandleTypeDef* hi2c) {
    METHODTRACE
    auto rc = initBridgeBME68x(hi2c, commBridgeCfg, BME68X_I2C_ADDR_HIGH);
    if (rc != BME68X_OK) {
        METHODLOGS(error, "initBridgeBME68x != BME68X_OK: %i", rc)
        return false;
    }
    rc = bsec_init();
    if (rc != BSEC_OK) {
        METHODLOGS(error, "bsec_init != BME68X_OK: %i", rc)
        return false;
    }

    rc = bsec_set_configuration(bsec_config_iaq, sizeof(bsec_config_iaq),
                                work_buffer, sizeof(work_buffer));
    if (rc != BSEC_OK) {
        METHODLOGS(error, "bsec_set_configuration != BSEC_OK: %i", rc)
        return false;
    }

    bsec_sensor_configuration_t requestedOutputs[BSEC_REQUESTED_OUTPUTS];
    uint8_t nRequested = 0;

    requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_LP, BSEC_OUTPUT_BREATH_VOC_EQUIVALENT};
    requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_LP, BSEC_OUTPUT_SENSOR_HEAT_COMPENSATED_TEMPERATURE};
    requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_LP, BSEC_OUTPUT_SENSOR_HEAT_COMPENSATED_HUMIDITY};

    bsec_sensor_configuration_t requiredSensorSettings[BSEC_MAX_PHYSICAL_SENSOR];
    uint8_t nRequired = BSEC_MAX_PHYSICAL_SENSOR;

    rc = bsec_update_subscription(requestedOutputs, nRequested,
                                  requiredSensorSettings, &nRequired);

    return (rc == BSEC_OK);
}

static CommonMessage msg{};
static bsec_input_t inputs[BSEC_MAX_PHYSICAL_SENSOR];
static bme68x_data data;
static bsec_output_t outputs[BSEC_NUMBER_OUTPUTS];

void SensorBme68x::readAndSendToQueue(const bsec_bme_settings_t& s, int64_t timestamp_ns) {
    uint8_t n_data = 0;
    if (bme68x_get_data(BME68X_FORCED_MODE, &data, &n_data, &commBridgeCfg) != BME68X_OK || n_data == 0) return;

    uint8_t n_inputs = 0;

    if (s.process_data & BSEC_PROCESS_TEMPERATURE) {
        inputs[n_inputs].sensor_id = BSEC_INPUT_TEMPERATURE;
        inputs[n_inputs].signal = data.temperature;
        inputs[n_inputs].time_stamp = timestamp_ns;
        n_inputs++;
    }
    if (s.process_data & BSEC_PROCESS_HUMIDITY) {
        inputs[n_inputs].sensor_id = BSEC_INPUT_HUMIDITY;
        inputs[n_inputs].signal = data.humidity;
        inputs[n_inputs].time_stamp = timestamp_ns;
        n_inputs++;
    }
    if (s.process_data & BSEC_PROCESS_GAS) {
        inputs[n_inputs].sensor_id = BSEC_INPUT_GASRESISTOR;
        inputs[n_inputs].signal = data.gas_resistance;
        inputs[n_inputs].time_stamp = timestamp_ns;
        n_inputs++;
    }

    uint8_t n_outputs = BSEC_NUMBER_OUTPUTS;
    if (n_inputs == 0) return;
    if (bsec_do_steps(inputs, n_inputs, outputs, &n_outputs) != BSEC_OK) return;

    msg.id = BME680;
    msg.timestamp_ms = getTimestampMs();
    auto& payload = msg.payload.bme680;
    std::memset(&payload, 0, sizeof(msg.payload.bme680));
    for (uint8_t i = 0; i < n_outputs; i++) {
        auto &output = outputs[i];
        switch (output.sensor_id) {
            case BSEC_OUTPUT_BREATH_VOC_EQUIVALENT:
                payload.indoorAirQualityIndex = static_cast<uint16_t>(output.signal);
                break;
            case BSEC_OUTPUT_SENSOR_HEAT_COMPENSATED_TEMPERATURE:
                payload.temperature = static_cast<int8_t>(output.signal);
                break;
            case BSEC_OUTPUT_SENSOR_HEAT_COMPENSATED_HUMIDITY:
                payload.humidity = static_cast<uint8_t>(output.signal);
                break;
            default:
                break;
        }
    }
    xQueueSend(msgQueue_, &msg, pdMS_TO_TICKS(5));
}

static bsec_bme_settings_t bme_settings;

void SensorBme68x::taskLoop() {
    for (;;) {
        int64_t timestamp_ns = getTimestampNs();
        bsec_sensor_control(timestamp_ns, &bme_settings);

        if (bme_settings.trigger_measurement) {
            applyBsecSensorSettings(bme_settings);

            uint32_t wait_ms = 10;
            if (bme_settings.run_gas && bme_settings.heater_duration > 0) {
                wait_ms = (uint32_t)bme_settings.heater_duration + 10;
                if (wait_ms > BSEC_TASK_MAX_WAIT_MS) // critical fix #2: hard cap
                    wait_ms = BSEC_TASK_MAX_WAIT_MS;
            }
            vTaskDelay(pdMS_TO_TICKS(wait_ms));

            readAndSendToQueue(bme_settings, timestamp_ns);
        }

        int64_t next_call_ns = bme_settings.next_call - getTimestampNs();
        boundedDelay((next_call_ns > 0) ? (uint32_t)(next_call_ns / 1000000) : 1);
    }
}
