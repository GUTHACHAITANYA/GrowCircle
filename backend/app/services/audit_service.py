"""
Audit log service for recording OWASP Top-10 security and DPDP compliance events.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_log import AuditLog


async def log_security_event(
    db: AsyncSession,
    action: str,
    user_id: int | None = None,
    actor_role: str = "anonymous",
    client_ip: str | None = None,
    target_resource: str | None = None,
    target_id: str | None = None,
    details: str | dict[str, Any] | None = None,
    status: str = "SUCCESS",
) -> AuditLog:
    """Records an immutable security audit trail entry."""
    details_str = str(details) if isinstance(details, dict) else details

    log_entry = AuditLog(
        user_id=user_id,
        actor_role=actor_role,
        client_ip=client_ip,
        action=action,
        target_resource=target_resource,
        target_id=target_id,
        details=details_str,
        status=status,
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)
    return log_entry
