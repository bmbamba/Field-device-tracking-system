"""
grid_map_widget.py - SCADA map with satellite/terrain background support.
"""

import math, os
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, Signal
from PySide6.QtGui import (QPainter, QPen, QBrush, QColor, QFont,
                            QLinearGradient, QPainterPath, QRadialGradient,
                            QPixmap, QCursor)


def _font(px: int, bold: bool = False) -> QFont:
    f = QFont("Courier New")
    f.setPixelSize(max(8, px))
    if bold:
        f.setWeight(QFont.Weight.Bold)
    return f


class GridMapWidget(QWidget):
    device_context_requested = Signal(str, int, int)

    GRID_MIN = 0
    GRID_MAX = 1000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)

        self._devices      = {}
        self._blink        = False
        self._show_labels  = True
        self._geofences    = []

        # Satellite background
        self._bg_pixmap    = None      # QPixmap when loaded
        self._bg_mode      = "dark"    # "dark" | "satellite" | "terrain"

        # Zoom / pan
        self._zoom          = 1.0
        self._pan_x         = 0.0
        self._pan_y         = 0.0
        self._drag_start    = None
        self._drag_pan_start = None

        # Try to auto-load satellite_map.jpg next to this file
        here = os.path.dirname(os.path.abspath(__file__))
        auto = os.path.join(here, "satellite_map.jpg")
        if os.path.exists(auto):
            self.load_background(auto)

        t = QTimer(self)
        t.timeout.connect(self._toggle_blink)
        t.start(600)

    # ── Public API ────────────────────────────────────────────────────

    def update_devices(self, devices):
        self._devices = {d.device_id: d for d in devices}
        self.update()

    def toggle_labels(self):
        self._show_labels = not self._show_labels
        self.update()

    def set_bg_mode(self, mode: str):
        """mode: 'dark' | 'satellite'"""
        self._bg_mode = mode
        self.update()

    def load_background(self, path: str):
        px = QPixmap(path)
        if not px.isNull():
            self._bg_pixmap = px
            self._bg_mode   = "satellite"
            self.update()
            return True
        return False

    def add_geofence(self, x1, y1, x2, y2, label="EXCLUSION ZONE"):
        self._geofences.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "label": label})
        self.update()

    def clear_geofences(self):
        self._geofences.clear()
        self.update()

    def reset_view(self):
        self._zoom  = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self.update()

    # ── Mouse ─────────────────────────────────────────────────────────

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom = max(0.3, min(10.0, self._zoom * factor))
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start     = (event.position().x(), event.position().y())
            self._drag_pan_start = (self._pan_x, self._pan_y)
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
        elif event.button() == Qt.MouseButton.RightButton:
            gx, gy = self._to_grid(event.position().x(), event.position().y())
            for dev in self._devices.values():
                if math.hypot(dev.current_x - gx, dev.current_y - gy) < 2.5:
                    self.device_context_requested.emit(
                        dev.device_id,
                        int(event.globalPosition().x()),
                        int(event.globalPosition().y()))
                    break

    def mouseMoveEvent(self, event):
        if self._drag_start:
            dx = event.position().x() - self._drag_start[0]
            dy = event.position().y() - self._drag_start[1]
            cs = self._cell_size()
            self._pan_x = self._drag_pan_start[0] - dx / cs
            self._pan_y = self._drag_pan_start[1] + dy / cs
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = None
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def mouseDoubleClickEvent(self, event):
        self.reset_view()

    # ── Paint ─────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        self._draw_background(p)
        self._draw_geofences(p)
        self._draw_grid(p)
        self._draw_routes(p)
        self._draw_trails(p)
        self._draw_waypoints(p)
        self._draw_devices(p)
        self._draw_hud(p)
        p.end()

    # ── Background ────────────────────────────────────────────────────

    def _draw_background(self, p):
        if self._bg_mode == "satellite" and self._bg_pixmap:
            self._draw_satellite_bg(p)
        else:
            self._draw_dark_bg(p)

    def _draw_dark_bg(self, p):
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor(8, 15, 28))
        grad.setColorAt(1, QColor(4, 8, 18))
        p.fillRect(self.rect(), QBrush(grad))

    def _draw_satellite_bg(self, p):
        grid_span = self.GRID_MAX - self.GRID_MIN
        sx0       = self._to_screen_x(self.GRID_MIN)
        sy0       = self._to_screen_y(self.GRID_MAX)
        grid_px_w = self._cell_w() * grid_span
        grid_px_h = self._cell_h() * grid_span
        p.fillRect(self.rect(), QColor(10, 18, 12))
        target = QRectF(sx0, sy0, grid_px_w, grid_px_h)
        p.drawPixmap(target.toRect(), self._bg_pixmap)
        p.fillRect(target.toRect(), QColor(0, 0, 0, 55))

    # ── Grid ──────────────────────────────────────────────────────────

    def _draw_grid(self, p):
        satellite = (self._bg_mode == "satellite" and self._bg_pixmap)

        minor_col  = QColor(255, 255, 255, 15) if satellite else QColor(20, 45, 75, 210)
        major_col  = QColor(255, 255, 255, 50) if satellite else QColor(38, 88, 135, 240)
        label_col  = QColor(220, 240, 255, 200) if satellite else QColor(75, 140, 185)
        border_col = QColor(255, 255, 255, 90)  if satellite else QColor(55, 120, 175)

        x_left  = self._to_screen_x(self.GRID_MIN)
        x_right = self._to_screen_x(self.GRID_MAX)
        y_top   = self._to_screen_y(self.GRID_MAX)
        y_bot   = self._to_screen_y(self.GRID_MIN)

        # Minor lines every 50 units
        p.setPen(QPen(minor_col, 0.6))
        for g in range(self.GRID_MIN, self.GRID_MAX + 1, 50):
            sx = int(self._to_screen_x(g))
            sy = int(self._to_screen_y(g))
            p.drawLine(sx, int(y_top), sx, int(y_bot))
            p.drawLine(int(x_left), sy, int(x_right), sy)

        # Major lines every 100 units
        p.setPen(QPen(major_col, 1.2))
        for g in range(self.GRID_MIN, self.GRID_MAX + 1, 100):
            sx = int(self._to_screen_x(g))
            sy = int(self._to_screen_y(g))
            p.drawLine(sx, int(y_top), sx, int(y_bot))
            p.drawLine(int(x_left), sy, int(x_right), sy)

        # Border
        p.setPen(QPen(border_col, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(int(x_left), int(y_top),
                   int(x_right - x_left), int(y_bot - y_top))

        # Axis labels
        p.setFont(_font(9))
        for g in range(self.GRID_MIN, self.GRID_MAX + 1, 100):
            sx = int(self._to_screen_x(g))
            sy = int(self._to_screen_y(g))
            lbl = str(g)

            # X axis below grid
            if satellite:
                p.setPen(QColor(0, 0, 0, 160))
                p.drawText(sx - 7, int(y_bot) + 17, lbl)
            p.setPen(label_col)
            p.drawText(sx - 8, int(y_bot) + 16, lbl)

            # Y axis left of grid
            if satellite:
                p.setPen(QColor(0, 0, 0, 160))
                p.drawText(int(x_left) - 30, sy + 5, lbl)
            p.setPen(label_col)
            p.drawText(int(x_left) - 31, sy + 4, lbl)

    # ── Geofences ─────────────────────────────────────────────────────

    def _draw_geofences(self, p):
        for zone in self._geofences:
            sx1, sy1 = self._to_screen((zone["x1"], zone["y1"]))
            sx2, sy2 = self._to_screen((zone["x2"], zone["y2"]))
            rx, ry = min(sx1,sx2), min(sy1,sy2)
            rw, rh = abs(sx2-sx1), abs(sy2-sy1)

            p.setBrush(QBrush(QColor(220, 40, 40, 45)))
            p.setPen(QPen(QColor(255, 60, 60, 200), 1.8, Qt.PenStyle.DashLine))
            p.drawRect(int(rx), int(ry), int(rw), int(rh))

            # Label with shadow
            p.setFont(_font(10, bold=True))
            p.setPen(QColor(0, 0, 0, 160))
            p.drawText(int(rx)+5, int(ry)+16, zone["label"])
            p.setPen(QColor(255, 100, 100, 230))
            p.drawText(int(rx)+4, int(ry)+15, zone["label"])

    # ── Routes ────────────────────────────────────────────────────────

    def _draw_routes(self, p):
        for dev in self._devices.values():
            if not dev.travel_plan:
                continue
            pts = self._plan_points(dev.travel_plan)
            if len(pts) < 2:
                continue
            color = QColor(dev.color)
            color.setAlpha(100)
            pen = QPen(color, 1.8, Qt.PenStyle.DashLine)
            pen.setDashPattern([6, 4])
            p.setPen(pen)
            for i in range(len(pts) - 1):
                x1, y1 = self._to_screen(pts[i])
                x2, y2 = self._to_screen(pts[i+1])
                p.drawLine(int(x1), int(y1), int(x2), int(y2))

    # ── Trails ────────────────────────────────────────────────────────

    def _draw_trails(self, p):
        for dev in self._devices.values():
            trail = dev.trail
            if len(trail) < 2:
                continue
            color = QColor(dev.color)
            n = len(trail)
            for i in range(1, n):
                alpha = int(15 + 220 * (i / n))
                width = 1.0 + 1.5 * (i / n)
                color.setAlpha(alpha)
                p.setPen(QPen(color, width))
                x1, y1 = self._to_screen(trail[i-1])
                x2, y2 = self._to_screen(trail[i])
                p.drawLine(int(x1), int(y1), int(x2), int(y2))

    # ── Waypoints ─────────────────────────────────────────────────────

    def _draw_waypoints(self, p):
        for dev in self._devices.values():
            if not dev.travel_plan:
                continue
            pts   = self._plan_points(dev.travel_plan)
            color = QColor(dev.color)
            for i, pt in enumerate(pts):
                sx, sy = self._to_screen(pt)
                if not (-10 <= sx <= self.width()+10 and -10 <= sy <= self.height()+10):
                    continue
                is_dest  = (i == len(pts) - 1)
                is_start = (i == 0)
                color.setAlpha(220)

                if is_dest or is_start:
                    sz = 10 if is_dest else 8
                    p.setPen(QPen(color, 2))
                    p.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 60)))
                    p.drawRect(int(sx-sz/2), int(sy-sz/2), sz, sz)
                    if self._show_labels:
                        lbl = "DEST" if is_dest else "START"
                        p.setFont(_font(8, bold=True))
                        # Shadow
                        p.setPen(QColor(0,0,0,160))
                        p.drawText(int(sx)+7, int(sy)-1, lbl)
                        p.setPen(color)
                        p.drawText(int(sx)+6, int(sy)-2, lbl)
                else:
                    sz = 4
                    p.setPen(QPen(color, 1.5))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    path = QPainterPath()
                    path.moveTo(sx, sy-sz)
                    path.lineTo(sx+sz, sy)
                    path.lineTo(sx, sy+sz)
                    path.lineTo(sx-sz, sy)
                    path.closeSubpath()
                    p.drawPath(path)

    # ── Devices ───────────────────────────────────────────────────────

    def _draw_devices(self, p):
        for dev in self._devices.values():
            sx, sy = self._to_screen((dev.current_x, dev.current_y))
            if not (-40 <= sx <= self.width()+40 and -40 <= sy <= self.height()+40):
                continue

            color = QColor(dev.color)
            alert = (dev.status == "ALERT")
            speed = getattr(dev, 'speed', 0) or 0
            glow_r = max(16, min(38, 16 + speed * 1.8))

            if alert and self._blink:
                glow_col = QColor(255, 50, 50, 110)
                dot_col  = QColor(255, 80, 80)
            else:
                glow_col = QColor(color.red(), color.green(), color.blue(), 55)
                dot_col  = color

            # Glow
            grad = QRadialGradient(sx, sy, glow_r)
            grad.setColorAt(0.0, glow_col)
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(sx, sy), glow_r, glow_r)

            # Outer ring
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(dot_col.red(), dot_col.green(), dot_col.blue(), 120), 1))
            p.drawEllipse(QPointF(sx, sy), 10, 10)

            # Filled dot
            p.setBrush(QBrush(dot_col))
            p.setPen(QPen(QColor(255, 255, 255, 200), 1.5))
            p.drawEllipse(QPointF(sx, sy), 6, 6)

            # White center
            p.setBrush(QBrush(QColor(255, 255, 255, 220)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(sx, sy), 2.5, 2.5)

            # Crosshair
            p.setPen(QPen(QColor(dot_col.red(), dot_col.green(), dot_col.blue(), 160), 1))
            p.drawLine(int(sx)-16, int(sy), int(sx)-11, int(sy))
            p.drawLine(int(sx)+11, int(sy), int(sx)+16, int(sy))
            p.drawLine(int(sx), int(sy)-16, int(sx), int(sy)-11)
            p.drawLine(int(sx), int(sy)+11, int(sx), int(sy)+16)

            if self._show_labels:
                self._draw_device_label(p, dev, sx, sy, dot_col)

    def _draw_device_label(self, p, dev, sx, sy, color):
        satellite = (self._bg_mode == "satellite" and self._bg_pixmap)

        dist_str = eta_str = ""
        if dev.travel_plan and dev.travel_plan.get("destination"):
            dx = dev.travel_plan["destination"][0] - dev.current_x
            dy = dev.travel_plan["destination"][1] - dev.current_y
            dist_rem = math.hypot(dx, dy)
            dist_str = f"D:{dist_rem:.1f}u"
            spd = dev.speed if dev.speed > 0 else 0.1
            eta_s = dist_rem / spd
            eta_str = f"ETA:{eta_s:.0f}s" if eta_s < 60 else f"ETA:{eta_s/60:.1f}m"

        lines = [dev.device_id,
                 f"({dev.current_x:.1f},{dev.current_y:.1f})",
                 f"SPD:{dev.speed:.1f}  {dist_str}",
                 eta_str]
        lines = [l for l in lines if l]

        lh = 11
        lw = 108
        lx = int(sx) + 14
        ly = int(sy) - 10

        # Background — more opaque on satellite for readability
        bg_alpha = 220 if satellite else 195
        p.fillRect(lx-3, ly-lh, lw, lh*len(lines)+6, QColor(5, 12, 22, bg_alpha))
        p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 180), 0.8))
        p.drawRect(lx-3, ly-lh, lw, lh*len(lines)+6)

        p.setFont(_font(9, bold=True))
        p.setPen(color)
        p.drawText(lx, ly, lines[0])

        p.setFont(_font(8))
        p.setPen(QColor(200, 220, 240))
        for i, line in enumerate(lines[1:], 1):
            p.drawText(lx, ly + i*lh, line)

    # ── HUD (scale + zoom + mode badge) ──────────────────────────────

    def _draw_hud(self, p):
        satellite = (self._bg_mode == "satellite" and self._bg_pixmap)

        # Mode badge top-right
        badge_text = "● SATELLITE" if satellite else "● GRID"
        badge_col  = QColor(60, 200, 100)  if satellite else QColor(50, 120, 180)
        bg_col     = QColor(0, 30, 10, 180) if satellite else QColor(0, 15, 35, 180)
        p.setFont(_font(9, bold=True))
        fm_w = 95
        bx = self.width() - fm_w - 8
        by = 8
        p.fillRect(bx, by, fm_w, 18, bg_col)
        p.setPen(QPen(badge_col, 0.8))
        p.drawRect(bx, by, fm_w, 18)
        p.setPen(badge_col)
        p.drawText(bx+6, by+13, badge_text)

        # Scale bar bottom-right
        bar_len = max(20, int(self._to_screen_x(100) - self._to_screen_x(0)))
        bx2 = self.width() - bar_len - 16
        by2 = self.height() - 18
        text_col = QColor(220, 240, 255, 180) if satellite else QColor(80, 150, 200)
        p.setPen(QPen(text_col, 2))
        p.drawLine(bx2, by2, bx2+bar_len, by2)
        p.drawLine(bx2, by2-3, bx2, by2+3)
        p.drawLine(bx2+bar_len, by2-3, bx2+bar_len, by2+3)
        p.setFont(_font(8))
        p.setPen(text_col)
        p.drawText(bx2, by2-5, "100 units")

        # Zoom bottom-left
        p.setFont(_font(9))
        zoom_col = QColor(220, 240, 255, 160) if satellite else QColor(50, 100, 140)
        p.setPen(zoom_col)
        p.drawText(10, self.height()-10, f"ZOOM  {self._zoom:.1f}×")

    # ── Coordinate helpers ────────────────────────────────────────────

    def _margin(self):
        return 22   # bottom and top margin (small — just enough for labels)

    def _margin_left(self):
        return 40   # left margin for Y axis labels

    def _margin_bottom(self):
        return 28   # bottom margin for X axis labels

    def _cell_w(self):
        return ((self.width() - self._margin_left() - 8) /
                (self.GRID_MAX - self.GRID_MIN)) * self._zoom

    def _cell_h(self):
        return ((self.height() - self._margin_bottom() - 8) /
                (self.GRID_MAX - self.GRID_MIN)) * self._zoom

    def _cell_size(self):
        return (self._cell_w() + self._cell_h()) / 2

    def _to_screen_x(self, gx):
        return self._margin_left() + (gx - self.GRID_MIN - self._pan_x) * self._cell_w()

    def _to_screen_y(self, gy):
        return (self.height() - self._margin_bottom() -
                (gy - self.GRID_MIN - self._pan_y) * self._cell_h())

    def _to_screen(self, pt):
        return self._to_screen_x(pt[0]), self._to_screen_y(pt[1])

    def _to_grid(self, sx, sy):
        gx = (sx - self._margin_left()) / self._cell_w() + self.GRID_MIN + self._pan_x
        gy = (self.height() - self._margin_bottom() - sy) / self._cell_h() + self.GRID_MIN + self._pan_y
        return gx, gy

    def _plan_points(self, plan):
        pts = [tuple(plan["start"])]
        pts += [tuple(wp) for wp in plan.get("waypoints", [])]
        if plan.get("destination"):
            pts.append(tuple(plan["destination"]))
        return pts

    def _toggle_blink(self):
        self._blink = not self._blink
        self.update()
