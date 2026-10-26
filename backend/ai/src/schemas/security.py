from pydantic import BaseModel, ConfigDict, Field


class SecurityOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SecurityEvaluation(SecurityOutput):
    is_malicious: bool
    has_pii: bool
    has_credentials: bool
    sanitized_text: str = Field(
        max_length=200000,
    )
    reason: str = Field(max_length=2000)


class JailbreakCheck(SecurityOutput):
    is_jailbreak: bool
