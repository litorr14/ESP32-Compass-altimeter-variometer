"""
Vario Acoustic Audio Engine for ESP32-C3 PWM (Passive Buzzer on GPIO 4).
Generates standard soaring/paragliding acoustic variometer audio:
- Climbing / Thermal Lift: Pulsed beeps with pitch and beep repetition rate scaling with climb rate (m/s).
- Sinking: Continuous low-pitch sink alarm when descent rate exceeds sink threshold.
- Deadband: Pure silence between lift threshold and sink threshold.
"""

import time
from machine import Pin, PWM

class VarioAudio:
    """Non-blocking Variometer PWM Audio Synthesizer."""

    def __init__(self, pin_num=4, enabled=True):
        self.pin_num = pin_num
        self.enabled = enabled
        self.pwm = None
        
        # Audio Thresholds (in m/s)
        self.climb_start = 0.20   # Lift audio threshold (+0.20 m/s)
        self.climb_max   = 4.00   # Max climb rate for scaling pitch (+4.0 m/s)
        self.sink_start  = -0.20  # Sink audio threshold (-0.20 m/s)
        self.sink_max    = -3.00  # Max sink rate for scaling sink tone (-3.0 m/s)

        # Tone Frequencies (in Hz)
        self.freq_climb_min = 450   # Hz at minimum lift (+0.20 m/s)
        self.freq_climb_max = 1850  # Hz at strong lift (+4.00 m/s)
        self.freq_sink_min  = 300   # Hz at sink start (-0.20 m/s)
        self.freq_sink_max  = 160   # Hz at heavy sink (-3.00 m/s)

        # Pulse Timing (in ms)
        self.period_max_ms  = 480   # ms period between beeps at slight lift
        self.period_min_ms  = 80    # ms period between beeps at strong lift
        self.duty_ratio     = 0.50  # 50% sound ON, 50% sound OFF

        # Internal State Machine
        self.is_beeping = False
        self.tone_on = False
        self.last_state_change = time.ticks_ms()
        self.current_freq = 0

        self._init_pwm()

    def _init_pwm(self):
        try:
            self.pwm = PWM(Pin(self.pin_num), freq=1000, duty_u16=0)
        except Exception as e:
            print(f"Failed to init PWM on GPIO {self.pin_num}: {e}")
            self.pwm = None

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False
        self._silence()

    def toggle(self):
        if self.enabled:
            self.disable()
        else:
            self.enable()
        return self.enabled

    def _sound_on(self, freq_hz):
        if self.pwm and self.enabled:
            try:
                self.pwm.freq(int(freq_hz))
                self.pwm.duty_u16(32768)  # 50% square wave duty
            except Exception:
                pass
        self.tone_on = True

    def _silence(self):
        if self.pwm:
            try:
                self.pwm.duty_u16(0)
            except Exception:
                pass
        self.tone_on = False

    def update(self, climb_rate_mps):
        """
        Non-blocking audio update called in the main loop.
        climb_rate_mps: current vertical speed in meters per second.
        """
        if not self.enabled or self.pwm is None:
            self._silence()
            return

        now = time.ticks_ms()

        # 1. SINK TONE: Continuous modulated low drone when sinking
        if climb_rate_mps <= self.sink_start:
            sink_clipped = max(min(climb_rate_mps, self.sink_start), self.sink_max)
            # fraction: 0.0 (at -0.20 m/s) to 1.0 (at -3.00 m/s)
            fraction = (self.sink_start - sink_clipped) / (self.sink_start - self.sink_max)
            sink_freq = int(self.freq_sink_min - fraction * (self.freq_sink_min - self.freq_sink_max))
            self._sound_on(sink_freq)
            self.is_beeping = False
            return

        # 2. DEADBAND: Silence between sink_start and climb_start
        if climb_rate_mps < self.climb_start:
            if self.tone_on:
                self._silence()
            self.is_beeping = False
            return

        # 3. CLIMB / LIFT: Pulsed modulated beeping
        climb_clipped = min(max(climb_rate_mps, self.climb_start), self.climb_max)
        fraction = (climb_clipped - self.climb_start) / (self.climb_max - self.climb_start)

        # Calculate frequency and period
        target_freq = int(self.freq_climb_min + fraction * (self.freq_climb_max - self.freq_climb_min))
        period_ms = int(self.period_max_ms - fraction * (self.period_max_ms - self.period_min_ms))
        on_time_ms = int(period_ms * self.duty_ratio)
        off_time_ms = period_ms - on_time_ms

        elapsed = time.ticks_diff(now, self.last_state_change)

        if not self.is_beeping:
            # Start fresh beep cycle immediately upon entering lift
            self.is_beeping = True
            self._sound_on(target_freq)
            self.last_state_change = now
        else:
            if self.tone_on:
                # Currently making sound: check if on_time expired
                if elapsed >= on_time_ms:
                    self._silence()
                    self.last_state_change = now
            else:
                # Currently in silence pause: check if off_time expired
                if elapsed >= off_time_ms:
                    self._sound_on(target_freq)
                    self.last_state_change = now

    def deinit(self):
        """Turn off PWM audio."""
        self._silence()
        if self.pwm:
            try:
                self.pwm.deinit()
            except Exception:
                pass
            self.pwm = None
