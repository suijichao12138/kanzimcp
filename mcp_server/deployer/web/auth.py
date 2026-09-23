#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""auth.py — Web 管理界面的 Basic Auth"""
import base64
import hashlib
import hmac
import secrets


def hash_password(password: str, salt: str = "") -> str:
    """SHA-256(salt + password)。salt 为空则纯哈希（兼容老配置）。"""
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def verify(auth_header: str, expected_user: str, expected_hash: str) -> bool:
    """校验 Authorization: Basic xxx 头。"""
    if not auth_header or not auth_header.lower().startswith("basic "):
        return False
    try:
        raw = base64.b64decode(auth_header.split(None, 1)[1]).decode("utf-8")
        user, _, pwd = raw.partition(":")
    except Exception:                                        # noqa: BLE001
        return False
    if not hmac.compare_digest(user, expected_user):
        return False
    return hmac.compare_digest(hash_password(pwd), expected_hash)


def gen_password(nbytes: int = 9) -> str:
    """生成随机密码（首次启动时用）。"""
    return secrets.token_urlsafe(nbytes)
