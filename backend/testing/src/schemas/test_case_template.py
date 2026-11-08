from typing import Any

from pydantic import BaseModel, Field, field_validator


TemplateType = str


class TestCaseTemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=300)
    template_type: TemplateType = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=5000)
    definition: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("template_type")
    @classmethod
    def normalize_template_type(cls, value):
        normalized = value.strip()
        if not normalized:
            raise ValueError("Template type must not be empty")
        return normalized


class TestCaseTemplatePatch(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=300)
    template_type: TemplateType | None = None
    description: str | None = Field(default=None, max_length=5000)
    definition: dict[str, Any] | None = None
    tags: list[str] | None = Field(default=None, max_length=100)

    @field_validator("template_type")
    @classmethod
    def normalize_template_type(cls, value):
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Template type must not be empty")
        return normalized


class TestCaseTemplateArchive(BaseModel):
    expected_revision: int = Field(ge=1)
    reason: str = Field(min_length=2, max_length=2000)
