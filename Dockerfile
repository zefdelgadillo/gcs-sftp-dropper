FROM python:3
ADD src/main.py /
ADD src/requirements.txt /

RUN pip install -r requirements.txt

ENV GCP_PROJECT ""
ENV SECRET_NAME ""
ENV USERNAME ""
ENV SFTP_HOST ""
ENV BASE_DIR ""
ENV AUTH_MODE ""

# CMD ["python", "./main.py"]
ENTRYPOINT ["python", "./main.py"]
