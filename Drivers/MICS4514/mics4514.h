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
 * @file mics4514.h
 * @brief Driver for the mics4514 sensor for stm32.
 */

#ifndef _MICS4514_H_
#define _MICS4514_H_

#ifdef __cplusplus
 extern "C" {
#endif
	#include "stdint.h"

	//Pin an port of the preheat pin
	#define MICS_PRE_Pin 		GPIO_PIN_7
	#define MICS_PRE_GPIO_Port	GPIOB
	
	#define MICS4514_NOX_ADC_HANDLER	hadc1
	#define MICS4514_RED_ADC_HANDLER	hadc2

	#define MICS4514_NOX_R0 1022	//Reference resistance for the NO2 sensing element
	#define MICS4514_RED_R0 1000000	//Reference resistance for the NO2 sensing element
	
	#define MICS4514_NOX_PREHEAT 1	//seconds for preheating the NO2 sensing element
		
	
	void 		mics4514_init(void);
	uint32_t	mics4514_measureNO2(void);
	uint32_t	mics4514_measureCO(void);
	

#ifdef __cplusplus
}
#endif
	
#endif /* _MICS4514_H_ */
