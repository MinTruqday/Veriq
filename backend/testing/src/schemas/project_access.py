"""Typed project grants, owned by project authorization rather than runtime policies."""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ProjectRoleId = str


def canonical_permission(value):
    return str(value or "").strip()


def _normalize_role(value):
    return str(value or "").strip().upper()


class ProjectCapability(BaseModel):
    name: str = Field(min_length=1)
    read_only: bool = False
    responsibility: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("responsibility")
    @classmethod
    def validate_responsibility(cls, value):
        if value is not None and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", value):
            raise ValueError("PROJECT_RESPONSIBILITY_INVALID")
        return value


class ProjectRoleGrant(BaseModel):
    role: ProjectRoleId = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")
    permissions: list[str]

    @field_validator("role")
    @classmethod
    def normalize_role(cls, value):
        return _normalize_role(value)


class ProjectSettingGrant(BaseModel):
    role: ProjectRoleId = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")
    setting: str = Field(min_length=1)
    enabled: bool
    effect: Literal["ALLOW", "DENY"]
    permissions: list[str]

    @field_validator("role")
    @classmethod
    def normalize_role(cls, value):
        return _normalize_role(value)


class ProjectAccessControl(BaseModel):
    schema_version: Literal[1] = 1
    revision: int = Field(default=1, ge=1)
    capabilities: list[ProjectCapability]
    role_grants: list[ProjectRoleGrant]
    setting_grants: list[ProjectSettingGrant] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self):
        names = [item.name for item in self.capabilities]
        if len(names) != len(set(names)):
            raise ValueError("DUPLICATE_PROJECT_CAPABILITY")
        roles = [item.role for item in self.role_grants]
        if len(roles) != len(set(roles)):
            raise ValueError("DUPLICATE_PROJECT_ROLE_GRANT")
        role_names = set(roles)
        if any(
            grant.role not in role_names
            for grant in self.setting_grants
        ):
            raise ValueError("UNKNOWN_PROJECT_SETTING_ROLE")
        known = set(names)
        for grant in [*self.role_grants, *self.setting_grants]:
            if not set(grant.permissions) <= known:
                raise ValueError("UNKNOWN_PROJECT_CAPABILITY")
        return self

    @classmethod
    def from_legacy(cls, values):
        known_fields = {"project_permissions", "read_only_permissions", "role_permissions", "policy_permissions", "conditional_permissions", "conditional_denials", "comment_collaborator_permissions", "collaborator_permissions"}
        if set(values) - known_fields:
            raise ValueError("UNRECOGNIZED_LEGACY_ACCESS_FIELDS")
        read_only = set(values.get("read_only_permissions", []))
        rules = [
            ProjectSettingGrant(role=rule["role"], setting=key, enabled=True, effect="ALLOW", permissions=rule["permissions"])
            for key, rule in values.get("policy_permissions", {}).items()
        ]
        for field, effect in (("conditional_permissions", "ALLOW"), ("conditional_denials", "DENY")):
            rules.extend(ProjectSettingGrant(**rule, effect=effect) for rule in values.get(field, []))
        return cls(
            capabilities=[ProjectCapability(name=name, read_only=name in read_only) for name in sorted(set(values["project_permissions"]))],
            role_grants=[ProjectRoleGrant(role=role, permissions=permissions) for role, permissions in values["role_permissions"].items()],
            setting_grants=rules,
        )

    def permission_values(self):
        """Compatibility interface for callers; database authority is the typed model."""
        capabilities = {canonical_permission(item.name): item for item in self.capabilities}
        role_permissions = {
            grant.role: sorted({canonical_permission(item) for item in grant.permissions})
            for grant in self.role_grants
        }
        setting_grants = [
            (
                grant.effect,
                {
                    **grant.model_dump(exclude={"effect"}),
                    "permissions": sorted({canonical_permission(item) for item in grant.permissions}),
                },
            )
            for grant in self.setting_grants
        ]
        return {
            "revision": self.revision,
            "project_permissions": sorted(capabilities),
            "responsibility_permissions": {
                name: item.responsibility for name, item in capabilities.items() if item.responsibility
            },
            "read_only_permissions": sorted(
                name for name, item in capabilities.items() if item.read_only
            ),
            "role_permissions": role_permissions,
            "conditional_permissions": [item for effect, item in setting_grants if effect == "ALLOW"],
            "conditional_denials": [item for effect, item in setting_grants if effect == "DENY"],
        }
