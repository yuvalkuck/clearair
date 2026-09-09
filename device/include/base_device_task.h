//
// Created by uv on 03/08/2026.
//

#ifndef CLEARAIR_BASE_DEVICE_TASK_H
#define CLEARAIR_BASE_DEVICE_TASK_H
#include <cstdint>
#include "cmsis_os.h"
#include "FreeRTOS.h"
#include "queue.h"

class BaseDeviceTask {
protected:
    osThreadId_t osThreadId_;
    QueueHandle_t msgQueue_;
    BaseDeviceTask() = default;
public:
    void setup(osThreadId_t threadID, osMessageQueueId_t msgQ) {
        osThreadId_ = threadID;
        msgQueue_ = static_cast<QueueHandle_t>(msgQ);
    }

    void resume(bool abort = false) const {
        if (abort) {
            osThreadTerminate(osThreadId_);
            return;
        }
        osThreadResume(osThreadId_);
        vTaskDelay(pdMS_TO_TICKS(50));
    }

    // Sleeps the rest of the shared per-iteration sleep/work budget
    // (DETECTION_SLEEP_LOOP_LIMIT - elapsedMs), unless elapsedMs already exceeds that
    // budget, in which case it logs a warning and does a short 5-tick yield instead;
    // defined out-of-line so it's compiled once instead of duplicated into every
    // sensor task's static library.
    void boundedDelay(uint32_t elapsedMs) const;
};
#endif //CLEARAIR_BASE_TASK_H
