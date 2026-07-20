//
// Created by uv on 20/07/2026.
//
#include "app_main.h"
int app_main(void) {
    while (1)
    {
        /* USER CODE END WHILE */

        /* USER CODE BEGIN 3 */
        HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5,GPIO_PIN_SET);
        HAL_Delay(200);
        HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5,GPIO_PIN_RESET);
        HAL_Delay(200);
    }

}

