//
// Created by uv on 22/07/2026.
//
#include "bridge_bme680.h"
#include "task_bme680.h"
#include "bsec_interface.h"
#include "bsec_iaq.h"


TaskBme680::TaskBme680(I2C_HandleTypeDef* hi2c,
                       osMessageQueueId_t* output_queue,
                       uint8_t i2c_addr8 // 8-bit shifted address
) : hi2c_(hi2c), i2c_addr8_(i2c_addr8), msgQueue_(*output_queue) {}

static uint8_t work_buffer[BSEC_MAX_WORKBUFFER_SIZE];

bool TaskBme680::configure() {
    auto rc = initBridgeBME680(hi2c_, i2c_addr8_);
    if (rc != BME68X_OK) {
        return false;
    }
    rc = bsec_init();
    if (rc != BSEC_OK) {
        return false;
    }

    rc = bsec_set_configuration(bsec_config_iaq, sizeof(bsec_config_iaq),
                                work_buffer, sizeof(work_buffer));


    return (rc == BSEC_OK);
}

bool TaskBme680::run() {

    bsec_sensor_configuration_t requestedOutputs[6];
    uint8_t nRequested = 0;

    requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_CONT, BSEC_OUTPUT_IAQ};
    requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_CONT, BSEC_OUTPUT_STATIC_IAQ};
    requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_CONT, BSEC_OUTPUT_CO2_EQUIVALENT};
    requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_CONT, BSEC_OUTPUT_BREATH_VOC_EQUIVALENT};
    requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_CONT, BSEC_OUTPUT_RAW_TEMPERATURE};
    requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_CONT, BSEC_OUTPUT_RAW_HUMIDITY};

    bsec_sensor_configuration_t requiredSensorSettings[BSEC_MAX_PHYSICAL_SENSOR];
    uint8_t nRequired = BSEC_MAX_PHYSICAL_SENSOR;

    auto rc = bsec_update_subscription(requestedOutputs, nRequested,
                                  requiredSensorSettings, &nRequired);
    return (rc == BSEC_OK);
}
