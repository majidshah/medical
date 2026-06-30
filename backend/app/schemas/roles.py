import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class RoleResponse(BaseModel):
    id: uuid.UUID
    key: str
    name: str

    model_config = {"from_attributes": True}


class GrantRoleRequest(BaseModel):
    email: EmailStr
    role_key: str


class AccountRoleResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    role_id: uuid.UUID
    granted_by_account_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
