FROM python:3.14-slim-trixie
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

RUN useradd --create-home --uid 1000 mluser
WORKDIR /app
RUN chown mluser:mluser /app

COPY docker/requirements-serve.txt .
RUN pip install --no-cache-dir --no-compile -r requirements-serve.txt

COPY --chown=mluser:mluser src/serve.py src/serve.py

USER mluser
EXPOSE 8000
CMD ["uvicorn", "serve:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
