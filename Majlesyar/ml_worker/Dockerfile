FROM pytorch/pytorch:2.2.2-cuda12.1-cudnn8-devel

ARG TRIPOSR_REF=107cefdc244c39106fa830359024f6a2f1c78871
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/opt/triposr
WORKDIR /worker

RUN apt-get update \
    && apt-get install -y --no-install-recommends git build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && git clone https://github.com/VAST-AI-Research/TripoSR.git /opt/triposr \
    && git -C /opt/triposr checkout "${TRIPOSR_REF}" \
    && rm -rf /opt/triposr/.git

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY triposr_api.py ./

EXPOSE 8080
CMD ["uvicorn", "triposr_api:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
