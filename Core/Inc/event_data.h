//
// Created by uv on 21/07/2026.
//

#ifndef CLEARAIR_EVENT_DATA_H
#define CLEARAIR_EVENT_DATA_H
#include <stdint.h>

typedef enum __attribute__((packed)){
        NO_VALUE = 0x00,
        IAQ,
        STATIC_IAQ,
        TEMPERATURE,
        HUMIDITY,
        PRESSURE,
        CO2_EQUIVALENT,
        VOC_EQUIVALENT,
        RAW_GAS,
    } ValueTypeBME;


    // Keep this POD (plain-old-data) so it can be copied through an RTOS queue safely.
    struct DataBME680 {
        ValueTypeBME type;
        float value;
        uint8_t accuracy; // BSEC accuracy 0-3, or 0xFF if n/a
    };

    struct DataUiValue {
        uint32_t value;
    };
    struct DataParticle {
        float mc_1p0;
        float mc_2p5;
        float mc_4p0;
        float mc_10p0;
        float nc_0p5;
        float nc_1p0;
        float nc_2p5;
        float nc_4p0;
        float nc_10p0;
        uint16_t typical_particle_size;
    };


#endif //CLEARAIR_EVENT_DATA_H
