//
// Created by uv on 21/07/2026.
//

#ifndef CLEARAIR_EVENT_MESSAGE_H
#define CLEARAIR_EVENT_MESSAGE_H

#include "event_data.h"
namespace Message {
    enum class UniqueID : uint8_t {
        BME680 = 0,
        // Add other sensors here, e.g. LSM6DS3, BMP280, etc.
    };

    struct Sensor {
        UniqueID id;
        uint32_t timestamp_ms;
        union {
            Data::BME680D bme680;
            // BmpData bmp; etc. for other sensors
        } payload;
    };
}
#endif //CLEARAIR_EVENT_MESSAGE_H
