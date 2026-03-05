FROM python:3.12-slim

WORKDIR /srv

RUN pip install --no-cache-dir "piper-tts[http]"

COPY start.sh /srv/start.sh
RUN chmod +x /srv/start.sh

EXPOSE 5000
CMD ["/srv/start.sh"]