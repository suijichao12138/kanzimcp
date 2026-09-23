#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""notify.py — 飞书通知（urllib 直调 open.feishu.cn，零第三方依赖）"""
import json
import urllib.request


def _post(url: str, payload: dict, headers: dict | None = None, timeout: int = 20) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _token(app_id: str, app_secret: str) -> str:
    r = _post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
              {"app_id": app_id, "app_secret": app_secret})
    if r.get("code") != 0:
        raise RuntimeError(f"取 token 失败: {r}")
    return r["tenant_access_token"]


def send(cfg: dict, text: str) -> tuple[bool, str]:
    """发一条文本消息。cfg = deployer 配置里的 feishu_notify 节。

    未启用或未配置时静默跳过（不算失败），避免首次部署就被通知卡住。
    """
    cfg = cfg or {}
    if not cfg.get("enabled"):
        return True, "通知未启用，已跳过"
    app_id = cfg.get("app_id") or ""
    app_secret = cfg.get("app_secret") or ""
    receive_id = cfg.get("receive_id") or ""
    if not (app_id and app_secret and receive_id):
        return True, "通知未配置完整，已跳过"
    try:
        tok = _token(app_id, app_secret)
        r = _post(
            f"https://open.feishu.cn/open-apis/im/v1/messages"
            f"?receive_id_type={cfg.get('receive_id_type', 'open_id')}",
            {"receive_id": receive_id, "msg_type": "text",
             "content": json.dumps({"text": text}, ensure_ascii=False)},
            headers={"Authorization": f"Bearer {tok}"},
        )
        if r.get("code") != 0:
            return False, f"发送失败: {r}"
        return True, "已发送"
    except Exception as e:                                   # noqa: BLE001
        return False, f"通知异常: {e}"
