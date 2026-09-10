//
// Created by uv on 29/07/2026.
//

#ifndef CLEARAIR_TASK_MQ131_H
#define CLEARAIR_TASK_MQ131_H
#include "base_device_task.h"

class SensorO3 : public BaseDeviceTask {
    public:
    SensorO3() = default;
    bool configure(bool isColdBoot);
    [[noreturn]] void taskLoop() const;

    private:
    bool isColdBoot_ = false;
};

#endif //CLEARAIR_TASK_MQ131_H
