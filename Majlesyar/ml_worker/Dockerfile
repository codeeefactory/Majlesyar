FROM pytorch/pytorch:2.2.2-cuda12.1-cudnn8-devel

ARG TRIPOSR_REF=107cefdc244c39106fa830359024f6a2f1c78871
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/opt/triposr TORCH_CUDA_ARCH_LIST=7.5
WORKDIR /worker

RUN apt-get update \
    && apt-get install -y --no-install-recommends git build-essential cmake ninja-build \
    && rm -rf /var/lib/apt/lists/* \
    && git clone https://github.com/VAST-AI-Research/TripoSR.git /opt/triposr \
    && git -C /opt/triposr checkout "${TRIPOSR_REF}" \
    && rm -rf /opt/triposr/.git

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip install --no-cache-dir --no-build-isolation \
        git+https://github.com/tatsy/torchmcubes.git@3aef8afa5f21b113afc4f4ea148baee850cbd472
COPY triposr_api.py ./

EXPOSE 8080
CMD ["uvicorn", "triposr_api:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
