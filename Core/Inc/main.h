/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32g4xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

void HAL_TIM_MspPostInit(TIM_HandleTypeDef *htim);

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define MQ131_ADC_Pin GPIO_PIN_0
#define MQ131_ADC_GPIO_Port GPIOA
#define MICS_CO1_Pin GPIO_PIN_1
#define MICS_CO1_GPIO_Port GPIOA
#define FAN_FRONT_TACH_Pin GPIO_PIN_5
#define FAN_FRONT_TACH_GPIO_Port GPIOA
#define MICS_NO2_Pin GPIO_PIN_7
#define MICS_NO2_GPIO_Port GPIOA
#define ZC_INPUT_Pin GPIO_PIN_0
#define ZC_INPUT_GPIO_Port GPIOB
#define ZC_INPUT_EXTI_IRQn EXTI0_IRQn
#define TRIAC_DIMMER_Pin GPIO_PIN_1
#define TRIAC_DIMMER_GPIO_Port GPIOB
#define BOOT_MODE_Pin GPIO_PIN_14
#define BOOT_MODE_GPIO_Port GPIOB
#define BUZZER_IN_Pin GPIO_PIN_15
#define BUZZER_IN_GPIO_Port GPIOB
#define LED_BOARD_Pin GPIO_PIN_6
#define LED_BOARD_GPIO_Port GPIOC
#define FAN_FRONT_PWM_Pin GPIO_PIN_8
#define FAN_FRONT_PWM_GPIO_Port GPIOA
#define FAN_REAR_PWM_Pin GPIO_PIN_9
#define FAN_REAR_PWM_GPIO_Port GPIOA
#define I2C_SCL_Pin GPIO_PIN_15
#define I2C_SCL_GPIO_Port GPIOA
#define FAN_REAR_TACH_Pin GPIO_PIN_3
#define FAN_REAR_TACH_GPIO_Port GPIOB
#define I2C_SDA_Pin GPIO_PIN_7
#define I2C_SDA_GPIO_Port GPIOB

/* USER CODE BEGIN Private defines */
#define DETECTION_SLEEP_LOOP_LIMIT 50000 // 5sec of sleep
/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
