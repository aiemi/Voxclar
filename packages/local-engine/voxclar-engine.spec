# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = ['pyaudiowpatch', 'sounddevice', 'scipy.signal', 'websockets', 'websockets.asyncio', 'websockets.asyncio.client', 'websockets.asyncio.server', 'websockets.legacy.server', 'numpy']


a = Analysis(
    ['run_engine.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'faster_whisper', 'ctranslate2', 'transformers', 'huggingface_hub', 'tokenizers', 'safetensors', 'sklearn', 'scikit-learn', 'openai', 'anthropic', 'numba', 'llvmlite', 'pyarrow', 'pandas', 'PIL', 'cv2', 'matplotlib'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='voxclar-engine',
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
    name='voxclar-engine',
)
