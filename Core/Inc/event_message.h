//
// Created by uv on 21/07/2026.
//

#ifndef CLEARAIR_EVENT_MESSAGE_H
#define CLEARAIR_EVENT_MESSAGE_H

#include "event_data.h"

    typedef enum __attribute__((packed)) {
        InvalidID = 0,
        // Sensors
        BME680,
        MQ131CO3,
        SPS30Particle,
        MICS4514CO1NO2,
        // Other Events
    } UniqueID;

    struct CommonMessage {
        UniqueID id;
        uint32_t timestamp_ms;
        union {
            struct DataBME680 bme680;
            struct DataUiValue uiValue;
            struct DataParticle particle;
            struct DataCO1NO2 co1_no2;
            // BmpData bmp; etc. for other sensors
        } payload;
    };

#endif //CLEARAIR_EVENT_MESSAGE_H
