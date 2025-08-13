import re
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Self

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, Field, HttpUrl, RootModel, SecretStr, model_validator


class EmailValidated(RootModel):
    root: str

    @model_validator(mode="before")
    @classmethod
    def email_validation(cls, data: Any) -> Any:
        if isinstance(data, str):
            try:
                val_email = validate_email(data, check_deliverability=False)
                cls.__original = val_email.original
                cls.__domain = val_email.domain
                cls.__local_part = val_email.local_part
                return val_email.normalized
            except EmailNotValidError as e:
                raise ValueError(e)

    def get_domain(self) -> str:
        return self.__domain

    def get_original(self) -> str:
        return self.__original

    def get_local_part(self) -> str:
        return self.__local_part


class PasswordValidated(RootModel):
    root: SecretStr

    @model_validator(mode="after")
    def password_validation(self) -> Self:
        match = re.match(
            r"^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[^a-zA-Z0-9]).{12,}$",
            self.root.get_secret_value(),
        )
        if match is None:
            raise ValueError(
                "The password needs to have at least one lowercase letter, uppercase letter, number, special character and at least 12 characters in total"
            )
        return self


class UserInDb(BaseModel):
    id: int
    email: EmailValidated


class AdditionalUserInfo(BaseModel):
    accepted_tos: dict[int, int]


class JobBase(BaseModel):
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


class InProcessJobBase(BaseModel):
    id: int
    progress: float = Field(ge=0.0, le=100.0, default=0.0)
    abort: bool = False


class LocalAccountOperationModeEnum(str, Enum):
    DISABLED = "disabled"
    NO_SIGNUP_HIDDEN = "no-signup_hidden"
    NO_SIGNUP = "no-signup"
    ENABLED = "enabled"


class LocalAccountSettingsBase(BaseModel):
    mode: LocalAccountOperationModeEnum = Field(
        default=LocalAccountOperationModeEnum.ENABLED,
        description="""
        To what extend local accounts should be enabled.
        - enabled: Both login and signup possible and advertised in frontend to users (default).
        - no_signup: Login possible and advertised to users, signup not. Thus users can only login using already existing accounts (created through provisioning or by signup before this setting was set). Use this for example if you want users to login using local accounts that you created for them through provisioning.
        - no_signup_hidden: Login still possible but not advertised to users in the frontend. Especially helpful if the only local accounts should be provisioned admin accounts for administration purposes while normal users should only login using oidc or ldap accounts.
        - disabled: no login, no signup, no provisioned accounts. Login only through ldap and oidc. Please note that in this case you need to provide admin accounts through ldap or oidc as well!
        """,
        validate_default=True,
    )
    allowed_email_domains: list[
        Annotated[
            str,
            Field(
                pattern=r"^([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+$",
                examples=["uni-heidelberg.de", "stud.uni-heidelberg.de"],
                description="Allowed domains in email addresses. Users will only be able to sign up/change their email of their local accounts if their email address uses one of these domains (the part after the '@'). If left empty, then all email domains are allowed.",
            ),
        ]
    ] = []
    allow_creation_of_api_tokens: bool = Field(
        default=True,
        description="If set to true then users logged in with local accounts can create api tokens with infinite lifetime. They will get invalidated if the user gets deleted.",
    )


class ProviderSettingsBase(BaseModel):
    hidden: bool = Field(
        default=False,
        description="Whether this provider should not be advertised to the user on the frontend. Useful if this provider should only provide admin accounts.",
        validate_default=True,
    )
    icon_url: HttpUrl | None = Field(
        default=None,
        description="URL to a square icon that will be shown to the user in the frontend next to the 'Login with <name>' to visually represent the account/identity provider. Should be a link to a square png with transparent background, or alternatively to a svg",
        examples=[
            "https://ssl.gstatic.com/images/branding/googleg/2x/googleg_standard_color_64dp.png"
        ],
    )
    allow_creation_of_api_tokens: bool = Field(
        default=True,
        description="If set to true then users logged in from this identity provider can create api tokens with infinite lifetime. These tokens will be automatically invalidated if the user gets deleted from the identity provider ones the periodic background job gets called. Run the periodic background task more often to get user access revoked quicker.",
    )


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
    min_speakers: int | None = Field(
        default=None,
        ge=0,
    )
    max_speakers: int | None = Field(
        default=None,
        ge=0,
    )

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
    highlight_words: bool = False
    max_line_count: int | None = Field(
        default=None,
        ge=1,
    )
    max_line_width: int | None = Field(default=None, ge=1)

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
    processing: AlignmentProcessingSettings = AlignmentProcessingSettings()
    return_char_alignments: bool = False
    interpolate_method: InterpolateMethodEnum = InterpolateMethodEnum.NEAREST


class TaskEnum(str, Enum):
    TRANSCRIBE = "transcribe"
    TRANSLATE = "translate"

    def __str__(self) -> str:
        return self.value


class VadSettings(BaseModel):
    vad_onset: float = Field(
        gt=0.0,
        lt=1.0,
        default=0.5,
    )
    vad_offset: float = Field(
        ge=0.0,
        le=1.0,
        default=0.363,
    )
    chunk_size: int = Field(ge=1, le=30, default=30)


class AsrSettings(BaseModel):
    beam_size: int = Field(
        ge=1,
        default=5,
    )
    patience: float = Field(
        gt=0.0,
        default=1.0,
    )
    length_penalty: float = Field(
        ge=0.0,
        le=1.0,
        default=1.0,
    )
    temperature: float = Field(
        ge=0.0,
        default=0.0,
    )
    temperature_increment_on_fallback: float = Field(
        ge=0.0,
        default=0.2,
    )
    compression_ratio_threshold: float = Field(
        ge=0.0,
        default=2.4,
    )
    log_prob_threshold: float = -1.0
    no_speech_threshold: float = 0.6
    initial_prompt: str | None = Field(
        default=None,
        max_length=2000,
    )
    suppress_tokens: list[int] = [-1]
    suppress_numerals: bool = False


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
]


class JobSettingsBase(BaseModel):
    task: TaskEnum = TaskEnum.TRANSCRIBE
    model: JobModelEnum = JobModelEnum.LARGE
    language: JobLangEnum | None = None  # None means automatic detection
    alignment: AlignmentSettings | None = AlignmentSettings()  # None means no alignment
    diarization: DiarizationSettings | None = None  # None means no diarization
    vad_settings: VadSettings = VadSettings()
    asr_settings: AsrSettings = AsrSettings()

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
