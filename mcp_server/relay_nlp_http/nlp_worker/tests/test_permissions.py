from dataclasses import dataclass

from copilot.rpc import (
    PermissionDecisionApproveOnce,
    PermissionDecisionReject,
    PermissionDecisionUserNotAvailable,
)

from copilot_runtime import PermissionConfig, build_permission_handler


@dataclass
class Request:
    tool_name: str | None = None
    kind: str | None = None
    managed_approval_required: bool = False


def test_permission_policy_deny_precedes_allow() -> None:
    handler = build_permission_handler(
        PermissionConfig(default="deny", allow=["kanzi-*"], deny=["kanzi-delete-*"])
    )
    assert isinstance(handler(Request("kanzi-read"), {}), PermissionDecisionApproveOnce)
    assert isinstance(handler(Request("kanzi-delete-node"), {}), PermissionDecisionReject)


def test_ask_and_managed_approval_fail_closed() -> None:
    handler = build_permission_handler(PermissionConfig(default="ask"))
    assert isinstance(handler(Request("unknown"), {}), PermissionDecisionUserNotAvailable)
    assert isinstance(
        handler(Request("safe", managed_approval_required=True), {}),
        PermissionDecisionUserNotAvailable,
    )


def test_runtime_read_kind_can_be_explicitly_allowed_with_default_deny() -> None:
    handler = build_permission_handler(
        PermissionConfig(default="deny", allow=["read"])
    )

    assert isinstance(
        handler(Request(kind="read"), {}),
        PermissionDecisionApproveOnce,
    )
    assert isinstance(
        handler(Request(kind="write"), {}),
        PermissionDecisionReject,
    )
