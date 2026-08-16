FROM python:3.12-slim

# Ansible needs a proper /etc/passwd entry for the running user and sshpass-style
# tooling; keep the image slim but include what ansible-playbook needs locally.
RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /configpilot

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

RUN mkdir -p generated_configs mock_devices/dev mock_devices/staging mock_devices/prod

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
