"""
Micro-Compass-Vario UI Renderer for MicroPython and GC9A01 Display (240x240).
High-performance scanline rasterization with RAM double-buffering.
Displays:
1. Rotating Compass Rose & 3D Dual-Triangle Needle
2. 3x Large Heading readout (Degrees, same horizontal orientation)
3. 3x Large Barometric Altitude readout (m)
4. 3x Large Variometer Climb/Sink rate readout (m/s)
"""

import math
import framebuf
from gc9a01 import color565, BLACK, WHITE, RED, GREEN, BLUE, YELLOW, ORANGE, GRAY, DARKGRAY

# Color definitions (byte-swapped for GC9A01 FrameBuffer)
C_BG        = BLACK
C_BEZEL     = color565(70, 80, 100)
C_NORTH     = 0x00F8                # Pure Red
C_SOUTH     = WHITE
C_HEADING   = color565(0, 220, 255)  # Cyan/Gold
C_ALT_TEXT  = color565(255, 235, 0)  # Bright Yellow
C_CLIMB     = color565(0, 250, 80)   # Vivid Green
C_SINK      = color565(255, 70, 0)   # Vivid Orange-Red
C_NEUTRAL   = GRAY

class CompassUI:
    """Integrated Flight Instrument UI for Compass + Variometer."""

    def __init__(self, display):
        self.display = display
        self.cx = 120  # Screen Center X
        self.cy = 120  # Screen Center Y
        self.radius = 114

        # Off-Screen RAM Double-Buffer (200x200 tile) for ZERO display flicker
        self.tw = 200
        self.th = 200
        self.tx = 20   # Left offset on 240x240 screen
        self.ty = 20   # Top offset on 240x240 screen
        
        # Center coordinates for compass dial & needle inside 200x200 tile
        self.tcx = 100 
        self.tcy = 88
        self.tradius = 84

        self.tile_buf = bytearray(self.tw * self.th * 2)
        self.fb = framebuf.FrameBuffer(self.tile_buf, self.tw, self.th, framebuf.RGB565)

        # Preallocated scratch buffers for 3x font rendering (zero GC allocations per frame)
        self._mono_buf = bytearray(160)
        self._mono_fb = framebuf.FrameBuffer(self._mono_buf, 160, 8, framebuf.MONO_HLSB)

    def draw_static_dial(self):
        """Draw outer static bezel ring on display background."""
        self.display.fill(C_BG)

        # Draw outer bezel ring (radii 114, 115, 116)
        for r in range(self.radius, self.radius + 3):
            x = r
            y = 0
            err = 0
            while x >= y:
                for px, py in (
                    (self.cx + x, self.cy + y), (self.cx - x, self.cy + y),
                    (self.cx + x, self.cy - y), (self.cx - x, self.cy - y),
                    (self.cx + y, self.cy + x), (self.cx - y, self.cy + x),
                    (self.cx + y, self.cy - x), (self.cx - y, self.cy - x)
                ):
                    if 0 <= px < 240 and 0 <= py < 240:
                        self.display.fill_rect(px, py, 1, 1, C_BEZEL)
                y += 1
                err += 1 + 2 * y
                if 2 * (err - x) + 1 > 0:
                    x -= 1
                    err += 1 - 2 * x

    def update(self, heading_deg, altitude_m=None, vspeed_mps=None, pitch_deg=0.0, roll_deg=0.0):
        """Render complete flight frame off-screen and push atomically over SPI."""
        heading_int = int(heading_deg + 0.5) % 360
        north_angle = -heading_deg

        # 1. Clear off-screen RAM buffer
        self.fb.fill(BLACK)

        # 2. Draw rotating compass tick marks
        r_outer = self.tradius
        for deg in range(0, 360, 15):
            rad = math.radians(north_angle + deg)
            sin_a = math.sin(rad)
            cos_a = math.cos(rad)

            if deg % 90 == 0:
                length = 10
                color = WHITE
            elif deg % 45 == 0:
                length = 7
                color = GRAY
            else:
                length = 4
                color = DARKGRAY

            r_inner = r_outer - length
            x0 = int(self.tcx + r_outer * sin_a)
            y0 = int(self.tcy - r_outer * cos_a)
            x1 = int(self.tcx + r_inner * sin_a)
            y1 = int(self.tcy - r_inner * cos_a)
            self.fb.line(x0, y0, x1, y1, color)

        # 3. Draw 2x Cardinal Labels (N, E, S, W) rotating on dial
        r_label = self.tradius - 18

        # North (Red)
        rad_N = math.radians(north_angle)
        self._draw_fb_text_scaled(int(self.tcx + r_label * math.sin(rad_N) - 8), int(self.tcy - r_label * math.cos(rad_N) - 8), "N", C_NORTH, scale=2)

        # East (White)
        rad_E = math.radians(north_angle + 90)
        self._draw_fb_text_scaled(int(self.tcx + r_label * math.sin(rad_E) - 8), int(self.tcy - r_label * math.cos(rad_E) - 8), "E", WHITE, scale=2)

        # South (White)
        rad_S = math.radians(north_angle + 180)
        self._draw_fb_text_scaled(int(self.tcx + r_label * math.sin(rad_S) - 8), int(self.tcy - r_label * math.cos(rad_S) - 8), "S", WHITE, scale=2)

        # West (White)
        rad_W = math.radians(north_angle + 270)
        self._draw_fb_text_scaled(int(self.tcx + r_label * math.sin(rad_W) - 8), int(self.tcy - r_label * math.cos(rad_W) - 8), "W", WHITE, scale=2)

        # 4. Draw 3D Compass Needle
        self._draw_fb_needle(north_angle)

        # 5. Draw 3x Large Bearing / Heading Readout at Top (e.g. "342°")
        heading_str = f"{heading_int:03d}"
        self._draw_heading_badge_3x(heading_str)

        # 6. Draw 3x Large Variometer & Altitude Readouts at Bottom
        if altitude_m is not None and vspeed_mps is not None:
            self._draw_vario_panel_3x(altitude_m, vspeed_mps)

        # 7. Push completed off-screen frame atomically over SPI (ZERO flicker!)
        self.display.write_buffer(self.tx, self.ty, self.tw, self.th, self.tile_buf)

    def _draw_fb_text_scaled(self, x, y, text, color, scale=3):
        """Render text scaled by arbitrary integer multiplier (scale x 8 px per character)."""
        if not text:
            return
        n = len(text)
        w = n * 8
        if w > 160:
            w = 160
            text = text[:20]

        # Use preallocated monochrome buffer
        self._mono_fb.fill(0)
        self._mono_fb.text(text, 0, 0, 1)

        for py in range(8):
            dst_y = y + py * scale
            if dst_y < 0 or dst_y + scale > self.th:
                continue
            for px in range(w):
                if self._mono_fb.pixel(px, py):
                    dst_x = x + px * scale
                    if 0 <= dst_x and dst_x + scale <= self.tw:
                        self.fb.fill_rect(dst_x, dst_y, scale, scale, color)

    def _draw_fb_needle(self, heading):
        """Draw 3D dual-triangle compass needle into off-screen FrameBuffer."""
        rad = math.radians(heading)
        sin_a = math.sin(rad)
        cos_a = math.cos(rad)

        len_tip = 44
        len_tail = 30
        width = 7

        # North Tip (Red)
        nx = int(self.tcx + len_tip * sin_a)
        ny = int(self.tcy - len_tip * cos_a)

        # South Tip (White)
        sx = int(self.tcx - len_tail * sin_a)
        sy = int(self.tcy + len_tail * cos_a)

        # Base side points
        bx1 = int(self.tcx + width * cos_a)
        by1 = int(self.tcy + width * sin_a)
        bx2 = int(self.tcx - width * cos_a)
        by2 = int(self.tcy - width * sin_a)

        # Fill North triangle (Red)
        self._fill_fb_triangle(nx, ny, bx1, by1, bx2, by2, C_NORTH)

        # Fill South triangle (White)
        self._fill_fb_triangle(sx, sy, bx1, by1, bx2, by2, C_SOUTH)

        # Center pin cap
        self._fill_fb_circle(self.tcx, self.tcy, 4, C_BEZEL)
        self._fill_fb_circle(self.tcx, self.tcy, 2, WHITE)

    def _fill_fb_triangle(self, x0, y0, x1, y1, x2, y2, color):
        """Fast scanline triangle rasterizer."""
        if y0 > y1: x0, y0, x1, y1 = x1, y1, x0, y0
        if y0 > y2: x0, y0, x2, y2 = x2, y2, x0, y0
        if y1 > y2: x1, y1, x2, y2 = x2, y2, x1, y1

        total_height = y2 - y0
        if total_height == 0:
            return

        for i in range(total_height):
            second_half = i > (y1 - y0) or (y1 == y0)
            segment_height = (y2 - y1) if second_half else (y1 - y0)
            if segment_height == 0:
                continue

            alpha = i / total_height
            beta = (i - (y1 - y0 if second_half else 0)) / segment_height

            ax = int(x0 + (x2 - x0) * alpha)
            bx = int(x1 + (x2 - x1) * beta) if second_half else int(x0 + (x1 - x0) * beta)

            if ax > bx:
                ax, bx = bx, ax

            y = y0 + i
            if 0 <= y < self.th and bx >= 0 and ax < self.tw:
                x_start = max(0, ax)
                x_end = min(self.tw - 1, bx)
                self.fb.hline(x_start, y, x_end - x_start + 1, color)

    def _fill_fb_circle(self, x0, y0, r, color):
        """Draw filled circle."""
        for y in range(-r, r + 1):
            x_len = int(math.sqrt(r * r - y * y))
            self.fb.hline(x0 - x_len, y0 + y, 2 * x_len + 1, color)

    def _draw_heading_badge_3x(self, heading_3digit_str):
        """Draw 3x large horizontal heading readout with degree mark at top."""
        # 3 digits at 3x scale = 3 * 24 = 72 px wide, 24 px tall
        w_digits = len(heading_3digit_str) * 24
        total_w = w_digits + 10  # include degree symbol space
        start_x = self.tcx - (total_w // 2)
        top_y = 6

        # Sleek background badge frame
        self.fb.rect(start_x - 4, top_y - 2, total_w + 8, 28, C_BEZEL)
        self.fb.fill_rect(start_x - 3, top_y - 1, total_w + 6, 26, BLACK)

        # 3x Large digits
        self._draw_fb_text_scaled(start_x, top_y, heading_3digit_str, C_HEADING, scale=3)

        # Degree circle symbol (top right of numbers)
        deg_x = start_x + w_digits + 3
        deg_y = top_y + 3
        self.fb.rect(deg_x, deg_y, 6, 6, C_HEADING)

    def _draw_vario_panel_3x(self, alt_m, vspeed_mps):
        """Draw 3x large Altitude and 3x large Climb/Sink rate at bottom in identical horizontal orientation."""
        
        # -------------------------------------------------------------
        # 1. ALTITUDE READOUT (3x Large: e.g. "1450m")
        # -------------------------------------------------------------
        alt_val = int(alt_m + 0.5)
        alt_str = f"{alt_val}m"
        w_alt = len(alt_str) * 24
        x_alt = self.tcx - (w_alt // 2)
        y_alt = 138

        # Render 3x Altitude text
        self._draw_fb_text_scaled(x_alt, y_alt, alt_str, C_ALT_TEXT, scale=3)

        # -------------------------------------------------------------
        # 2. VERTICAL SPEED READOUT (3x Large: e.g. "+1.8" or "-0.8")
        # -------------------------------------------------------------
        sign = "+" if vspeed_mps >= 0 else ""
        vspeed_str = f"{sign}{vspeed_mps:.1f}"
        
        if vspeed_mps >= 0.20:
            v_color = C_CLIMB
        elif vspeed_mps <= -0.20:
            v_color = C_SINK
        else:
            v_color = C_NEUTRAL

        w_vspeed = len(vspeed_str) * 24
        x_vspeed = self.tcx - (w_vspeed // 2)
        y_vspeed = 168

        # Render 3x Vertical Speed text
        self._draw_fb_text_scaled(x_vspeed, y_vspeed, vspeed_str, v_color, scale=3)

        # -------------------------------------------------------------
        # 3. Dynamic Micro Tape Bar Indicator (Bottom Edge)
        # -------------------------------------------------------------
        bar_cx = self.tcx
        bar_y = 196
        bar_len = int(min(max(vspeed_mps * 10.0, -40), 40))

        self.fb.hline(bar_cx - 40, bar_y, 80, DARKGRAY)
        self.fb.vline(bar_cx, bar_y - 2, 5, WHITE)

        if bar_len > 0:
            self.fb.fill_rect(bar_cx, bar_y - 1, bar_len, 3, C_CLIMB)
        elif bar_len < 0:
            self.fb.fill_rect(bar_cx + bar_len, bar_y - 1, -bar_len, 3, C_SINK)

    def draw_error_screen(self, title, lines):
        """Display initialization error message."""
        self.display.fill(BLACK)
        self._draw_string(self.cx - (len(title) * 4), 40, title, RED)
        self.display.draw_line(20, 56, 220, 56, RED)

        start_y = 75
        spacing = 22
        for i, line in enumerate(lines):
            tx = self.cx - (len(line) * 4)
            self._draw_string(tx, start_y + (i * spacing), line, WHITE)

    def _draw_string(self, x, y, text, color, bg=BLACK):
        """16-bit RGB565 text renderer."""
        w = len(text) * 8
        h = 8
        buf = bytearray(w * h * 2)
        fb = framebuf.FrameBuffer(buf, w, h, framebuf.RGB565)
        fb.fill(bg)
        fb.text(text, 0, 0, color)
        self.display.write_buffer(x, y, w, h, buf)
