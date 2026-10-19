
#include "event_message.h"
#include "logger.h"
#include "queue.h"
#include "main.h"
#include "task_fanctrl.h"

extern osMessageQueueId_t SensorEventsHandle;
extern ControllerFanMotor taskFanMotor;
static CommonMessage msg{};

namespace {

// Ordered by severity, so the worst metric wins via a plain compare.
enum class DangerLevel : uint8_t {
    Off = 0,   // fan stopped: reading below fanOn (or below fanOff once running), air is fine
    Ventilate, // fan running, from fanOn up to evacuate: speed follows the reading
    Evacuate,  // at or above evacuate: fan at 100% and buzzer on, leave the area
};

// Per-metric thresholds, in the metric's own unit.
struct LevelThresholds {
    float fanOff;   // running fan turns off again below this reading (<= fanOn, avoids on/off chatter)
    float fanOn;    // stopped fan turns on at FAN_MIN_PERCENT at this reading
    float fanMax;   // reading where the fan reaches FAN_MAX_PERCENT (must be > fanOn)
    float evacuate; // reading where the buzzer turns on (>= fanMax)
};

// Danger level plus the fan speed it asks for. Fan is 0 until fanOn, then ramps
// linearly from FAN_MIN_PERCENT at fanOn to FAN_MAX_PERCENT at fanMax.
struct Severity {
    DangerLevel level;
    uint8_t fanPercent;
};

constexpr float FAN_MIN_PERCENT = 50.0f;
constexpr float FAN_MAX_PERCENT = 100.0f;

// previous is this metric's last result: it tells whether the fan is already running,
// so the on/off switch point differs (fanOn to start, fanOff to stop).
Severity severityFromThresholds(float value, const LevelThresholds& t, Severity previous) {
    float offPoint = previous.level == DangerLevel::Off ? t.fanOn : t.fanOff;
    if (value < offPoint) return {DangerLevel::Off, 0};
    if (value >= t.evacuate) return {DangerLevel::Evacuate, static_cast<uint8_t>(FAN_MAX_PERCENT)};

    float fraction = (value - t.fanOn) / (t.fanMax - t.fanOn);
    if (fraction < 0.0f) fraction = 0.0f; // between fanOff and fanOn: hold the minimum speed
    if (fraction > 1.0f) fraction = 1.0f;
    return {DangerLevel::Ventilate,
            static_cast<uint8_t>(FAN_MIN_PERCENT + (FAN_MAX_PERCENT - FAN_MIN_PERCENT) * fraction)};
}

Severity maxSeverity(Severity a, Severity b) {
    return {a.level > b.level ? a.level : b.level,
            a.fanPercent > b.fanPercent ? a.fanPercent : b.fanPercent};
}

// Values are {fanOff, fanOn, fanMax, evacuate}. The evacuate points are the original
// "extremely polluted" / ceiling limits; the fan reaches full speed before them.

// BSEC2 IAQ index (0-500): <=100 good, 101-150 lightly, 151-200 moderately,
// 201-300 heavily/severely polluted, >300 extremely polluted.
constexpr LevelThresholds BME680_IAQ{90.0f, 101.0f, 201.0f, 301.0f};

// MQ131 raw 12-bit ADC counts (0-4095), not yet converted to ppb.
// PLACEHOLDER: calibrate against a reference before field use.
constexpr LevelThresholds MQ131_ADC{1400.0f, 1500.0f, 2500.0f, 3200.0f};

// SPS30 mass concentration in ug/m3 (US EPA AQI breakpoints).
constexpr LevelThresholds SPS30_PM2P5{10.0f, 12.1f, 55.5f, 150.5f};
constexpr LevelThresholds SPS30_PM10{50.0f, 55.0f, 255.0f, 355.0f};

// MiCS-4514 values in ppb (task_mics4514 scales ppm by 1000).
// CO: 9 ppm WHO 8h, 35 ppm NIOSH REL, 200 ppm NIOSH ceiling.
constexpr LevelThresholds MICS4514_CO{8000.0f, 9000.0f, 35000.0f, 200000.0f};
// NO2: 0.1 ppm EPA 1h, 1 ppm NIOSH STEL, 5 ppm OSHA ceiling.
constexpr LevelThresholds MICS4514_NO2{80.0f, 100.0f, 1000.0f, 5000.0f};

// Latest severity of each metric, updated as readings arrive.
struct MetricLevels {
    Severity indoorAirQuality; // BME680 IAQ
    Severity ozone;            // MQ131
    Severity pm2p5;            // SPS30
    Severity pm10;             // SPS30
    Severity carbonMonoxide;   // MiCS-4514
    Severity nitrogenDioxide;  // MiCS-4514

    [[nodiscard]] Severity worst() const {
        Severity w = indoorAirQuality;
        w = maxSeverity(w, ozone);
        w = maxSeverity(w, pm2p5);
        w = maxSeverity(w, pm10);
        w = maxSeverity(w, carbonMonoxide);
        w = maxSeverity(w, nitrogenDioxide);
        return w;
    }
};

MetricLevels metricLevels{};

void updateBME680(const DataBME680& data) {
    metricLevels.indoorAirQuality = severityFromThresholds(static_cast<float>(data.indoorAirQualityIndex), BME680_IAQ, metricLevels.indoorAirQuality);
}

void updateMQ131(const DataUiValue& data) {
    metricLevels.ozone = severityFromThresholds(static_cast<float>(data.value), MQ131_ADC, metricLevels.ozone);
}

void updateSPS30(const DataParticle& data) {
    metricLevels.pm2p5 = severityFromThresholds(data.mc_2p5, SPS30_PM2P5, metricLevels.pm2p5);
    metricLevels.pm10 = severityFromThresholds(data.mc_10p0, SPS30_PM10, metricLevels.pm10);
}

void updateMICS4514(const DataCO1NO2& data) {
    metricLevels.carbonMonoxide = severityFromThresholds(data.co1, MICS4514_CO, metricLevels.carbonMonoxide);
    metricLevels.nitrogenDioxide = severityFromThresholds(data.no2, MICS4514_NO2, metricLevels.nitrogenDioxide);
}

// A stopped motor needs full power to get moving; there is no tach feedback,
// so "arrived at 100%" is a fixed spin-up time. PLACEHOLDER: measure on the real fan.
constexpr uint32_t FAN_KICKSTART_MS = 2000;

DangerLevel appliedLevel = DangerLevel::Off;
uint8_t appliedFanPercent = 0;
bool fanKicking = false;
TickType_t fanKickStart = 0;

// Ticks left of the spin-up, or portMAX_DELAY when none is running.
TickType_t fanKickRemainingTicks() {
    if (!fanKicking) {
        return portMAX_DELAY;
    }
    TickType_t elapsed = xTaskGetTickCount() - fanKickStart;
    TickType_t total = pdMS_TO_TICKS(FAN_KICKSTART_MS);
    return elapsed >= total ? 0 : total - elapsed;
}

// Fan and buzzer follow the worst severity across all metrics.
void evaluateLevels() {
    METHODTRACE
    Severity worst = metricLevels.worst();
    if (worst.level != appliedLevel) {

        appliedLevel = worst.level;
        HAL_GPIO_WritePin(BUZZER_IN_GPIO_Port, BUZZER_IN_Pin,
                          worst.level == DangerLevel::Evacuate ? GPIO_PIN_SET : GPIO_PIN_RESET);
        METHODLOGS(info, "danger level:%u fan:%u%%", (unsigned)worst.level, (unsigned)worst.fanPercent);
    }

    if (fanKicking) {
        if (worst.fanPercent == 0) {
            fanKicking = false; // air is clean again, no point finishing the spin-up
        } else if (fanKickRemainingTicks() > 0) {
            return;
        } else {
            fanKicking = false; // spin-up done, drop to the requested speed below
        }
    }
    if (worst.fanPercent == appliedFanPercent) {
        return;
    }
    if (appliedFanPercent == 0) {
        taskFanMotor.speedPercent(100);
        appliedFanPercent = 100;
        fanKicking = true;
        fanKickStart = xTaskGetTickCount();
        return;
    }
    taskFanMotor.speedPercent(worst.fanPercent);
    appliedFanPercent = worst.fanPercent;
}

}

extern "C" [[noreturn]] void mainSensorsMsgLoop(void* argument) {
    METHODTRACE
    auto xQueue = (QueueHandle_t)SensorEventsHandle;
    for (;;) {
        if (xQueueReceive(xQueue, &msg, fanKickRemainingTicks()) == pdTRUE) {
            switch (msg.id) {
                case BME680: {
                    auto payload = msg.payload.bme680;
                    METHODLOGS(debug, "bme680: Temp:%d, Humid:%u, AirQ:%u", payload.temperature, (unsigned)payload.humidity, (unsigned)payload.indoorAirQualityIndex);
                    updateBME680(payload);
                }
                break;
                case MQ131CO3: {
                    auto payload = msg.payload.uiValue;
                    METHODLOGS(debug, "MQ131: CO3:%lu", (unsigned long)payload.value);
                    updateMQ131(payload);
                }

                break;
                case SPS30Particle: {
                    auto payload = msg.payload.particle;
                    METHODLOGS(debug, "SPS30: 2p5:%f, 10p0:%f, typical:%f", (double)payload.mc_2p5, (double)payload.mc_10p0, (double)payload.tps);
                    updateSPS30(payload);
                }
                break;
                case MICS4514CO1NO2: {
                    auto payload = msg.payload.co1_no2;
                    METHODLOGS(debug, "MiCS: co1:%f no2:%f", payload.co1, payload.no2);
                    updateMICS4514(payload);
                }
                break;
                default:
                    METHODLOG(warn, "unrecognized message type");
                    break;
            }
        }
        evaluateLevels();
    }
}
