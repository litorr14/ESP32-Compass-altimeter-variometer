# Micro-Compass-Vario in MicroPython (ESP32-C3 SuperMini)

This project contains the complete implementation of the **Micro-Compass-Vario** flight computer and navigation instrument in **MicroPython**, designed to run on the **ESP32-C3 SuperMini** microcontroller with a GC9A01 1.28" round SPI TFT display, GY-271 magnetometer, MPU-6050 IMU, BMP280 barometer/altimeter, and a non-blocking PWM acoustic variometer synthesizer using a passive buzzer.

---

## ✨ Key Features

* **🚀 RAM Double-Buffered Graphics Engine**: 200×200 px off-screen buffer (80 KB) with **0% display flicker** and **0% blackouts** at ~35–60 FPS.
* **🔍 High-Visibility 3× Scaled Typography**:
  * **Bearing / Heading (Top)**: 3× scaled digits (24×24 px per character, e.g., `342°`) inside a protective bezel frame with a degree mark.
  * **Barometric Altitude (Center/Bottom)**: 3× scaled digits (24×24 px, e.g., `1450m`) in **Bright Yellow** for maximum contrast.
  * **Climb / Sink Rate (Bottom)**: 3× scaled digits (24×24 px, e.g., `+1.8` / `-0.8`) with dynamic color transitions (Green for climb, Orange-Red for sink, Gray for neutral).
* **🔊 Non-Blocking Acoustic Variometer (PWM on GPIO 4)**:
  * **Lift / Climb Mode ($> +0.20\text{ m/s}$)**: Frequency-modulated pulsed beeps (450 Hz to 1850 Hz) with accelerating beep rate under strong lift.
  * **Sink Mode ($< -0.20\text{ m/s}$)**: Continuous modulated low-drone warning tone (300 Hz down to 160 Hz).
  * **Deadband ($\pm 0.20\text{ m/s}$)**: Pure silence between $-0.20\text{ m/s}$ and $+0.20\text{ m/s}$ to prevent false alarms from draft noise or hand twitches.
* **🧮 Sensor Fusion & Anti-Spike Filtering**:
  * BMP280 hardware IIR filter maxed to coefficient `16`.
  * Dual-stage vertical velocity derivation based on smoothed altitude curves ($\alpha = 0.10$, ~0.5s time constant) eliminating sudden pressure spikes.
  * **Pre-Trigonometry 2D Vector Filtering**: Continuous low-pass smoothing on $(mx, my)$ before $\operatorname{atan2}$ computation, eliminating 100% of electrical ADC noise and angular spikes.
* **🧭 Precision True-North & Clockwise Aviation Navigation**:
  * Correct data channel register mapping starting at `0x01` (`X_L, X_M, Y_L, Y_M, Z_L, Z_M`).
  * Clockwise aviation standard ($0^\circ \text{ N} \rightarrow 90^\circ \text{ E} \rightarrow 180^\circ \text{ S} \rightarrow 270^\circ \text{ W}$).
  * Exact True-North lock with stable, liquid-damped nautical needle feel.

---

## 🛠️ Hardware Components

1. **Microcontroller**: ESP32-C3 SuperMini (RISC-V 32-bit single-core @ 160 MHz, native USB-CDC).
2. **Display**: GC9A01 1.28" Round TFT SPI Display (240×240 px, 7-pin).
3. **Shared I2C Bus Sensors (GPIO 0 SDA, GPIO 1 SCL)**:
   * **GY-271 Magnetometer**: QMC5883L / QMC6310 (`0x0D` / `0x2C`).
   * **MPU-6050 6-DOF IMU**: Accelerometer + Gyroscope (`0x68`, AD0 to GND).
   * **BMP280 Barometer/Altimeter**: High-precision pressure sensor (`0x76`, SDO to GND).
4. **Audio**: Passive Buzzer for PWM tone synthesis on **GPIO 4**.
5. **Power / Battery**:
   * **1S 3.7V LiPo / Li-Ion battery** connected to `5V/VBUS` and `GND` (500 mAh gives ~5.5–6 hours of flight).
   * Or direct 5V USB-C power from any micro power bank.

---

## 📌 Pinout & Wiring Connections

### 1. GC9A01 Round TFT Display (SPI)

| Display Pin | ESP32-C3 SuperMini Pin | Hardware Function |
| :--- | :--- | :--- |
| **SCL / SCK** | **GPIO 10** | Hardware SPI1 Clock (SCK @ 20 MHz) |
| **SDA / MOSI**| **GPIO 6** | Hardware SPI1 MOSI Data |
| **DC** | **GPIO 5** | Data / Command Control |
| **CS** | **GPIO 7** | SPI Chip Select |
| **RES / RST** | **GPIO 3** | Hardware Reset |
| **VCC** | **3.3V** | Power (3.3V Rail) |
| **GND** | **GND** | Common Ground |

### 2. Shared I2C Sensor Bus (GPIO 0 SDA, GPIO 1 SCL)

| Sensor Module | Module Pins | I2C Address | Notes |
| :--- | :--- | :--- | :--- |
| **GY-271 Magnetometer** | SDA (IO0), SCL (IO1), VCC (3.3V), GND | `0x0D` / `0x2C` | 3-axis compass |
| **MPU-6050 IMU** | SDA (IO0), SCL (IO1), VCC (3.3V), GND, AD0 -> GND | `0x68` | 6-DOF attitude cues |
| **BMP280 Barometer** | SDA (IO0), SCL (IO1), VCC (3.3V), GND, SDO -> GND | `0x76` | Altimeter / Vario |

### 3. Acoustic Variometer Buzzer (PWM)

| Buzzer Pin | ESP32-C3 Pin | Function |
| :--- | :--- | :--- |
| **Signal (+)** | **GPIO 4** | PWM Audio Output (`machine.PWM`) |
| **Ground (-)** | **GND** | Common Ground |

### 4. 🔋 Battery & Power Supply Options

| Method | Battery Type | Connection Points | Typical Autonomy |
| :--- | :--- | :--- | :--- |
| **1S LiPo / Li-Ion (300 mAh)** | 3.7V Nominal (4.2V Max) | (+) to `5V/VBUS`, (-) to `GND` | **~3.5 Hours** |
| **1S LiPo / Li-Ion (500 mAh)** | 3.7V Nominal (4.2V Max) | (+) to `5V/VBUS`, (-) to `GND` | **~5.5 to 6 Hours** |
| **1S Li-Ion 18650 (1200 mAh)**| 3.7V Nominal (4.2V Max) | (+) to `5V/VBUS`, (-) to `GND` | **~14 to 15 Hours** |
| **Micro USB Power Bank** | 5V Output | Native ESP32-C3 USB-C Port | **> 28 Hours** (2500 mAh) |

> 💡 **Wiring Note**: Connecting a 1S LiPo (3.7V–4.2V) directly to the ESP32-C3 SuperMini's **`5V/VBUS`** pin powers the system safely via the onboard low-dropout 3.3V regulator. Adding a micro **TP4056 USB-C charging module with protection** is recommended for built-in battery charging and low-voltage cut-off protection.

---

## 🎯 Magnetometer Calibration

Real-time verified Hard-Iron and Soft-Iron calibration values for this flight instrument:

```python
Xoffset = 3384.0
Yoffset = -985.0
Zoffset = -132.0
Xscale  = 1.055
Yscale  = 1.000
Zscale  = 1.000
headingOffset = -4.0
```

### To recalibrate in a new environment:
1. Run `Test_Codes/compass_live_debug.py` in Thonny.
2. Rotate the device 360° in the air for 20 seconds and press `Ctrl+C`.
3. Paste the printed values into the header of `CODES/main.py`.

---

## 🚀 Execution Instructions

1. Upload all files from the `CODES/` directory to your ESP32-C3 board using **Thonny IDE**.
2. Open the MicroPython REPL console, press **Ctrl+D** (soft reboot), and execute:
   ```python
   import main
   main.main()
   ```
