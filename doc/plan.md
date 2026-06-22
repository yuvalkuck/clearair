## Peripheral Configuration Pipeline (STM32CubeMX)

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

---

## Core Implementation Source Code (`main.c`)

### Private Variables
Place this block inside `/* USER CODE BEGIN PV */`:

```c
#define RX_BUFFER_SIZE 64

// AC Phase Dimming Variables (Delays in Microseconds)
// 50Hz half-wave = 10000us max. Safe boundary limits: 500us (Max Power) to 9500us (Min Power)
volatile uint16_t dimming_delay_us = 8000; 

// Asynchronous DMA Communication Buffers
uint8_t rx_buffer[RX_BUFFER_SIZE];   // Filled silently by the DMA hardware engine
uint8_t main_buffer[RX_BUFFER_SIZE]; // Copy buffer used for background processing
volatile uint8_t data_ready = 0;     // Packet parsing flag
```

### Driver Initialization
Place this block inside `main(void)` right before the main application loop in `/* USER CODE BEGIN 2 */`:

```c
// Prepare Timer 3 Update Interrupts without starting the physical counter
__HAL_TIM_ENABLE_IT(&htim3, TIM_IT_UPDATE);

// Start the non-blocking background DMA listener for ESP32 communications
HAL_UART_Receive_DMA(&huart2, rx_buffer, RX_BUFFER_SIZE);
```

### Non-Blocking Main Loop Execution
Place this block inside `/* USER CODE BEGIN WHILE */`: