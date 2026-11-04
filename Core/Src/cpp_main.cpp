//
// Created by uv on 20/07/2026.
//
#include "cpp_main.h"
#include "task_bme680.h"
#include "task_mq131.h"
#include "task_particle.h"
#include "task_mics4514.h"
#include "task_fanctrl.h"
#include "task_rtc.h"
#include "cmsis_os.h"
#include "logger.h"

extern I2C_HandleTypeDef hi2c1;
extern I2C_HandleTypeDef hi2c2;
extern osMessageQueueId_t SensorEventsHandle;
extern osThreadId_t bmeTaskHandle;
extern osThreadId_t co1no2TaskHandle;
extern osThreadId_t particleTaskHandle;
extern osThreadId_t o3TaskHandle;
extern osThreadId_t rtcTaskHandle;

SensorBme68x taskBme68x;
SensorO3 taskSensorO3;
SensorParticle taskParticle;
SensorCO1NO2 taskCO1NO2;
ControllerFanMotor taskFanMotor;
ClockRtc taskRtc;
enum ElementReady {
    Invalid = 0x00,
    BME = 0x01,
    O3 = 0x02,
    CO = 0x04,
    Particle = 0x08,
    Fan = 0x10,
    Rtc = 0x20,
};

constexpr auto LED_INDICATE_ERROR = 100;
constexpr auto LED_INDICATE_OK = 1000;

extern "C" [[noreturn]] void appStartDefaultTask(void* argument) {

    taskBme68x.setup(bmeTaskHandle, SensorEventsHandle);
    taskSensorO3.setup(o3TaskHandle, SensorEventsHandle);
    taskParticle.setup(particleTaskHandle, SensorEventsHandle);
    taskCO1NO2.setup(co1no2TaskHandle, SensorEventsHandle);
    taskRtc.setup(rtcTaskHandle, SensorEventsHandle);
    //
    uint8_t elementReady = ElementReady::Invalid;
    bool coldButton = HAL_GPIO_ReadPin(BOOT_MODE_GPIO_Port, BOOT_MODE_Pin) == GPIO_PIN_SET;
    auto leep = LED_INDICATE_OK;
    // RTC first: its offline time decides the MQ131 / MiCS-4514 warm-up
    auto rc = taskRtc.configure(&hi2c2, coldButton);
    if (!rc) {
        leep = LED_INDICATE_ERROR;
        // METHODLOG(error, "taskRtc configure failed")
    } else {
        elementReady |= ElementReady::Rtc;
    }
    bool isColdBoot = taskRtc.isColdBoot();
    rc = taskBme68x.configure(&hi2c1);
    if (!rc) {
        leep = LED_INDICATE_ERROR;
        // METHODLOG(error, "taskBme68x configure failed")
    } else {
        elementReady |= ElementReady::BME;
    }
    rc = taskSensorO3.configure(isColdBoot);
    if (!rc) {
        leep = LED_INDICATE_ERROR;
        // METHODLOG(error, "taskSensorO3 configure failed")
    } else {
        elementReady |= ElementReady::O3;
    }
    rc = taskFanMotor.configure();
    if (!rc) {
        // leep = LED_INDICATE_ERROR;
        //METHODLOG(error, "taskFanMotor configure failed")
    } else {
        elementReady |= ElementReady::Fan;
    }
    elementReady |= ElementReady::CO;
    taskCO1NO2.configure(isColdBoot);
    // Particle takes some time to configure
    rc = taskParticle.configure(&hi2c1);
    if (!rc) {
        leep = LED_INDICATE_ERROR;
        // METHODLOG(error, "taskParticle configure failed")
    } else {
        elementReady |= ElementReady::Particle;
    }
    //////////////////
    MESSAGELOG( "Resume available tasks");
    if ( elementReady & ElementReady::Particle) {taskParticle.resume();}
    vTaskDelay(pdMS_TO_TICKS(100));
    if ( elementReady & ElementReady::BME) {taskBme68x.resume();}
    vTaskDelay(pdMS_TO_TICKS(100));
    if ( elementReady & ElementReady::O3) {taskSensorO3.resume();}
    vTaskDelay(pdMS_TO_TICKS(100));
    if ( elementReady & ElementReady::CO) {taskCO1NO2.resume();}
    if ( elementReady & ElementReady::Rtc) {taskRtc.resume();}
    MESSAGELOG("End startup");
    for (;;) {
        HAL_GPIO_TogglePin(LED_BOARD_GPIO_Port,LED_BOARD_Pin);
        vTaskDelay(pdMS_TO_TICKS(leep));
    }
}

extern "C" [[noreturn]] void bmeTaskHandler(void* argument) {
    osThreadSuspend(osThreadGetId()); // suspend - will be resumed elsewhere
    taskBme68x.taskLoop();
}

extern "C" [[noreturn]] void particleTaskHandler(void* argument) {
    osThreadSuspend(osThreadGetId()); // suspend - will be resumed elsewhere
    taskParticle.taskLoop();
}

extern "C" [[noreturn]] void co1no2TaskHandler(void* argument) {
    osThreadSuspend(osThreadGetId()); // suspend - will be resumed elsewhere
    taskCO1NO2.taskLoop();
}

extern "C" [[noreturn]] void o3TaskHandler(void* argument) {
    osThreadSuspend(osThreadGetId()); // suspend - will be resumed elsewhere
    taskSensorO3.taskLoop();
}

extern "C" [[noreturn]] void rtcTaskHandler(void* argument) {
    osThreadSuspend(osThreadGetId()); // suspend - will be resumed elsewhere
    taskRtc.taskLoop();
}

//
