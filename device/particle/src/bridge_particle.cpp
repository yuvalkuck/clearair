//
// Created by uv on 21/07/2026
//
#include "stm32f4xx_hal.h"
#include "bridge_particle.h"
#include "cmsis_os.h"
#include "sensirion_config.h"
#include "sps30_i2c.h"


namespace {
    constexpr uint32_t I2C_TIMEOUT_MS = 100;
    I2C_HandleTypeDef* i2cH_;
    uint8_t dev_addr_ = SPS30_I2C_ADDR_69 << 1;
}

sensirion_cb_t sensirion_cb = {0};
extern "C" void sensirion_i2c_hal_setup(sensirion_cb_t*);

/**
 * Select the current i2c bus by index.
 * All following i2c operations will be directed at that bus.
 *
 * THE IMPLEMENTATION IS OPTIONAL ON SINGLE-BUS SETUPS (all sensors on the same
 * bus)
 *
 * @param bus_idx   Bus index to select
 * @returns         0 on success, an error code otherwise
 */

/**
 * Initialize all hard- and software components that are needed for the I2C
 * communication.
 */

/**
 * Release all resources initialized by sensirion_i2c_hal_init().
 */

/**
 * Execute one read transaction on the I2C bus, reading a given number of bytes.
 * If the device does not acknowledge the read command, an error shall be
 * returned.
 *
 * @param address 7-bit I2C address to read from
 * @param data    pointer to the buffer where the data is to be stored
 * @param count   number of bytes to read from I2C and store in the buffer
 * @returns 0 on success, error code otherwise
 */
static int8_t hal_read(uint8_t address, uint8_t* data, uint8_t count) {
    auto rc = HAL_I2C_Master_Receive(i2cH_, dev_addr_, data, count, HAL_MAX_DELAY);
    if (rc == HAL_OK) {
        return 0; // Success
    }
    return -1; // Failure
}

/**
 * Execute one write transaction on the I2C bus, sending a given number of
 * bytes. The bytes in the supplied buffer must be sent to the given address. If
 * the slave device does not acknowledge any of the bytes, an error shall be
 * returned.
 *
 * @param address 7-bit I2C address to write to
 * @param data    pointer to the buffer containing the data to write
 * @param count   number of bytes to read from the buffer and send over I2C
 * @returns 0 on success, error code otherwise
 */

static int8_t hal_write(uint8_t address, const uint8_t* data, uint8_t count) {
    auto rc = HAL_I2C_Master_Transmit(i2cH_, dev_addr_, (uint8_t*)data, count, HAL_MAX_DELAY);
    if (rc == HAL_OK) {
        return 0; // Success
    }
    return -1; // Failure
}

/**
 * Sleep for a given number of microseconds. The function should delay the
 * execution for at least the given time, but may also sleep longer.
 *
 * Despite the unit, a <10 millisecond precision is sufficient.
 *
 * @param useconds the sleep time in microseconds
 */
static void hal_sleep_usec(uint32_t useconds) {
    // For short delays under RTOS, busy-wait; for longer, prefer vTaskDelay in caller context.
    // bme68x calls this with small values (µs), so a tight loop using DWT cycle counter
    // is common, or HAL_Delay-based approximation if µs precision isn't critical.
    if (useconds < 1000) {
        volatile uint32_t cycles = (SystemCoreClock / 1000000U) * useconds / 5U;
        while (cycles--) { __NOP(); }
    }
    else {
        vTaskDelay(pdMS_TO_TICKS(useconds));
    }
}

void initBridgeParticle(I2C_HandleTypeDef* hi2c, uint8_t dev_addr_7bit) {
    i2cH_ = hi2c;
    dev_addr_ = dev_addr_7bit << 1;
    sps30_init(dev_addr_);
    sensirion_cb.sensirion_i2c_hal_read = hal_read;
    sensirion_cb.sensirion_i2c_hal_write = hal_write;
    sensirion_cb.sensirion_i2c_hal_sleep_usec = hal_sleep_usec;
    sensirion_i2c_hal_setup(&sensirion_cb);
}
