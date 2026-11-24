# 🚨 Safety Core & Fail-Safes

**Status:** none of the fail-safes below is implemented yet. The implemented safety behavior is the threshold-based fan ramp and buzzer in [Sensor-Level Fan Control](../README.md#sensor-level-fan-control).

*   **Loss of Signal Safeguard:** If the `I2C1` communication lines stall, or if the `ADC1` DMA buffer fails to cycle for 5 consecutive periods, the firmware shifts into an Emergency Override state, locking the TRIAC delay to 0% to force the exhaust fan to run continuously at 100% capacity.
*   **Electrical Fault Monitoring:** If any analog channel detects an out-of-bounds voltage (0V matching a short circuit, or 3.3V matching a ruptured line), the event is reported over telemetry and the ventilation loop steps up to full speed.
*   **Non-Volatile Baseline Recovery:** The system stores the active BSEC2 engine state data matrix to internal flash sectors every hour to prevent calibration degradation during unexpected system power losses.
