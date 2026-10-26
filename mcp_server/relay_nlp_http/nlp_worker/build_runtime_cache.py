"""Select, validate, and provision the project-local Copilot Runtime cache."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from copilot_runtime import (
    EXPECTED_RUNTIME_VERSION,
    RUNTIME_VERSION_MARKER,
    ConfigError,
    CopilotRuntime,
    validate_runtime_binary,
    write_runtime_version_marker,
)

_RUNTIME_COMPONENTS = ("copilot.exe", "copilot-runtime.exe", "runtime.node")
_HOSTLESS_MARKER = ".hostless-runtime-assets-v2"


class RuntimeCacheError(RuntimeError):
    """The build Runtime cache cannot be selected or provisioned."""


@dataclass(frozen=True)
class RuntimeSelection:
    executable: Path
    bundle: Path
    source: str


DownloadRunner = Callable[[Path], None]


def _bundle_dirs(cache_root: Path) -> tuple[Path, ...]:
    return (
        cache_root,
        cache_root / "prebuilds" / "win32-x64",
    )


def inspect_runtime_bundle(bundle: Path) -> tuple[Path | None, str]:
    """Validate one direct Runtime bundle and explain why it cannot be reused."""
    missing = [
        name
        for name in (*_RUNTIME_COMPONENTS, _HOSTLESS_MARKER)
        if not (bundle / name).is_file()
    ]
    if missing:
        return None, f"missing {', '.join(missing)}"

    executable = bundle / "copilot.exe"
    marker = bundle / RUNTIME_VERSION_MARKER
    try:
        if marker.is_file():
            validate_runtime_binary(executable, marker_path=marker)
        else:
            validate_runtime_binary(executable)
            write_runtime_version_marker(executable, marker)
    except ConfigError as exc:
        return None, str(exc)
    return executable.resolve(), "valid"


def find_cached_runtime(
    project_root: Path,
    *,
    output: Callable[[str], None] = print,
) -> RuntimeSelection | None:
    """Find a valid canonical or versioned project-local Runtime cache."""
    build_dir = project_root.resolve() / "build"
    cache_roots = (
        build_dir / "copilot-runtime",
        build_dir / f"copilot-runtime-{EXPECTED_RUNTIME_VERSION}",
    )
    for cache_root in cache_roots:
        for bundle in _bundle_dirs(cache_root):
            executable, reason = inspect_runtime_bundle(bundle)
            if executable is not None:
                return RuntimeSelection(
                    executable=executable,
                    bundle=executable.parent,
                    source=str(bundle),
                )
            if bundle.exists():
                output(f"Runtime cache rejected: {bundle} ({reason})")
    return None


def _sync_bundle(source: Path, canonical: Path) -> RuntimeSelection:
    """Atomically replace the canonical cache with a validated complete bundle."""
    source = source.resolve()
    canonical = canonical.resolve()
    if source == canonical:
        executable = canonical / "copilot.exe"
        write_runtime_version_marker(executable, canonical / RUNTIME_VERSION_MARKER)
        return RuntimeSelection(executable, canonical, str(source))

    canonical.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=".copilot-runtime-", dir=canonical.parent)
    )
    try:
        shutil.copytree(source, temporary, dirs_exist_ok=True)
        executable = temporary / "copilot.exe"
        marker = temporary / RUNTIME_VERSION_MARKER
        write_runtime_version_marker(executable, marker)
        validate_runtime_binary(executable, marker_path=marker)
        if canonical.exists():
            shutil.rmtree(canonical)
        temporary.replace(canonical)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return RuntimeSelection(
        executable=canonical / "copilot.exe",
        bundle=canonical,
        source=str(source),
    )


def _run_sdk_download(extract_dir: Path, *, force: bool) -> subprocess.CompletedProcess:
    arguments = [
        sys.executable,
        "-m",
        "copilot",
        "download-runtime",
    ]
    if force:
        arguments.append("--force")
    arguments.extend(
        [
            "--version",
            EXPECTED_RUNTIME_VERSION,
            "--in-process",
        ]
    )
    environment = os.environ.copy()
    environment["COPILOT_CLI_EXTRACT_DIR"] = str(extract_dir)
    environment.pop("COPILOT_CLI_PATH", None)
    try:
        return subprocess.run(
            arguments,
            env=environment,
            timeout=900,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeCacheError(
            "Copilot Runtime download timed out after 900 seconds"
        ) from exc


def download_sdk_runtime(
    extract_dir: Path,
    *,
    output: Callable[[str], None] = print,
) -> None:
    """Download normally, retrying once with force only for a damaged SDK cache."""
    output(
        f"No reusable project Runtime cache; downloading official "
        f"Runtime {EXPECTED_RUNTIME_VERSION} without --force."
    )
    completed = _run_sdk_download(extract_dir, force=False)
    if completed.returncode == 0:
        return

    has_cache_files = extract_dir.exists() and any(extract_dir.rglob("*"))
    if not has_cache_files:
        raise RuntimeCacheError(
            f"official Runtime download failed with exit code "
            f"{completed.returncode}"
        )

    output(
        f"SDK download cache is incomplete or damaged: {extract_dir}; "
        "removing only this cache and retrying once with --force."
    )
    shutil.rmtree(extract_dir)
    retried = _run_sdk_download(extract_dir, force=True)
    if retried.returncode != 0:
        raise RuntimeCacheError(
            f"official Runtime forced retry failed with exit code "
            f"{retried.returncode}"
        )


def _find_downloaded_runtime(extract_dir: Path) -> RuntimeSelection:
    for bundle in _bundle_dirs(extract_dir):
        executable, reason = inspect_runtime_bundle(bundle)
        if executable is not None:
            return RuntimeSelection(executable, executable.parent, str(bundle))
        if bundle.exists():
            last_reason = reason
    raise RuntimeCacheError(
        f"download completed but Runtime bundle is invalid under {extract_dir}: "
        f"{locals().get('last_reason', 'bundle not found')}"
    )


def _write_build_outputs(
    selection: RuntimeSelection,
    *,
    env_file: Path,
    release_marker: Path,
) -> None:
    marker = selection.bundle / RUNTIME_VERSION_MARKER
    validate_runtime_binary(selection.executable, marker_path=marker)
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(
        f'set "COPILOT_RUNTIME_SOURCE={selection.executable}"\n'
        f'set "COPILOT_RUNTIME_BUNDLE={selection.bundle}"\n',
        encoding="utf-8",
    )
    release_marker.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(marker, release_marker)


def ensure_runtime_cache(
    project_root: Path,
    *,
    env_file: Path,
    release_marker: Path,
    download_runner: DownloadRunner | None = None,
    output: Callable[[str], None] = print,
) -> RuntimeSelection:
    """Reuse a valid local cache, otherwise download and canonicalize it."""
    CopilotRuntime.validate_sdk_version()
    project_root = project_root.resolve()
    canonical = project_root / "build" / "copilot-runtime"
    selection = find_cached_runtime(project_root, output=output)
    if selection is not None:
        if selection.bundle != canonical.resolve():
            output(
                f"Reusing validated Runtime cache: {selection.bundle}; "
                f"syncing it to {canonical}."
            )
            selection = _sync_bundle(selection.bundle, canonical)
        else:
            output(
                f"Reusing validated Runtime cache: {selection.bundle}; "
                "network download skipped."
            )
            selection = _sync_bundle(selection.bundle, canonical)
        _write_build_outputs(
            selection,
            env_file=env_file,
            release_marker=release_marker,
        )
        return selection

    runner = download_runner or download_sdk_runtime
    extract_dir = project_root / "build" / "copilot-runtime-download"
    runner(extract_dir)
    downloaded = _find_downloaded_runtime(extract_dir)
    selection = _sync_bundle(downloaded.bundle, canonical)
    output(f"Official Runtime cached for future builds: {canonical}")
    _write_build_outputs(
        selection,
        env_file=env_file,
        release_marker=release_marker,
    )
    return selection


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate or provision the project-local Copilot Runtime cache"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path("build/runtime-env.cmd"),
    )
    parser.add_argument(
        "--release-marker",
        type=Path,
        default=Path("build/runtime-version.txt"),
    )
    args = parser.parse_args()
    try:
        selection = ensure_runtime_cache(
            args.project_root,
            env_file=args.env_file.resolve(),
            release_marker=args.release_marker.resolve(),
        )
    except (ConfigError, OSError, RuntimeCacheError) as exc:
        print(f"Runtime cache error: {exc}", file=sys.stderr)
        return 1
    print(f"Validated Runtime source: {selection.executable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
