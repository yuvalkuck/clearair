#include "base_device_task.h"
#include "main.h"
#include "logger.h"

void BaseDeviceTask::boundedDelay(uint32_t elapsedMs) const {
    if (elapsedMs > DETECTION_SLEEP_LOOP_LIMIT) {
    MESSAGELOG("task run took longer than the loop limit");
        vTaskDelay(pdMS_TO_TICKS(5));
    } else {
        vTaskDelay(pdMS_TO_TICKS(DETECTION_SLEEP_LOOP_LIMIT - elapsedMs));
    }
}
