"""
main_window.py - Full-featured SCADA tracking control center.

Features implemented:
  - Zoom/pan map (mouse wheel + drag)
  - Toggle device labels
  - Speed halo on map
  - Geofence zones (add via GUI)
  - ETA + distance remaining on map labels
  - Speed change alerts
  - Geofence breach alerts
  - Export telemetry to CSV
  - Alert history panel (dedicated tab)
  - Session summary on server stop
  - Right-click device on map -> context menu
  - Double-click table row -> device detail panel
  - Dark/Light theme toggle
  - Keyboard shortcuts
  - Config save/load (JSON)
  - Fleet plan assignment (all devices at once)
  - Reconnection-aware server
"""

import os, json, csv
from datetime import datetime
import sound_engine

from PySide6.QtWidgets import (
    QMessageBox, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QLabel, QPushButton, QLineEdit, QTableWidget,
    QTableWidgetItem, QTextEdit, QGroupBox, QFormLayout, QComboBox,
    QDoubleSpinBox, QHeaderView, QFrame, QScrollArea, QTabWidget,
    QDialog, QDialogButtonBox, QMenu, QFileDialog, QCheckBox,
    QSpinBox, QStatusBar
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QDateTime
from PySide6.QtGui import (QColor, QFont, QKeySequence, QShortcut,
                            QAction)

from grid_map_widget import GridMapWidget
from device_registry import DeviceRegistry
from tracker_engine import TrackerEngine
from communication_server import CommunicationServer
from route_planner import make_plan
import logger

# ── Themes ───────────────────────────────────────────────────────────────────

DARK_THEME = """
QMainWindow, QWidget {
    background-color: #0B1120;
    color: #C8D8E8;
    font-family: "Segoe UI", "Courier New", monospace;
    font-size: 12px;
}
QGroupBox {
    background-color: #0D1628;
    border: 1px solid #1E3A5F;
    border-radius: 6px;
    margin-top: 14px;
    padding: 10px 8px 8px 8px;
    font-family: "Courier New";
    font-size: 11px;
    font-weight: bold;
    color: #4FC3F7;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px; top: -1px;
    padding: 2px 8px;
    background-color: #0D1628;
    border: 1px solid #1E3A5F;
    border-radius: 3px;
    color: #4FC3F7;
    letter-spacing: 1px;
}
QPushButton {
    background-color: #112240;
    color: #64B5F6;
    border: 1px solid #1E3A5F;
    border-radius: 4px;
    padding: 7px 14px;
    font-family: "Courier New";
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}
QPushButton:hover  { background-color: #1A3555; border-color: #4FC3F7; color: #E3F2FD; }
QPushButton:pressed { background-color: #0A1828; }
QPushButton#success { background-color: #0A2218; color: #4CAF50; border-color: #2E7D32; }
QPushButton#success:hover { background-color: #143020; border-color: #4CAF50; }
QPushButton#danger  { background-color: #1E0A0A; color: #EF5350; border-color: #7B1F1F; }
QPushButton#danger:hover  { background-color: #2A0E0E; border-color: #EF5350; }
QPushButton#assign  { background-color: #0A1E35; color: #29B6F6; border-color: #0D47A1; }
QPushButton#assign:hover  { background-color: #0D2844; border-color: #29B6F6; }
QPushButton#neutral { background-color: #111E30; color: #90A4AE; border-color: #263238; }
QPushButton#neutral:hover { background-color: #182840; border-color: #90A4AE; }
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {
    background-color: #080F1C;
    color: #B0C4D8;
    border: 1px solid #1E3A5F;
    border-radius: 4px;
    padding: 5px 8px;
    selection-background-color: #1A3555;
    min-height: 22px;
}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #4FC3F7; color: #E3F2FD;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #0D1628; color: #C8D8E8;
    border: 1px solid #1E3A5F;
    selection-background-color: #1A3555;
}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #112240; border: none; width: 16px;
}
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover,
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #1A3555;
}
QTableWidget {
    background-color: #070E1A; alternate-background-color: #0A1220;
    color: #B0C4D8; gridline-color: #122035;
    border: 1px solid #1E3A5F; border-radius: 4px;
    selection-background-color: #1A3555;
}
QHeaderView::section {
    background-color: #0D1E35; color: #4FC3F7;
    border: none; border-right: 1px solid #1E3A5F;
    border-bottom: 1px solid #1E3A5F;
    padding: 6px 4px;
    font-family: "Courier New"; font-size: 11px; font-weight: bold;
}
QTableWidget::item { padding: 4px; border-bottom: 1px solid #0F1E30; }
QTableWidget::item:selected { background-color: #1A3555; color: #E3F2FD; }
QTextEdit {
    background-color: #040810; color: #26A65B;
    border: 1px solid #0F2030; border-radius: 4px;
    font-family: "Courier New"; font-size: 11px; padding: 4px;
}
QTabWidget::pane {
    border: 1px solid #1E3A5F; border-radius: 4px;
    background-color: #0B1120;
}
QTabBar::tab {
    background-color: #0D1628; color: #607D8B;
    border: 1px solid #1E3A5F; border-bottom: none;
    padding: 6px 16px; font-family: "Courier New"; font-size: 11px;
}
QTabBar::tab:selected { background-color: #112240; color: #4FC3F7; }
QTabBar::tab:hover    { background-color: #1A3555; color: #90CAF9; }
QScrollBar:vertical   { background: #080F1C; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #1E3A5F; border-radius: 4px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #2A5280; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar:horizontal { background: #080F1C; height: 8px; border-radius: 4px; }
QScrollBar::handle:horizontal { background: #1E3A5F; border-radius: 4px; }
QSplitter::handle { background-color: #1E3A5F; }
QSplitter::handle:horizontal { width: 2px; }
QSplitter::handle:vertical   { height: 2px; }
QScrollArea { border: none; background-color: transparent; }
QStatusBar { background-color: #070E1A; color: #4FC3F7;
             font-family: "Courier New"; font-size: 11px;
             border-top: 1px solid #1E3A5F; }
QMenu { background-color: #0D1628; color: #C8D8E8;
        border: 1px solid #1E3A5F; }
QMenu::item:selected { background-color: #1A3555; }
QCheckBox { color: #90A4AE; }
QCheckBox::indicator { width: 14px; height: 14px;
    background-color: #080F1C; border: 1px solid #1E3A5F; border-radius: 2px; }
QCheckBox::indicator:checked { background-color: #1A3555; border-color: #4FC3F7; }
"""

LIGHT_THEME = """
QMainWindow, QWidget { background-color: #F0F4F8; color: #1A2535; font-size: 12px; }
QGroupBox { background-color: #E8EEF5; border: 1px solid #B0C4D8; border-radius: 6px;
    margin-top: 14px; padding: 10px 8px; font-weight: bold; color: #1565C0; }
QGroupBox::title { left: 10px; top: -1px; padding: 2px 8px;
    background-color: #E8EEF5; border: 1px solid #B0C4D8;
    border-radius: 3px; color: #1565C0; }
QPushButton { background-color: #BBDEFB; color: #0D47A1; border: 1px solid #90CAF9;
    border-radius: 4px; padding: 7px 14px; font-weight: bold; }
QPushButton:hover { background-color: #90CAF9; }
QPushButton#success { background-color: #C8E6C9; color: #1B5E20; border-color: #81C784; }
QPushButton#danger  { background-color: #FFCDD2; color: #B71C1C; border-color: #EF9A9A; }
QPushButton#assign  { background-color: #B3E5FC; color: #01579B; border-color: #4FC3F7; }
QPushButton#neutral { background-color: #ECEFF1; color: #546E7A; border-color: #B0BEC5; }
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {
    background-color: #FFFFFF; color: #1A2535; border: 1px solid #90A4AE;
    border-radius: 4px; padding: 5px 8px; }
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #1565C0; }
QComboBox QAbstractItemView { background-color: #FFFFFF; color: #1A2535; }
QTableWidget { background-color: #FFFFFF; alternate-background-color: #F5F9FF;
    color: #1A2535; gridline-color: #D0DCE8; border: 1px solid #B0C4D8; }
QHeaderView::section { background-color: #E3EEF9; color: #1565C0;
    border: none; border-bottom: 1px solid #B0C4D8; padding: 6px 4px; font-weight: bold; }
QTextEdit { background-color: #FFFFFF; color: #1B5E20;
    border: 1px solid #B0C4D8; border-radius: 4px; }
QTabBar::tab { background-color: #E8EEF5; color: #607D8B;
    border: 1px solid #B0C4D8; padding: 6px 16px; }
QTabBar::tab:selected { background-color: #BBDEFB; color: #0D47A1; }
QScrollBar:vertical { background: #ECEFF1; width: 8px; }
QScrollBar::handle:vertical { background: #90A4AE; border-radius: 4px; }
QStatusBar { background-color: #E3EEF9; color: #1565C0; border-top: 1px solid #B0C4D8; }
QSplitter::handle { background-color: #B0C4D8; }
QCheckBox { color: #37474F; }
QCheckBox::indicator { background-color: #FFFFFF; border: 1px solid #90A4AE; border-radius: 2px; width: 14px; height: 14px; }
QCheckBox::indicator:checked { background-color: #BBDEFB; border-color: #1565C0; }
"""


class LogSignal(QObject):
    new_line  = Signal(str)
    new_alert = Signal(str, str, str)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TRACKING CONTROL CENTER  ·  CLAN v1.0")
        self.resize(1550, 950)
        self.setMinimumSize(1100, 700)

        self._dark_mode = True
        self._maximized_panel = None
        self._alert_history = []     # list of dicts
        self._session_start = datetime.now()
        self._telemetry_log = []     # for CSV export

        self.registry = DeviceRegistry()
        self.tracker  = TrackerEngine(self.registry, alert_callback=self._on_alert)
        self.server   = CommunicationServer(self.registry, self.tracker)

        self._log_signal = LogSignal()
        self._log_signal.new_line.connect(self._append_log)
        self._log_signal.new_alert.connect(self._handle_alert_on_main_thread)
        logger.register_callback(self._log_signal.new_line.emit)

        self.setStyleSheet(DARK_THEME)
        self._build_ui()
        self._setup_shortcuts()
        self._start_server()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_ui)
        self._refresh_timer.start(500)

        self._blink_state = True
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink_led)
        self._blink_timer.start(1000)

    # ══════════════════════════════════════════════════════════════════
    # Keyboard shortcuts
    # ══════════════════════════════════════════════════════════════════

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("R"), self, self._register_device)
        QShortcut(QKeySequence("P"), self, self._assign_plan)
        QShortcut(QKeySequence("C"), self, lambda: self._log_console.clear())
        QShortcut(QKeySequence("T"), self, self._toggle_theme)
        QShortcut(QKeySequence("L"), self, self._toggle_labels)
        QShortcut(QKeySequence("E"), self, self._export_csv)
        QShortcut(QKeySequence("M"), self, self._toggle_mute)
        QShortcut(QKeySequence("S"), self, self._toggle_satellite)
        QShortcut(QKeySequence("F5"), self, self.map_widget.reset_view if hasattr(self, 'map_widget') else lambda: None)

    # ══════════════════════════════════════════════════════════════════
    # UI
    # ══════════════════════════════════════════════════════════════════

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(5)
        root.addWidget(self._build_title_bar())

        left   = self._build_left_panel()
        center = self._build_center_panel()
        right  = self._build_right_tabs()
        log    = self._build_log_panel()

        left.setMinimumWidth(220)
        center.setMinimumWidth(300)
        right.setMinimumWidth(220)
        log.setMinimumHeight(60)

        self._h_split = QSplitter(Qt.Orientation.Horizontal)
        self._h_split.setHandleWidth(4)
        self._h_split.addWidget(left)
        self._h_split.addWidget(center)
        self._h_split.addWidget(right)
        self._h_split.setSizes([310, 780, 420])
        self._h_split.setCollapsible(0, False)
        self._h_split.setCollapsible(1, False)
        self._h_split.setCollapsible(2, False)

        self._v_split = QSplitter(Qt.Orientation.Vertical)
        self._v_split.setHandleWidth(4)
        self._v_split.addWidget(self._h_split)
        self._v_split.addWidget(log)
        self._v_split.setSizes([700, 200])
        self._v_split.setCollapsible(0, False)
        self._v_split.setCollapsible(1, False)
        root.addWidget(self._v_split)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage(
            "  R=Register  P=Assign Plan  C=Clear Log  T=Theme  L=Labels  "
            "S=Satellite  M=Mute  E=Export  F5=Reset Map  |  "
            "Map: Scroll=Zoom  Drag=Pan  DblClick=Reset  RightClick=Device Menu"
        )

    # ── Title bar ─────────────────────────────────────────────────────

    def _build_title_bar(self):
        bar = QFrame()
        bar.setFixedHeight(50)
        bar.setObjectName("titleBar")
        bar.setStyleSheet("""
            QFrame#titleBar {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #071428, stop:0.5 #0D1E38, stop:1 #071428);
                border: 1px solid #1E3A5F; border-radius: 5px;
            }
        """)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)

        self._title_led = QLabel("⬤")
        self._title_led.setStyleSheet("color:#4CAF50; font-size:13px;")
        lay.addWidget(self._title_led)
        lay.addSpacing(8)

        title = QLabel("FIELD DEVICE TRACKING SYSTEM")
        title.setStyleSheet(
            "color:#29B6F6; font-family:'Courier New'; font-size:16px; "
            "font-weight:bold; letter-spacing:4px;"
        )
        lay.addWidget(title)
        lay.addSpacing(12)

        ver = QLabel("CLAN v1.0")
        ver.setStyleSheet(
            "color:#3A6080; background:#071428; border:1px solid #1E3A5F; "
            "border-radius:3px; font-family:'Courier New'; font-size:10px; padding:2px 8px;"
        )
        lay.addWidget(ver)
        lay.addStretch()

        self._clock_label = QLabel()
        self._clock_label.setStyleSheet(
            "color:#4FC3F7; font-family:'Courier New'; font-size:13px; letter-spacing:2px;"
        )
        self._update_clock()
        ct = QTimer(self); ct.timeout.connect(self._update_clock); ct.start(1000)
        lay.addWidget(self._clock_label)
        lay.addSpacing(16)

        self._dev_count_badge = QLabel("DEVICES: 0")
        self._dev_count_badge.setStyleSheet(
            "color:#4CAF50; font-family:'Courier New'; font-size:11px; "
            "background:#071A0F; border:1px solid #1B5E20; border-radius:3px; padding:3px 8px;"
        )
        lay.addWidget(self._dev_count_badge)
        lay.addSpacing(8)

        btn_layout = QPushButton("⊞ RESET LAYOUT")
        btn_layout.setObjectName("neutral")
        btn_layout.setFixedHeight(28)
        btn_layout.clicked.connect(self._reset_layout)
        lay.addWidget(btn_layout)

        btn_theme = QPushButton("◑ THEME")
        btn_theme.setObjectName("neutral")
        btn_theme.setFixedHeight(28)
        btn_theme.clicked.connect(self._toggle_theme)
        lay.addWidget(btn_theme)

        return bar

    # ── Left panel ────────────────────────────────────────────────────

    def _build_left_panel(self):
        outer = QWidget()
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(3)

        hdr = QFrame()
        hdr.setStyleSheet("QFrame{background:#0D1628;border:1px solid #1E3A5F;border-radius:4px;}")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(10, 4, 6, 4)
        t = QLabel("◈  CONTROLS")
        t.setStyleSheet("color:#4FC3F7;font-family:'Courier New';font-size:12px;font-weight:bold;letter-spacing:2px;")
        hl.addWidget(t); hl.addStretch()
        btn_max_left = QPushButton("⛶")
        btn_max_left.setFixedSize(24, 24)
        btn_max_left.setToolTip("Maximize / Restore")
        btn_max_left.setStyleSheet("QPushButton{background:#0D1628;color:#4FC3F7;border:1px solid #1E3A5F;border-radius:3px;font-size:11px;padding:1px 6px;}QPushButton:hover{background:#1A3555;color:#E3F2FD;}")
        btn_max_left.clicked.connect(lambda: self._maximize_panel("left"))
        hl.addWidget(btn_max_left)
        outer_lay.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        c = QWidget()
        lay = QVBoxLayout(c)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(10)
        lay.addWidget(self._build_registration_box())
        lay.addWidget(self._build_plan_box())
        lay.addWidget(self._build_geofence_box())
        lay.addWidget(self._build_server_box())
        lay.addStretch()
        scroll.setWidget(c)
        outer_lay.addWidget(scroll)
        return outer

    def _build_registration_box(self):
        box = QGroupBox("◈  DEVICE REGISTRATION  [R]")
        lay = QFormLayout(box)
        lay.setSpacing(8)
        lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._reg_name = QLineEdit("Field Unit")
        self._reg_name.setPlaceholderText("e.g. TOYOTA, Drone-01")
        self._reg_type = QComboBox()
        self._reg_type.addItems([
            "GROUND_VEHICLE","UAV","FIELD_UNIT",
            "SENSOR_NODE","RELAY_STATION","VESSEL","MOTORCYCLE"
        ])
        self._reg_ix = self._spinbox(0, 99999, 0)
        self._reg_iy = self._spinbox(0, 99999, 0)

        lay.addRow(self._lbl("Name:"),    self._reg_name)
        lay.addRow(self._lbl("Type:"),    self._reg_type)
        lay.addRow(self._lbl("Start X:"), self._reg_ix)
        lay.addRow(self._lbl("Start Y:"), self._reg_iy)

        btn = QPushButton("▶  REGISTER DEVICE")
        btn.setObjectName("success"); btn.setMinimumHeight(34)
        btn.clicked.connect(self._register_device)
        lay.addRow(btn)
        return box

    def _build_plan_box(self):
        box = QGroupBox("◈  TRAVEL PLAN EDITOR  [P]")
        lay = QFormLayout(box)
        lay.setSpacing(8)
        lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._plan_device   = QComboBox()
        self._plan_sx       = self._spinbox(0, 99999, 0)
        self._plan_sy       = self._spinbox(0, 99999, 0)
        self._plan_wp       = QLineEdit("10,5; 20,10; 30,15")
        self._plan_wp.setPlaceholderText("x,y ; x,y ; x,y  (optional)")
        self._plan_dx       = self._spinbox(0, 99999, 40)
        self._plan_dy       = self._spinbox(0, 99999, 30)
        self._plan_speed    = self._spinbox(0.1, 9999, 5, 0.5)
        self._plan_interval = self._spinbox(0.5, 300,  2, 0.5)

        lay.addRow(self._lbl("Device:"),       self._plan_device)
        lay.addRow(self._lbl("Start X:"),      self._plan_sx)
        lay.addRow(self._lbl("Start Y:"),      self._plan_sy)
        lay.addRow(self._lbl("Waypoints:"),    self._plan_wp)
        lay.addRow(self._lbl("Dest X:"),       self._plan_dx)
        lay.addRow(self._lbl("Dest Y:"),       self._plan_dy)
        lay.addRow(self._lbl("Speed:"),        self._plan_speed)
        lay.addRow(self._lbl("Interval (s):"), self._plan_interval)

        hint = QLabel("Waypoints: x,y ; x,y ; x,y")
        hint.setStyleSheet("color:#3A6080; font-size:10px; font-style:italic;")
        lay.addRow(hint)

        btn_assign = QPushButton("▶  ASSIGN TO DEVICE")
        btn_assign.setObjectName("assign"); btn_assign.setMinimumHeight(32)
        btn_assign.clicked.connect(self._assign_plan)

        btn_fleet = QPushButton("▶▶  ASSIGN TO ALL DEVICES")
        btn_fleet.setObjectName("neutral"); btn_fleet.setMinimumHeight(32)
        btn_fleet.clicked.connect(self._assign_plan_fleet)

        lay.addRow(btn_assign)
        lay.addRow(btn_fleet)
        return box

    def _build_geofence_box(self):
        box = QGroupBox("◈  GEOFENCE / EXCLUSION ZONES")
        lay = QFormLayout(box)
        lay.setSpacing(8)
        lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._gf_x1 = self._spinbox(0, 99999, 10)
        self._gf_y1 = self._spinbox(0, 99999, 10)
        self._gf_x2 = self._spinbox(0, 99999, 20)
        self._gf_y2 = self._spinbox(0, 99999, 20)
        self._gf_label = QLineEdit("EXCLUSION ZONE")

        lay.addRow(self._lbl("Zone X1:"), self._gf_x1)
        lay.addRow(self._lbl("Zone Y1:"), self._gf_y1)
        lay.addRow(self._lbl("Zone X2:"), self._gf_x2)
        lay.addRow(self._lbl("Zone Y2:"), self._gf_y2)
        lay.addRow(self._lbl("Label:"),   self._gf_label)

        btn_add = QPushButton("▶  ADD GEOFENCE")
        btn_add.setObjectName("neutral"); btn_add.setMinimumHeight(30)
        btn_add.clicked.connect(self._add_geofence)

        btn_clear = QPushButton("✕  CLEAR ALL ZONES")
        btn_clear.setObjectName("danger"); btn_clear.setMinimumHeight(30)
        btn_clear.clicked.connect(self._clear_geofences)

        lay.addRow(btn_add)
        lay.addRow(btn_clear)
        return box

    def _build_server_box(self):
        box = QGroupBox("◈  SERVER CONTROL")
        lay = QVBoxLayout(box); lay.setSpacing(8)

        sf = QFrame()
        sf.setStyleSheet(
            "QFrame{background:#071428;border:1px solid #1E3A5F;border-radius:4px;}"
        )
        sl = QHBoxLayout(sf); sl.setContentsMargins(8, 4, 8, 4)
        self._srv_led   = QLabel("⬤")
        self._srv_led.setStyleSheet("color:#4CAF50; font-size:14px;")
        self._srv_label = QLabel("ONLINE  ·  127.0.0.1:9000")
        self._srv_label.setStyleSheet(
            "color:#4CAF50; font-family:'Courier New'; font-size:11px;"
        )
        sl.addWidget(self._srv_led); sl.addWidget(self._srv_label); sl.addStretch()
        lay.addWidget(sf)

        row = QHBoxLayout()
        btn_stop = QPushButton("■  STOP SERVER")
        btn_stop.setObjectName("danger"); btn_stop.setMinimumHeight(32)
        btn_stop.clicked.connect(self._stop_server)

        btn_export = QPushButton("⬇  EXPORT CSV  [E]")
        btn_export.setObjectName("neutral"); btn_export.setMinimumHeight(32)
        btn_export.clicked.connect(self._export_csv)

        row.addWidget(btn_stop); row.addWidget(btn_export)
        lay.addLayout(row)

        self._btn_mute = QPushButton("🔔  SOUND ON  [M]")
        self._btn_mute.setObjectName("neutral"); self._btn_mute.setMinimumHeight(30)
        self._btn_mute.clicked.connect(self._toggle_mute)
        lay.addWidget(self._btn_mute)

        btn_save = QPushButton("💾  SAVE CONFIG")
        btn_save.setObjectName("neutral"); btn_save.setMinimumHeight(30)
        btn_save.clicked.connect(self._save_config)

        btn_load = QPushButton("📂  LOAD CONFIG")
        btn_load.setObjectName("neutral"); btn_load.setMinimumHeight(30)
        btn_load.clicked.connect(self._load_config)

        r2 = QHBoxLayout()
        r2.addWidget(btn_save); r2.addWidget(btn_load)
        lay.addLayout(r2)
        return box

    # ── Center panel ──────────────────────────────────────────────────

    def _build_center_panel(self):
        w = QWidget()
        lay = QVBoxLayout(w); lay.setContentsMargins(2, 0, 2, 0); lay.setSpacing(4)

        hdr = QFrame()
        hdr.setStyleSheet(
            "QFrame{background:#0D1628;border:1px solid #1E3A5F;border-radius:4px;}"
        )
        hl = QHBoxLayout(hdr); hl.setContentsMargins(10, 5, 10, 5)

        t = QLabel("◈  LIVE OPERATIONAL MAP")
        t.setStyleSheet(
            "color:#4FC3F7; font-family:'Courier New'; font-size:12px; "
            "font-weight:bold; letter-spacing:2px;"
        )
        hl.addWidget(t); hl.addStretch()

        btn_labels = QPushButton("◉ LABELS  [L]")
        btn_labels.setObjectName("neutral"); btn_labels.setFixedHeight(26)
        btn_labels.clicked.connect(self._toggle_labels)
        hl.addWidget(btn_labels)

        self._btn_satellite = QPushButton("🛰  SATELLITE")
        self._btn_satellite.setObjectName("neutral"); self._btn_satellite.setFixedHeight(26)
        self._btn_satellite.clicked.connect(self._toggle_satellite)
        hl.addWidget(self._btn_satellite)

        btn_load_map = QPushButton("📂 LOAD MAP")
        btn_load_map.setObjectName("neutral"); btn_load_map.setFixedHeight(26)
        btn_load_map.clicked.connect(self._load_map_image)
        hl.addWidget(btn_load_map)

        btn_reset = QPushButton("⌖ RESET  [F5]")
        btn_reset.setObjectName("neutral"); btn_reset.setFixedHeight(26)
        btn_reset.clicked.connect(lambda: self.map_widget.reset_view())
        hl.addWidget(btn_reset)

        btn_max_map = QPushButton("⛶")
        btn_max_map.setFixedSize(24, 24)
        btn_max_map.setToolTip("Maximize / Restore")
        btn_max_map.setStyleSheet("QPushButton{background:#0D1628;color:#4FC3F7;border:1px solid #1E3A5F;border-radius:3px;font-size:11px;padding:1px 6px;}QPushButton:hover{background:#1A3555;color:#E3F2FD;}")
        btn_max_map.clicked.connect(lambda: self._maximize_panel("map"))
        hl.addWidget(btn_max_map)

        lay.addWidget(hdr)

        self.map_widget = GridMapWidget()
        self.map_widget.device_context_requested.connect(self._show_device_context_menu)
        lay.addWidget(self.map_widget)
        return w

    # ── Right tabs ────────────────────────────────────────────────────

    def _build_right_tabs(self):
        outer = QWidget()
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(3)

        hdr = QFrame()
        hdr.setStyleSheet("QFrame{background:#0D1628;border:1px solid #1E3A5F;border-radius:4px;}")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(10, 4, 6, 4)
        t = QLabel("◈  DATA PANELS")
        t.setStyleSheet("color:#4FC3F7;font-family:'Courier New';font-size:12px;font-weight:bold;letter-spacing:2px;")
        hl.addWidget(t); hl.addStretch()
        btn_max_right = QPushButton("⛶")
        btn_max_right.setFixedSize(24, 24)
        btn_max_right.setToolTip("Maximize / Restore")
        btn_max_right.setStyleSheet("QPushButton{background:#0D1628;color:#4FC3F7;border:1px solid #1E3A5F;border-radius:3px;font-size:11px;padding:1px 6px;}QPushButton:hover{background:#1A3555;color:#E3F2FD;}")
        btn_max_right.clicked.connect(lambda: self._maximize_panel("right"))
        hl.addWidget(btn_max_right)
        outer_lay.addWidget(hdr)

        self._right_tabs = QTabWidget()
        self._right_tabs.addTab(self._build_telemetry_tab(),     "TELEMETRY")
        self._right_tabs.addTab(self._build_alert_history_tab(), "ALERTS")
        self._right_tabs.addTab(self._build_detail_tab(),        "DEVICE DETAIL")
        outer_lay.addWidget(self._right_tabs)
        return outer

    def _build_telemetry_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w); lay.setContentsMargins(4, 4, 4, 4); lay.setSpacing(4)

        cols = ["ID","Name","X","Y","Destination","Deviation","Status","Speed","Updated"]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.cellDoubleClicked.connect(self._on_table_double_click)
        lay.addWidget(self.table)

        legend = QFrame()
        legend.setStyleSheet(
            "QFrame{background:#07101E;border:1px solid #1E3A5F;border-radius:4px;}"
        )
        ll = QHBoxLayout(legend); ll.setContentsMargins(8, 4, 8, 4)
        for color, text in [("#4CAF50","ONLINE"),("#EF5350","ALERT"),
                             ("#78909C","OFFLINE"),("#29B6F6","ARRIVED")]:
            dot = QLabel("⬤")
            dot.setStyleSheet(f"color:{color}; font-size:10px;")
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"color:{color}; font-family:'Courier New'; font-size:10px;"
            )
            ll.addWidget(dot); ll.addWidget(lbl); ll.addSpacing(8)
        ll.addStretch()
        lay.addWidget(legend)
        return w

    def _build_alert_history_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w); lay.setContentsMargins(4, 4, 4, 4); lay.setSpacing(4)

        cols = ["Time","Device","Type","Detail"]
        self._alert_table = QTableWidget(0, len(cols))
        self._alert_table.setHorizontalHeaderLabels(cols)
        self._alert_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents)
        self._alert_table.horizontalHeader().setStretchLastSection(True)
        self._alert_table.setAlternatingRowColors(True)
        self._alert_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._alert_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._alert_table.verticalHeader().setVisible(False)
        lay.addWidget(self._alert_table)

        btn_clear = QPushButton("✕  CLEAR ALERT HISTORY")
        btn_clear.setObjectName("danger"); btn_clear.setFixedHeight(28)
        btn_clear.clicked.connect(self._clear_alert_history)
        lay.addWidget(btn_clear)
        return w

    def _build_detail_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w); lay.setContentsMargins(8, 8, 8, 8)
        hint = QLabel("Double-click any row in the Telemetry tab\nto see full device details here.")
        hint.setStyleSheet("color:#3A6080; font-style:italic;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_text = QTextEdit()
        self._detail_text.setReadOnly(True)
        self._detail_text.setStyleSheet(
            "QTextEdit{background:#04080F;color:#80CBC4;"
            "font-family:'Courier New';font-size:12px;}"
        )
        lay.addWidget(hint)
        lay.addWidget(self._detail_text)
        return w

    # ── Log panel ─────────────────────────────────────────────────────

    def _build_log_panel(self):
        w = QWidget()
        lay = QVBoxLayout(w); lay.setContentsMargins(2, 0, 2, 0); lay.setSpacing(4)

        hdr = QFrame()
        hdr.setStyleSheet(
            "QFrame{background:#0D1628;border:1px solid #1E3A5F;border-radius:4px;}"
        )
        hl = QHBoxLayout(hdr); hl.setContentsMargins(10, 4, 10, 4)
        t = QLabel("◈  SYSTEM EVENT LOG")
        t.setStyleSheet(
            "color:#4FC3F7;font-family:'Courier New';font-size:12px;"
            "font-weight:bold;letter-spacing:2px;"
        )
        hl.addWidget(t); hl.addStretch()

        btn_clear = QPushButton("CLEAR  [C]")
        btn_clear.setFixedHeight(24)
        btn_clear.setStyleSheet(
            "QPushButton{background:#0D1628;color:#607080;"
            "border:1px solid #1E3A5F;border-radius:3px;font-size:10px;padding:2px 8px;}"
            "QPushButton:hover{color:#EF5350;border-color:#7B1F1F;}"
        )
        btn_clear.clicked.connect(lambda: self._log_console.clear())
        hl.addWidget(btn_clear)

        btn_max_log = QPushButton("⛶")
        btn_max_log.setFixedSize(24, 24)
        btn_max_log.setToolTip("Maximize / Restore")
        btn_max_log.setStyleSheet("QPushButton{background:#0D1628;color:#4FC3F7;border:1px solid #1E3A5F;border-radius:3px;font-size:11px;padding:1px 6px;}QPushButton:hover{background:#1A3555;color:#E3F2FD;}")
        btn_max_log.clicked.connect(lambda: self._maximize_panel("log"))
        hl.addWidget(btn_max_log)
        lay.addWidget(hdr)

        self._log_console = QTextEdit()
        self._log_console.setReadOnly(True)
        self._log_console.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        lay.addWidget(self._log_console)
        return w

    # ══════════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════════

    def _spinbox(self, lo=0, hi=99999, val=0, step=1.0, dec=1):
        sb = QDoubleSpinBox()
        sb.setRange(lo, hi); sb.setValue(val)
        sb.setSingleStep(step); sb.setDecimals(dec)
        return sb

    def _lbl(self, text):
        l = QLabel(text)
        l.setStyleSheet(
            "color:#607D8B;font-family:'Courier New';"
            "font-size:11px;min-width:80px;"
        )
        return l

    # ══════════════════════════════════════════════════════════════════
    # Server
    # ══════════════════════════════════════════════════════════════════

    def _toggle_satellite(self):
        if self.map_widget._bg_mode == "satellite" and self.map_widget._bg_pixmap:
            self.map_widget.set_bg_mode("dark")
            self._btn_satellite.setText("🛰  SATELLITE")
        else:
            if self.map_widget._bg_pixmap:
                self.map_widget.set_bg_mode("satellite")
                self._btn_satellite.setText("⬛  GRID")
            else:
                logger.warning("No satellite image loaded. Click LOAD MAP first.")

    def _load_map_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Map Image", "",
            "Images (*.jpg *.jpeg *.png *.bmp *.tif *.tiff)"
        )
        if not path:
            return
        if self.map_widget.load_background(path):
            self._btn_satellite.setText("⬛  GRID")
            logger.info(f"Satellite map loaded: {os.path.basename(path)}")
        else:
            logger.error(f"Failed to load image: {path}")

    def _toggle_mute(self):
        muted = not sound_engine._muted
        sound_engine.set_muted(muted)
        if muted:
            self._btn_mute.setText("🔇  SOUND OFF  [M]")
            self._btn_mute.setStyleSheet(
                "QPushButton{background:#1E0A0A;color:#EF5350;"
                "border:1px solid #7B1F1F;border-radius:4px;"
                "padding:7px 14px;font-family:'Courier New';font-size:11px;}"
            )
        else:
            self._btn_mute.setText("🔔  SOUND ON  [M]")
            self._btn_mute.setStyleSheet("")
        logger.info(f"Alert sounds {'muted' if muted else 'unmuted'}.")

    def _start_server(self):
        self.server.start()
        logger.info("Control Center started. TCP server on 127.0.0.1:9000")

    def _stop_server(self):
        self.server.stop()
        self._srv_led.setStyleSheet("color:#EF5350; font-size:14px;")
        self._srv_label.setText("OFFLINE")
        self._srv_label.setStyleSheet(
            "color:#EF5350;font-family:'Courier New';font-size:11px;"
        )
        self._title_led.setStyleSheet("color:#EF5350; font-size:13px;")
        self._show_session_summary()

    # ══════════════════════════════════════════════════════════════════
    # Actions
    # ══════════════════════════════════════════════════════════════════

    def _register_device(self):
        name  = self._reg_name.text().strip() or "Unknown"
        dtype = self._reg_type.currentText()
        ix, iy = self._reg_ix.value(), self._reg_iy.value()
        rec = self.registry.register(name, dtype, (ix, iy))
        logger.info(f"Registered {rec.device_id}  |  {name}  |  {dtype}  |  ({ix},{iy})")
        self._plan_device.addItem(f"{rec.device_id}  ({name})", rec.device_id)
        self._plan_sx.setValue(ix)
        self._plan_sy.setValue(iy)

    def _assign_plan(self):
        idx = self._plan_device.currentIndex()
        if idx < 0:
            logger.warning("No device selected."); return
        dev_id = self._plan_device.itemData(idx)
        self._do_assign(dev_id)

    def _assign_plan_fleet(self):
        devices = self.registry.all_devices()
        if not devices:
            logger.warning("No devices registered."); return
        for dev in devices:
            self._do_assign(dev.device_id)
        logger.info(f"Fleet plan assigned to {len(devices)} devices.")

    def _do_assign(self, dev_id):
        start = (self._plan_sx.value(), self._plan_sy.value())
        dest  = (self._plan_dx.value(), self._plan_dy.value())
        waypoints = []
        for token in self._plan_wp.text().split(";"):
            token = token.strip()
            if "," in token:
                try:
                    x, y = token.split(",", 1)
                    waypoints.append((float(x.strip()), float(y.strip())))
                except ValueError:
                    pass
        plan = make_plan(start, waypoints, dest,
                         self._plan_interval.value(), self._plan_speed.value())
        self.registry.set_travel_plan(dev_id, plan)
        self.server.push_travel_plan(dev_id, plan)
        logger.info(f"Plan -> {dev_id}  start={start}  dest={dest}  "
                    f"wps={len(waypoints)}  speed={self._plan_speed.value()}")

    def _add_geofence(self):
        x1, y1 = self._gf_x1.value(), self._gf_y1.value()
        x2, y2 = self._gf_x2.value(), self._gf_y2.value()
        label  = self._gf_label.text().strip() or "EXCLUSION ZONE"
        self.tracker.add_geofence(x1, y1, x2, y2, label)
        self.map_widget.add_geofence(x1, y1, x2, y2, label)
        logger.info(f"Geofence added: '{label}'  ({x1},{y1}) -> ({x2},{y2})")

    def _clear_geofences(self):
        self.tracker.clear_geofences()
        self.map_widget.clear_geofences()
        logger.info("All geofences cleared.")

    def _reset_layout(self):
        total_w = self._h_split.width()
        self._h_split.setSizes([310, total_w - 730, 420])
        total_v = self._v_split.height()
        self._v_split.setSizes([total_v - 200, 200])
        self._maximized_panel = None

    def _maximize_panel(self, panel: str):
        """Maximize one panel to fill the entire space, or restore if already maximized."""
        if self._maximized_panel == panel:
            self._reset_layout()
            return

        self._maximized_panel = panel
        total_w = self._h_split.width()
        total_v = self._v_split.height()
        BIG = 99999

        if panel == "left":
            self._h_split.setSizes([BIG, 0, 0])
            self._v_split.setSizes([total_v - 60, 60])
        elif panel == "map":
            self._h_split.setSizes([0, BIG, 0])
            self._v_split.setSizes([total_v - 60, 60])
        elif panel == "right":
            self._h_split.setSizes([0, 0, BIG])
            self._v_split.setSizes([total_v - 60, 60])
        elif panel == "log":
            self._h_split.setSizes([0, BIG, 0])
            self._v_split.setSizes([0, BIG])

    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        self.setStyleSheet(DARK_THEME if self._dark_mode else LIGHT_THEME)

    def _toggle_labels(self):
        self.map_widget.toggle_labels()

    # ══════════════════════════════════════════════════════════════════
    # Context menu (right-click on map device)
    # ══════════════════════════════════════════════════════════════════

    def _show_device_context_menu(self, device_id: str, gx: int, gy: int):
        rec = self.registry.get(device_id)
        if not rec:
            return
        menu = QMenu(self)
        menu.setTitle(device_id)

        act_info = QAction(f"📋  {device_id}  ({rec.device_name})", self)
        act_info.setEnabled(False)
        menu.addAction(act_info)
        menu.addSeparator()

        act_plan = QAction("📍  Assign travel plan", self)
        act_plan.triggered.connect(lambda: self._do_assign(device_id))
        menu.addAction(act_plan)

        act_detail = QAction("🔍  View full details", self)
        act_detail.triggered.connect(lambda: self._show_device_detail(device_id))
        menu.addAction(act_detail)

        menu.addSeparator()
        act_remove = QAction("✕  Remove device", self)
        act_remove.triggered.connect(lambda: self._remove_device(device_id))
        menu.addAction(act_remove)

        menu.exec(self.mapToGlobal(self.map_widget.mapTo(self, self.map_widget.rect().center())))

    def _remove_device(self, device_id):
        self.registry.remove(device_id)
        logger.info(f"Device {device_id} removed from registry.")

    # ══════════════════════════════════════════════════════════════════
    # Device detail panel
    # ══════════════════════════════════════════════════════════════════

    def _on_table_double_click(self, row, col):
        id_item = self.table.item(row, 0)
        if id_item:
            self._show_device_detail(id_item.text())

    def _show_device_detail(self, device_id: str):
        rec = self.registry.get(device_id)
        if not rec:
            return
        self._right_tabs.setCurrentIndex(2)   # Switch to Detail tab

        plan = rec.travel_plan or {}
        dest = plan.get("destination", ["—","—"])
        wps  = plan.get("waypoints", [])
        updated = rec.last_update.strftime("%Y-%m-%d %H:%M:%S") if rec.last_update else "—"

        import math
        dist_rem = "—"
        eta      = "—"
        if plan.get("destination"):
            dx = plan["destination"][0] - rec.current_x
            dy = plan["destination"][1] - rec.current_y
            d  = math.sqrt(dx*dx + dy*dy)
            dist_rem = f"{d:.2f} units"
            if rec.speed > 0:
                eta_s = d / rec.speed
                eta = f"{eta_s:.0f}s" if eta_s < 60 else f"{eta_s/60:.1f}min"

        txt = f"""
╔══════════════════════════════════════════╗
  DEVICE DETAIL  —  {device_id}
╚══════════════════════════════════════════╝

  Name         : {rec.device_name}
  Type         : {rec.device_type}
  Status       : {rec.status}
  Color        : {rec.color}

  Position     : ({rec.current_x:.3f}, {rec.current_y:.3f})
  Speed        : {rec.speed:.2f} u/s
  Distance     : {rec.distance_travelled:.2f} units traveled
  Deviation    : {rec.deviation:.3f} units from route
  Last Update  : {updated}

  Travel Plan
  ───────────
  Start        : {plan.get("start", "—")}
  Waypoints    : {len(wps)} point(s)
  {chr(10).join(f'    [{i+1}] {w}' for i,w in enumerate(wps))}
  Destination  : ({dest[0]}, {dest[1]})
  Dist Remain  : {dist_rem}
  ETA          : {eta}
  Speed        : {plan.get("speed", "—")} u/s
  Interval     : {plan.get("report_interval","—")} s

  Trail Points : {len(rec.trail)}
"""
        self._detail_text.setText(txt)

    # ══════════════════════════════════════════════════════════════════
    # Refresh
    # ══════════════════════════════════════════════════════════════════

    def _refresh_ui(self):
        devices = self.registry.all_devices()
        self._dev_count_badge.setText(f"DEVICES: {len(devices)}")
        self._refresh_table(devices)
        self.map_widget.update_devices(devices)

        # Log telemetry for CSV
        for dev in devices:
            if dev.last_update:
                self._telemetry_log.append({
                    "time":     dev.last_update.strftime("%Y-%m-%d %H:%M:%S"),
                    "id":       dev.device_id,
                    "name":     dev.device_name,
                    "x":        dev.current_x,
                    "y":        dev.current_y,
                    "speed":    dev.speed,
                    "distance": dev.distance_travelled,
                    "deviation":dev.deviation,
                    "status":   dev.status,
                })

    def _refresh_table(self, devices):
        self.table.setRowCount(len(devices))
        status_colors = {
            "ALERT":   "#EF5350","ONLINE":  "#4CAF50",
            "OFFLINE": "#78909C","ARRIVED": "#29B6F6","IDLE": "#607D8B",
        }
        for row, dev in enumerate(devices):
            dest = "—"
            if dev.travel_plan and dev.travel_plan.get("destination"):
                d = dev.travel_plan["destination"]
                dest = f"({d[0]:.1f},{d[1]:.1f})"
            updated = dev.last_update.strftime("%H:%M:%S") if dev.last_update else "—"
            cells = [
                dev.device_id, dev.device_name,
                f"{dev.current_x:.2f}", f"{dev.current_y:.2f}",
                dest, f"{dev.deviation:.2f}", dev.status,
                f"{dev.speed:.1f}", updated,
            ]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 6:
                    c = status_colors.get(text, "#C8D8E8")
                    item.setForeground(QColor(c))
                    f = QFont("Courier New"); f.setPixelSize(11); f.setBold(True)
                    item.setFont(f)
                elif col == 5:
                    try:
                        v = float(text)
                        item.setForeground(QColor(
                            "#EF5350" if v > 3 else "#FFA726" if v > 1.5 else "#66BB6A"
                        ))
                    except ValueError: pass
                elif col in (2, 3):
                    item.setForeground(QColor("#80CBC4"))
                elif col == 7:
                    item.setForeground(QColor("#FFA726"))
                self.table.setItem(row, col, item)

            if dev.status == "ALERT":
                for col in range(len(cells)):
                    it = self.table.item(row, col)
                    if it: it.setBackground(QColor(40, 10, 10))

    # ══════════════════════════════════════════════════════════════════
    # Log
    # ══════════════════════════════════════════════════════════════════

    def _append_log(self, line: str):
        if "[WARNING]" in line or "ALERT" in line or "CHANGE" in line:
            color = "#FFA726"
        elif "[ERROR]" in line:
            color = "#EF5350"
        elif "[DEBUG]" in line:
            color = "#37474F"
        elif any(k in line for k in ("ARRIVED","Registered","Plan","Started")):
            color = "#4FC3F7"
        else:
            color = "#4CAF50"
        self._log_console.setTextColor(QColor(color))
        self._log_console.append(line)
        sb = self._log_console.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ══════════════════════════════════════════════════════════════════
    # Alerts
    # ══════════════════════════════════════════════════════════════════

    def _on_alert(self, device_id: str, alert_type: str, detail: str):
        """Background thread — emit signal only."""
        self._log_signal.new_alert.emit(device_id, alert_type, detail)

    def _handle_alert_on_main_thread(self, device_id: str, alert_type: str, detail: str):
        """Main thread — update alert history, play sound, show popup for critical alerts."""
        rec  = self.registry.get(device_id)
        name = rec.device_name if rec else device_id

        # Always add to alert history table
        self._add_to_alert_history(device_id, name, alert_type, detail)

        # Play alert sound (non-blocking, respects mute)
        sound_engine.play(alert_type, device_id)

        # Popup only for destination change and wrong destination
        if alert_type in ("DEST_CHANGE", "WRONG_DEST"):
            self._show_alert_dialog(device_id, alert_type, detail)

    def _add_to_alert_history(self, device_id, name, alert_type, detail):
        ts = datetime.now().strftime("%H:%M:%S")
        self._alert_history.append({
            "time": ts, "device": f"{device_id} ({name})",
            "type": alert_type, "detail": detail
        })
        row = self._alert_table.rowCount()
        self._alert_table.insertRow(row)

        type_colors = {
            "DEST_CHANGE": "#FFA726", "WRONG_DEST":  "#EF5350",
            "DEVIATION":   "#FF7043", "GEOFENCE":    "#AB47BC",
            "SPEED_STOP":  "#78909C", "SPEED_SPIKE": "#FFD54F",
            "ARRIVED":     "#4FC3F7",
        }
        color = type_colors.get(alert_type, "#C8D8E8")

        for col, text in enumerate([ts, f"{device_id} ({name})", alert_type, detail]):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QColor(color))
            self._alert_table.setItem(row, col, item)

        self._alert_table.scrollToBottom()

        # Flash the alerts tab
        self._right_tabs.setTabText(1, f"ALERTS ●  ({row+1})")

    def _clear_alert_history(self):
        self._alert_table.setRowCount(0)
        self._alert_history.clear()
        self._right_tabs.setTabText(1, "ALERTS")

    def _show_alert_dialog(self, device_id: str, alert_type: str, detail: str):
        rec  = self.registry.get(device_id)
        name = rec.device_name if rec else device_id
        if alert_type == "DEST_CHANGE":
            title  = "DESTINATION CHANGE DETECTED"
            header = "⚠  DESTINATION CHANGE ALERT"
            color  = "#FFA726"
            icon   = QMessageBox.Icon.Warning
        else:
            title  = "WRONG DESTINATION"
            header = "✖  WRONG DESTINATION ALERT"
            color  = "#EF5350"
            icon   = QMessageBox.Icon.Critical

        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setIcon(icon)
        msg.setText(header)
        msg.setInformativeText(
            f"Device  :  {device_id}  ({name})\nDetails :  {detail}"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setStyleSheet(f"""
            QMessageBox {{ background-color: #0B1120; }}
            QMessageBox QLabel {{
                color: {color}; font-family: "Courier New";
                font-size: 12px; min-width: 420px; padding: 6px;
            }}
            QPushButton {{
                background-color: #112240; color: #64B5F6;
                border: 1px solid #1E3A5F; border-radius: 4px;
                padding: 6px 24px; font-family: "Courier New"; min-width: 80px;
            }}
            QPushButton:hover {{ background-color: #1A3555; border-color: #4FC3F7; }}
        """)
        msg.exec()

    # ══════════════════════════════════════════════════════════════════
    # Export & Config
    # ══════════════════════════════════════════════════════════════════

    def _export_csv(self):
        if not self._telemetry_log:
            logger.warning("No telemetry data to export yet.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Telemetry CSV", "telemetry_export.csv",
            "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "time","id","name","x","y","speed",
                    "distance","deviation","status"
                ])
                w.writeheader()
                w.writerows(self._telemetry_log)
            logger.info(f"Exported {len(self._telemetry_log)} telemetry records to {path}")
        except Exception as e:
            logger.error(f"CSV export failed: {e}")

    def _save_config(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Config", "tracking_config.json", "JSON Files (*.json)"
        )
        if not path:
            return
        config = {"devices": [], "geofences": []}
        for dev in self.registry.all_devices():
            config["devices"].append({
                "name": dev.device_name, "type": dev.device_type,
                "initial_position": list(dev.initial_position),
                "travel_plan": dev.travel_plan,
            })
        for gf in self.tracker._geofences:
            config["geofences"].append({
                "x1":gf[0],"y1":gf[1],"x2":gf[2],"y2":gf[3],"label":gf[4]
            })
        try:
            with open(path, "w") as f:
                json.dump(config, f, indent=2)
            logger.info(f"Config saved to {path}")
        except Exception as e:
            logger.error(f"Save config failed: {e}")

    def _load_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Config", "", "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            with open(path) as f:
                config = json.load(f)
            for d in config.get("devices", []):
                pos = tuple(d.get("initial_position", [0, 0]))
                rec = self.registry.register(d["name"], d["type"], pos)
                self._plan_device.addItem(f"{rec.device_id}  ({rec.device_name})", rec.device_id)
                if d.get("travel_plan"):
                    self.registry.set_travel_plan(rec.device_id, d["travel_plan"])
            for gf in config.get("geofences", []):
                self.tracker.add_geofence(
                    gf["x1"],gf["y1"],gf["x2"],gf["y2"],gf.get("label","ZONE")
                )
                self.map_widget.add_geofence(
                    gf["x1"],gf["y1"],gf["x2"],gf["y2"],gf.get("label","ZONE")
                )
            logger.info(f"Config loaded from {path}")
        except Exception as e:
            logger.error(f"Load config failed: {e}")

    # ══════════════════════════════════════════════════════════════════
    # Session summary
    # ══════════════════════════════════════════════════════════════════

    def _show_session_summary(self):
        devices = self.registry.all_devices()
        duration = datetime.now() - self._session_start
        mins = int(duration.total_seconds() / 60)
        secs = int(duration.total_seconds() % 60)

        lines = [f"Session Duration : {mins}m {secs}s",
                 f"Total Devices    : {len(devices)}",
                 f"Total Alerts     : {len(self._alert_history)}",
                 f"Telemetry Points : {len(self._telemetry_log)}",
                 "", "── Device Summary ──"]
        for dev in devices:
            lines.append(
                f"  {dev.device_id}  {dev.device_name:12}  "
                f"dist={dev.distance_travelled:.1f}u  "
                f"status={dev.status}"
            )

        msg = QMessageBox(self)
        msg.setWindowTitle("SESSION SUMMARY")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText("SERVER STOPPED  —  SESSION SUMMARY")
        msg.setInformativeText("\n".join(lines))
        msg.setStandardButtons(
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Ok
        )
        msg.setStyleSheet("""
            QMessageBox { background-color: #0B1120; }
            QMessageBox QLabel {
                color: #4FC3F7; font-family: "Courier New";
                font-size: 11px; min-width: 460px;
            }
            QPushButton {
                background-color: #112240; color: #64B5F6;
                border: 1px solid #1E3A5F; border-radius: 4px;
                padding: 6px 20px; font-family: "Courier New";
            }
            QPushButton:hover { background-color: #1A3555; }
        """)
        result = msg.exec()
        if result == QMessageBox.StandardButton.Save:
            self._export_csv()

    # ══════════════════════════════════════════════════════════════════
    # Clock + LED
    # ══════════════════════════════════════════════════════════════════

    def _update_clock(self):
        self._clock_label.setText(
            QDateTime.currentDateTime().toString("yyyy-MM-dd  HH:mm:ss")
        )

    def _blink_led(self):
        self._blink_state = not self._blink_state
        c = "#4CAF50" if self._blink_state else "#1B5E20"
        self._title_led.setStyleSheet(f"color:{c}; font-size:13px;")
