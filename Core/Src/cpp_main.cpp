//
// Created by uv on 20/07/2026.
//
#include "cpp_main.h"
#include "task_bme680.h"
#include "task_mq131.h"
#include "task_particle.h"
#include "task_mics4514.h"
#include "task_fanctrl.h"
#include "cmsis_os.h"
#include "logger.h"

extern I2C_HandleTypeDef hi2c3;
extern osMessageQueueId_t SensorEventsHandle;
extern osThreadId_t bmeTaskHandle;
extern osThreadId_t co1no2TaskHandle;
extern osThreadId_t particleTaskHandle;
extern osThreadId_t o3TaskHandle;

SensorBme68x taskBme68x;
SensorO3 taskSensorO3;
SensorParticle taskParticle;
SensorCO1NO2 taskCO1NO2;
ControllerFanMotor taskFanMotor;
enum ElementReady {
    Invalid = 0x00,
    BME = 0x01,
    O3 = 0x02,
    CO = 0x04,
    Particle = 0x08,
    Fan = 0x10,
};

constexpr auto LED_INDICATE_ERROR = 100;
constexpr auto LED_INDICATE_OK = 1000;

extern "C" [[noreturn]] void appStartDefaultTask(void* argument) {
    METHODTRACE
    taskBme68x.setup(bmeTaskHandle, SensorEventsHandle);
    taskSensorO3.setup(o3TaskHandle, SensorEventsHandle);
    taskParticle.setup(particleTaskHandle, SensorEventsHandle);
    taskCO1NO2.setup(co1no2TaskHandle, SensorEventsHandle);
    //
    uint8_t elementReady = ElementReady::Invalid;
    auto leep = LED_INDICATE_OK;
    auto rc = taskBme68x.configure(&hi2c3);
    if (!rc) {
        leep = LED_INDICATE_ERROR;
        METHODLOG(error, "taskBme68x configure failed")
    } else {
        elementReady |= ElementReady::BME;
    }
    rc = taskSensorO3.configure();
    if (!rc) {
        leep = LED_INDICATE_ERROR;
        METHODLOG(error, "taskSensorO3 configure failed")
    } else {
        elementReady |= ElementReady::O3;
    }
    rc = taskFanMotor.configure();
    if (!rc) {
        leep = LED_INDICATE_ERROR;
        METHODLOG(error, "taskFanMotor configure failed")
    } else {
        elementReady |= ElementReady::Fan;
    }
    elementReady |= ElementReady::CO;
    taskCO1NO2.configure();
    // Particle takes some time to configure
    rc = taskParticle.configure(&hi2c3);
    if (!rc) {
        leep = LED_INDICATE_ERROR;
        METHODLOG(error, "taskParticle configure failed")
    } else {
        elementReady |= ElementReady::Particle;
    }
    //////////////////
    METHODLOG(info, "Resume available tasks");
    if ( elementReady & ElementReady::BME) {taskBme68x.resume();}
    if ( elementReady & ElementReady::O3) {taskSensorO3.resume();}
    if ( elementReady & ElementReady::CO) {taskCO1NO2.resume();}
    if ( elementReady & ElementReady::Particle) {taskParticle.resume();}
    METHODLOG(info, "End startup");
    for (;;) {
        BSP_LED_Toggle(LED2);
        vTaskDelay(pdMS_TO_TICKS(leep));
    }
}

extern "C" [[noreturn]] void mainSensorsMsgLoop(void* argument) {
    METHODTRACE
    CommonMessage msg{};
    auto xQueue = (QueueHandle_t)SensorEventsHandle;
    for (;;) {
        if (xQueueReceive(xQueue, &msg, portMAX_DELAY) == pdTRUE) {
            switch (msg.id) {
                case BME680: {
                    auto payload = msg.payload.bme680;
                    METHODLOGF(debug, "bme680: Temp:{}, Humid:{}, AirQ:{}", payload.temperature, payload.humidity, payload.indoorAirQualityIndex);
                }
                break;
                case MQ131CO3: {
                    auto payload = msg.payload.uiValue;
                    METHODLOGF(debug, "MQ131: CO3:{}", payload.value);
                }

                break;
                case SPS30Particle: {
                    auto payload = msg.payload.particle;
                    METHODLOGF(debug, "SPS30: 2p5:{}, 10p0:{}, tipical:{}", payload.mc_2p5,payload.mc_10p0, payload.tps);
                }
                break;
                case MICS4514CO1NO2: {
                    auto payload = msg.payload.co1_no2;
                    METHODLOGF(debug, "MiCS: co1:{} no2:{}", payload.co1,payload.no2);
                }
                break;
                default:
                    METHODLOG(warn, "unrecognize message type");
                    break;
            }
        }
    }
}

extern "C" [[noreturn]] void bmeTaskHandler(void* argument) {
    osThreadSuspend(osThreadGetId()); // suspend - will be release elsewhere
    taskBme68x.taskLoop();
}

extern "C" [[noreturn]] void particleTaskHandler(void* argument) {
    osThreadSuspend(osThreadGetId()); // suspend - will be release elsewhere
    taskParticle.taskLoop();
}

extern "C" [[noreturn]] void co1no2TaskHandler(void* argument) {
    osThreadSuspend(osThreadGetId()); // suspend - will be release elsewhere
    taskCO1NO2.taskLoop();
}

extern "C" [[noreturn]] void o3TaskHandler(void* argument) {
    osThreadSuspend(osThreadGetId()); // suspend - will be release elsewhere
    taskSensorO3.taskLoop();
}

//
