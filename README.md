# CleanAir == STM32 F446RE AC Motor Dimming & Multi-Device Control System

This document outlines the architecture, configuration pipeline, and asynchronous code structure required to build a safe, non-blocking phase-angle AC motor control loop using an STM32 Nucleo-F446RE, an ESP32-C6 communication bridge, and a BME688 environmental sensor.

---

## 1. System Architecture

To prevent high-voltage AC timing from stalling or causing jitters, the firmware isolates tasks into three parallel execution layers:

1. **AC Timing (High-Priority Hardware Interrupts):** Tracks the 0V crossing of the AC wave and fires the Triac via precise microsecond hardware timers.
2. **Data Streaming (Zero-CPU Background Processing):** Direct Memory Access (DMA) automatically captures UART command packets from the ESP32-C6 directly into RAM without stepping on the CPU's processing time.
3. **Application Loop (Non-Blocking Foreground Tasks):** Regularly polls the I2C BME688 sensor and dynamically modifies the control variables.

### Hardware Signal Diagram

## 2. Hardware Pin Assignment

| Peripheral / Signal | Nucleo-F446RE Pin | Configuration Mode | Description |
| :--- | :--- | :--- | :--- |
| **Dimmer Zero-Cross** | `PA0` | `GPIO_EXTI0` | Interrupt input from the dimmer's Z-C isolation circuit. |
| **Dimmer Triac Gate** | `PA1` | `GPIO_Output` | Pulse output to fire the Triac. Label as `DIM_GATE`. |
| **ESP32-C6 UART RX** | `PA2` | `USART2_TX` | Transmit channel to the ESP32-C6. |
| **ESP32-C6 UART TX** | `PA3` | `USART2_RX` | Receive channel from the ESP32-C6 (Configured with DMA). |
| **BME688 I2C SCL** | `PB8` | `I2C1_SCL` | Clock line for environmental sensor. |
| **BME688 I2C SDA** | `PB9` | `I2C1_SDA` | Data line for environmental sensor. |

---

## 3. Peripheral Configuration Pipeline (STM32CubeMX)

### GPIO & External Interrupts
1. Map `PA0` as `GPIO_EXTI0`.
2. Under **System Core -> GPIO -> PA0**, set **GPIO Mode** to `External Interrupt Mode with Rising edge trigger`.
3. Under **System Core -> NVIC**, check the box to **Enable** `EXTI line0 interrupt`.

### Hardware Timer 3 (Microsecond Stopwatch)
1. Under **Timers -> TIM3**, change **Clock Source** to `Internal Clock`.
2. Given a standard 180MHz system clock on the F446RE, the APB1 timer bus runs at 90MHz.
3. Under **Parameter Settings**, set **Prescaler (PSC)** to `90 - 1`. This forces the timer to increment exactly once every microsecond ($1\mu\text{s}$).
4. Set **Counter Period (ARR)** to `0xFFFF` (This will be adjusted dynamically in the ISR).
5. Under the **NVIC Settings** tab, check the box to **Enable** `TIM3 global interrupt`.

### USART2 & Direct Memory Access (DMA)
1. Under **Connectivity -> USART2**, set **Mode** to `Asynchronous`.
2. Configure your desired Baud Rate (e.g., `115200`).
3. Click the **DMA Settings** tab -> **Add** -> Select `USART2_RX`.
4. Leave Direction as `Peripheral To Memory`. Set **Mode** to `Circular`.
5. Under **NVIC Settings**, ensure `USART2 global interrupt` is checked.

### Code Generation for CLion (Debian)
1. Go to the **Project Manager** tab.
2. Select **Toolchain / IDE** as `STM32CubeIDE` (or `CMake` depending on your MX version).
3. Click **GENERATE CODE**. Open the directory directly inside **CLion**. Your local `arm-none-eabi-gcc` toolchain will parse the structural metadata natively.


