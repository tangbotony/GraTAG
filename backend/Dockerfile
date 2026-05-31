FROM registry.cn-shanghai.aliyuncs.com

RUN rm -rf /app/

WORKDIR /app

COPY . /app/

RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

RUN mkdir -p /app/Backend/logs

EXPOSE 5000-6000

WORKDIR /app/Backend
