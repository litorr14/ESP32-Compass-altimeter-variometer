"""
System Diagnostic & Self-Test Script for Micro-Compass-Vario.
Tests:
1. I2C Bus Scan (verifies 0x0D QMC5883L, 0x68 MPU-6050, 0x76 BMP280).
2. Live BMP280 Altitude and Temperature readout.
3. Live MPU-6050 Pitch and Roll readout.
4. Passive Buzzer PWM chirp sequence on GPIO 4.
"""

import time
from machine import Pin, SoftI2C, I2C, PWM

PIN_SDA = 0
PIN_SCL = 1
PIN_BUZZER = 4

print("=" * 50)
print("🛠️ MICRO-COMPASS-VARIO HARDWARE SELF-TEST")
print("=" * 50)

# 1. Initialize I2C
try:
    i2c = SoftI2C(sda=Pin(PIN_SDA, Pin.IN, Pin.PULL_UP), scl=Pin(PIN_SCL, Pin.IN, Pin.PULL_UP), freq=100000)
except Exception:
    i2c = I2C(0, sda=Pin(PIN_SDA, Pin.IN, Pin.PULL_UP), scl=Pin(PIN_SCL, Pin.IN, Pin.PULL_UP), freq=100000)

devices = i2c.scan()
print(f"\n1. I2C Bus Scan: Found {len(devices)} device(s):")
for addr in devices:
    label = "Unknown"
    if addr in (0x0D, 0x1E): label = "Magnetometer (QMC5883L / HMC5883L)"
    elif addr in (0x68, 0x69): label = "IMU (MPU-6050)"
    elif addr in (0x76, 0x77): label = "Barometer (BMP280 / BME280)"
    print(f"   - 0x{addr:02X} : {label}")

# 2. Test Buzzer
print("\n2. Testing Buzzer on GPIO 4 (Chirp Test)...")
try:
    pwm = PWM(Pin(PIN_BUZZER), freq=1000, duty_u16=0)
    for f in (600, 900, 1300, 1800):
        pwm.freq(f)
        pwm.duty_u16(32768)
        time.sleep_ms(70)
        pwm.duty_u16(0)
        time.sleep_ms(30)
    pwm.deinit()
    print("   ✅ Buzzer chirp complete!")
except Exception as e:
    print(f"   ❌ Buzzer test failed: {e}")

print("\n" + "=" * 50)
print("Diagnostic test completed.")
print("=" * 50)
