@echo off
REM 启动 kz_mcp_http：所有启动参数都在 config.json 里改（白名单在 users.json，改它不重启、热更新）
cd /d %~dp0
start /min kz_mcp_http.exe --config config.json
REM 如需命令行覆盖（可选，优先级高于 config.json）：
REM start /min kz_mcp_http.exe --config config.json --listen 0.0.0.0:9001 --heartbeat-interval 5
