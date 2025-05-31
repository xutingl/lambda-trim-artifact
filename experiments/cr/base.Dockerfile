FROM public.ecr.aws/lambda/python:3.12

# Set up the working directory
COPY experiments/cr/ ${LAMBDA_TASK_ROOT}/

# Installing criu dependencies
RUN dnf install -y git \
    && dnf install -y gcc make \
    protobuf protobuf-c protobuf-c-devel protobuf-compiler protobuf-devel python3-protobuf \
    libnet-devel libnl3-devel libcap-devel libuuid-devel \
    libaio-devel libbsd-devel libdrm-devel gnutls-devel nftables-devel \
    iproute iptables python3-yaml xmlto which tar \
    bzip2-devel libffi-devel openssl openssl-devel \
    && pip install asciidoc google-api-python-client

# Installing criu
RUN git clone https://github.com/checkpoint-restore/criu.git \
    && cd criu \
    && make \
    && make install

# Install λ-trim
COPY ltrim-0.1.0-py3-none-any.whl ${LAMBDA_TASK_ROOT}/ltrim-0.1.0-py3-none-any.whl
RUN pip install ltrim-0.1.0-py3-none-any.whl

ENTRYPOINT [ "/bin/bash" ]
