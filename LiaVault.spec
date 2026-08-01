# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app_grafica.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('config', 'config'), ('licencia.key', '.'), ('metadata.json', '.'), ('app_offline.py', '.'), ('validador.py', '.')],
    hiddenimports=['spacy', 'es_core_news_sm', 'presidio_analyzer', 'presidio_anonymizer', 'easyocr', 'fitz', 'openpyxl', 'docx'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LiaVault',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LiaVault',
)
