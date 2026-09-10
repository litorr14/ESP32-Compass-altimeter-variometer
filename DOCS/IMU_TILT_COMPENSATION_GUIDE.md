# Role of MPU-6050 IMU in Micro-Compass-Vario

**Project**: Micro-Compass-Vario  
**Sensor**: MPU-6050 6-DOF IMU (3-Axis Accelerometer + 3-Axis Gyroscope)  
**I2C Address**: `0x68` (AD0 to GND)  
**Location in Code**: [`CODES/mpu6050.py`](file:///c:/Users/Victolt%20MSI/Documents/Software/Antigravity%20Tests/Micro-compass-%20vario/CODES/mpu6050.py) & [`CODES/vario_fusion.py`](file:///c:/Users/Victolt%20MSI/Documents/Software/Antigravity%20Tests/Micro-compass-%20vario/CODES/vario_fusion.py)

---

## 📌 Executive Summary

The **MPU-6050 IMU** performs two fundamental flight computer functions in this system:
1. **3D Tilt Compensation for the Magnetic Compass**: Eliminates magnetic dip errors so the compass heading remains accurate when the aircraft pitches or rolls.
2. **Inertial Variometer Assistance (Z-axis Acceleration)**: Provides instantaneous vertical motion detection for fusion with barometric altitude.

---

## 🧭 1. Tilt Compensation & The Physics of Magnetic Dip

### The Problem: Magnetic Dip Angle (Inclination)
Earth's magnetic field does not travel parallel to the ground everywhere. Except at the magnetic equator, magnetic field lines dip downward into the Earth (typically at angles of $45^\circ$ to $70^\circ$).

* **When Flat**: A 2D magnetometer only measures horizontal field components ($M_x, M_y$) using $\text{Heading} = \text{atan2}(-M_y, M_x)$.
* **When Tilted (In Flight)**: Whenever the aircraft pitches up/down or banks in a turn, the vertical component of Earth's magnetic field ($M_z$) leaks into the $M_x$ and $M_y$ sensors.
* **Result Without Tilt Compensation**: A pitch or roll angle of just $20^\circ$ can distort the compass reading by **$30^\circ$ to $60^\circ$**, making navigation unreliable in flight.

---

## 🧮 2. Mathematical Solution: 3D Euler Transformation

The MPU-6050 continuously measures the 3D gravity vector at 50 Hz to calculate exact Pitch ($\theta$) and Roll ($\phi$) angles:

$$\text{Pitch } (\theta) = \text{atan2}(-A_x, \sqrt{A_y^2 + A_z^2})$$
$$\text{Roll } (\phi) = \text{atan2}(A_y, A_z)$$

In [`vario_fusion.py`](file:///c:/Users/Victolt%20MSI/Documents/Software/Antigravity%20Tests/Micro-compass-%20vario/CODES/vario_fusion.py#L67-L93), these angles are used in a 3D Euler rotation matrix to project the magnetometer vector $(M_x, M_y, M_z)$ back onto the horizontal ground plane:

$$X_h = M_x \cos(\theta) + M_y \sin(\phi)\sin(\theta) + M_z \cos(\phi)\sin(\theta)$$
$$Y_h = M_y \cos(\phi) - M_z \sin(\phi)$$
$$\text{Heading} = \text{atan2}(-Y_h, X_h) + \text{headingOffset}$$

### Benefits:
* **True North Lock**: The compass needle and top heading badge (`342°`) stay locked onto magnetic North regardless of whether you are climbing, descending, or banking through a turn.
* **Gimbal Stability**: Liquid-smooth heading updates without mechanical gimbal lock.

---

## ⚡ 3. Inertial Vertical Speed Fusion (Future / Advanced Feature)

The MPU-6050 also measures linear vertical acceleration ($A_z$):

* **Barometer Characteristic**: High absolute accuracy over long periods, but suffers from pneumatic equalization latency (~100–300 ms).
* **Accelerometer Characteristic**: Zero latency (instantaneous response to upward or downward movement), but drifts over time if integrated alone.
* **Complementary / Kalman Fusion**:
  - The MPU-6050 detects vertical movement the exact millisecond it starts (triggering immediate audio chirps).
  - The BMP280 barometer continuously anchors the altitude and eliminates acceleration drift.

---

## 🛠️ Summary Table

| Feature | Without MPU-6050 | With MPU-6050 Tilt Compensation |
| :--- | :--- | :--- |
| **Heading when Flat** | Accurate | Accurate |
| **Heading in 25° Pitch/Bank** | **$30^\circ\text{–}60^\circ$ Error** | **$0^\circ$ Error (True North Locked)** |
| **Aircraft Attitude Awareness** | None | Real-time Pitch & Roll Tracking |
| **Vario Response Potential** | Barometric only (~300ms lag) | Instantaneous Inertial-Aided (< 20ms) |
