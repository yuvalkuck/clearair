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

constexpr auto LED_INDICATE_ERROR = 100;
constexpr auto LED_INDICATE_OK = 1000;

extern "C" [[noreturn]] void appStartDefaultTask(void* argument) {
    METHODTRACE
    taskBme68x.setup(bmeTaskHandle, SensorEventsHandle);
    taskSensorO3.setup(o3TaskHandle, SensorEventsHandle);
    taskParticle.setup(particleTaskHandle, SensorEventsHandle);
    taskCO1NO2.setup(co1no2TaskHandle, SensorEventsHandle);
    //
    auto leep = LED_INDICATE_OK;
    auto rc = taskBme68x.configure(&hi2c3);
    if (!rc) {
        leep = LED_INDICATE_ERROR;
        METHODLOG(error, "taskBme68x configure failed")
    } else {
        taskBme68x.resume();
    }
    rc = taskSensorO3.configure();
    if (!rc) {
        leep = LED_INDICATE_ERROR;
        METHODLOG(error, "taskSensorO3 configure failed")
    } else {
        taskSensorO3.resume();
    }
    rc = taskFanMotor.configure();
    if (!rc) {
        leep = LED_INDICATE_ERROR;
        METHODLOG(error, "taskFanMotor configure failed")
    }
    // Particle takes some time to configure
    rc = taskParticle.configure(&hi2c3);
    if (!rc) {
        leep = LED_INDICATE_ERROR;
        METHODLOG(error, "taskParticle configure failed")
    } else {
        taskParticle.resume();
    }
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
                }
                break;
                case MQ131CO3: {
                    auto payload = msg.payload.uiValue;
                }

                break;
                case SPS30Particle: {
                    auto payload = msg.payload.particle;
                }
                break;
                case MICS4514CO1NO2: {
                    auto payload = msg.payload.co1_no2;
                }
                break;
                default:
                    // WARNING
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
