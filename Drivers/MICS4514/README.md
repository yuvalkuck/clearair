# mics4514-stm32-driver
Driver for the mics4514 sensor for stm32.

&nbsp;
&nbsp;
&nbsp;

### [Open Documentation]( http://paulopereira98.github.io/mics4514-stm32-driver/mics4514_8h.html)
&nbsp;
### How to use:

##### Connect RED pin directly to adc.
##### Connect NOX pin through a resistive divider made with equal value resistors.
###### -The voltage at the adc should be half the sensor voltage (recommended value: 100kΩ).

##### Set pin for preheating and the handlers for the NOX and RED adcs:
```c
/* mics4514.h */
#define MICS_PRE_Pin 		GPIO_PIN_7
#define MICS_PRE_GPIO_Port	GPIOB

#define MICS4514_NOX_ADC_HANDLER	hadc1
#define MICS4514_RED_ADC_HANDLER	hadc2
```

##### Call the mics4514_init() function on startup
```c
/* main.c */
int main(void)
{
  /* ... */
  
  mics4514_init();
  
  /* ... */
}
```
