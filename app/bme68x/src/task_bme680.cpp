//
// Created by uv on 22/07/2026.
//
#include "bridge_bme680.h"
#include "bme68x.h"
#include "task_bme680.h"
#include "bsec_interface.h"




TaskBme680::TaskBme680(I2C_HandleTypeDef* hi2c,
                       uint8_t i2c_addr8, // 8-bit shifted address
                       osMessageQueueId_t* output_queue) : hi2c_(hi2c), i2c_addr8_(i2c_addr8), msgQueue_(*output_queue) {}

bool TaskBme680::load() {
    if (!bridgeBME680::init(hi2c_, i2c_addr8_) || ( bsec_init() != BME68X_OK ) ) {
        return false;
    }
    bsec_sensor_configuration_t requestedOutputs[6];
    uint8_t nRequested = 0;

    requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_LP, BSEC_OUTPUT_IAQ};
    requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_LP, BSEC_OUTPUT_STATIC_IAQ};
    requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_LP, BSEC_OUTPUT_CO2_EQUIVALENT};
    requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_LP, BSEC_OUTPUT_BREATH_VOC_EQUIVALENT};
    requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_LP, BSEC_OUTPUT_RAW_TEMPERATURE};
    requestedOutputs[nRequested++] = {BSEC_SAMPLE_RATE_LP, BSEC_OUTPUT_RAW_HUMIDITY};

    bsec_sensor_configuration_t requiredSensorSettings[BSEC_MAX_PHYSICAL_SENSOR];
    uint8_t nRequired = BSEC_MAX_PHYSICAL_SENSOR;

    return bsec_update_subscription(requestedOutputs, nRequested,
                                     requiredSensorSettings, &nRequired) == BSEC_OK;
}

bool TaskBme680::start() {
    return false;
}
