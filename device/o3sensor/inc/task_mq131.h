//
// Created by uv on 29/07/2026.
//

#ifndef CLEARAIR_TASK_MQ7_H
#define CLEARAIR_TASK_MQ7_H
#include "base_device_task.h"

class SensorO3 : public BaseDeviceTask {
    public:
    SensorO3() = default;
    bool configure() const;
    [[noreturn]] void taskLoop() const;

};

#endif //CLEARAIR_TASK_MQ7_H
