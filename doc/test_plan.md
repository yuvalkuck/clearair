# 🧪 Test Plan

Bench test plan for the WeAct G474CE Long carrier board (`hardware/WeAct-G474CE-Long`). The sensor tunnel does not exist yet, so these stages check function only: no airflow and no calibration. Work through the stages in order, and do not start a stage until the one before it passes.

| Stage | Subject | Needs |
| :--- | :--- | :--- |
| [A](#stage-a-unpowered-checks) | Unpowered checks | Meter only |
| [B](#stage-b-first-power-up) | First power-up | Lab supply, no firmware |
| [C](#stage-c-io-by-hand) | Outputs, inputs, I2C by hand | Lab supply, no firmware |
| [D](#stage-d-analog-sensors-and-80-mm-fans) | Analog sensors, 80 mm fans, full load | Lab supply, no firmware |
| [E](#stage-e-flash-and-existing-firmware) | Flash, existing firmware | Firmware in this repo |
| [F](#stage-f-system-test-with-the-test-keys) | System test with the 4 test keys | New firmware (not written yet) |
| [G](#stage-g-mains-triac-and-ac-fan) | TRIAC and AC fan | 220VAC mains |
| [H](#stage-h-ac-dc-modules) | AC-DC modules replace the lab supply | 220VAC mains |
| [I](#stage-i-after-install) | After install, field test | Tunnel + enclosure |

## Tools and test points

**Tools:** multimeter, lab supply with two outputs and a current limit (12V and 5V), a jumper wire with a 1 kΩ resistor in series, a USB-C cable, and the STLINK-V3MINIE.

**Test points on the board:**

| Test point | Net |
| :--- | :--- |
| `TP1` | GND |
| `TP2` | +3V3 |
| `TP3` | ZC_OUT |
| `TP4` | TRIAC_DIMMER |
| `TP5` | +5V |
| `TP6` | +12V |
| `TP7` | FAN_12V (after relay `K1`) |

**Driving a pin net by hand (Stages C and D):** with no firmware on the G4, its pins stay in the reset state (high impedance). A pin net can then be pulled to 3V3 (`TP2`) or to GND (`TP1`) through the 1 kΩ jumper. Never put more than 3.3 V on a pin net.

**Test keys:** `SW3`-`SW6` on the board, read on the `PA4` ladder (`FORCE_STATES_SW`). `TEST1` sets the fan off, `TEST2` lowers the fan speed, `TEST3` raises it, and `TEST4` sets 100% fan plus the buzzer. Stage C checks their hardware. Stage F uses them as the system test, and Stage I uses them again after install. The firmware for them is not written yet.

Fill in the "Measured" and "Pass" columns while you test.

## Stage A: unpowered checks

No supply, no modules, no USB. Meter in Ω or continuity mode.

| # | Check | How | Expected | Measured | Pass |
| :--- | :--- | :--- | :--- | :--- | :--- |
| A1 | Solder bridges | Look at the headers, the `U6` socket and `K1` with a magnifier | No solder between pads | | |
| A2 | `C27` 220 µF | Look at the marking | `+` lead in the `+` pad | | |
| A3 | `D3` 1N4148 | Look at the band | Band (cathode) toward +12V | | |
| A4 | `D1` green, `D2` red | Look at the flat side | Flat side (cathode) as on the silkscreen | | |
| A5 | `Q3`, `Q6` 2N2222A | Look at the flat side | As on the silkscreen | | |
| A6 | `U6` 74AHCT125N | Look at the notch | Notch as on the silkscreen | | |
| A7 | `A1` WeAct board | Look at pin 1 | Pin 1 as on the silkscreen | | |
| A8 | +12V to GND | Black on `TP1`, red on `TP6` | Not near 0 Ω (may climb while caps charge) | | |
| A9 | +5V to GND | Red on `TP5` | Not near 0 Ω | | |
| A10 | +3V3 to GND | Red on `TP2` | Not near 0 Ω | | |
| A11 | FAN_12V to GND | Red on `TP7` | Not near 0 Ω | | |
| A12 | Rail to rail | `TP6`-`TP5`, `TP5`-`TP2`, `TP6`-`TP7` | No short | | |
| A13 | Module headers | For `J3`-`J7`, `J9`, `J10`: check against the schematic and the module's pin labels | VCC and GND on the board match the module | | |
| A14 | `P3` 5V pad vs USB-C VBUS | Diode mode between the `P3` pad and the VBUS pin of the USB-C connector, both directions | Write down: continuity (one 5V source at a time) or a diode drop (a diode is in between) | | |
| A15 | Standby keys | `PB1` to GND while pressing `SW7`, then while shorting `J12` | Short when pressed, open when released | | |
| A16 | Cold-boot key | `PB2` to GND while pressing `SW2` | Short when pressed | | |
| A17 | Reset key | NRST to GND while pressing `SW1` | Short when pressed | | |

## Stage B: first power-up

No modules plugged in, no USB. 12V first, then 5V.

| # | Check | How | Expected | Measured | Pass |
| :--- | :--- | :--- | :--- | :--- | :--- |
| B1 | 12V on | 12V only, current limit 100 mA | `TP6` = 12 V, a few mA | | |
| B2 | Relay open | Measure `TP7` | 0 V (`R44` holds `PB5` low, `K1` open) | | |
| B3 | Buzzer off | Listen | Silent | | |
| B4 | 5V on | Add 5V, current limit 300 mA | `TP5` = 5 V | | |
| B5 | 3V3 rail | Measure `TP2` | 3.2-3.4 V | | |
| B6 | 5V current | Read the supply | Near the board estimate in the power budget (about 40-60 mA) | | |
| B7 | Status LED | Look | Red `D2` on, green `D1` off | | |
| B8 | Heat | Touch after 1 min | `U6`, the board regulator, `Q3` and `Q6` not hot | | |

## Stage C: I/O by hand

Lab supply on, no firmware. The I2C checks need the I2C modules plugged in.

| # | Check | How | Expected | Measured | Pass |
| :--- | :--- | :--- | :--- | :--- | :--- |
| C1 | Relay on | 1 kΩ from `TP2` to the `PB5` net | `K1` clicks, `TP7` = 12 V, 12V current rises about 17 mA | | |
| C2 | Relay off | Remove the jumper | `K1` opens, `TP7` = 0 V | | |
| C3 | Buzzer on | 1 kΩ from `TP2` to the `PB10` net | `BZ1` sounds | | |
| C4 | Buzzer off | Remove the jumper | Silent | | |
| C5 | Status LED | 1 kΩ from the `PB0` net to `TP1` | Green `D1` on, red `D2` off | | |
| C6 | Level shifter high | 1 kΩ from `TP2` to the `PA6` net | `J9` pin 2 (DIN) about 5 V | | |
| C7 | Level shifter low | 1 kΩ from the `PA6` net to `TP1` | `J9` pin 2 about 0 V | | |
| C8 | Test keys | Measure the `PA4` node, press each key | None 3.30 V, `TEST1` (`SW3`) 0.30 V, `TEST2` (`SW4`) 0.82 V, `TEST3` (`SW5`) 1.34 V, `TEST4` (`SW6`) 1.98 V | | |
| C9 | Off-board keys | Measure the `PB11` node, short each `J11` pin 1-4 to pin 5 | None 3.30 V, KEY1 0.30 V, KEY2 0.82 V, KEY3 1.34 V, KEY4 1.98 V | | |
| C10 | I2C1 idle | Plug in `J3` SPS30 and `J4` BME680, then measure SDA and SCL | 3.3 V, not 5 V | | |
| C11 | I2C2 idle | Plug in `J7` RTC (and `J10` display if fitted), then measure SDA and SCL | 3.3 V, not 5 V | | |

## Stage D: analog sensors and 80 mm fans

Lab supply on, no firmware. Plug in one module at a time and note the 5V current step. Raise the current limits as needed: 5V up to 1 A, 12V up to 1.5 A.

| # | Check | How | Expected | Measured | Pass |
| :--- | :--- | :--- | :--- | :--- | :--- |
| D1 | MQ131 `J5` | Plug in, read the 5V current | About +170 mA. Heater warms up | | |
| D2 | MQ131 output | Measure the `PA0` net | ≤ 3.3 V | | |
| D3 | MiCS-4514 `J6` | Plug in, read the 5V current | About +60 mA | | |
| D4 | MiCS-4514 outputs | Measure the `PA1` and `PA7` nets | ≤ 3.3 V | | |
| D5 | SPS30 `J3` | Read the 5V current | Note the step. Its fan only starts on an I2C command | | |
| D6 | WS2812B `J9` | Plug in, read the 5V current | Note the step | | |
| D7 | RobotDyn `U5` logic side | Plug in, no mains | `TP3` (`PB12` side) ≤ 3.3 V, `TP4` = 0 V | | |
| D8 | 80 mm fans on | Plug in `M2` and `M3`, close `K1` as in C1 | Both fans run at full speed (PWM not driven) | | |
| D9 | Fan tach | Measure the `PA5` and `PB3` nets while the fans run | Never above 3.3 V | | |
| D10 | 12V full load | Fans running and buzzer on (C3) | 12V current ≤ 1.44 A | | |
| D11 | 5V full load | All modules plugged in, after the heaters settle | ≤ 0.83 A, near 0.44 A typical | | |
| D12 | Heat | Touch after 5 min | Nothing hot except the gas sensor heaters | | |

## Stage E: flash and existing firmware

Wire the 5V supply as found in A14. The log is on `USART2` (`PA2` TX, `PA3` RX), 115200 baud, 8N1. Read it through the STLINK-V3MINIE VCP or a USB-serial adapter.

| # | Check | How | Expected | Measured | Pass |
| :--- | :--- | :--- | :--- | :--- | :--- |
| E1 | MCU found | Hold BOOT0, plug in USB, connect STM32CubeProgrammer (USB DFU), or connect the STLINK-V3MINIE (SWD) | Device reads as STM32G474 | | |
| E2 | Build and flash | `cmake --preset Debug`, `cmake --build build/Debug`, flash | Flash and verify OK | | |
| E3 | Startup | Reset, watch the log | "End startup" in the log | | |
| E4 | Board LED | Look at the `PC6` LED | Toggles every 1000 ms (all OK). Every 100 ms means the RTC, BME680, MQ131 or SPS30 failed to configure | | |
| E5 | RTC | Read the log | `RTC offline: ...min (...)` line, RTC at 0x51 on `I2C2` | | |
| E6 | Warm boot | Reset again within 1 hour, `SW2` not pressed | Log says `warm` | | |
| E7 | Cold boot | Reset while holding `SW2` (`PB2`) | Log says `cold` | | |
| E8 | BME680 | Read the log | Readings arrive | | |
| E9 | SPS30 | Read the log | Readings arrive, SPS30 fan runs | | |
| E10 | MiCS-4514 | Read the log | Readings arrive | | |
| E11 | MQ131 | Read the log | No readings for 48 h after a cold boot (30 min after a warm boot) | | |

## Stage F: system test with the test keys

Needs firmware that is not written yet: 80 mm fan PWM and tach, relay, standby, status LED, key ladders and WS2812B.

| # | Check | How | Expected | Measured | Pass |
| :--- | :--- | :--- | :--- | :--- | :--- |
| F1 | Fan PWM | Scope on `PA10` and `PA9` | 25 kHz | | |
| F2 | Fan RPM | Read the log | RPM from the `PA5` and `PB3` tach for each fan | | |
| F3 | `TEST1` | Press `SW3` | Fan off | | |
| F4 | `TEST2` | Press `SW4` | Fan speed one step lower | | |
| F5 | `TEST3` | Press `SW5` | Fan speed one step higher | | |
| F6 | `TEST4` | Press `SW6` | 100% fan plus the buzzer pattern | | |
| F7 | Kick-start | Start the fan from off | 100% for `FAN_KICKSTART_MS`, then the set speed | | |
| F8 | Alarm pattern | Evacuate level | As in README "Evacuate alarm" | | |
| F9 | Standby on | Press and release `SW7` (or `J12`) | On release: `K1` opens, fans stop, buzzer off, LED changes | | |
| F10 | Standby off | Press and release again | Back to normal | | |
| F11 | WS2812B | Change the levels with the keys | Each LED color follows its metric level | | |

## Stage G: mains, TRIAC and AC fan

**220VAC is lethal.** Work with the board unplugged from the mains, use an isolated scope or differential probe, and never touch the RobotDyn high-voltage side while it is powered.

| # | Check | How | Expected | Measured | Pass |
| :--- | :--- | :--- | :--- | :--- | :--- |
| G1 | Zero cross | Scope on `TP3` | Pulses at 100 Hz (two per 50 Hz period), ≤ 3.3 V on `PB12` | | |
| G2 | Gate pulses | Scope on `TP4` | One pulse after each zero cross | | |
| G3 | Fan follows keys | Use the test keys | The AC fan speed changes with each key | | |
| G4 | Minimum speed | Lower the speed to 50% | Fan runs without humming or stalling. Tune `TRIAC_MIN_POWER_DELAY_US` | | |
| G5 | Spin-up | Start the fan from off | Fan starts. Tune `FAN_KICKSTART_MS` | | |

## Stage H: AC-DC modules

The same safety rules as Stage G apply.

| # | Check | How | Expected | Measured | Pass |
| :--- | :--- | :--- | :--- | :--- | :--- |
| H1 | Startup | Switch on the mains and measure `TP5` and `TP6` | 5 V and 12 V, no overshoot that resets the MCU | | |
| H2 | Ripple | Scope on `TP5` and `TP6` at full load | Note the value | | |
| H3 | Full load | Repeat D10 and D11 | Same limits as Stage D | | |

## Stage I: after install

Needs the tunnel and the enclosure.

| # | Check | How | Expected | Measured | Pass |
| :--- | :--- | :--- | :--- | :--- | :--- |
| I1 | Key test | Repeat F3-F10 in the installed unit | Same results as Stage F | | |
| I2 | Field test | Run with the welder ([Roadmap](roadmap.md) items 6-7) | Fan level and alarm follow the air | | |
