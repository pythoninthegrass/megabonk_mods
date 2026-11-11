# Build context is this directory: docker build -t megabonk-levels-api pocketbase
FROM alpine:3.24.4

ARG TARGETARCH
ARG PB_VERSION=0.40.6
ARG PB_SHA256_AMD64=0e1f609158ed945f809f8a02ae012aa0427129c66ebb63c1aee76f2c0309373f
ARG PB_SHA256_ARM64=d22c66ceb67ca92b7d767f36d826e848a276bcfa3c197ead20bf87c42208984f

RUN apk upgrade --no-cache \
 && apk add --no-cache ca-certificates \
 && if apk info | grep -q '^openssh'; then echo "an openssh package is installed; the image must not ship sshd" >&2; exit 1; fi

RUN case "$TARGETARCH" in \
      amd64) sha="$PB_SHA256_AMD64" ;; \
      arm64) sha="$PB_SHA256_ARM64" ;; \
      *) echo "unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac \
 && wget -q -O /tmp/pocketbase.zip "https://github.com/pocketbase/pocketbase/releases/download/v${PB_VERSION}/pocketbase_${PB_VERSION}_linux_${TARGETARCH}.zip" \
 && echo "${sha}  /tmp/pocketbase.zip" | sha256sum -c - \
 && unzip -q /tmp/pocketbase.zip pocketbase -d /usr/local/bin \
 && rm /tmp/pocketbase.zip \
 && chmod 0755 /usr/local/bin/pocketbase

RUN addgroup -S pocketbase && adduser -S -G pocketbase -h /pb pocketbase \
 && mkdir /pb_data && chown pocketbase:pocketbase /pb_data

COPY --chown=pocketbase:pocketbase entrypoint.sh /pb/entrypoint.sh
COPY --chown=pocketbase:pocketbase pb_hooks /pb/pb_hooks
COPY --chown=pocketbase:pocketbase pb_migrations /pb/pb_migrations

USER pocketbase
VOLUME /pb_data
EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:8090/api/health || exit 1

ENTRYPOINT ["/pb/entrypoint.sh"]
