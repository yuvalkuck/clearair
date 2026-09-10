//
// Created by uv on 30/07/2026.
//

#ifndef CLEARAIR_TIMESTAMP_H
#define CLEARAIR_TIMESTAMP_H
#include "cmsis_os2.h"

static uint32_t getTimestampMs() {
    // 64-bit intermediate avoids overflowing the tick*1000 multiplication in
    // 32 bits, which previously wrapped after ~71 minutes of uptime.
    return (uint32_t)((uint64_t)osKernelGetTickCount() * 1000ULL / osKernelGetTickFreq());
}

static int64_t getTimestampNs() {
    // Convert milliseconds to nanoseconds
    return 1000000ULL * getTimestampMs();
}

#endif //CLEARAIR_TIMESTAMP_H
