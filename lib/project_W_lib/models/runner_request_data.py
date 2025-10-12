from typing import Self

from pydantic import BaseModel, Field, model_validator


class RunnerRegisterRequest(BaseModel):
    name: str = Field(max_length=40)
    version: str
    git_hash: str = Field(max_length=40)
    source_code_url: str
    priority: int = Field(gt=0)


class Transcript(BaseModel):
    as_txt: str
    as_srt: str
    as_tsv: str
    as_vtt: str
    as_json: dict


class RunnerSubmitResultRequest(BaseModel):
    error_msg: str | None = None
    transcript: Transcript | None = None

    @model_validator(mode="after")
    def either_error_or_transcript(self) -> Self:
        if self.error_msg is None and self.transcript is None:
            raise ValueError(
                "Either `error_msg` or `transcript` must be set for job submission"
            )
        return self


class HeartbeatRequest(BaseModel):
    progress: float = Field(
        ge=0.0,
        le=100.0,
        default=0.0,
    )
