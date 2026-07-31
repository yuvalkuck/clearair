//
// Created by uv on 30/07/2026.
//

#ifndef CLEARAIR_TIMESTAMP_H
#define CLEARAIR_TIMESTAMP_H
#include "cmsis_os2.h"

static uint32_t getTimestampSec() {
    return osKernelGetTickCount() / osKernelGetTickFreq();
}

static uint32_t getTimestampMs() {
    // Convert ticks to milliseconds safely based on your RTOS clock rate
    // (If configTICK_RATE_HZ is 1000, ms directly equals ticks)
    return osKernelGetTickCount() * 1000 / osKernelGetTickFreq();
}

static int64_t getTimestampNs() {
    // Convert milliseconds to nanoseconds
    return 1000000ULL * getTimestampMs();
}

#endif //CLEARAIR_TIMESTAMP_H
