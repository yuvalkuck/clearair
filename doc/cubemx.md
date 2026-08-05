# STM32CubeMX Configuration Manual: Project CleanAir

This guide provides step-by-step instructions to configure **STM32CubeMX** from scratch for the CleanAir project. It maps the STM32F446RE peripherals to handle the **SPS30/BME680 (I2C)**, **MQ131/MiCS-4514 (DMA ADC)**, **RobotDyn TRIAC (EXTI + One-Pulse Timer)**, and **FreeRTOS**.

---

## 🛠️ Step 1: System Core & OS Foundation Configuration

Before assigning specific sensor pins, the underlying operating system clock and debug settings must be isolated.

### 1.1 RCC (Reset and Clock Control)
1. In the left-hand column, expand **System Core** and select **RCC**.
2. Set **High Speed Clock (HSE)** to **BYPASS Clock Source** (The Nucleo board uses an 8MHz external oscillator routed from the ST-LINK debugger chip).

### 1.2 SYS (System Debug & Timebase)
1. Select **SYS** under the **System Core** menu.
2. Change **Debug** to **Serial Wire** (Enables standard SWD debugging via PA13/PA14).
3. Change **Timebase Source** to **TIM6** (Mandatory for FreeRTOS. This frees up `SysTick` for the OS scheduler and uses Timer 6 for internal HAL timeouts).

### 1.3 FreeRTOS Initialization
1. In the left panel, expand **Middleware and Software Packs** and select **FREERTOS**.
2. Change the **Interface** drop-down menu to **CMSIS_V2**.
3. Under the **Configuration** tab below, navigate to the **Tasks and Queues** section.
4. Modify the `defaultTask` or add your tasks to mirror the architecture:
    * **FanCtrlTask**: Priority `osPriorityHigh` (4), Stack Size `512` words.
    * **BsecEngineTask**: Priority `osPriorityAboveNormal` (3), Stack Size `1024` words (Required for heavy float calculations).
    * **Sps30DriverTask**: Priority `osPriorityNormal` (2), Stack Size `512` words.
    * **TelemetryTask**: Priority `osPriorityBelowNormal` (1), Stack Size `512` words.

---

## 🧭 Step 2: Communication & Debug Interfaces

### 2.1 USART2 (Debug Telemetry)
1. Expand **Connectivity** and select **USART2**.
2. Set **Mode** to **Asynchronous**.
3. Under **Parameter Settings**:
    * Baud Rate: `115200 Bits/s`
    * Word Length: `8 Bits`
    * Parity: `None`
    * Stop Bits: `1`
4. *Verification*: In the chip pinout preview, **PA2** must flash as `USART2_TX` and **PA3** as `USART2_RX`.

### 2.2 I2C2 (SPS30 & BME680 Bus)
1. Under **Connectivity**, select **I2C2**.
2. Change **Mode** to **I2C**.
3. Under **Parameter Settings**:
    * I2C Speed Mode: `Standard Mode`
    * I2C Clock Speed: `100000` (100 kHz)
4. **Critical Pin Reassignment**:
    * By default, CubeMX may assign I2C2 to other pins. Look at the chip map window.
    * Left-click on pin **PB10** and select **I2C2_SCL**.
    * Left-click on pin **PB3** and select **I2C2_SDA** (This will override the default JTAG-SWO assignment, disabling trace capabilities while keeping your SWD debugging live).

---

## 📊 Step 3: Analog Gas Sensor Interface (ADC1 with DMA)

To collect continuous readings from the MQ131 and the two channels of the MiCS-4514 simultaneously without wasting processing cycles, configure ADC1 in Scan Mode handled via DMA.

### 3.1 ADC1 Pin Assignment
1. Expand **Analog** and select **ADC1**.
2. Check the boxes to enable **IN0**, **IN1**, and **IN7**.
3. *Verification Check*: In the visual pinout map, verify that **PA0** is assigned as `ADC1_IN0`, **PA1** is `ADC1_IN1`, and **PA7** is `ADC1_IN7`.

### 3.2 ADC1 Configuration Matrix
1. Go to the **Configuration** panel for ADC1 and select the **Parameter Settings** tab.
2. Under **ADC_Settings**:
    * Clock Prescaler: `PCLK2 divided by 4`
    * Resolution: `12 bits (15 ADC clock cycles)`
    * Scan Conversion Mode: **Enabled**
    * Continuous Conversion Mode: **Enabled**
    * Discontinuous Conversion Mode: **Disabled**
3. Under **ADC_Regular_Conversion_Config**:
    * Number Of Conversion: `3`
    * **Rank 1**: Channel -> `Channel 0`, Sampling Time -> `56 Cycles` (or higher for gas stability).
    * **Rank 2**: Channel -> `Channel 1`, Sampling Time -> `56 Cycles`.
    * **Rank 3**: Channel -> `Channel 7`, Sampling Time -> `56 Cycles`.

### 3.3 DMA Settings
1. Click the **DMA Settings** tab within the ADC1 panel.
2. Click **Add** and select **ADC1**.
3. Select the newly created DMA stream row and configure the **DMA Request Settings**:
    * Stream: `DMA2 Stream 0` (assigned automatically by hardware architecture).
    * Direction: `Peripheral To Memory`
    * Priority: `Low`
    * Mode: **Circular** (This allows continuous buffering without software intervention).
4. Under **Data Width**:
    * Peripheral: `Half Word` (16-bit register matching a 12-bit ADC result).
    * Memory: `Half Word` (Increments automatically into your local C uint16_t array).
    * Check the box for **Memory Increment (MINC)**. Do **NOT** check Peripheral Increment (PINC).

---

## ⚡ Step 4: Real-Time AC Dimmer Control Setup

The phase-delay dimmer utilizes external edge triggers combined with an internal precise timer to switch the TRIAC gate safely.

### 4.1 RobotDyn Zero-Cross Input (PA10)
1. On the graphical chip diagram, locate pin **PA10**.
2. Left-click **PA10** and select **GPIO_EXTI10**.
3. In the left menu tree, go to **System Core** -> **GPIO**.
4. Click on the row for **PA10** and configure its properties at the bottom:
    * GPIO Mode: `External Interrupt Mode with Falling edge trigger detection`
    * GPIO Pull-up/Pull-down: `Pull-up` (or `No pull-up and no pull-down` if your RobotDyn module has an onboard hardware pull-up resistor to 3.3V).
    * User Label: `ROBOTDYN_ZC`

### 4.2 RobotDyn TRIAC Gate Output (PA6)
1. On the graphical chip diagram, locate pin **PA6**.
2. Left-click **PA6** and select **GPIO_Output**.
3. Navigate back to **System Core** -> **GPIO** and select the row for **PA6**:
    * GPIO output level: `Low`
    * GPIO mode: `Output Push Pull`
    * GPIO Pull-up/Pull-down: `No pull-up and no pull-down`
    * Maximum output speed: `High` (Required for fast microsecond trigger pulses).
    * User Label: `TRIAC_GATE`

### 4.3 Phase-Delay Timing Module (TIM2)
1. Expand **Timers** and select **TIM2**.
2. Change **Clock Source** to **Internal Clock**.
3. Change **Channel 1** or slave routing settings to **Output Compare No Output** or leave default internal mode (TIM2 is used strictly for its internal counter and ISR flag to pulse PA6 manually).
4. Under **Parameter Settings**:
    * **Prescaler (PSC)**: `83` (Assuming a 84 MHz APB1 timer clock, setting the prescaler to 83 yields a counting frequency of $84\,\text{MHz} / (83 + 1) = 1\,\text{MHz}$. This gives a clean timing resolution of exactly **1 microsecond per tick**).
    * Counter Mode: `Up`
    * **Counter Period (ARR)**: `65535` (Max out the 32-bit register resolution; it will be dynamically reset and overridden inside your zero-cross interrupt code).

### 4.4 Status Indicator Mapping (PA5)
1. On the graphical chip diagram, locate pin **PA5**.
2. Left-click **PA5** and select **GPIO_Output**.
3. In **System Core** -> **GPIO**, select the **PA5** row:
    * GPIO Output Level: `Low`
    * GPIO Mode: `Output Push Pull`
    * User Label: `STATUS_LED`

---

## 🔔 Step 5: NVIC Interrupt Vectors Priority Assignment

Since real-time AC dimmer operations cannot tolerate latency variations introduced by thread context switching under FreeRTOS, you must organize interrupt nesting priorities meticulously.

1. Under **System Core**, select **NVIC**.
2. Click the **NVIC** tab in the sub-pane configuration grid.
3. Configure the **Preemption Priority** values exactly as follows:
    * **Time base: Timer 6 interrupt**: `15` (The lowest priority vector, as required by FreeRTOS integration frameworks).
    * **EXTI line [15:10] interrupts**: `5` (High priority. Must be equal to or lower numerically than `5` to completely bypass FreeRTOS scheduler blocks, ensuring immediate response to the zero-cross physical signal).
    * **TIM2 global interrupt**: `5` (High priority. Must match your EXTI routine priority to ensure smooth transition from delay phase tracking to firing the hardware TRIAC gate pulse).
    * **DMA2 stream0 global interrupt**: `6` (Medium priority. Continuous background data movement).

---

## ⚙️ Step 6: Clock Tree Optimization

1. Select the **Clock Configuration** tab located along the top main horizontal navigation bar of CubeMX.
2. In the **Input Frequency** box next to your HSE clock source block, type `8`.
3. In the selector choice section directly following, check the circle indicator for **HSE**.
4. Find the box labeled **System Clock Mux** and select **PLLCLK**.
5. Move to the **HCLK (MHz)** box, type `180` (the maximum supported core frequency for the STM32F446RE architecture), and hit **Enter**.
6. CubeMX will display a warning dialog prompt asking to automatically calculate missing multipliers and dividers. Click **OK** or **Yes**.
7. *Verification*: Verify that **APB1 Timer Clocks** reads **84 MHz** and **APB2 Timer Clocks** reads **180 MHz**.

---

## 💾 Step 7: Project Export Generation

1. Click on the **Project Manager** tab along the top horizontal navigation bar.
2. Under **Project**:
    * Project Name: `CleanAir`
    * Toolchain / IDE: Select your target environment (e.g., `STM32CubeIDE`, `MDK-ARM v5`, or `CMake`).
3. Under **Code Generator**:
    * Ensure **Clear all holes with blank spaces** is checked.
    * Under *Generated files*, check the option box for **Generate peripheral initialization as a pair of '.c/.h' files per peripheral** (This prevents all code from dumping into `main.c`, providing a clean, separated file design layout for I2C, ADC, and Timers).
4. Click the blue **GENERATE CODE** button located at the upper top right-hand corner of the application window.
