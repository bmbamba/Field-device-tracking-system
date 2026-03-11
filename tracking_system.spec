# tracking_system.spec  —  PyInstaller build spec for CLAN Tracking Control Center
# Run with:  py -m PyInstaller tracking_system.spec

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('LICENSE.txt', '.'),
        ('README.md', '.'),
        ('tracking_icon.ico',       '.'),
        ('tracking_icon.png',       '.'),
        # ('satellite_map.jpg', '.'),  # Copy this file manually if you have it
        ('alert_arrived.wav',       '.'),
        ('alert_dest_change.wav',   '.'),
        ('alert_deviation.wav',     '.'),
        ('alert_geofence.wav',      '.'),
        ('alert_speed.wav',         '.'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtNetwork',
        'main_window',
        'grid_map_widget',
        'device_registry',
        'tracker_engine',
        'communication_server',
        'route_planner',
        'logger',
        'protocol',
        'math_utils',
        'sound_engine',
        'winsound',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ClanTracking',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='tracking_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ClanTracking',
)
