//
// Created by uv on 11/08/2026.
//

#ifndef CLEARAIR_TASK_MICS4514_H
#define CLEARAIR_TASK_MICS4514_H
#include "base_device_task.h"
class SensorCO1NO2 : public BaseDeviceTask {
public:
    SensorCO1NO2() = default;
    void configure(bool isColdBoot);
    [[noreturn]] void taskLoop() const;

private:
    bool isColdBoot_ = false;
};

#endif //CLEARAIR_TASK_MICS4514_H
