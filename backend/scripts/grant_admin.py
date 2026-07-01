#!/usr/bin/env python3
"""Bootstrap the very first admin account.

This is the ONLY way to create an admin when none exists yet — there is
no API endpoint that can do this, because the admin-grant endpoint
itself requires an existing admin (require_admin). Run this directly by
a human with shell/DB access; it is never reachable over HTTP.

Usage:
    python scripts/grant_admin.py someone@example.com

Subsequent admins should be granted via an existing admin calling
POST /api/v1/admin/roles/grant — this script is for bootstrapping only,
but is safe to re-run (grant_role is idempotent).
"""

import asyncio
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.services.roles import ADMIN_ROLE_KEY, RoleError, grant_role


async def main(email: str) -> None:
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        try:
            await grant_role(
                session,
                target_email=email,
                role_key=ADMIN_ROLE_KEY,
                granted_by_account_id=None,
            )
        except RoleError as e:
            print(f"Error: {e.detail}", file=sys.stderr)
            await engine.dispose()
            sys.exit(1)

    await engine.dispose()
    print(f"Granted '{ADMIN_ROLE_KEY}' to {email}.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/grant_admin.py <email>", file=sys.stderr)
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
