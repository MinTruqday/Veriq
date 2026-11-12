import base64
import binascii
import hmac
import json
from datetime import datetime, timezone

from fastapi import HTTPException
from loguru import logger
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.exceptions import InvalidAuthenticationResponse, InvalidRegistrationResponse
from webauthn.helpers.structs import (
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialType,
    UserVerificationRequirement,
)

from src.core.infrastructure.configuration import settings
from src.repositories.identity import IdentityRepository as AuthenticationRepository

RP_ID = settings.PASSKEY_RP_ID
RP_NAME = settings.PASSKEY_RP_NAME
ORIGINS = [item.strip() for item in settings.PASSKEY_ALLOWED_ORIGINS.split(",") if item.strip()]
EXPECTED_ORIGIN = ORIGINS if len(ORIGINS) > 1 else ORIGINS[0]


class PasskeyService:
    @staticmethod
    async def login_begin(email: str):
        user = await AuthenticationRepository.get_auth_credential_by_email(email)
        if not user:
            raise HTTPException(
                status_code=404, detail="Không tìm thấy thông tin tài khoản người dùng"
            )
        passkeys = user.get("passkeys", [])
        if not passkeys:
            raise HTTPException(status_code=400, detail="Tài khoản này chưa thiết lập Passkey")
        options = generate_authentication_options(
            rp_id=RP_ID,
            allow_credentials=[
                PublicKeyCredentialDescriptor(
                    id=base64.b64decode(p["credential_id"]),
                    type=PublicKeyCredentialType.PUBLIC_KEY,
                    transports=p.get("transports"),
                )
                for p in passkeys
            ],
            user_verification=UserVerificationRequirement.PREFERRED,
        )
        try:
            await AuthenticationRepository.set_redis_passkey_challenge(email, options.challenge)
        except Exception:
            logger.exception("Failed to persist temporary authentication challenge to cache layer")
        await AuthenticationRepository.upsert_passkey_challenge(email, options.challenge)
        return json.loads(options_to_json(options))

    @staticmethod
    async def login_finish(email: str, credential_data: dict):
        user = await AuthenticationRepository.get_auth_credential_by_email(email)
        if not user:
            raise HTTPException(
                status_code=404, detail="Không tìm thấy thông tin tài khoản người dùng"
            )
        challenge = await AuthenticationRepository.consume_passkey_challenge(email)
        if not challenge:
            raise HTTPException(
                status_code=400, detail="Mã xác minh bảo mật không hợp lệ hoặc đã quá hạn sử dụng"
            )
        credential_id_b64 = credential_data.get("id")
        if not isinstance(credential_id_b64, str) or not credential_id_b64:
            raise HTTPException(status_code=400, detail="Passkey không hợp lệ")
        try:
            credential_id = base64.urlsafe_b64decode(
                credential_id_b64 + "=" * (-len(credential_id_b64) % 4)
            )
        except (ValueError, binascii.Error):
            raise HTTPException(status_code=400, detail="Passkey không hợp lệ")
        passkey = next(
            (
                p
                for p in user.get("passkeys", [])
                if hmac.compare_digest(base64.b64decode(p["credential_id"]), credential_id)
            ),
            None,
        )
        if not passkey:
            raise HTTPException(
                status_code=400, detail="Thông tin mã bảo mật cung cấp không chính xác"
            )
        try:
            verification = verify_authentication_response(
                credential=credential_data,
                expected_challenge=challenge,
                expected_origin=EXPECTED_ORIGIN,
                expected_rp_id=RP_ID,
                credential_public_key=base64.b64decode(passkey["public_key"]),
                credential_current_sign_count=passkey["sign_count"],
            )
        except InvalidAuthenticationResponse:
            raise HTTPException(
                status_code=400, detail="Quá trình xác minh dữ liệu mã bảo mật gặp sự cố"
            )
        await AuthenticationRepository.update_passkey_sign_count(
            user["_id"], credential_id_b64, verification.new_sign_count
        )
        from src.services.session import SessionService

        return await SessionService.issue_token_for_user(user, "passkey_login")

    @staticmethod
    async def register_begin(email: str):
        user = await AuthenticationRepository.get_auth_credential_by_email(email)
        if not user:
            raise HTTPException(
                status_code=404, detail="Không tìm thấy thông tin tài khoản người dùng"
            )

        passkeys = user.get("passkeys", [])

        options = generate_registration_options(
            rp_id=RP_ID,
            rp_name=RP_NAME,
            user_id=str(user["_id"]).encode("utf-8"),
            user_name=email,
            user_display_name=email,
            exclude_credentials=[
                PublicKeyCredentialDescriptor(
                    id=base64.b64decode(p["credential_id"]), type=PublicKeyCredentialType.PUBLIC_KEY
                )
                for p in passkeys
            ],
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
        )

        try:
            await AuthenticationRepository.set_redis_passkey_challenge(email, options.challenge)
        except Exception:
            logger.exception("Failed to persist temporary authentication challenge to cache layer")

        await AuthenticationRepository.upsert_passkey_challenge(email, options.challenge)

        return json.loads(options_to_json(options))

    @staticmethod
    async def register_finish(email: str, credential_data: dict):
        user = await AuthenticationRepository.get_auth_credential_by_email(email)
        if not user:
            raise HTTPException(
                status_code=404, detail="Không tìm thấy thông tin tài khoản người dùng"
            )

        challenge = await AuthenticationRepository.consume_passkey_challenge(email)

        if not challenge:
            raise HTTPException(
                status_code=400, detail="Mã xác minh bảo mật không hợp lệ hoặc đã quá hạn sử dụng"
            )

        try:
            verification = verify_registration_response(
                credential=credential_data,
                expected_challenge=challenge,
                expected_origin=EXPECTED_ORIGIN,
                expected_rp_id=RP_ID,
            )
        except InvalidRegistrationResponse:
            raise HTTPException(
                status_code=400, detail="Quá trình xác minh dữ liệu mã bảo mật gặp sự cố"
            )

        new_passkey = {
            "credential_id": base64.b64encode(verification.credential_id).decode("utf-8"),
            "public_key": base64.b64encode(verification.credential_public_key).decode("utf-8"),
            "sign_count": verification.sign_count,
            "created_at": datetime.now(timezone.utc),
        }

        result = await AuthenticationRepository.add_passkey(user["_id"], new_passkey)
        if result.modified_count == 0:
            raise HTTPException(status_code=409, detail="Mã bảo mật đã được đăng ký")

        return {"message": "Thực hiện đăng ký mã bảo mật hoàn tất"}
