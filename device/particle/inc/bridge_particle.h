//
// Created by uv on 02/08/2026.
//

#ifndef CLEARAIR_BRIDGE_PARTICLE_H
#define CLEARAIR_BRIDGE_PARTICLE_H
#include "stm32f4xx_hal_i2c.h"

void initBridgeParticle(I2C_HandleTypeDef* hi2c,uint8_t dev_addr_7bit = 0x69);
#endif //CLEARAIR_BRIDGE_PARTICLE_H
