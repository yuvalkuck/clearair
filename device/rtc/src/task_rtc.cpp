#include "task_rtc.h"

#include "logger.h"

namespace {
constexpr uint16_t PCF8563_ADDR = 0x51 << 1;   // HAL wants the 8-bit form
constexpr uint32_t I2C_TIMEOUT_MS = 10;

constexpr uint8_t REG_CONTROL_1 = 0x00;
constexpr uint8_t REG_CONTROL_2 = 0x01;
constexpr uint8_t REG_SECONDS = 0x02;
constexpr uint8_t REG_MINUTE_ALARM = 0x09;
constexpr uint8_t REG_CLKOUT = 0x0D;

constexpr uint8_t CONTROL_1_STOP = 0x20;
constexpr uint8_t SECONDS_VL = 0x80;
constexpr uint8_t ALARM_AE = 0x80;

// Offline under this gives the MQ131 warm restart, at or over it the 48 h preheat.
constexpr int32_t OFFLINE_COLD_LIMIT_MIN = 60;
constexpr uint32_t STAMP_PERIOD_MS = 60UL * 1000UL;

constexpr uint8_t fromBcd(uint8_t v) { return static_cast<uint8_t>((v >> 4) * 10 + (v & 0x0F)); }
constexpr uint8_t toBcd(uint8_t v) { return static_cast<uint8_t>(((v / 10) << 4) | (v % 10)); }
}

bool ClockRtc::writeReg(uint8_t reg, uint8_t* data, uint16_t len) const {
    return HAL_I2C_Mem_Write(hi2c_, PCF8563_ADDR, reg, I2C_MEMADD_SIZE_8BIT, data, len, I2C_TIMEOUT_MS) == HAL_OK;
}

bool ClockRtc::readReg(uint8_t reg, uint8_t* data, uint16_t len) const {
    return HAL_I2C_Mem_Read(hi2c_, PCF8563_ADDR, reg, I2C_MEMADD_SIZE_8BIT, data, len, I2C_TIMEOUT_MS) == HAL_OK;
}

// One burst read: the chip freezes its counters during the access, so the fields agree.
bool ClockRtc::readTime(DateTime& dt) const {
    uint8_t r[5];
    if (!readReg(REG_SECONDS, r, sizeof(r))) {
        return false;
    }
    dt.clockLost = (r[0] & SECONDS_VL) != 0;
    dt.min = fromBcd(r[1] & 0x7F);
    dt.hour = fromBcd(r[2] & 0x3F);
    dt.day = fromBcd(r[3] & 0x3F);
    dt.wday = r[4] & 0x07;
    return true;
}

bool ClockRtc::readStamp(Stamp& st) const {
    uint8_t r[4];
    if (!readReg(REG_MINUTE_ALARM, r, sizeof(r))) {
        return false;
    }
    st.min = fromBcd(r[0] & 0x7F);
    st.hour = fromBcd(r[1] & 0x3F);
    st.day = fromBcd(r[2] & 0x3F);
    st.wday = r[3] & 0x07;
    // Never written (fresh module): register contents are undefined
    return st.min <= 59 && st.hour <= 23 && st.day >= 1 && st.day <= 31 && st.wday <= 6;
}

bool ClockRtc::writeStamp() const {
    DateTime now{};
    if (!readTime(now)) {
        return false;
    }
    uint8_t w[4] = {
        static_cast<uint8_t>(toBcd(now.min) | ALARM_AE),
        static_cast<uint8_t>(toBcd(now.hour) | ALARM_AE),
        static_cast<uint8_t>(toBcd(now.day) | ALARM_AE),
        static_cast<uint8_t>(now.wday | ALARM_AE),
    };
    return writeReg(REG_MINUTE_ALARM, w, sizeof(w));
}

// Only elapsed time matters, so the clock restarts at an arbitrary epoch:
// Saturday 2000-01-01 00:00:00. Writing the seconds register clears VL.
bool ClockRtc::resetClock() const {
    uint8_t stop = CONTROL_1_STOP;
    uint8_t epoch[7] = {0x00, 0x00, 0x00, 0x01, 6, 0x01, 0x00};
    uint8_t run = 0x00;
    return writeReg(REG_CONTROL_1, &stop, 1)
        && writeReg(REG_SECONDS, epoch, sizeof(epoch))
        && writeReg(REG_CONTROL_1, &run, 1);
}

// The stamp has no month, so a gap is only counted when the stamp is from today,
// or from yesterday (weekday one back, day one back or the 1st of a month).
// Anything else returns -1: too long or unknown.
int32_t ClockRtc::offlineMinutes(const DateTime& now, const Stamp& st) {
    const int32_t nowMin = now.hour * 60 + now.min;
    const int32_t stampMin = st.hour * 60 + st.min;
    if (now.day == st.day && now.wday == st.wday) {
        return nowMin >= stampMin ? nowMin - stampMin : -1;
    }
    const bool nextWday = now.wday == (st.wday + 1) % 7;
    const bool nextDay = now.day == st.day + 1 || now.day == 1;
    if (nextWday && nextDay) {
        return nowMin + 24 * 60 - stampMin;
    }
    return -1;
}

bool ClockRtc::configure(I2C_HandleTypeDef* hi2c, bool forceCold) {
    METHODTRACE
    hi2c_ = hi2c;
    isColdBoot_ = true;

    // Alarm and timer interrupts off, flags cleared, CLKOUT off (COT not connected)
    uint8_t control2 = 0x00;
    uint8_t clkout = 0x00;
    if (!writeReg(REG_CONTROL_2, &control2, 1) || !writeReg(REG_CLKOUT, &clkout, 1)) {
        return false;
    }

    DateTime now{};
    if (!readTime(now)) {
        return false;
    }
    Stamp stamp{};
    int32_t offline = -1;
    if (!now.clockLost && readStamp(stamp)) {
        offline = offlineMinutes(now, stamp);
    }
    isColdBoot_ = forceCold || offline < 0 || offline >= OFFLINE_COLD_LIMIT_MIN;
    METHODLOGS(info, "RTC offline: %ldmin (%s)", (long)offline, isColdBoot_ ? "cold" : "warm");

    if (now.clockLost && !resetClock()) {
        return false;
    }
    return writeStamp();
}

// Sole user of its I2C bus after configure(), so no bus lock is needed.
[[noreturn]] void ClockRtc::taskLoop() const {
    METHODTRACE
    TickType_t lastWake = xTaskGetTickCount();
    for (;;) {
        vTaskDelayUntil(&lastWake, pdMS_TO_TICKS(STAMP_PERIOD_MS));
        if (!writeStamp()) {
            METHODLOG(warn, "RTC stamp write failed")
        }
    }
}
