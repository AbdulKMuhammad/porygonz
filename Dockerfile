FROM rust:1.89-slim AS build

RUN apt update && apt install -y python3.13 make build-essential python3.13-venv

COPY pyproject.toml pyproject.toml

ARG GEN

RUN mkdir ./packages && \
    python3.13 -m venv venv && \
    . venv/bin/activate && \
    # pip24 is required for --config-settings
    pip install --upgrade pip==24.2 && \
    pip install -v --target ./packages requests==2.32.4 websockets==14.1 python-dateutil==2.8.0 && \
    if [ -n "$GEN" ]; then \
        pip install -v --target ./packages poke-engine==0.0.46 --config-settings="build-args=--features poke-engine/${GEN} --no-default-features"; \
    else \
        pip install -v --target ./packages poke-engine==0.0.46 --config-settings="build-args=--features poke-engine/terastallization --no-default-features"; \
    fi

FROM python:3.13-slim

WORKDIR /foul-play

COPY config.py /foul-play/config.py
COPY constants.py /foul-play/constants.py
COPY data /foul-play/data
COPY run.py /foul-play/run.py
COPY fp /foul-play/fp
COPY teams /foul-play/teams

COPY --from=build /packages/ /usr/local/lib/python3.13/site-packages/

ENV PYTHONIOENCODING=utf-8

ENTRYPOINT ["python3", "run.py"]
