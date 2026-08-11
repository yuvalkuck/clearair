//
// Created by uv on 11/08/2026.
//

#ifndef CLEARAIR_COLLECTED_DATA_H
#define CLEARAIR_COLLECTED_DATA_H
#include <stdint.h>
struct CollectedAirData {
    int8_t temperature; //  Temperature in C - BME680 with BSEC2
    uint8_t humidity; // Humidity in % - BME680 with BSEC2
    uint16_t metalOxideParticulates_25; // metal oxide particulates pm2.5 - SPS30
    uint16_t metalOxideParticulates_10; // metal oxide particulates pm10 - SPS30
    uint16_t carbonMonoxide; // co1 - MiCS-4514
    uint16_t indoorAirQualityIndex; // Indoor Air Quality (IAQ) index - BME680 with BSEC2
    float nitrogenDioxide; // no2 - MiCS-4514
    float ozone; // o3 - MQ131
    float breathVOC; // Breath VOC (bVOC) equivalent- BME680 with BSEC2
};
#endif //CLEARAIR_COLLECTED_DATA_H

