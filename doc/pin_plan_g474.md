# 📌 STM32G474CEU6 Pin Plan (WeAct G4 Long)

Pin map for the **STM32G474CEU6** (UFQFPN48) on the WeAct G4 Long board, debugged with an STLINK-V3MINIE. It is applied in `clear-air.ioc` except for the front and rear fan PWM and tach rows (`TIM1`, `TIM2`), which are still planned. Pin functions come from the CubeMX DB (`STM32G474C(B-C-E)Ux.xml`).

**CubeMX labels used by `device/*`:** `MQ131_ADC`, `MICS_CO1`, `MICS_NO2`, `ZC_INPUT`, `TRIAC_DIMMER`, `BOOT_MODE`, `BUZZER_ON`, `LED_DATA`, `BUTTONS_ADC`, `FORCE_STATES_SW`, `STANDBY_SW`, `STANDBY_LED`, `FILTER_FAN_POWER`, `LED_BOARD`, `I2C_SCL`, `I2C_SDA`, `RTC_SCL`, `RTC_SDA`. The sensor bus handle is `hi2c1` and the RTC bus handle is `hi2c2` (`Core/Src/cpp_main.cpp`).

## Service → Pin Assignments

| Service | Peripheral | G474 Pin (UFQFPN48 pin #) | Notes |
| :--- | :--- | :--- | :--- |
| **SPS30 + BME680** | I2C1 | PA15 SCL (38), PB7 SDA (45) | 4.7 kΩ pull-ups to 3.3V. `PA15` is free because debug uses SWD only (no `JTDI`). |
| **PCF8563 RTC (HW-689)** | I2C2 | PC4 SCL (16), PA8 SDA (30) | Address 0x51, own bus, 4.7 kΩ pull-ups to 3.3V. Standard mode 100 kHz. `COT` and `INT` are not connected. CR1220 backup cell on the module. |
| **MQ-131 Output** | ADC1_IN1 | PA0 (8) | Through the 1.8 kΩ / 3.3 kΩ divider. |
| **MiCS-4514 (CO)** | ADC2_IN2 | PA1 (9) | `PA1` is shared by ADC1/ADC2 IN2. Select ADC2 in CubeMX. |
| **MiCS-4514 ($NO_2$)** | ADC2_IN4 | PA7 (15) | Through the divider. |
| **Buttons (resistor ladder)** | ADC2_IN14 | PB11 (24) | `BUTTONS_ADC`. `R26` 10 kΩ pull-up to 3.3V, keys on `J11` through `R27`-`R30`, `C28` 100 nF to GND. ADC2 regular rank 3, after `MICS_CO1` (rank 1) and `MICS_NO2` (rank 2), 640.5 cycles. |
| **Test buttons (resistor ladder)** | ADC2_IN17 | PA4 (12) | `FORCE_STATES_SW`. `R31` 10 kΩ pull-up to 3.3V, keys `SW3`-`SW6` through `R32`-`R35`, `C29` 100 nF to GND. ADC2 regular rank 4, after `BUTTONS_ADC` (rank 3), 640.5 cycles; `NbrOfConversion` becomes 4. |
| **Standby switch** | GPIO Input | PB1 (18) | `STANDBY_SW`. Pull-up; low = `SW7` or the external switch on `J12` is closed. No EXTI needed (read in a task). |
| **Fan power relay** | GPIO Output | PB5 (43) | `FILTER_FAN_POWER`. Push-pull, initial LOW. HIGH = `Q6` on, relay `K1` closed, both 80 mm fans powered; LOW = fans off. About 17 mA coil current from 12V, 2.6 mA from the pin through `R41`. |
| **Status LED (red / green)** | GPIO Output | PB0 (17) | `STANDBY_LED`. Push-pull, initial HIGH. HIGH or unconfigured = red `D2` on and green `D1` off (`R40` pulls the node up to 3V3); LOW = green on. |
| **RobotDyn ZC Input** | GPIO EXTI12 | PB12 (25) | Falling edge, pull-up, through the divider. Uses the shared `EXTI15_10_IRQn` vector (priority 5); no other EXTI line 10-15 is in use. |
| **RobotDyn Gate Out** | GPIO Output | PB9 (47) | Push-pull, high speed, driven from the `TIM3` ISR. |
| **Cold/Warm Boot Select** | GPIO Input | PB2 (19) | Pull-up, read once at boot. |
| **Safety Buzzer** | GPIO Output | PB10 (22) | Drives the 2N2222A base through R9 (1 kΩ); Q3 switches the 12V buzzer on its low side. HIGH = buzzer on. Initial state LOW. |
| **Front Fan PWM (80 mm)** | TIM1_CH3 | PA10 (32) | 25 kHz PWM to the fan's PWM wire. 1 kΩ in series. Prescaler `0`, period `6799` at 170 MHz. Fan 12V and GND come from the 12V rail, GND common with the STM32. |
| **Rear Fan PWM (80 mm)** | TIM1_CH2 | PA9 (31) | Same timer as the front fan, so the same 25 kHz. 1 kΩ in series. |
| **Front Fan Tach** | TIM2_CH1 | PA5 (13) | Input capture, 10 kΩ pull-up to 3.3V. The tach is an open-collector output; confirm on the bench that the fan does not pull it up to 12V. |
| **Rear Fan Tach** | TIM2_CH2 | PB3 (41) | Input capture, 10 kΩ pull-up to 3.3V. `TIM2` is 32-bit, so a stalled fan does not overflow the period count. |
| **Status Indicator** | GPIO Output | PC6 (29) | On-board WeAct user LED. |
| **Debug & Telemetry** | USART2 | PA2 TX (10), PA3 RX (11) | The board has no on-board ST-LINK, and the 4-pin SWD header has no VCP lines. Wire `PA2`/`PA3` to the STLINK-V3MINIE 14-pin connector (`T_VCP_RX`/`T_VCP_TX`) or to a USB-serial adapter. |
| **Status LEDs (WS2812B chain)** | TIM16_CH1 + DMA | PA6 (14) | PWM at 800 kHz (prescaler `0`, period `211` at 170 MHz), one compare value per bit from DMA. Through `U6` (74AHCT125N at 5 V) and `R25` 330 Ω to `J9` DIN. |
| **Display (future)** | I2C2 (shared with the RTC) | PC4 SCL (16), PA8 SDA (30) | Header `J10`. Not used by the firmware yet. |
| **Phase-Delay Tracking** | TIM3 | Internal | At 170 MHz SYSCLK with APB1 = HCLK, set prescaler `169` for a 1 µs tick. |
| **HAL Timebase** | TIM6 | Internal | `TIM6_DAC_IRQn`. |
| **OS Kernel Clock** | SysTick | Internal | FreeRTOS only. |
| **Manual Reset (external button)** | NRST | PG10-NRST (7) | In parallel with the on-board reset key. |

## Reserved Pins (board / debugger — do not assign)

| Pin | Used by |
| :--- | :--- |
| PA13, PA14 | SWD (`SWDIO`, `SWCLK`). The STLINK-V3MINIE connects to the board's dedicated 4-pin SWD header (3V3, SWDIO, SWCLK, GND) next to the two keys. That header has no `SWO` or `JTDI`, so `PB3` and `PA15` are free. |
| PA11, PA12 | On-board USB-C (`USB_DM`, `USB_DP`) |
| PB8-BOOT0 | BOOT0, wired to the on-board BOOT key |
| PG10-NRST | NRST, wired to the on-board reset key and the external reset button |
| PF0, PF1 | 8 MHz HSE crystal |
| PC14, PC15 | 32.768 kHz LSE crystal |
| PC6 | On-board user LED (used as the status indicator above) |
| PC13 | On-board user key |
| PB4, PB6 | UCPD1 dead-battery pull-downs (`CC2`/`CC1`). Avoided, so they stay free of side effects. |

## Conflict Check

*   Each pin above has one function.
*   The only EXTI line in use is EXTI12 (`PB12`).
*   No alternate function overlaps another selected peripheral. The other I2C1 pin options are not used: `PA13`/`PA14` are SWD and `PB8` is BOOT0. The I2C1 SDA alternate `PB9` is the TRIAC gate GPIO. The I2C1 SMBA pin (`PB5`) stays unused.
*   On the UFQFPN48, `I2C2` is the only second I2C bus that fits: its SDA is on `PA8` or `PF0` (HSE), `I2C3` SCL is only on `PA8`, and `I2C4` needs `PA13`/`PC6`/`PB7`, which are all taken. So the front fan PWM moved from `TIM1_CH1` (`PA8`) to `TIM1_CH3` (`PA10`), and `I2C2` uses `PC4`/`PA8`.
*   `PA9`/`PA10` (`TIM1_CH2`/`TIM1_CH3`) and `PA5`/`PB3` (`TIM2_CH1`/`TIM2_CH2`) were spare. `TIM1` and `TIM2` are not used by anything else in this plan. The CubeMX DB lists these functions for the G474 UFQFPN48.
*   `VREF+` (pin 20) must connect to `VDDA` on the board for the ADCs to read against 3.3V.

*   The ZC input, TRIAC gate, boot button, buzzer and LED data sit on `PB12`, `PB9`, `PB2`, `PB10` and `PA6` (`TIM16_CH1`, a timer nothing else uses) so that SPI2 stays free (SPI3 lost its MOSI pin `PB5` to `FILTER_FAN_POWER`; COMP1, COMP4 and DAC1_OUT1 are taken by `PB1`, `PB0` and `PA4`; COMP2 stays on `PA7`) for later use. SPI1, I2C3, I2C4, COMP3, USART1 and LPUART1 cannot be freed on this package without moving an ADC, fan or I2C pin; UART4 shares `PC10`/`PC11` with SPI3.

**Spare pins after this plan:** PB13, PB14, PB15, PC10, PC11.

| Free service | Pins |
| :--- | :--- |
| SPI2 | `PB13` SCK, `PB14` MISO, `PB15` MOSI (software NSS) |
| COMP2 | INP `PA7` (shared with `MICS_NO2`) |
