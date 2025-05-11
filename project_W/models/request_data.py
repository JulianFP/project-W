from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, SecretStr, model_validator

from .base import EmailValidated, PasswordValidated


class SignupData(BaseModel):
    email: EmailValidated
    password: PasswordValidated


class PasswordResetData(BaseModel):
    token: SecretStr
    new_password: PasswordValidated


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
    FAROESE = "fo"
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
    TELUGU = "te"
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


class JobSettings(BaseModel):
    model: JobModelEnum = JobModelEnum.LARGE
    language: JobLangEnum | None = None  # None means automatic detection

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


class RunnerRegisterRequest(BaseModel):
    name: str = Field(max_length=40)
    version: str
    git_hash: str = Field(max_length=40)
    source_code_url: str
    priority: int


class Transcript(BaseModel):
    as_txt: str
    as_srt: str
    as_tsv: str
    as_vtt: str
    as_json: dict


class TranscriptTypeEnum(str, Enum):
    TXT = "as_txt"
    SRT = "as_srt"
    TSV = "as_tsv"
    VTT = "as_vtt"
    JSON = "as_json"


class RunnerSubmitResultRequest(BaseModel):
    error_msg: str | None = None
    transcript: Transcript | None = None

    @model_validator(mode="after")
    def either_error_or_transcript(self) -> Self:
        if self.error_msg is None and self.transcript is None:
            raise ValueError("Either `error_msg` or `transcript` must be set for job submission")
        return self


class HeartbeatRequest(BaseModel):
    progress: float
