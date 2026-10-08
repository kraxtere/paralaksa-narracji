FROM python:3.12-slim
ENV PORT=7860 PYTHONUNBUFFERED=1
RUN useradd -m -u 1000 user
WORKDIR /home/user/app
COPY --chown=user requirements.txt server.py konta.py powiadomienia.py ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=user public/ public/
USER user
EXPOSE 7860
CMD ["python", "server.py"]
