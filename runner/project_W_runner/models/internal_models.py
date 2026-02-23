from httpx import HTTPError, Response
from pydantic import BaseModel, Field, ValidationError
from project_W_lib.models.response_models import JobSettingsResponse, ErrorResponse
from project_W_lib.models.request_models import Transcript


class ResponseNotJson(Exception):
    """
    This gets raised if backend response with non-json response even though json was expected
    """

    pass


class BackendError(HTTPError):
    """
    This gets raised instead of httpx's exception to include the detail field that the backend may return
    """

    status_code: int

    def __init__(self, response: Response) -> None:
        self.status_code = response.status_code
        error_message = f"Backend responded with {response.status_code}, "
        if response.headers.get("Content-Type") == "application/json":
            json_response = response.json()
            try:
                error_response = ErrorResponse.model_validate(json_response)
                error_message += error_response.detail
            except ValidationError:
                error_message += str(json_response)
        else:
            error_message += response.text
        super().__init__(error_message)


class ShutdownSignal(Exception):
    """
    Exception that is raised when the runner should shut down.
    This could be either because a graceful shutdown was requested
    or because of an error, e.g. if a server request times out.
    """

    reason: str

    def __init__(self, reason: str, e: Exception | None = None):
        if e is None:
            self.reason = reason
        else:
            self.reason = f"{reason}: {type(e).__name__}: '{str(e)}'"


class JobData(BaseModel):
    id: int | None = None
    error_msg: str | None = None
    transcript: Transcript | None = None
    progress: float | None = Field(
        ge=0.0,
        le=100.0,
        default=None,
    )
    settings: JobSettingsResponse | None = None
