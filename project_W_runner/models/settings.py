from enum import Enum

from platformdirs import user_cache_path
from pydantic import (
    BaseModel,
    ConfigDict,
    DirectoryPath,
    Field,
    FilePath,
    HttpUrl,
    SecretStr,
)

program_name = "project-W-runner"


class ComputeTypeEnum(str, Enum):
    FLOAT16 = "float16"
    FLOAT32 = "float32"
    INT8 = "int8"


class ModelPrefetchingEnum(str, Enum):
    NONE = "none"
    WITHOUT_ALIGNMENT_AND_DIARIZATION = "without_alignment_and_diarization"
    WITHOUT_ALIGNMENT = "without_alignment"
    ALL = "all"


class WhisperSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_cache_dir: DirectoryPath = Field(
        default=user_cache_path(appname=program_name, ensure_exists=True),
        description="The directory in which whisperx should download/read models from",
        validate_default=True,
    )
    model_prefetching: ModelPrefetchingEnum = Field(
        default=ModelPrefetchingEnum.ALL,
        description="Which models to prefetch before connecting to the backend. Can be set to 'all' (default), 'without_alignment' (prefetches everything but alignment models), 'without_alignment_and_diarization' (only prefetches whisper and vad models), and 'none' (doesn't prefetch any models). It is recommended to leave this to 'all' in production since otherwise users might have to wait for the runner to fetch models first (which could very well fail, especially for the diarization model)",
        validate_default=True,
    )
    hf_token: SecretStr = Field(
        description="Hugging Face token required to download pyannote models for diarization. To get a token please create a Hugging Face account, accept the conditions for the pyannote/segmentation-3.0 and pyannote/speaker-diarization-3.1 models and create a token with the permissions to access content of public gated repos",
    )
    torch_device: str = Field(
        default="cuda",
        description="On which torch device whisperx should run",
        validate_default=True,
    )
    compute_type: ComputeTypeEnum = Field(
        default=ComputeTypeEnum.FLOAT16,
        description="The compute type used by the whisper model. One of 'float16', 'float32', 'int8'. Set this to int8 if you want to run whisper on CPU",
        validate_default=True,
    )
    batch_size: int = Field(
        default=16,
        ge=2,
        description="Batch size for inference with Whisper model. Set this to a smaller value (e.g. to 4) if you want to run whisper on CPU",
        validate_default=True,
    )


class BackendSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: HttpUrl = Field(
        description="The Url used to connect to the backend",
    )
    ca_pem_file_path: FilePath | None = Field(
        default=None,
        description="Path to the pem certs file that includes the certificates that should be trusted for the backend (alternative certificate verification). Useful if the backend uses a self-signed certificate",
    )
    auth_token: SecretStr = Field(
        description="The token of this runner that is used to authenticate to the backend. The backend also uses this token to identify the runner which means that each runner needs to have their own unique token",
    )


class RunnerAttributes(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(
        max_length=40,
        description="A unique string identifier. This name is displayed to users for transparency reasons so that they have some idea where their data is going and so that it is easier to identify runners. Ideally the name should contain the location/organization where the runner is hosted",
        examples=[
            "university runner 1",
            "working group runner 3",
            "cloud cluster runner 12",
        ],
    )
    priority: int = Field(
        gt=0,
        default=100,
        description="The priority in the job assignment process. If both runner A and B are free and runner A has a higher priority than runner B it means that any given job will always be assigned to runner A first. Furthermore the runner priority should be a relative measure for the runners hardware capability, e.g. if runner A has double the priority as runner B it should be roughly twice as powerful",
    )


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    runner_attributes: RunnerAttributes = Field(description="General attributes of this runner")
    backend_settings: BackendSettings = Field(description="How to connect to the Project-W Backend")
    whisper_settings: WhisperSettings = Field(
        description="Settings related to performing the actual transcription and running the whisper and other ML models",
    )
