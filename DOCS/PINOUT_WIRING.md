# Micro-Compass-Vario Hardware Pinout & Wiring Guide

**System**: Micro-Compass-Vario (Flight Computer & Variometer)  
**Microcontroller**: ESP32-C3 SuperMini (RISC-V Architecture, 160MHz)  
**Display**: GC9A01 1.28" 240x240 Round TFT Display (7-Pin SPI)  
**Sensors**: 
- **GY-271 Magnetometer** (QMC5883L / QMC6310, I2C `0x0D`)
- **MPU-6050 IMU** (6-DOF Accelerometer + Gyroscope, I2C `0x68`)
- **BMP280 Barometer** (Pressure & Altimeter, I2C `0x76`)
**Audio**: Passive Buzzer (PWM Tone Generation on GPIO 4)

---

## 📌 1. Master System Wiring Matrix

```
                              +-------------------------+
                              |   ESP32-C3 SuperMini    |
                              +-------------------------+
                               | 3.3V  GND  IO0  IO1  IO4
                               |   |    |    |    |    |
        +----------------------+   |    |    |    |    +---------------------+
        |                          |    |    |    |                          |
        v                          v    v    |    |                          v
+---------------+                +-------------+  |                  +---------------+
|  GC9A01 TFT   |                | Power Rails |  |                  | Passive Buzzer|
| (240x240 SPI) |                | (3.3V & GND)|  |                  | (Vario Audio) |
+---------------+                +-------------+  |                  +---------------+
| VCC -> 3.3V   |                                 |                  | (+) -> GPIO 4 |
| GND -> GND    |         +-----------------------+                  | (-) -> GND    |
| SCL -> GPIO10 |         |           |           |                  +---------------+
| SDA -> GPIO6  |         v           v           v
| DC  -> GPIO5  |   +-----------+ +-----------+ +-----------+
| CS  -> GPIO7  |   |  GY-271   | | MPU-6050  | |  BMP280   |
| RES -> GPIO3  |   | (Compass) | |   (IMU)   | |  (Baro)   |
+---------------+   +-----------+ +-----------+ +-----------+
                    | VCC->3.3V | | VCC->3.3V | | VCC->3.3V |
                    | GND->GND  | | GND->GND  | | GND->GND  |
                    | SDA->IO0  | | SDA->IO0  | | SDA->IO0  |
                    | SCL->IO1  | | SCL->IO1  | | SCL->IO1  |
                    +-----------+ | AD0->GND  | | SDO->GND  |
                                  +-----------+ +-----------+
```

---

## 🖥️ 2. GC9A01 Round TFT Display Connections (SPI)

| Display Pin | Label on Display | ESP32-C3 SuperMini Pin | Hardware Function | Notes |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **VCC** | **3.3V** | Power (3.3V) | Connect to 3.3V rail |
| 2 | **GND** | **GND** | Ground | Connect to common GND rail |
| 3 | **SCL / SCK** | **GPIO 10** | SPI Clock (SCK) | Hardware SPI1 Bus (20 MHz) |
| 4 | **SDA / MOSI** | **GPIO 6** | SPI Data (MOSI) | Hardware SPI1 Bus |
| 5 | **DC** | **GPIO 5** | Data / Command Control | GPIO Output |
| 6 | **CS** | **GPIO 7** | SPI Chip Select | GPIO Output |
| 7 | **RES / RST** | **GPIO 3** | Hardware Reset | GPIO Output |

---

## 🧲 3. Shared I2C Sensors Bus (GPIO 0 & GPIO 1)

All three sensors connect in parallel to the single I2C bus:

| Module | Pin | ESP32-C3 SuperMini Pin | Function | I2C Address |
| :--- | :--- | :--- | :--- | :--- |
| **GY-271 (QMC5883L)** | VCC / GND | 3.3V / GND | Power | `0x0D` (Fixed) |
| | SDA / SCL | **GPIO 0 / GPIO 1** | I2C Bus | |
| **MPU-6050 (IMU)** | VCC / GND | 3.3V / GND | Power | `0x68` (AD0 to GND) |
| | SDA / SCL | **GPIO 0 / GPIO 1** | I2C Bus | |
| | AD0 | **GND** | Address Select | Sets address to `0x68` |
| **BMP280 (Altimeter)**| VCC / GND | 3.3V / GND | Power | `0x76` (SDO to GND) |
| | SDA / SCL | **GPIO 0 / GPIO 1** | I2C Bus | |
| | SDO | **GND** | Address Select | Sets address to `0x76` |

> [!TIP]  
> If using wires longer than 10 cm or experiencing I2C bus noise, attach **4.7kΩ pull-up resistors** between SDA and 3.3V, and between SCL and 3.3V.

---

## 🔊 4. Acoustic Variometer Buzzer (GPIO 4)

| Buzzer Pin | ESP32-C3 SuperMini Pin | Hardware Function | Notes |
| :--- | :--- | :--- | :--- |
| **Signal (+)** | **GPIO 4** | PWM Output | Uses `machine.PWM` for variable frequency tone |
| **Ground (-)** | **GND** | Ground | Common Ground |

---

## ⚡ 5. Power Distribution, Battery Options & Consumption

### Current Consumption Breakdown
| Component | Active Current | Peak Current |
| :--- | :--- | :--- |
| **ESP32-C3 SuperMini** (Wi-Fi off, 160MHz) | ~35 mA | ~55 mA |
| **GC9A01 Round TFT Display** (Full backlight) | ~30 mA | ~45 mA |
| **GY-271 Magnetometer** (QMC5883L / QMC6310) | ~1 mA | ~2 mA |
| **MPU-6050 6-DOF IMU** | ~3.5 mA | ~4 mA |
| **BMP280 Barometer / Altimeter** | ~0.1 mA | ~0.5 mA |
| **Passive Buzzer** (Active sound generation) | ~10 mA | ~20 mA |
| **Total Average Operating Current** | **~80 mA** | **~125 mA** |

---

### 🔋 Battery Specifications & Powering Methods

#### Recommended Battery Types:
1. **1S LiPo (Lithium Polymer) / Li-Ion Battery (3.7V Nominal, 4.2V Fully Charged)**:
   - **Form Factor**: Flat compact cell (e.g. 503035, 603048 or 18650 cell).
   - **Connection**:
     - Connect Battery (+) to the **`5V / VBUS`** pin on the ESP32-C3 SuperMini (which feeds into the onboard low-dropout 3.3V voltage regulator).
     - Connect Battery (-) to **`GND`**.
   - **Recommended Add-on**: A micro **TP4056 USB-C charging module with protection** (prevents over-discharge below 3.0V).

2. **5V USB Power Source / Micro Power Bank**:
   - Direct plug-in via the native USB-C port of the ESP32-C3 SuperMini.

#### Estimated Battery Flight Autonomy:
* **300 mAh 1S LiPo**: **~3.5 hours** of continuous flight.
* **500 mAh 1S LiPo**: **~5.5 to 6 hours** of continuous flight.
* **1000 mAh 1S LiPo / 18650**: **~11 to 12 hours** of continuous flight.
* **2500 mAh Micro Power Bank**: **> 28 hours** of continuous operation.

---

## 🛠️ 6. Software Pin Configuration (`CODES/main.py`)

```python
# Hardware SPI (GC9A01 Display)
PIN_SCK  = 10  # GPIO 10 (SCL on display)
PIN_MOSI = 6   # GPIO 6  (SDA on display)
PIN_DC   = 5   # GPIO 5  (DC on display)
PIN_CS   = 7   # GPIO 7  (CS on display)
PIN_RST  = 3   # GPIO 3  (RES on display)

# I2C Bus (GY-271, MPU-6050, BMP280)
PIN_SDA  = 0   # GPIO 0
PIN_SCL  = 1   # GPIO 1

# Vario Buzzer Audio (PWM)
PIN_BUZZER = 4 # GPIO 4
```
