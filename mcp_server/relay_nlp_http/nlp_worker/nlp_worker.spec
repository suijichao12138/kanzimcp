import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, copy_metadata


project_root = Path(SPECPATH)
runtime_source = Path(os.environ.get("COPILOT_RUNTIME_SOURCE", ""))
if not runtime_source.is_file():
    raise SystemExit(
        "COPILOT_RUNTIME_SOURCE must point to the downloaded Windows copilot.exe"
    )

copilot_datas, copilot_binaries, copilot_hiddenimports = collect_all("copilot")
datas = [
    *copilot_datas,
    *copy_metadata("github-copilot-sdk"),
    *collect_data_files("certifi"),
]
binaries = [*copilot_binaries, (str(runtime_source), "runtime")]
hiddenimports = [
    *copilot_hiddenimports,
    "pydantic_core._pydantic_core",
    "yaml._yaml",
]

a = Analysis(
    [str(project_root / "nlp_worker.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "ruff"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="nlp_worker",
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
    contents_directory="_internal",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="nlp-worker-portable",
)
