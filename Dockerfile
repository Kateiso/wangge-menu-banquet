FROM python:3.12-slim
WORKDIR /app

# 离线安装依赖（绕过 Docker 网络问题）
COPY backend/wheels /tmp/wheels
RUN pip install --no-cache-dir --no-index --find-links=/tmp/wheels /tmp/wheels/*.whl && rm -rf /tmp/wheels

COPY backend/ ./backend/
COPY frontend/dist ./frontend/dist

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
