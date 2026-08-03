//
// Created by uv on 03/08/2026.
//

#ifndef CLEARAIR_BASE_DEVICE_TASK_H
#define CLEARAIR_BASE_DEVICE_TASK_H
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
    }
};
#endif //CLEARAIR_BASE_TASK_H
