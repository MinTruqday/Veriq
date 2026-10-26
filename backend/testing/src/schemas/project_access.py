"""Typed project grants, owned by project authorization rather than runtime policies."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


ProjectRoleValue = Literal["BA", "QA", "TESTER", "DEVELOPER", "VIEWER"]


class ProjectCapability(BaseModel):
    name: str = Field(min_length=1)
    read_only: bool = False


class ProjectRoleGrant(BaseModel):
    role: ProjectRoleValue
    permissions: list[str]


class ProjectSettingGrant(BaseModel):
    role: ProjectRoleValue
    setting: str = Field(min_length=1)
    enabled: bool
    effect: Literal["ALLOW", "DENY"]
    permissions: list[str]


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
        return {
            "project_permissions": [item.name for item in self.capabilities],
            "read_only_permissions": [item.name for item in self.capabilities if item.read_only],
            "role_permissions": {grant.role: grant.permissions for grant in self.role_grants},
            "conditional_permissions": [grant.model_dump(exclude={"effect"}) for grant in self.setting_grants if grant.effect == "ALLOW"],
            "conditional_denials": [grant.model_dump(exclude={"effect"}) for grant in self.setting_grants if grant.effect == "DENY"],
        }
