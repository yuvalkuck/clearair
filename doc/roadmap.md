# 🗺️ Roadmap

- [x] 1. **KiCad schematic.** ✅ **Done.** "Create" is a big word here: Claude generated it on request (`hardware/WeAct-G474CE-Long/clearair.kicad_sch`).
- [x] 2. **Move to a WeAct G4 Long** (STM32G474CEU6 Long + STLINK-V3MINIE).
- [x] 3. **Fan and alarm thresholds:** thresholds, fan ramp, kick-start and the evacuation buzzer trigger are implemented (see [Sensor-Level Fan Control](../README.md#sensor-level-fan-control)). Still to do: calibrate the MQ131 thresholds, measure the real minimum fan speed and spin-up time on the bench, latch the alarm, and add stale-data / loss-of-signal handling.
- [ ] 4. **Sensor cylinder:** design and 3D print a cylinder that holds all the sensitive sensors, downstream of a fan with a 3M 2091 particulate filter.
- [ ] 5. **Minimal field test,** with buttons that inject the fan and alarm events.
- [ ] 6. **Power + MCU enclosure:** design and build it (220V AC to 12V and 5V DC).
- [ ] 7. **Full field test** with the welder.
