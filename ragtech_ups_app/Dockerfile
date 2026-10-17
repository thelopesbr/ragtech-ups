FROM ghcr.io/home-assistant/base-python:3.13-alpine3.24-2026.08.0

# Versão do app (config.yaml), passada pelo Supervisor; é também a tag da lib no GitHub
ARG BUILD_VERSION

RUN pip install --no-cache-dir \
    "ragtech-ups[mqtt] @ https://github.com/thelopesbr/ragtech-ups/archive/refs/tags/v${BUILD_VERSION}.tar.gz"

COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
