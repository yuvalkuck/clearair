//
// Created by uv on 20/07/2026.
//
#include "cpp_main.h"
#include "task_bme680.h"
#include "task_mq131.h"
#include "task_particle.h"
#include "task_mics4514.h"
#include "task_fanctrl.h"
#include "cmsis_os.h"
#include "collected_data.h"

extern I2C_HandleTypeDef hi2c2;
extern osMessageQueueId_t SensorEventsHandle;
extern osThreadId_t bmeTaskHandle;
extern osThreadId_t co1no2TaskHandle;
extern osThreadId_t particleTaskHandle;
extern osThreadId_t o3TaskHandle;
extern osThreadId_t fanCtrlTaskHandle;

SensorBme68x taskBme68x;
SensorO3 taskSensorO3;
SensorParticle taskParticle;
SensorCO1NO2 taskCO1NO2;
ControllerFanMotor taskFanMotor;

constexpr auto LED_INDICATE_ERROR = 100;
constexpr auto LED_INDICATE_OK = 1000;
extern TIM_HandleTypeDef htim3;
#define TRIAC_MAX_POWER_VALUE 500;
#define TRIAC_MIN_POWER_VALUE 10000;
volatile uint32_t motor_speed_delay = TRIAC_MIN_POWER_VALUE;
extern "C" void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if (GPIO_Pin == ZC_INPUT_Pin)
    {
        htim3.Instance->CNT = 0;                     // Reset timer clock
        htim3.Instance->CCR2 = motor_speed_delay;    // Bind current variable delay
        HAL_TIM_OC_Start_IT(&htim3, TIM_CHANNEL_2);  // Arm the channel interrupt
    }
}

extern "C" [[noreturn]] void appStartDefaultTask(void* argument) {
    taskBme68x.setup(bmeTaskHandle, SensorEventsHandle);
    taskSensorO3.setup(o3TaskHandle, SensorEventsHandle);
    taskParticle.setup(particleTaskHandle, SensorEventsHandle);
    taskCO1NO2.setup(co1no2TaskHandle, SensorEventsHandle);
    taskFanMotor.setup(fanCtrlTaskHandle, SensorEventsHandle);
    //
    auto leep = LED_INDICATE_OK;
    auto rc = taskBme68x.configure(&hi2c2);
    if (!rc) { leep = LED_INDICATE_ERROR; }
    else {
        taskBme68x.resume();
    }
    taskSensorO3.resume();
    rc = taskParticle.configure(&hi2c2);
    if (!rc) { leep = LED_INDICATE_ERROR; }
    else {
        taskParticle.resume();
    }
    for (;;) {
        BSP_LED_Toggle(LED2);
        vTaskDelay(pdMS_TO_TICKS(leep));
    }
}

extern "C" [[noreturn]] void mainSensorsMsgLoop(void* argument) {
    CommonMessage msg{};
    auto xQueue = (QueueHandle_t)SensorEventsHandle;
    for (;;) {
        if (xQueueReceive(xQueue, &msg, portMAX_DELAY) == pdTRUE) {
            switch (msg.id) {
                case BME680: {
                    auto payload = msg.payload.bme680;
                }
                break;
                case MQ131CO3: {
                    auto payload = msg.payload.uiValue;
                }

                break;
                case SPS30Particle: {
                    auto payload = msg.payload.particle;
                }
                break;
                case MICS4514CO1NO2: {
                    auto payload = msg.payload.co1_no2;
                }
                    break;
                default:
                    // WARNING
                    break;
            }
        }
    }
}

extern "C" [[noreturn]] void bmeTaskHandler(void* argument) {
    osThreadSuspend(osThreadGetId()); // suspend - will be release elseware
    taskBme68x.taskLoop();
}

extern "C" [[noreturn]] void particleTaskHandler(void* argument) {
    osThreadSuspend(osThreadGetId()); // suspend - will be release elseware
    taskParticle.taskLoop();
}

extern "C" [[noreturn]] void co1no2TaskHandler(void* argument) {
    osThreadSuspend(osThreadGetId()); // suspend - will be release elseware
    taskCO1NO2.taskLoop();
}

extern "C" [[noreturn]] void o3TaskHandler(void* argument) {
    osThreadSuspend(osThreadGetId()); // suspend - will be release elseware
    taskSensorO3.taskLoop();
}

extern "C" void fanCtrlTaskHandler(void *argument) {
    osThreadSuspend(osThreadGetId()); // suspend - will be release elseware
    taskFanMotor.taskLoop();
}



//
