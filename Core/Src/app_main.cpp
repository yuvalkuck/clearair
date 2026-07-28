//
// Created by uv on 20/07/2026.
//
#include "app_main.h"
#include "task_bme680.h"
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
extern osThreadId_t bmeSensorHandle;
extern osMessageQueueId_t SensorEventsHandle;
TaskBme680 taskBme680;

extern "C" [[noreturn]] void appStartDefaultTask(void* argument) {
    /* USER CODE BEGIN 5 */
    auto leep = 100;
    auto rc = taskBme680.configure(SensorEventsHandle, &hi2c2,BME68X_I2C_ADDR_HIGH);
    if (rc) {
        taskBme680.run();
        leep = 1000;
    }
    for (;;) {
        BSP_LED_Toggle(LED2);
        vTaskDelay(pdMS_TO_TICKS(leep));
    }
    /* USER CODE END 5 */
}

extern "C" [[noreturn]] void appBmeSensorTask(void* argument) {
    /* USER CODE BEGIN bmeSensorTask */
    osThreadSuspend(osThreadGetId()); // suspend - will be release elseware
    taskBme680.taskLoop();
    /* USER CODE END bmeSensorTask */
}

extern "C" [[noreturn]] void mainSensorsMsgLoop(void* argument) {
    CommonMessage msg{};
    auto xQueue = (QueueHandle_t)SensorEventsHandle;
    for (;;) {
        if (xQueueReceive(xQueue, &msg, portMAX_DELAY) == pdTRUE) {
            switch (msg.id) {
                case UniqueID::BME680:
                    break;
                default:
                    break;
            }
        }
    }
}

int app_main(void) {
    /* Start scheduler */
    osKernelStart();

    return 0;
}
