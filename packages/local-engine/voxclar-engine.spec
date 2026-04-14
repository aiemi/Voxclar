# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = [
    # External
    'pyaudiowpatch', 'sounddevice', 'scipy.signal', 'websockets',
    'websockets.asyncio', 'websockets.asyncio.client', 'websockets.asyncio.server',
    'websockets.legacy.server', 'numpy', 'httpx', 'pydantic',
    # Internal — Cython .so modules (PyInstaller can't trace imports inside .so)
    'src.server', 'src.engine',
    'src.asr', 'src.asr.server_asr_stream',
    'src.audio', 'src.audio.capture_manager', 'src.audio.echo_canceller',
    'src.audio.macos_capture', 'src.audio.mic_capture', 'src.audio.noise_reducer',
    'src.audio.vad', 'src.audio.windows_capture',
    'src.utils', 'src.utils.audio_utils', 'src.utils.ring_buffer',
    # Stdlib used inside .so modules
    'asyncio', 'json', 'logging', 'os', 'platform', 'subprocess', 'tempfile',
    'threading', 'time', 'struct', 'difflib',
]

# Collect Cython .so files as binaries so PyInstaller bundles them
import glob as _glob
for _so in _glob.glob('src/**/*.so', recursive=True):
    binaries.append((_so, os.path.dirname(_so)))

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

# Post-build: bundle pre-compiled Swift helper next to voxclar-engine
import shutil, os
swift_helper_src = os.path.join(os.path.dirname(SPEC), 'imeet_audio_capture')
swift_helper_dst = os.path.join(DISTPATH, 'voxclar-engine', 'imeet_audio_capture')
if os.path.exists(swift_helper_src):
    shutil.copy2(swift_helper_src, swift_helper_dst)
    os.chmod(swift_helper_dst, 0o755)
    print(f'[spec] Copied Swift helper: {swift_helper_dst}')
else:
    print(f'[spec] WARNING: Swift helper not found at {swift_helper_src}')
