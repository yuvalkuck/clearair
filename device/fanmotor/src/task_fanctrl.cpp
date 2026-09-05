//
// Created by uv on 11/08/2026.
//

#include "task_fanctrl.h"
#include "logger.h"
#include "main.h"
#include "cmsis_os.h"

extern TIM_HandleTypeDef htim3;
// TIM3 is clocked at 1 MHz (90 MHz timer clock / (89+1) prescaler),
// so ARR counts double as a microsecond delay from the zero-cross.
static constexpr uint32_t TRIAC_MAX_POWER_DELAY_US = 500;   // fire early in the half-cycle -> 100% speed
static constexpr uint32_t TRIAC_MIN_POWER_DELAY_US = 10000; // fire late in the half-cycle -> 50% speed
static constexpr uint32_t GATE_PULSE_WIDTH_US = 100;        // opto-TRIAC gate trigger pulse width
static constexpr uint8_t MIN_ON_SPEED_PERCENT = 50;

static volatile uint8_t speedPercent_ = 0;
static uint32_t speedDelayUs_ = TRIAC_MIN_POWER_DELAY_US;
static volatile uint32_t zeroCrossCount_ = 0;


namespace {
    ControllerFanMotor* gActiveFanMotor = nullptr;
}

ControllerFanMotor::ControllerFanMotor() {
    gActiveFanMotor = this;
}

bool ControllerFanMotor::configure() {
    METHODTRACE

    // Validate the dimmer module is actually responding: its zero-cross
    // opto circuit toggles ZC_INPUT twice per AC mains cycle (~10ms @ 50Hz)
    // on its own, independent of anything we drive. If no zero-cross
    // interrupt arrives within a few mains cycles, the module isn't
    // connected/powered, or its ZC circuit has failed.
    const uint32_t crossingsBefore = zeroCrossCount_;
    vTaskDelay(pdMS_TO_TICKS(50));
    if (zeroCrossCount_ == crossingsBefore) {
        METHODLOG(error, "AC dimmer module not responding - no zero-cross detected")
        return false;
    }

    return true;
}

void ControllerFanMotor::speedPercent(uint8_t percent) {
    if (percent != 0 && percent < MIN_ON_SPEED_PERCENT) {
        percent = MIN_ON_SPEED_PERCENT;
    } else if (percent > 100) {
        percent = 100;
    }
    speedPercent_ = percent;
    if (percent == 0) {
        HAL_GPIO_WritePin(DIMMER_LEVEL_GPIO_Port, DIMMER_LEVEL_Pin, GPIO_PIN_RESET);
        return;
    }
    constexpr uint32_t span = TRIAC_MIN_POWER_DELAY_US - TRIAC_MAX_POWER_DELAY_US;
    constexpr uint32_t onRange = 100 - MIN_ON_SPEED_PERCENT;
    speedDelayUs_ = TRIAC_MIN_POWER_DELAY_US - (span * (percent - MIN_ON_SPEED_PERCENT)) / onRange;
}

void ControllerFanMotor::onZeroCross() {
    ++zeroCrossCount_;
    if (speedPercent_ == 0) {
        return; // gate stays low - TRIAC never fires
    }
    HAL_GPIO_WritePin(DIMMER_LEVEL_GPIO_Port, DIMMER_LEVEL_Pin, GPIO_PIN_RESET); // gate off between cycles
    htim3.Instance->CNT = 0;                    // Reset timer clock
    htim3.Instance->ARR = speedDelayUs_;  // Bind current delay
    HAL_TIM_Base_Start_IT(&htim3);        // Arm the update interrupt
}

void ControllerFanMotor::onGateCompareMatch() {
    HAL_GPIO_WritePin(DIMMER_LEVEL_GPIO_Port, DIMMER_LEVEL_Pin, GPIO_PIN_SET);

    // Hold the gate pulse for a fixed, brief duration. TIM3's counter is
    // free-running at 1 MHz, so this is a plain microsecond busy-wait;
    // the 16-bit cast matches the hardware counter's wrap width.
    const uint16_t fireTick = static_cast<uint16_t>(htim3.Instance->CNT);
    while (static_cast<uint16_t>(htim3.Instance->CNT - fireTick) < GATE_PULSE_WIDTH_US) {
    }

    HAL_GPIO_WritePin(DIMMER_LEVEL_GPIO_Port, DIMMER_LEVEL_Pin, GPIO_PIN_RESET);
    HAL_TIM_Base_Stop_IT(&htim3);
}

extern "C" void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin) {
    if (GPIO_Pin == ZC_INPUT_Pin && gActiveFanMotor != nullptr) {
        gActiveFanMotor->onZeroCross();
    }
}

// HAL_TIM_PeriodElapsedCallback is already defined in main.c for TIM6 (the
// HAL timebase tick), so it can't be redefined here for TIM3. Hooked instead
// from TIM3_IRQHandler's own USER CODE marker in stm32f4xx_it.c.
extern "C" void FanMotorOnTimerFired(void) {
    if (gActiveFanMotor != nullptr) {
        gActiveFanMotor->onGateCompareMatch();
    }
}
