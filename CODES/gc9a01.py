"""
GC9A01 240x240 Round TFT Display Driver for MicroPython (SPI)
Optimized SPI bus setup with hardware line stabilization delays for ESP32-C3 RISC-V.
"""

import time
import ustruct
from micropython import const

# GC9A01 Commands
GC9A01_SWRESET = const(0x01)
GC9A01_SLPOUT  = const(0x11)
GC9A01_INVOFF  = const(0x20)
GC9A01_INVON   = const(0x21)
GC9A01_DISPON  = const(0x29)
GC9A01_CASET   = const(0x2A)
GC9A01_RASET   = const(0x2B)
GC9A01_RAMWR   = const(0x2C)
GC9A01_MADCTL  = const(0x36)
GC9A01_COLMOD  = const(0x3A)

def color565(r, g, b):
    """Convert RGB 888 to RGB 565 color (uint16 big-endian)."""
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

# Common predefined colors (RGB565 uint16)
BLACK   = const(0x0000)
WHITE   = const(0xFFFF)
RED     = const(0xF800)
GREEN   = const(0x07E0)
BLUE    = const(0x001F)
CYAN    = const(0x07FF)
MAGENTA = const(0xF81F)
YELLOW  = const(0xFFE0)
ORANGE  = const(0xFD20)
GRAY    = const(0x7BEF)
DARKGRAY = const(0x39E7)

class GC9A01:
    """MicroPython Driver for GC9A01 240x240 Circular Display over SPI."""

    def __init__(self, spi, dc, cs=None, rst=None, width=240, height=240, rotation=0):
        self.spi = spi
        self.dc = dc
        self.cs = cs
        self.rst = rst
        self.width = width
        self.height = height
        self._rotation = rotation

        self.dc.init(self.dc.OUT, value=0)
        if self.cs:
            self.cs.init(self.cs.OUT, value=1)
        if self.rst:
            self.rst.init(self.rst.OUT, value=1)

        self.reset()
        self.init_display()
        self.set_rotation(self._rotation)

    def write_cmd(self, cmd, data=None):
        """Send command byte and optional parameters at maximum SPI speed."""
        if self.cs:
            self.cs.value(0)
        self.dc.value(0)
        self.spi.write(bytearray([cmd]))
        if data:
            self.dc.value(1)
            self.spi.write(data)
        if self.cs:
            self.cs.value(1)

    def write_data(self, data):
        """Send raw data bytes under CS low pulse at maximum SPI speed."""
        if self.cs:
            self.cs.value(0)
        self.dc.value(1)
        self.spi.write(data)
        if self.cs:
            self.cs.value(1)

    def reset(self):
        """Hardware reset of display module."""
        if self.rst:
            self.rst.value(1)
            time.sleep_ms(20)
            self.rst.value(0)
            time.sleep_ms(50)
            self.rst.value(1)
            time.sleep_ms(150)

    def init_display(self):
        """Send complete initialization command sequence to GC9A01."""
        init_seq = (
            (GC9A01_SWRESET, b""), # Software reset
            (0xEF, b""),
            (0xEB, b"\x14"),
            (0xFE, b""),
            (0xEF, b""),
            (0xEB, b"\x14"),
            (0x84, b"\x40"),
            (0x85, b"\xFF"),
            (0x86, b"\xFF"),
            (0x87, b"\xFF"),
            (0x88, b"\x0A"),
            (0x89, b"\x21"),
            (0x8A, b"\x00"),
            (0x8B, b"\x80"),
            (0x8C, b"\x01"),
            (0x8D, b"\x01"),
            (0x8E, b"\xFF"),
            (0x8F, b"\xFF"),
            (0xB6, b"\x00\x20"),
            (0x36, b"\x08"),        # MADCTL BGR
            (0x3A, b"\x05"),        # 16-bit color format (RGB565)
            (0x90, b"\x08\x08\x08\x08"),
            (0xBD, b"\x06"),
            (0xBC, b"\x00"),
            (0xFF, b"\x60\x01\x04"),
            (0xC3, b"\x13"),
            (0xC4, b"\x13"),
            (0xC9, b"\x22"),
            (0xBE, b"\x11"),
            (0xE1, b"\x10\x0E"),
            (0xDF, b"\x21\x0C\x02"),
            (0xF0, b"\x45\x09\x08\x08\x26\x2A"),
            (0xF1, b"\x43\x70\x72\x36\x37\x6F"),
            (0xF2, b"\x45\x09\x08\x08\x26\x2A"),
            (0xF3, b"\x43\x70\x72\x36\x37\x6F"),
            (0xED, b"\x1B\x0B"),
            (0xAE, b"\x77"),
            (0xCD, b"\x63"),
            (0x70, b"\x07\x07\x04\x0E\x0F\x09\x07\x08\x03"),
            (0xE8, b"\x34"),
            (0x62, b"\x18\x0D\x71\xED\x70\x70\x18\x0D\x71\xED\x70\x70"),
            (0x63, b"\x18\x11\x71\xF1\x70\x70\x18\x11\x71\xF1\x70\x70"),
            (0x64, b"\x28\x29\xF1\x01\xF1\x00\x07"),
            (0x66, b"\x3C\x00\xCD\x67\x45\x45\x10\x00\x00\x00"),
            (0x67, b"\x00\x3C\x00\x00\x00\x01\x54\x10\x32\x98"),
            (0x74, b"\x10\x85\x80\x00\x00\x4E\x00"),
            (0x98, b"\x3E\x07"),
            (0x35, b"\x00"),       # TE ON
            (GC9A01_INVON, b""),   # Invert display colors
            (GC9A01_SLPOUT, b""),  # Sleep Out
            (GC9A01_DISPON, b""),  # Display ON
        )

        for cmd, data in init_seq:
            self.write_cmd(cmd, data)
            time.sleep_ms(10)

        time.sleep_ms(120)

    def set_rotation(self, rotation):
        """Set orientation (0: 0 deg, 1: 90 deg, 2: 180 deg, 3: 270 deg)."""
        self._rotation = rotation % 4
        madctl_values = [0x08, 0x68, 0xC8, 0xA8]
        self.write_cmd(GC9A01_MADCTL, bytearray([madctl_values[self._rotation]]))

    def set_window(self, x0, y0, x1, y1):
        """Define memory write rectangle window."""
        self.write_cmd(GC9A01_CASET, ustruct.pack(">HH", x0, x1))
        self.write_cmd(GC9A01_RASET, ustruct.pack(">HH", y0, y1))
        self.write_cmd(GC9A01_RAMWR)

    def fill(self, color):
        """Fill screen with a solid color."""
        self.set_window(0, 0, self.width - 1, self.height - 1)
        pixel_bytes = ustruct.pack(">H", color)
        chunk = pixel_bytes * 512
        num_chunks = (self.width * self.height) // 512
        for _ in range(num_chunks):
            self.write_data(chunk)

    def fill_rect(self, x, y, w, h, color):
        """Fill rectangular area on display."""
        if x >= self.width or y >= self.height or w <= 0 or h <= 0:
            return
        x1 = min(self.width - 1, x + w - 1)
        y1 = min(self.height - 1, y + h - 1)
        total_pixels = (x1 - x + 1) * (y1 - y + 1)
        self.set_window(x, y, x1, y1)
        pixel_bytes = ustruct.pack(">H", color)
        chunk = pixel_bytes * min(total_pixels, 512)
        rem = total_pixels
        while rem > 0:
            to_write = min(rem, 512)
            self.write_data(chunk[:to_write * 2])
            rem -= to_write

    def draw_line(self, x0, y0, x1, y1, color):
        """Draw line using Bresenham algorithm with fast horizontal/vertical fill_rect acceleration."""
        if x0 == x1:
            y_start = min(y0, y1)
            h = abs(y1 - y0) + 1
            self.fill_rect(x0, y_start, 1, h, color)
            return
        if y0 == y1:
            x_start = min(x0, x1)
            w = abs(x1 - x0) + 1
            self.fill_rect(x_start, y0, w, 1, color)
            return

        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            if 0 <= x0 < self.width and 0 <= y0 < self.height:
                self.fill_rect(x0, y0, 1, 1, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def write_buffer(self, x, y, w, h, buf):
        """Write 16-bit RGB565 buffer chunk directly to display window."""
        self.set_window(x, y, x + w - 1, y + h - 1)
        self.write_data(buf)
