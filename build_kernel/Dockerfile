FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive

# Install kernel dependencies
RUN apt-get update && apt-get install -y \

    make flex bison bc libelf-dev libssl-dev rsync file \

    && rm -rf /var/lib/apt/lists/*

# This folder needs to be mounted in the docker-compose
ENV PATH="/home/custom_llvm/build/bin:${PATH}"
