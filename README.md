# CleanAir == STM32 F446RE AC Motor Dimming & Multi-Device Control System
The project created for my electric welding room that need to be vent out when the air is not clear.
Project stages:
1. Turn on FAN & control it speed, when air quality require clear the air.
2. Add an alarm when fan is not able to clear the air, and humans need to clear the room.
3. Collect statistics to be able to add more fans if needed.

The HLD design has made by CludeAI, so i will be able to handle the real learning stage for the application & code.
(``See ./doc for PDF``)

* The Bosch BSEC2 is integrated to this code, specifically to STM32f446RE hardware.
* Because SCD30 clock-stretch behavior, it is separate to it own I2C controller.
* External network access is not relevant to this specific system, but if i will need to duplicate it for more stations it will be wize to add WIFI/Zegbee Support with ESP32C6. 
