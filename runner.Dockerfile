#bullseye required for
FROM python:3.12-slim-bullseye

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg git wget

RUN wget https://developer.download.nvidia.com/compute/cuda/repos/debian11/x86_64/cuda-keyring_1.1-1_all.deb

RUN dpkg -i cuda-keyring_1.1-1_all.deb

RUN apt-get update && apt-get install -y --no-install-recommends libcudnn8 libcudnn8-dev

WORKDIR /runner

# install whisper first, as it's a very large dependency (multiple GBs of data) which
# we don't want to re-download every time we change the code.
RUN pip install whisperx

COPY ./runner .

RUN --mount=source=./.git,target=.git,type=bind \
    pip install --no-cache-dir -e .[not_dummy]

CMD ["python", "-m", "project_W_runner"]
