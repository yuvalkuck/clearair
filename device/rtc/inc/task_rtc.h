//
// Created by uv on 02/11/2026.
//

#ifndef CLEARAIR_TASK_RTC_H
#define CLEARAIR_TASK_RTC_H
#include "base_device_task.h"
#include "stm32g4xx_hal.h"

// PCF8563 on its own I2C bus. Only elapsed time matters: configure() measures
// how long the board was off, then taskLoop() stamps "last alive" once a minute.
class ClockRtc : public BaseDeviceTask {
public:
    ClockRtc() = default;
    // forceCold: BOOT_MODE button pressed. Any failure leaves isColdBoot() true.
    bool configure(I2C_HandleTypeDef* hi2c, bool forceCold);
    [[nodiscard]] bool isColdBoot() const { return isColdBoot_; }
    [[noreturn]] void taskLoop() const;

private:
    struct DateTime {
        uint8_t min, hour, day, wday;
        bool clockLost;   // VL bit: oscillator stopped, time not valid
    };
    // "Last alive" stamp, kept in the four alarm registers (all AE=1, alarm never fires)
    struct Stamp {
        uint8_t min, hour, day, wday;
    };

    bool writeReg(uint8_t reg, uint8_t* data, uint16_t len) const;
    bool readReg(uint8_t reg, uint8_t* data, uint16_t len) const;
    bool readTime(DateTime& dt) const;
    bool readStamp(Stamp& st) const;
    bool writeStamp() const;
    bool resetClock() const;
    static int32_t offlineMinutes(const DateTime& now, const Stamp& st);

    I2C_HandleTypeDef* hi2c_ = nullptr;
    bool isColdBoot_ = true;
};

#endif //CLEARAIR_TASK_RTC_H
