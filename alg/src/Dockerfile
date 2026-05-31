FROM registry.cn-shanghai.aliyuncs.com/iaar/ainews:v4.1

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN pip install zh_core_web_sm-3.7.0.tar.gz
# COPY zh_core_web_sm-3.7.0.tar.gz /usr/local/lib/python3.9/site-packages/
# RUN python -c "import spacy; spacy.cli.download('zh_core_web_sm')"
EXPOSE 10000-20000
