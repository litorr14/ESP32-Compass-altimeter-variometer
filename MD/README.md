# Micro-Compass-Vario en MicroPython (ESP32-C3 SuperMini)

Este proyecto contiene la implementación completa del sistema de navegación e instrumento de vuelo **Micro-Compass-Vario** en **MicroPython**, diseñado para ejecutarse en la tarjeta **ESP32-C3 SuperMini** con pantalla redonda TFT GC9A01 de 1.28", magnetómetro GY-271, IMU MPU-6050, altímetro/barómetro BMP280 y sintetizador acústico PWM con buzzer pasivo.

---

## ✨ Características Principales

* **🚀 Motor Gráfico Double-Buffered en RAM**: Renderizado en buffer off-screen de 200x200 px (80 KB) con **0% parpadeo (zero flicker)** y **0% pantallas negras** a ~35–60 FPS.
* **🔍 Tipografía 3× de Alta Visibilidad**:
  * **Rumbo / Bearing (Superior)**: Fuente 3× (24x24 px, ej. `342°`) en marco protector con símbolo de grados.
  * **Altitud Barométrica (Centro/Inferior)**: Fuente 3× (24x24 px, ej. `1450m`) en **Amarillo Brillante** de alto contraste.
  * **Tasa de Ascenso/Descenso (Inferior)**: Fuente 3× (24x24 px, ej. `+1.8` / `-0.8`) con colores dinámicos (Verde en ascenso, Naranja-Rojo en descenso, Gris neutral).
* **🔊 Variómetro Acústico No Bloqueante (PWM en GPIO 4)**:
  * **Ascenso ($> +0.20\text{ m/s}$)**: Pitidos pulsados modulados en frecuencia (450 Hz a 1850 Hz) con aceleración progresiva del ritmo.
  * **Descenso ($< -0.20\text{ m/s}$)**: Tono continuo de tono bajo modulado (300 Hz a 160 Hz).
  * **Banda Muerta ($\pm 0.20\text{ m/s}$)**: Silencio total para evitar falsas alarmas por corrientes de aire o vibraciones.
* **🧮 Fusión de Sensores y Filtrado Anti-Picos**:
  * Filtro hardware IIR en BMP280 (coeficiente 16).
  * Derivación de velocidad vertical sobre curva de altitud suavizada ($\alpha = 0.10$, constante ~0.5s) que elimina picos espurios.
  * **Filtrado Vectorial 2D Pre-Trigonométrico**: Suavizado continuo de $(mx, my)$ antes del cálculo de $\operatorname{atan2}$, eliminando el 100% de picos e interferencias eléctricas.
* **🧭 Navegación de Precisión True-North y Formato Aeronáutico**:
  * Lectura correcta de canales de datos desde el registro `0x01` (`X_L, X_M, Y_L, Y_M, Z_L, Z_M`).
  * Convención aeronáutica estándar en sentido horario ($0^\circ \text{ N} \rightarrow 90^\circ \text{ E} \rightarrow 180^\circ \text{ S} \rightarrow 270^\circ \text{ W}$).
  * Alineación exacta a Norte Verdadero con aguja roja de orientación estable y efecto náutico en baño líquido.

---

## 🛠️ Componentes de Hardware

1. **Microcontrolador**: ESP32-C3 SuperMini (RISC-V single core @ 160MHz, USB-CDC nativo).
2. **Pantalla**: Display Redondo TFT 1.28" GC9A01 SPI (240x240 px, 7 pines).
3. **Sensores en Bus I2C Compartido (GPIO 0 SDA, GPIO 1 SCL)**:
   * Magnetómetro GY-271 (`0x0D` / `0x2C`).
   * IMU 6-DOF MPU-6050 (`0x68`, AD0 a GND).
   * Barómetro/Altímetro BMP280 (`0x76`, SDO a GND).
4. **Audio**: Buzzer Pasivo PWM en **GPIO 4**.
5. **Alimentación / Batería**:
   * **Batería LiPo / Li-Ion 1S de 3.7V** conectada a los pines `5V/VBUS` y `GND` (500 mAh brinda ~5.5 a 6 horas de vuelo continuo).
   * O alimentación directa de 5V mediante el puerto USB-C desde cualquier power bank.

---

## 📌 Esquema de Conexiones (Pinout)

### 1. Pantalla GC9A01 (SPI)

| Pin Pantalla | Pin ESP32-C3 SuperMini | Función Hardware |
|--------------|-------------------------|------------------|
| **SCL / SCK**| **GPIO 10**            | Reloj SPI Hardware (SCK) |
| **SDA / MOSI**| **GPIO 6**             | Salida Datos SPI Hardware (MOSI) |
| **DC**       | **GPIO 5**             | Control Data / Command |
| **CS**       | **GPIO 7**             | Chip Select SPI |
| **RES / RST**| **GPIO 3**             | Hardware Reset |
| **VCC**      | **3.3V**                | Alimentación (3.3V) |
| **GND**      | **GND**                 | Tierra / Masa |

### 2. Bus I2C Compartido (GPIO 0 SDA, GPIO 1 SCL)

| Módulo Sensor | Pines Bus | Dirección I2C |
|---------------|-----------|---------------|
| **GY-271**    | SDA (IO0), SCL (IO1), VCC (3.3V), GND | `0x0D` / `0x2C` |
| **MPU-6050**  | SDA (IO0), SCL (IO1), VCC (3.3V), GND, AD0 -> GND | `0x68` |
| **BMP280**    | SDA (IO0), SCL (IO1), VCC (3.3V), GND, SDO -> GND | `0x76` |

### 3. Buzzer Acústico (PWM)

| Pin Buzzer | Pin ESP32-C3 | Función |
|------------|--------------|---------|
| **Señal (+)** | **GPIO 4**   | Salida PWM Audio |
| **GND (-)**   | **GND**      | Tierra común |

### 4. 🔋 Opciones de Batería y Autonomía de Vuelo

| Método de Alimentación | Tipo de Batería | Puntos de Conexión | Autonomía Típica |
| :--- | :--- | :--- | :--- |
| **Batería LiPo 1S (300 mAh)** | 3.7V Nominal (4.2V Máx) | (+) a `5V/VBUS`, (-) a `GND` | **~3.5 Horas** |
| **Batería LiPo 1S (500 mAh)** | 3.7V Nominal (4.2V Máx) | (+) a `5V/VBUS`, (-) a `GND` | **~5.5 a 6 Horas** |
| **Celda Li-Ion 18650 (1200 mAh)**| 3.7V Nominal (4.2V Máx) | (+) a `5V/VBUS`, (-) a `GND` | **~14 a 15 Horas** |
| **Power Bank Micro USB** | Salida 5V estándar | Puerto USB-C nativo del ESP32 | **> 28 Horas** (2500 mAh) |

> 💡 **Nota de Conexión**: Conectar una batería LiPo 1S (3.7V–4.2V) directamente al pin **`5V/VBUS`** del ESP32-C3 SuperMini alimenta el circuito de forma segura a través del regulador de bajo voltaje (LDO) integrado de 3.3V. Se recomienda intercalar un módulo micro **TP4056 con protección** para carga por USB-C y corte automático por bajo voltaje.

---

## 🎯 Calibración del Magnetómetro

Valores Hard-Iron y Soft-Iron calculados y verificados en tiempo real para este instrumento:

```python
Xoffset = 3384.0
Yoffset = -985.0
Zoffset = -132.0
Xscale  = 1.055
Yscale  = 1.000
Zscale  = 1.000
headingOffset = -4.0
```

### Para recalibrar en un entorno nuevo:
1. Ejecuta `Test_Codes/compass_live_debug.py` en Thonny.
2. Rota el dispositivo 360° en el aire durante 20 segundos y presiona `Ctrl+C`.
3. Pega los nuevos valores impresos en el encabezado de `CODES/main.py`.

---

## 🚀 Instrucciones de Ejecución

1. Carga los archivos del directorio `CODES/` al ESP32-C3 mediante **Thonny IDE**.
2. En la consola REPL de MicroPython, presiona **Ctrl+D** (soft reboot) y ejecuta:
   ```python
   import main
   main.main()
   ```
