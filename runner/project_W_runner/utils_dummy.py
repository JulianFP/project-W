import os
import time
from io import StringIO
from typing import Callable
from project_W_lib.models.job_settings import JobSettingsBase

from .models.settings import WhisperSettings


def transcribe(
    audio_file: str,
    job_settings: JobSettingsBase,
    whisper_settings: WhisperSettings,
    progress_callback: Callable[[float], None],
) -> dict[str, StringIO]:
    # do some sanity checking (since this is mainly for the CI and we want to catch as many errors as possible)
    if not os.path.exists(audio_file):
        raise Exception("dummy transcribe checks: The provided audio file path doesn't exist")
    if os.path.getsize(audio_file) == 0:
        raise Exception("dummy transcribe checks: The provided audio file is empty")

    # check pydantic models
    JobSettingsBase.model_validate(job_settings.model_dump())
    WhisperSettings.model_validate(whisper_settings.model_dump())

    # simulate progress callback
    job_duration = 3  # job takes 3 seconds
    progress_step_size = 100.0 / job_duration
    for i in range(job_duration):
        progress_callback(progress_step_size * i)
        time.sleep(1)

    # return dummy transcripts
    return_obj = {
        "txt": StringIO(),
        "srt": StringIO(),
        "tsv": StringIO(),
        "vtt": StringIO(),
        "json": StringIO(),
    }
    return_obj["txt"].write(
        """Space, the final frontier.
These are the voyages of the starship Enterprise.
Its five-year mission, to explore strange new worlds, to seek out new life and new civilizations, to boldly go where no man has gone before."""
    )
    return_obj["srt"].write(
        """1
00:00:06,089 --> 00:00:14,663
Space, the final frontier.

2
00:00:14,683 --> 00:00:17,588
These are the voyages of the starship Enterprise.

3
00:00:18,910 --> 00:00:29,447
Its five-year mission, to explore strange new worlds, to seek out new life and new civilizations, to boldly go where no man has gone before."""
    )
    return_obj["tsv"].write(
        """start	end	text
6089	14663	Space, the final frontier.
14683	17588	These are the voyages of the starship Enterprise.
18910	29447	Its five-year mission, to explore strange new worlds, to seek out new life and new civilizations, to boldly go where no man has gone before."""
    )
    return_obj["vtt"].write(
        """WEBVTT

00:06.089 --> 00:14.663
Space, the final frontier.

00:14.683 --> 00:17.588
These are the voyages of the starship Enterprise.

00:18.910 --> 00:29.447
Its five-year mission, to explore strange new worlds, to seek out new life and new civilizations, to boldly go where no man has gone before."""
    )
    return_obj["json"].write(
        """{"language":"en","segments":[{"end":14.663,"text":" Space, the final frontier.","start":6.089,"words":[{"end":6.59,"word":"Space,","score":0.94,"start":6.089},{"end":7.311,"word":"the","score":0.462,"start":7.231},{"end":7.672,"word":"final","score":0.916,"start":7.351},{"end":14.663,"word":"frontier.","score":0.885,"start":7.752}]},{"end":17.588,"text":"These are the voyages of the starship Enterprise.","start":14.683,"words":[{"end":14.963,"word":"These","score":0.71,"start":14.683},{"end":15.124,"word":"are","score":0.965,"start":15.044},{"end":15.224,"word":"the","score":0.999,"start":15.164},{"end":15.705,"word":"voyages","score":0.842,"start":15.264},{"end":15.805,"word":"of","score":0.834,"start":15.765},{"end":15.925,"word":"the","score":0.829,"start":15.845},{"end":16.526,"word":"starship","score":0.862,"start":15.965},{"end":17.588,"word":"Enterprise.","score":0.923,"start":16.947}]},{"end":29.447,"text":"Its five-year mission, to explore strange new worlds, to seek out new life and new civilizations, to boldly go where no man has gone before.","start":18.91,"words":[{"end":19.01,"word":"Its","score":0.416,"start":18.91},{"end":19.491,"word":"five-year","score":0.424,"start":19.07},{"end":19.791,"word":"mission,","score":0.985,"start":19.511},{"end":20.432,"word":"to","score":0.958,"start":20.312},{"end":20.993,"word":"explore","score":0.817,"start":20.492},{"end":21.534,"word":"strange","score":0.825,"start":21.013},{"end":21.734,"word":"new","score":0.914,"start":21.594},{"end":22.195,"word":"worlds,","score":0.584,"start":21.775},{"end":22.956,"word":"to","score":0.845,"start":22.796},{"end":23.157,"word":"seek","score":0.889,"start":22.976},{"end":23.377,"word":"out","score":0.715,"start":23.237},{"end":23.638,"word":"new","score":0.602,"start":23.437},{"end":23.918,"word":"life","score":0.82,"start":23.678},{"end":24.299,"word":"and","score":0.731,"start":24.219},{"end":24.499,"word":"new","score":0.741,"start":24.339},{"end":25.34,"word":"civilizations,","score":0.845,"start":24.539},{"end":26.803,"word":"to","score":0.871,"start":26.622},{"end":27.263,"word":"boldly","score":0.939,"start":26.823},{"end":27.544,"word":"go","score":0.992,"start":27.324},{"end":27.764,"word":"where","score":0.939,"start":27.604},{"end":28.025,"word":"no","score":0.898,"start":27.844},{"end":28.305,"word":"man","score":0.835,"start":28.085},{"end":28.485,"word":"has","score":0.989,"start":28.365},{"end":28.746,"word":"gone","score":0.892,"start":28.546},{"end":29.447,"word":"before.","score":0.86,"start":28.806}]}],"word_segments":[{"end":6.59,"word":"Space,","score":0.94,"start":6.089},{"end":7.311,"word":"the","score":0.462,"start":7.231},{"end":7.672,"word":"final","score":0.916,"start":7.351},{"end":14.663,"word":"frontier.","score":0.885,"start":7.752},{"end":14.963,"word":"These","score":0.71,"start":14.683},{"end":15.124,"word":"are","score":0.965,"start":15.044},{"end":15.224,"word":"the","score":0.999,"start":15.164},{"end":15.705,"word":"voyages","score":0.842,"start":15.264},{"end":15.805,"word":"of","score":0.834,"start":15.765},{"end":15.925,"word":"the","score":0.829,"start":15.845},{"end":16.526,"word":"starship","score":0.862,"start":15.965},{"end":17.588,"word":"Enterprise.","score":0.923,"start":16.947},{"end":19.01,"word":"Its","score":0.416,"start":18.91},{"end":19.491,"word":"five-year","score":0.424,"start":19.07},{"end":19.791,"word":"mission,","score":0.985,"start":19.511},{"end":20.432,"word":"to","score":0.958,"start":20.312},{"end":20.993,"word":"explore","score":0.817,"start":20.492},{"end":21.534,"word":"strange","score":0.825,"start":21.013},{"end":21.734,"word":"new","score":0.914,"start":21.594},{"end":22.195,"word":"worlds,","score":0.584,"start":21.775},{"end":22.956,"word":"to","score":0.845,"start":22.796},{"end":23.157,"word":"seek","score":0.889,"start":22.976},{"end":23.377,"word":"out","score":0.715,"start":23.237},{"end":23.638,"word":"new","score":0.602,"start":23.437},{"end":23.918,"word":"life","score":0.82,"start":23.678},{"end":24.299,"word":"and","score":0.731,"start":24.219},{"end":24.499,"word":"new","score":0.741,"start":24.339},{"end":25.34,"word":"civilizations,","score":0.845,"start":24.539},{"end":26.803,"word":"to","score":0.871,"start":26.622},{"end":27.263,"word":"boldly","score":0.939,"start":26.823},{"end":27.544,"word":"go","score":0.992,"start":27.324},{"end":27.764,"word":"where","score":0.939,"start":27.604},{"end":28.025,"word":"no","score":0.898,"start":27.844},{"end":28.305,"word":"man","score":0.835,"start":28.085},{"end":28.485,"word":"has","score":0.989,"start":28.365},{"end":28.746,"word":"gone","score":0.892,"start":28.546},{"end":29.447,"word":"before.","score":0.86,"start":28.806}]}"""
    )

    progress_callback(100.0)
    return return_obj
