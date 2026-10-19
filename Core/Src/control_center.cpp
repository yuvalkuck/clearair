
#include "event_message.h"
#include "logger.h"
#include "queue.h"
extern osMessageQueueId_t SensorEventsHandle;
static CommonMessage msg{};
extern "C" [[noreturn]] void mainSensorsMsgLoop(void* argument) {
    METHODTRACE
    auto xQueue = (QueueHandle_t)SensorEventsHandle;
    for (;;) {
        if (xQueueReceive(xQueue, &msg, portMAX_DELAY) == pdTRUE) {
            switch (msg.id) {
                case BME680: {
                    auto payload = msg.payload.bme680;
                    METHODLOGS(debug, "bme680: Temp:%d, Humid:%u, AirQ:%u", payload.temperature, (unsigned)payload.humidity, (unsigned)payload.indoorAirQualityIndex);
                }
                break;
                case MQ131CO3: {
                    auto payload = msg.payload.uiValue;
                    METHODLOGS(debug, "MQ131: CO3:%lu", (unsigned long)payload.value);
                }

                break;
                case SPS30Particle: {
                    auto payload = msg.payload.particle;
                    METHODLOGS(debug, "SPS30: 2p5:%f, 10p0:%f, typical:%f", (double)payload.mc_2p5, (double)payload.mc_10p0, (double)payload.tps);
                }
                break;
                case MICS4514CO1NO2: {
                    auto payload = msg.payload.co1_no2;
                    METHODLOGS(debug, "MiCS: co1:%f no2:%f", payload.co1, payload.no2);
                }
                break;
                default:
                    METHODLOG(warn, "unrecognized message type");
                    break;
            }
        }
    }
}
