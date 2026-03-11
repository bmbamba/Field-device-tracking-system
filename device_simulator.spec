# device_simulator.spec  —  PyInstaller build spec for CLAN Device Simulator
# Run with:  py -m PyInstaller device_simulator.spec

block_cipher = None

a = Analysis(
    ['device_simulator.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('LICENSE.txt', '.'),
        ('tracking_icon.ico', '.'),
    ],
    hiddenimports=[
        'movement_engine',
        'communication_client',
        'protocol',
        'math_utils',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['PySide6', 'tkinter', 'matplotlib'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ClanDeviceSimulator',
    debug=False,
    strip=False,
    upx=True,
    console=True,           # Keep console so you can see device output
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
    name='ClanDeviceSimulator',
)
