/*
	Driver for the mics4514 sensor for stm32.
	Copyright (C) 2019  Paulo Pereira	(EEIC-UMinho)
	This program is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.
	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.
	You should have received a copy of the GNU General Public License
	along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/
/**
 * @file mics4514.c
 * @brief Driver for the mics4514 sensor for stm32.
 */

#include "mics4514.h"
#include "stdint.h"
#include "gpio.h"
#include "adc.h"
#include "math.h"

/**
  * @brief  initialization process for the mics4514 sensor
  * @retval None
  */
void mics4514_init(void)
{
	MX_ADC1_Init();
	MX_ADC2_Init();

	//enable preheat for NO2 sensing element and wait
	HAL_GPIO_WritePin(MICS_PRE_GPIO_Port, MICS_PRE_Pin, GPIO_PIN_SET);
	HAL_Delay(MICS4514_NOX_PREHEAT*1000);
	HAL_GPIO_WritePin(MICS_PRE_GPIO_Port, MICS_PRE_Pin, GPIO_PIN_RESET);
	
}

/**
  * @brief  read the analog NO2 value and calculate the ppb value
  * @retval NO2 concentration in ppb
  */
uint32_t mics4514_measureNO2(void)
{	
	uint32_t adc_value, result;
	double voltage, Rs, ppb;
	
	HAL_ADC_Start(&MICS4514_NOX_ADC_HANDLER);
	HAL_ADC_PollForConversion(&MICS4514_NOX_ADC_HANDLER, HAL_MAX_DELAY);
	adc_value = HAL_ADC_GetValue(&MICS4514_NOX_ADC_HANDLER);
	HAL_ADC_Stop(&MICS4514_NOX_ADC_HANDLER);
	
	if (!adc_value) //invalid value
		return 0;	
	
	voltage = (3.3*adc_value) / 4096;
	Rs = ((5/( voltage *2))-1)*19800;														//calculate sensing resistance
	ppb = 1000*powf(10, 0.9682f*(logf( Rs / (double)MICS4514_NOX_R0 )/logf(10))-0.8108f);	//calculate gas concentration
	result = ppb;
	return result;
}

/**
  * @brief  read the analog CO value and calculate the ppb value
  * @retval CO concentration in ppb
  */
uint32_t mics4514_measureCO(void)
{
	uint32_t adc_value, result;
	double voltage, Rs, ppb;
	
	HAL_ADC_Start(&MICS4514_RED_ADC_HANDLER);
	HAL_ADC_PollForConversion(&MICS4514_RED_ADC_HANDLER, HAL_MAX_DELAY);
	adc_value = HAL_ADC_GetValue(&MICS4514_RED_ADC_HANDLER);
	HAL_ADC_Stop(&MICS4514_RED_ADC_HANDLER);
	
	if (!adc_value) //invalid value
		return 0;	
	
	voltage = (3.3*adc_value) / 4096;
	Rs = ((5/voltage)-1)*47000;																					//calculate sensing resistance
	ppb = 1000*powf(10, -1.1859*(logf( Rs / (double)MICS4514_RED_R0 )/logf(10))+0.6201);	//calculate gas concentration
	result = ppb;
	return result;
}
