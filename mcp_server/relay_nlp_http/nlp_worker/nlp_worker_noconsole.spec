import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, copy_metadata


project_root = Path(SPECPATH)
runtime_source = Path(os.environ.get("COPILOT_RUNTIME_SOURCE", ""))
if not runtime_source.is_file():
    raise SystemExit(
        "COPILOT_RUNTIME_SOURCE must point to the SDK 1.0.26 Runtime 1.0.103 copilot.exe"
    )
runtime_bundle = Path(
    os.environ.get("COPILOT_RUNTIME_BUNDLE", str(runtime_source.parent))
).resolve()
if runtime_source.resolve().parent != runtime_bundle or not runtime_bundle.is_dir():
    raise SystemExit("COPILOT_RUNTIME_BUNDLE must be the parent of COPILOT_RUNTIME_SOURCE")
runtime_datas = [
    (
        str(path),
        str(Path("runtime") / path.relative_to(runtime_bundle).parent),
    )
    for path in sorted(runtime_bundle.rglob("*"))
    if path.is_file()
]
if not runtime_datas:
    raise SystemExit("Copilot Runtime bundle is empty")

copilot_datas, copilot_binaries, copilot_hiddenimports = collect_all("copilot")
datas = [
    *copilot_datas,
    *runtime_datas,
    *copy_metadata("github-copilot-sdk"),
    *collect_data_files("certifi"),
    # 网页控制台前端静态资源
    (str(project_root / "web" / "static"), "web/static"),
]
binaries = [*copilot_binaries]
hiddenimports = [
    *copilot_hiddenimports,
    "pydantic_core._pydantic_core",
    "yaml._yaml",
    "web.server",
    "web.api",
    "web.config_groups",
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
    console=False,
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
    name="nlp-worker-portable-noconsole",
)
