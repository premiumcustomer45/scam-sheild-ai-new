from typing import Literal

from pydantic import BaseModel, Field, field_validator


Verdict = Literal["lower-risk", "suspicious", "high-risk", "uncertain"]
Severity = Literal["safe", "info", "warning", "high"]


class UrlInput(BaseModel):
    url: str = Field(min_length=1, max_length=2048)

    @field_validator("url")
    @classmethod
    def strip_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Enter a URL to scan.")
        return value


class TextInput(BaseModel):
    text: str = Field(min_length=1, max_length=20000)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Enter a message to scan.")
        return value


class Indicator(BaseModel):
    code: str
    title: str
    detail: str
    severity: Severity


class UrlAssessment(BaseModel):
    url: str
    verdict: Verdict
    riskScore: int = Field(ge=0, le=100)
    indicators: list[Indicator]


class Prediction(BaseModel):
    verdict: Verdict
    riskScore: int = Field(ge=0, le=100)
    model_probability: float | None = None
    indicators: list[Indicator]
    recommendations: list[str]
    model_version: str
    limitations: list[str]
    urls: list[UrlAssessment] = Field(default_factory=list)
