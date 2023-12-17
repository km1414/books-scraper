FROM python:3.11.7-slim

RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"

RUN pip install --no-cache-dir -U pip
ADD requirements.txt .
RUN pip install --no-cache-dir -U -r requirements.txt &&rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
COPY . .

CMD ["python", "main.py"]
