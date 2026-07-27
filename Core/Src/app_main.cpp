//
// Created by uv on 20/07/2026.
//
#include "app_main.h"
#include "task_bme680.h"

#include "cmsis_os.h"
extern I2C_HandleTypeDef hi2c1;
extern I2C_HandleTypeDef hi2c2;
extern osMessageQueueId_t SensorEventsHandle;

extern "C" void appStartDefaultTask(void *argument)
{
    /* USER CODE BEGIN 5 */
    /* Infinite loop */
    TaskBme680 taskBme680(&hi2c2,&SensorEventsHandle,BME68X_I2C_ADDR_HIGH);
    auto rc = taskBme680.load();
    auto leep = 500;
    if ( !rc) {
        leep = 100;
    }
    for(;;)
    {
        BSP_LED_Toggle(LED2);
        vTaskDelay(pdMS_TO_TICKS(leep));
    }
    /* USER CODE END 5 */
}
extern "C" void appBmeSensorTask(void *argument)
{
    /* USER CODE BEGIN bmeSensorTask */
    /* Infinite loop */
    for(;;)
    {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
    /* USER CODE END bmeSensorTask */
}
int app_main(void) {
    /* Start scheduler */
    osKernelStart();

    return 0;
}

