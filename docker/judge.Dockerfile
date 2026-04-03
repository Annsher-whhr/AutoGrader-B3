FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        coreutils \
        gawk \
        grep \
        openssh-client \
        procps \
        python3 \
        sed \
        util-linux \
        vim \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1001 judge

WORKDIR /workspace
USER judge
