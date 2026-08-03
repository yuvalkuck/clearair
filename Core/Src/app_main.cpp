//
// Created by uv on 20/07/2026.
//
#include "app_main.h"
#include "task_bme680.h"
#include "task_mq7.h"
#include "task_particle.h"
#include "cmsis_os.h"
/*
 * Red LED set of 4 error status
 * 00 - All OK
 * 1->4: Bit On Per Device
 * 1 to 4 - all Blinking, AC control down
 */
enum ExDeviceErrState {
    NoError = 0x00,
    BME = 0x01,
    CO1 = 0x02,
    CO2 = 0x04,
    AirQuality = 0x08,
    // left for more
};

extern I2C_HandleTypeDef hi2c2;
extern osThreadId_t bmeSensorTaskHandle;
extern osThreadId_t co1SensorTaskHandle;
extern osThreadId_t partSensorTaskHandle;
extern osMessageQueueId_t SensorEventsHandle;

int app_main(void) {
    /* Start scheduler */
    osKernelStart();

    return 0;
}
TaskBme680 taskBme680;
SensorCO1 taskSensorCO1;
TaskParticle taskParticle;

extern "C" [[noreturn]] void appStartDefaultTask(void* argument) {
    taskBme680.setup(bmeSensorTaskHandle,SensorEventsHandle);
    taskSensorCO1.setup( co1SensorTaskHandle, SensorEventsHandle);
    taskParticle.setup(partSensorTaskHandle,SensorEventsHandle);
    //
    auto leep = 1000;
    auto rc = taskBme680.configure( &hi2c2);
    if (!rc) { leep = 100; }
    else { taskBme680.resume(); }
    taskSensorCO1.resume();
    taskParticle.configure(&hi2c2);
    for (;;) {
        BSP_LED_Toggle(LED2);
        vTaskDelay(pdMS_TO_TICKS(leep));
    }
}

extern "C" [[noreturn]] void mainSensorsMsgLoop(void* argument) {
    CommonMessage msg{};
    auto xQueue = (QueueHandle_t)SensorEventsHandle;
    for (;;) {
        if (xQueueReceive(xQueue, &msg, portMAX_DELAY) == pdTRUE) {
            switch (msg.id) {
                case UniqueID::BME680:
                    break;
                case UniqueID::MQ7CO1:
                    break;
                default:
                    break;
            }
        }
    }
}

extern "C" [[noreturn]] void appBmeSensorTask(void* argument) {
    osThreadSuspend(osThreadGetId()); // suspend - will be release elseware
    taskBme680.taskLoop();
}

extern "C" [[noreturn]] void co1SensorHandler(void* argument) {
    osThreadSuspend(osThreadGetId()); // suspend - will be release elseware
    taskSensorCO1.taskLoop();
}
extern "C" void particleSensorHandler(void *argument) {
    osThreadSuspend(osThreadGetId()); // suspend - will be release elseware
    taskParticle.taskLoop();
}
//
