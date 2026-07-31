//
// Created by uv on 29/07/2026.
//

#ifndef CLEARAIR_TASK_MQ7_H
#define CLEARAIR_TASK_MQ7_H
#include "cmsis_os.h"
#include "FreeRTOS.h"
#include "queue.h"

class SensorCO1 {
    QueueHandle_t msgQueue_;

    public:
    SensorCO1() = default;
    bool configure(
        osMessageQueueId_t output_queue
        );
    static void run();
    [[noreturn]] void taskLoop() const;

};

#endif //CLEARAIR_TASK_MQ7_H
