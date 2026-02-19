# !!! Must not contain default values, neither by setting them with `= <default value` nor through a Field with `default` or `default_factory` !!!
# See https://github.com/fastapi/fastapi/discussions/13010
from pydantic import BaseModel, Field, HttpUrl, model_validator
from datetime import datetime
from enum import Enum
from typing import Annotated, Self, Mapping

from .base import EmailValidated, UserBase


class ErrorResponse(BaseModel):
    detail: str

    class Config:
        json_schema_extra = {
            "example": {"detail": "error message"},
        }


class UserTypeEnum(str, Enum):
    LOCAL = "local"
    LDAP = "ldap"
    OIDC = "oidc"

class UserResponse(UserBase):
    provider_name: str
    user_type: UserTypeEnum
    is_verified: bool


class JobResponse(BaseModel):
    id: int
    creation_timestamp: datetime
    file_name: str
    finish_timestamp: datetime | None
    runner_name: str | None = Field(max_length=40)
    runner_id: int | None
    runner_version: str | None
    runner_git_hash: str | None = Field(max_length=40)
    runner_source_code_url: str | None
    downloaded: bool | None
    error_msg: str | None

class JobModelEnum(str, Enum):
    TINY = "tiny"
    TINY_EN = "tiny.en"
    BASE = "base"
    BASE_EN = "base.en"
    SMALL = "small"
    SMALL_EN = "small.en"
    MEDIUM = "medium"
    MEDIUM_EN = "medium.en"
    TURBO = "turbo"
    LARGE = "large"

    def __str__(self) -> str:
        return self.value

class JobLangEnum(str, Enum):
    # only support ISO 639 language codes since the full names have duplicates (e.g. Catalan and Valencian or Spanish and Castilian or Dutch and Flemish) and are longer
    AFRIKAANS = "af"
    AMHARIC = "am"
    ARABIC = "ar"
    ASSAMESE = "as"
    AZERBAIJANI = "az"
    BASHKIR = "ba"
    BELARUSIAN = "be"
    BULGARIAN = "bg"
    BENGALI = "bn"
    TIBETAN = "bo"
    BRETON = "br"
    BOSNIAN = "bs"
    CATALAN = "ca"
    CZECH = "cs"
    WELSH = "cy"
    DANISH = "da"
    GERMAN = "de"
    GREEK_MODERN = "el"
    ENGLISH = "en"
    SPANISH = "es"
    ESTONIAN = "et"
    BASQUE = "eu"
    PERSIAN = "fa"
    FINNISH = "fi"
    FAROESE = "fo"  # codespell:ignore fo
    FRENCH = "fr"
    GALICIAN = "gl"
    GUJARATI = "gu"
    HAUSA = "ha"
    HAWAIIAN = "haw"
    HEBREW = "he"
    HINDI = "hi"
    CROATIAN = "hr"
    HAITIAN = "ht"
    HUNGARIAN = "hu"
    ARMENIAN = "hy"
    INDONESIAN = "id"
    ICELANDIC = "is"
    ITALIAN = "it"
    JAPANESE = "ja"
    JAVANESE = "jw"
    GEORGIAN = "ka"
    KAZAKH = "kk"
    CENTRAL_KHMER = "km"
    KANNADA = "kn"
    KOREAN = "ko"
    LATIN = "la"
    LUXEMBOURGISH = "lb"
    LINGALA = "ln"
    LAO = "lo"
    LITHUANIAN = "lt"
    LATVIAN = "lv"
    MALAGASY = "mg"
    MAORI = "mi"
    MACEDONIAN = "mk"
    MALAYALAM = "ml"
    MONGOLIAN = "mn"
    MARATHI = "mr"
    MALAY = "ms"
    MALTESE = "mt"
    BURMESE = "my"
    NEPALI = "ne"
    DUTCH = "nl"
    NORWEGIAN_NYNORSK = "nn"
    NORWEGIAN = "no"
    OCCITAN = "oc"
    PUNJABI = "pa"
    POLISH = "pl"
    PASHTO = "ps"
    PORTUGUESE = "pt"
    ROMANIAN = "ro"
    RUSSIAN = "ru"
    SANSKRIT = "sa"
    SINDHI = "sd"
    SINHALA = "si"
    SLOVAK = "sk"
    SLOVENIAN = "sl"
    SHONA = "sn"
    SOMALI = "so"
    ALBANIAN = "sq"
    SERBIAN = "sr"
    SUNDANESE = "su"
    SWEDISH = "sv"
    SWAHILI = "sw"
    TAMIL = "ta"
    TELUGU = "te"  # codespell:ignore te
    TAJIK = "tg"
    THAI = "th"
    TURKMEN = "tk"
    TAGALOG = "tl"
    TURKISH = "tr"
    TATAR = "tt"
    UKRAINIAN = "uk"
    URDU = "ur"
    UZBEK = "uz"
    VIETNAMESE = "vi"
    YIDDISH = "yi"
    Yoruba = "yo"
    CANTONESE = "yue"
    MANDARIN = "zh"

    def __str__(self) -> str:
        return self.value

class DiarizationSettings(BaseModel):
    min_speakers: int | None = Field(ge=0)
    max_speakers: int | None = Field(ge=0)

    @model_validator(mode="after")
    def max_must_be_larger_equal_than_min(self) -> Self:
        if (
            self.min_speakers is not None
            and self.max_speakers is not None
            and self.max_speakers < self.min_speakers
        ):
            raise ValueError("max_speakers can't be smaller than min_speakers")
        return self

class AlignmentProcessingSettings(BaseModel):
    highlight_words: bool
    max_line_count: int | None = Field(ge=1)
    max_line_width: int | None = Field(ge=1)

    @model_validator(mode="after")
    def max_line_count_needs_max_line_width(self) -> Self:
        if self.max_line_count is not None and self.max_line_width is None:
            raise ValueError("max_line_width can't be None if max_line_count is set")
        return self

class InterpolateMethodEnum(str, Enum):
    NEAREST = "nearest"
    LINEAR = "linear"
    IGNORE = "ignore"

    def __str__(self) -> str:
        return self.value

class AlignmentSettings(BaseModel):
    processing: AlignmentProcessingSettings
    return_char_alignments: bool
    interpolate_method: InterpolateMethodEnum

class TaskEnum(str, Enum):
    TRANSCRIBE = "transcribe"
    TRANSLATE = "translate"

    def __str__(self) -> str:
        return self.value

class VadSettings(BaseModel):
    vad_onset: float = Field(
        gt=0.0,
        lt=1.0,
    )
    vad_offset: float = Field(
        gt=0.0,
        lt=1.0,
    )
    chunk_size: int = Field(ge=1, le=30)

class AsrSettings(BaseModel):
    beam_size: int = Field(ge=1)
    patience: float = Field(gt=0.0)
    length_penalty: float = Field(
        ge=0.0,
        le=1.0,
    )
    temperature: float = Field(ge=0.0)
    temperature_increment_on_fallback: float = Field(ge=0.0)
    compression_ratio_threshold: float = Field(ge=0.0)
    log_prob_threshold: float
    no_speech_threshold: float
    initial_prompt: str | None = Field(max_length=2000)
    suppress_tokens: list[int]
    suppress_numerals: bool

supported_alignment_languages = [
    "en",
    "fr",
    "de",
    "es",
    "it",
    "ja",
    "zh",
    "nl",
    "uk",
    "pt",
    "ar",
    "cs",
    "ru",
    "pl",
    "hu",
    "fi",
    "fa",
    "el",
    "tr",
    "da",
    "he",
    "vi",
    "ko",
    "ur",
    "te",  # codespell:ignore te
    "hi",
    "ca",
    "ml",
    "no",
    "nn",
    "sk",
    "sl",
    "hr",
    "ro",
    "eu",
    "gl",
    "ka",
    "lv",
    "tl",
    "sv",
]

class JobSettingsRunnerResponse(BaseModel):
    task: TaskEnum
    model: JobModelEnum
    language: JobLangEnum | None  # None means automatic detection
    alignment: AlignmentSettings | None  # None means no alignment
    diarization: DiarizationSettings | None  # None means no diarization
    vad_settings: VadSettings
    asr_settings: AsrSettings

    @model_validator(mode="after")
    def model_language_support_validation(self) -> Self:
        if self.language != JobLangEnum.ENGLISH and self.model in (
            JobModelEnum.TINY_EN,
            JobModelEnum.BASE_EN,
            JobModelEnum.SMALL_EN,
            JobModelEnum.MEDIUM_EN,
        ):
            raise ValueError(
                "If you want to use the 'tiny.en', 'base.en', 'small.en' or 'medium.en' models, you have to set the language to 'en'"
            )
        return self

    @model_validator(mode="after")
    def no_alignment_for_translation(self) -> Self:
        if self.task == TaskEnum.TRANSLATE and self.alignment is not None:
            raise ValueError("Alignment not supported for the translation task")
        return self

    @model_validator(mode="after")
    def alignment_supported_language(self) -> Self:
        if (
            self.alignment is not None
            and self.language is not None
            and self.language not in supported_alignment_languages
        ):
            raise ValueError(
                f"language {self.language} is not supported for alignment. Either disable alignment or choose another language"
            )
        return self

    @model_validator(mode="after")
    def only_translate_non_english(self) -> Self:
        if self.task == "translate" and self.language == "en":
            raise ValueError("Cannot translate English into English")
        return self


class JobSettingsResponse(JobSettingsRunnerResponse):
    email_notification: bool


class JobAndSettingsResponse(JobResponse):
    settings: JobSettingsResponse


class InProcessJobResponse(BaseModel):
    id: int
    progress: float = Field(ge=0.0, le=100.0)
    abort: bool


class JobStatus(str, Enum):
    """
    Represents all the possible statuses that a
    job request might have.
    """
    # The job request has been received by the server,
    # but is not currently queued for processing.
    # TODO: Do we even need to support this?
    NOT_QUEUED = "not_queued"
    # The backend has received the job request but no
    # runner has been assigned yet
    PENDING_RUNNER = "pending_runner"
    # A runner has been assigned, but has not started processing
    # the request
    RUNNER_ASSIGNED = "runner_assigned"
    # A runner has been assigned, and is currently processing
    # the request
    RUNNER_IN_PROGRESS = "runner_in_progress"
    # The job is currently being aborted, i.e. the backend waits
    # for the runner to stop processing this job
    ABORTING = "aborting"
    # The runner successfully completed the job and
    # the transcript is ready for retrieval
    SUCCESS = "success"
    # There was an error during the processing of the request
    FAILED = "failed"
    # The job was successfully completed, and the transcript
    # has been downloaded by the user.
    DOWNLOADED = "downloaded"

class JobInfoResponse(JobAndSettingsResponse, InProcessJobResponse):
    step: JobStatus


class SiteBannerResponse(BaseModel):
    id: int
    html: str
    urgency: int


class ImprintResponse(BaseModel):
    name: str
    email: EmailValidated | None
    url: HttpUrl | None
    additional_imprint_html: str | None

    @model_validator(mode="after")
    def exactly_one_of_url_additional_imprint_html(self) -> Self:
        if self.url is None and self.additional_imprint_html is None:
            raise ValueError(
                "You need to define one of 'url' or 'additional_imprint_html' if you want to have an imprint"
            )
        elif self.url is not None and self.additional_imprint_html is not None:
            raise ValueError(
                "You cannot define both 'url' and 'additional_imprint_html' at the same time, these options are mutually exclusive"
            )
        return self

class TosResponse(BaseModel):
    name: str
    version: int = Field(ge=1)
    tos_html: str

class AboutResponse(BaseModel):
    description: str
    source_code: str
    version: str
    git_hash: str
    imprint: ImprintResponse | None
    terms_of_services: Mapping[int, TosResponse]
    job_retention_in_days: int | None
    site_banners: list[SiteBannerResponse]


class TokenInfoResponse(BaseModel):
    id: int
    name: str
    admin_privileges: bool
    explicit: bool
    expires_at: datetime | None
    last_usage: datetime


class RunnerCreatedResponse(BaseModel):
    id: int
    token: str


class LocalAccountOperationModeEnum(str, Enum):
    DISABLED = "disabled"
    NO_SIGNUP_HIDDEN = "no_signup_hidden"
    NO_SIGNUP = "no_signup"
    ENABLED = "enabled"

class LocalAccountResponse(BaseModel):
    mode: LocalAccountOperationModeEnum
    allowed_email_domains: list[Annotated[
        str,
        Field(
            pattern=r"^([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+$",
            examples=["uni-heidelberg.de", "stud.uni-heidelberg.de"],
        )
    ]]
    allow_creation_of_api_tokens: bool

class ProviderResponse(BaseModel):
    hidden: bool
    icon_url: HttpUrl | None
    allow_creation_of_api_tokens: bool

class AuthSettingsResponse(BaseModel):
    local_account: LocalAccountResponse
    oidc_providers: Mapping[str, ProviderResponse]
    ldap_providers: Mapping[str, ProviderResponse]


class RegisteredResponse(BaseModel):
    id: int
    session_token: str


class HeartbeatResponse(BaseModel):
    abort: bool
    job_assigned: bool


class RunnerJobInfoResponse(BaseModel):
    id: int
    settings: JobSettingsResponse
