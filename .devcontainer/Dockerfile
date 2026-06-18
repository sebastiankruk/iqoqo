FROM ubuntu:24.04

# Instalacja podstawowych zależności dla agentów oraz serwera IDE
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    python3 \
    python3-pip \
    sudo \
    && rm -rf /var/lib/apt/lists/*
