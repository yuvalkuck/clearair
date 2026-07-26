//
// Created by uv on 20/07/2026.
//
#include "app_main.h"
#include "task_bme680.h"
extern I2C_HandleTypeDef hi2c1;
extern I2C_HandleTypeDef hi2c2;
extern osMessageQueueId_t SensorEventsHandle;

int app_main(void) {
    TaskBme680 taskBme680(&hi2c2,&SensorEventsHandle);
    taskBme680.load();

    while (1)
    {

        HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5,GPIO_PIN_SET);
        HAL_Delay(100);
        HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5,GPIO_PIN_RESET);
        HAL_Delay(100);
    }

}

