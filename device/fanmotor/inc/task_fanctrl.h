//
// Created by uv on 11/08/2026.
//

#ifndef CLEARAIR_TASK_FANCTRL_H
#define CLEARAIR_TASK_FANCTRL_H
#include "base_device_task.h"

class ControllerFanMotor : public BaseDeviceTask {
public:
    ControllerFanMotor() = default;
    [[noreturn]] void taskLoop() const;
};

#endif //CLEARAIR_TASK_FANCTRL_H
