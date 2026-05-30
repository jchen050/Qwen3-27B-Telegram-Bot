FROM nvidia/cuda:12.2.0-devel-ubuntu22.04

RUN apt-get update && apt-get install -y \
    git cmake build-essential \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/ggml-org/llama.cpp /opt/llama.cpp
WORKDIR /opt/llama.cpp

# libcuda.so.1 is not present during build — use the stub so the linker is satisfied.
# The real library is injected at runtime by the NVIDIA container runtime.
RUN echo "/usr/local/cuda/lib64/stubs" > /etc/ld.so.conf.d/cuda-stubs.conf && ldconfig && \
    cmake -B build -DGGML_CUDA=ON && \
    cmake --build build --config Release -j$(nproc) --target llama-server

EXPOSE 8080

ENTRYPOINT ["/opt/llama.cpp/build/bin/llama-server"]