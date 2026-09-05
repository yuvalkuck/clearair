#ifndef CLEARAIR_TASK_FANCTRL_H
#define CLEARAIR_TASK_FANCTRL_H
#include <cstdint>


// Drives the RobotDyn AC dimmer's TRIAC gate via phase-cut control.
// ZC_INPUT (opto zero-cross detector) and DIMMER_LEVEL (opto-TRIAC gate)
// are the only two wires to the dimmer module, and everything needed to
// drive them - HAL callbacks included - lives in this module.
class ControllerFanMotor {
public:
    ControllerFanMotor();

    bool configure();

    // 0 = fan off. The fan stalls below ~50% speed, so any non-zero value
    // below that is clamped up to 50; 50-100 maps to the actual ON range.
    void speedPercent(uint8_t percent);

    // ISR-context hooks, called from this module's own HAL_GPIO_EXTI_Callback
    // and HAL_TIM_PeriodElapsedCallback - this is the hardware real-time
    // path and bypasses the RTOS/message queue entirely.
    void onZeroCross();
    void onGateCompareMatch();

};

#endif //CLEARAIR_TASK_FANCTRL_H
