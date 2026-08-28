@echo off
title 启动Copilot自定义模型CLI
chcp 65001 >nul

:: 加载PATEO自建模型配置
set COPILOT_PROVIDER_TYPE=openai
set COPILOT_PROVIDER_BASE_URL=https://oneapi.pateo.com.cn/v1
set COPILOT_PROVIDER_API_KEY=sk-VPddFJYsxZ9D5mPZ3c6fE1Ef21C742D6B14b15543b8e728d
set COPILOT_MODEL=deepseek-v4-flash-fp8
set COPILOT_DISABLE_TOOL_CALLS=true
set COPILOT_DISABLE_EXTENDED_FIELDS=true

echo 已加载自定义模型配置：%COPILOT_MODEL%
echo 正在启动GitHub Copilot CLI...

nlp_worker_acp.exe --relay ws://10.10.118.152:58080/suijichao --mcp-port 9001 --bridge-http http://10.10.118.152:8081/suijichao --cwd D:\suijichao\kanzi\AIBox4

:: 退出后自动清空临时环境变量，不会污染系统全局配置
set COPILOT_PROVIDER_TYPE=
set COPILOT_PROVIDER_BASE_URL=
set COPILOT_PROVIDER_API_KEY=
set COPILOT_MODEL=



