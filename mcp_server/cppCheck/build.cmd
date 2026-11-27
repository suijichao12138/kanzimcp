@echo off
rem ============================================================================
rem  cppCheck 编译脚本
rem
rem  作用：检查环境 → 下载/校验检查工具 → PyInstaller 打包单文件 exe
rem  产物：dist\cppCheck.exe（自带全部检查工具，可脱离源码独立运行）
rem
rem  用法：build.cmd                正常编译
rem        build.cmd --skip-deps    跳过工具下载（已下载过时加速）
rem ============================================================================
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================================================
echo   cppCheck 编译
echo ============================================================================
echo   工作目录: %CD%
echo.

rem ---------- [1/6] 检查 Python ----------
echo [1/6] 检查 Python 环境...

set "PYEXE="
if exist "%CD%\.venv\Scripts\python.exe" set "PYEXE=%CD%\.venv\Scripts\python.exe"
if not defined PYEXE call :find_python

if not defined PYEXE (
    echo   [错误] 未找到 Python
    echo   请安装 Python 3.8+ ^(64 位^)，安装时勾选 "Add to PATH"
    exit /b 1
)
echo         Python: %PYEXE%

"%PYEXE%" -c "import sys; v=sys.version_info; assert (v.major,v.minor)>=(3,8), 'need 3.8+'; print('         版本 %%d.%%d.%%d' %% (v.major,v.minor,v.micro))"
if errorlevel 1 (
    echo   [错误] Python 版本过低，需要 3.8 及以上
    exit /b 1
)

"%PYEXE%" -c "import sys; assert sys.maxsize>2**32, 'need 64bit'; print('         64 位 OK')"
if errorlevel 1 (
    echo   [警告] 检测到 32 位 Python，建议换 64 位
)

"%PYEXE%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo   [错误] pip 不可用
    exit /b 1
)

rem ---------- [2/6] 检查/下载第三方工具 ----------
echo.
echo [2/6] 准备第三方检查工具...

if /i "%~1"=="--skip-deps" (
    echo         跳过（--skip-deps）
    goto :check_pyinstaller
)

"%PYEXE%" -m codescan setup
if errorlevel 1 (
    echo.
    echo   [错误] 工具准备失败
    echo   可手工下载 cppcheck 解压到 tools\cppcheck\
    echo      https://github.com/danmar/cppcheck/releases/tag/v2.22.0
    echo   注意：需把 cppcheckcore.dll 复制一份改名为 cppcheck-core.dll
    exit /b 1
)

:check_pyinstaller
echo.
echo [3/6] 检查 PyInstaller...
"%PYEXE%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo         未安装，正在安装...
    "%PYEXE%" -m pip install pyinstaller
    if errorlevel 1 (
        echo   [错误] PyInstaller 安装失败
        exit /b 1
    )
)
"%PYEXE%" -m PyInstaller --version

rem ---------- [4/6] 验证工具可用 ----------
echo.
echo [4/6] 验证工具可用性...
"%PYEXE%" -m codescan doctor
if errorlevel 1 (
    echo   [警告] 部分工具不可用，编译后功能会受限
)

rem ---------- [5/6] 打包 ----------
echo.
echo [5/6] PyInstaller 打包（首次约 2-4 分钟）...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

"%PYEXE%" -m PyInstaller --clean --noconfirm cppCheck.spec
if errorlevel 1 (
    echo   [错误] 打包失败
    exit /b 1
)

if not exist "dist\cppCheck.exe" (
    echo   [错误] 未生成 dist\cppCheck.exe
    exit /b 1
)

rem ---------- [6/6] 验证产物 ----------
echo.
echo [6/6] 验证产物...

for %%F in ("dist\cppCheck.exe") do set "SIZE=%%~zF"
set /a SIZEMB=%SIZE%/1048576
echo         体积: %SIZEMB% MB

rem 跑一次 --version 确认 exe 能启动（会解压内部资源）
echo         启动测试...
dist\cppCheck.exe --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [错误] exe 启动失败，可能缺依赖或打包不完整
    echo   可手工运行查看详细报错:  dist\cppCheck.exe --version
    exit /b 1
)
echo         [OK] 启动正常

rem 实际跑一次扫描，确认内部工具可用（造一个最小 C++ 样例）
echo         功能测试（最小样例扫描）...
set "ST=%TEMP%\cppcheck_selftest"
if exist "%ST%" rmdir /s /q "%ST%"
mkdir "%ST%\src" >nul 2>&1
> "%ST%\src\t.cpp" echo int f(){ int a[2]; a[5]=1; return 0; }
dist\cppCheck.exe scan --src "%ST%\src" --out "%ST%\out" --engines cppcheck --no-open >nul 2>&1
if exist "%ST%\out\report.html" (
    echo         [OK] 自检扫描通过
    rmdir /s /q "%ST%"
) else (
    echo   [警告] 自检扫描未通过，请手工验证
)

echo.
echo ============================================================================
echo   编译完成
echo ============================================================================
echo.
echo   产物: %CD%\dist\cppCheck.exe  (%SIZEMB% MB)
echo.
echo   部署方式：
echo     1. 把 dist\cppCheck.exe 复制到 deployer 的 data\tools\ 目录
echo     2. deployer 网页「代码检查」页会自动检测到工具就绪
echo.
echo   命令行用法：
echo     cppCheck.exe scan --src ^<源码目录^> --out ^<输出目录^> --no-open
echo.
endlocal
exit /b 0


:find_python
for /f "delims=" %%I in ('where python 2^>nul') do (
    if not defined PYEXE set "PYEXE=%%I"
)
if not defined PYEXE (
    for /f "delims=" %%I in ('where python3 2^>nul') do (
        if not defined PYEXE set "PYEXE=%%I"
    )
)
goto :eof
