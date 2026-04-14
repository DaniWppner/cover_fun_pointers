FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive

# Install kernel dependencies
RUN apt-get update && apt-get install -y \
    # These are needed for linux kernel build
    make flex bison bc libelf-dev libssl-dev rsync file \
    # These are nice to haves for developing inside the container
    # (running kernel scripts, etc.)
    python3 \

    && rm -rf /var/lib/apt/lists/*

# This folder needs to be mounted in the docker-compose
ENV PATH="/home/custom_llvm/build/bin:${PATH}"
