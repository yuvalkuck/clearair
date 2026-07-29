//
// Created by uv on 21/07/2026.
//

#ifndef CLEARAIR_EVENT_MESSAGE_H
#define CLEARAIR_EVENT_MESSAGE_H

#include "event_data.h"

    typedef enum __attribute__((packed)) {
        InvalidSensor = 0,
        BME680,
        MQ7CO1,
        // Add other sensors here, e.g. LSM6DS3, BMP280, etc.
    } UniqueID;

    struct CommonMessage {
        UniqueID id;
        uint32_t timestamp_ms;
        union {
            struct DataBME680 bme680;
            // BmpData bmp; etc. for other sensors
        } payload;
    };

#endif //CLEARAIR_EVENT_MESSAGE_H
