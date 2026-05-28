FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    software-properties-common wget \
    && rm -rf /var/lib/apt/lists/*

RUN wget -qO /usr/bin/solc https://github.com/ethereum/solidity/releases/download/v0.8.28/solc-static-linux \
    && chmod +x /usr/bin/solc

RUN apt-get update && apt-get install -y z3 && rm -rf /var/lib/apt/lists/*

CMD ["/bin/bash"]
