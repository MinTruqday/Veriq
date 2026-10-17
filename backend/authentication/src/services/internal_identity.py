from fastapi import HTTPException

from src.repositories.identity import IdentityRepository
from src.services.platform import account_view


class InternalIdentityService:
    @staticmethod
    async def lookup_accounts(user_ids: list[str]):
        identifiers = sorted(set(user_ids))
        accounts = await IdentityRepository.find_auth_credentials(
            {"_id": {"$in": identifiers}},
            {"email": 1, "full_name": 1, "slug": 1},
            len(identifiers),
        )
        return {
            str(account["_id"]): {
                "user_id": str(account["_id"]),
                "email": account.get("email"),
                "full_name": account.get("full_name"),
                "slug": account.get("slug"),
                "label": account.get("full_name")
                or account.get("email")
                or account.get("slug"),
            }
            for account in accounts
        }

    @staticmethod
    async def resolve_reference(value: str):
        reference = value.strip()
        query = {"email": reference.lower()} if "@" in reference else {"_id": reference}
        account = await IdentityRepository.find_auth_credential(query, {"_id": 1})
        if not account:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
        return {"user_id": str(account["_id"])}

    @staticmethod
    async def validate_session(session_id: str, user_id: str):
        account = await IdentityRepository.find_auth_credential(
            {"_id": user_id}, {"is_active": 1, "account_status": 1}
        )
        session = await IdentityRepository.get_session(
            user_id, session_id, {"_id": 1, "revoked_at": 1}
        )
        valid = bool(
            account
            and account.get("is_active", True) is not False
            and session
            and session.get("revoked_at") is None
            and await IdentityRepository.has_cached_session(user_id, session_id)
        )
        return {"valid": valid}

    @staticmethod
    async def project_creation_policy():
        config = await IdentityRepository.get_system_config_by_type(
            "project_creation", {"project_creation_policy": 1}
        )
        return {
            "project_creation_policy": (config or {}).get(
                "project_creation_policy", "AUTHENTICATED"
            )
        }

    @staticmethod
    async def account_by_id(user_id: str):
        return await InternalIdentityService._account({"_id": user_id})

    @staticmethod
    async def account_by_email(email: str):
        return await InternalIdentityService._account({"email": email.lower()})

    @staticmethod
    async def security_state(user_id: str):
        credential = await IdentityRepository.find_auth_credential(
            {"_id": user_id}, {"last_password_change": 1}
        )
        if not credential:
            raise HTTPException(
                status_code=404, detail="Không tìm thấy thông tin bảo mật"
            )
        return {"last_password_change": credential.get("last_password_change")}

    @staticmethod
    async def _account(query: dict):
        credential = await IdentityRepository.find_auth_credential(query)
        if not credential:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
        return account_view(credential)
