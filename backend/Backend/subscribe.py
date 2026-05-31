from models.qa import Qa_series, Qa_pair_collection, Qa_pair, Subscription, Timeline
import uuid
from datetime import datetime, timedelta
import requests
from flask import Blueprint, jsonify, request, Response, stream_with_context
import logging
import json
from http import HTTPStatus

import threading
import time
from datetime import datetime
import schedule
from models.qa import  Qa_pair_collection, Qa_pair, Subscription, Qa_pair_info
from config import config_manager
import copy

algorithm_url = config_manager.default_config['ALGORITHM_URL']

log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('AlgorithmRequests')
logger.setLevel(logging.INFO)
current_time = datetime.now().strftime("%Y%m%d")
log_file = config_manager.default_config['LOG_DIR'] + 'subscription_' + current_time + '.log'
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

import mongoengine as me
me.connect(
    db=config_manager.mongo_config['DB'],
    host=config_manager.mongo_config['Host'],
    port=int(config_manager.mongo_config['Port']),
    username=config_manager.mongo_config['Username'],
    password=config_manager.mongo_config['Password'],
    authentication_source=config_manager.mongo_config['authDB']
)

def check_subscriptions():
    current_time = datetime.now()
    logger.info("定时任务启动")
    # 查询数据库中符合条件的订阅记录
    subscriptions = Subscription.objects(push_time=str(current_time.hour))
    # 进一步判断interval
    if subscriptions:
        for subscription in subscriptions:
            date_now = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = datetime.strptime(subscription.end_time, "%m/%d/%Y")

            if date_end < date_now: # 该订阅记录已经超时
                try:
                    # 删除该记录
                    sub_id = subscription._id
                    subscription.delete()
                    qa_c = Qa_pair_collection.objects(_id=subscription.qa_pair_collection_id).first()
                    qa_c.update(is_subscribed = False,subscription_id = "")
                    logger.info(f"删除过期订阅记录：{sub_id}")
                except Exception as e:
                    logger.info(f"删除订阅记录时发生错误：{str(e)}")
            else:
                #检验是否到发送邮件的时间间隔
                fresh_time = datetime.strptime(subscription.fresh_time, "%Y-%m-%d")
                send_date = fresh_time + timedelta(days=subscription.push_interval)
                while send_date < date_now:
                    send_date = send_date + timedelta(days=subscription.push_interval)
                if send_date == date_now:
                    # 调用回答接口
                    logger.info("到达时间，重新生成回答")
                    # new_text = ask(subscription._id)
                    ask(subscription._id)
                    # 发送邮件给用户
                    send_email(subscription.email, subscription.query, subscription.qa_series_id)

                    # 更新 fresh_time 字段为当前时间
                    date_now_str = date_now.strftime("%Y-%m-%d")
                    subscription.fresh_time = date_now_str
                    subscription.save()  # 保存更新后的订阅记录


import pandas as pd
import tldextract
df = pd.read_csv('controllers/icon4.csv')
oss_url = "https://xxx.oss-cn-shanghai.aliyuncs.com/"
host_to_oss_id = pd.Series(df.oss_id.values, index=df.host).to_dict()
host1_to_oss_id = pd.Series(df.oss_id.values, index=df.host_1).to_dict()

import socket
hostname = socket.gethostname()
ip = socket.gethostbyname(hostname)

def ask(sub_id):
    subscription = Subscription.objects(_id=sub_id).first()
    qa_c = Qa_pair_collection.objects(_id=subscription.qa_pair_collection_id).first()
    if not qa_c:
        err_msg = "该问答对集合不存在"
        logger.error('subscription err_msg:'+ err_msg)
    qa_pair_id = str(uuid.uuid4())
    now = datetime.now()
    time_string = now.strftime("%Y-%m-%d %H:%M:%S")
    pair_list = qa_c.qa_pair_list
    version = len(pair_list)
    Qa_pair(_id=qa_pair_id, qa_series_id=subscription.qa_series_id, query=subscription.query, version=version,
            qa_pair_collection_id=subscription.qa_pair_collection_id,create_time=time_string).save()
    qa_pair_mongo = Qa_pair.objects(_id=qa_pair_id).first()
    pair_list.append(qa_pair_id)
    qa_c.save()
    data = {}
    data['query'] = subscription.query
    data['qa_pair_collection_id'] = subscription.qa_pair_collection_id
    data['qa_series_id'] = subscription.qa_series_id
    data['qa_pair_id'] = qa_pair_id
    data['type'] = "subscription"
    data["ip"] = ip

    url = algorithm_url + "/stream_execute"
    headers = {
    "Content-Type":"application/json"
    }
    headers["function"] = "answer"
    request_id = str(uuid.uuid4())
    headers["request-id"] = request_id
    headers["session-id"] = data['qa_series_id']

    log_data={}
    log_data["Request_url"] = "answer_question from subsciption"
    log_data["Request_headers"] = headers
    log_data["Request_data"] = data
    logger.info(log_data)

    def saveQaPair(qa_pair):
        qa_info_tosave = qa_pair['qa_info']
        qa_info_tosave.pop("sites")

        qa_pair_info_mongo = Qa_pair_info(site_num=qa_info_tosave['site_num'],
                     page_num=qa_info_tosave['page_num'],
                     word_num=qa_info_tosave['word_num'],
                     additional_query=qa_info_tosave['additional_query'],
                     search_query=qa_info_tosave['search_query'],
                     ref_pages=qa_info_tosave['ref_pages'],
                     )

        qa_pair_mongo.qa_info = qa_pair_info_mongo
        qa_pair_mongo.general_answer = qa_pair['general_answer']
        qa_pair_mongo.recommend_query = qa_pair['recommend_query']
        qa_pair_mongo.reference = qa_pair['reference']
        # 创建timeline类
        if qa_pair['timeline']:
            _id = str(uuid.uuid4())
            now = datetime.now()
            time_string = now.strftime("%Y-%m-%d %H:%M:%S")
            Timeline(_id=_id, data=qa_pair['timeline'], create_time=time_string).save()
            qa_pair_mongo.timeline_id = _id
            qa_pair_mongo.save()

    def process_data(response):
        def format_ref_page(recall_data_ref_pages):
            new_format = {
                "_id":"",
                "url":"",
                "site":"",
                "title":"",
                "summary":"",
                "content":"",
                "icon":""
            }
            siteList = set()
            return_recall_data = {}
            for key in recall_data_ref_pages.keys():
                new_format = {}
                new_format['_id'] = recall_data_ref_pages[key]['_id']
                new_format['url'] = recall_data_ref_pages[key]['url']
                ext = tldextract.extract(new_format['url'])
                new_format['site'] = ext.fqdn
                siteList.add(new_format['site'])
                new_format['title'] = recall_data_ref_pages[key]['title']
                new_format['summary'] = recall_data_ref_pages[key]['summary']
                new_format['content'] = recall_data_ref_pages[key]['content']
                new_format['icon'] = recall_data_ref_pages[key]['url']
                icon_url = host_to_oss_id.get(new_format['site'])
                if not icon_url:
                    icon_url = host1_to_oss_id.get(new_format['site'])
                    if icon_url:
                        icon_url = oss_url + icon_url
                        new_format['icon'] = icon_url
                else:
                    icon_url = oss_url + icon_url
                    new_format['icon'] = icon_url
                return_recall_data[key] = new_format
            return return_recall_data, list(siteList)

        def renew_qa_info(qa_info, ref_pages):
            # 统计page_num
            format_ref_pages, siteList = format_ref_page(ref_pages)
            ref_pages = format_ref_pages
            ## 去重page
            qa_info['ref_pages'].update(ref_pages)
            qa_info['page_num'] = len(qa_info['ref_pages'])
            # 统计word_num
            word_num = 0
            for key in ref_pages.keys():
                word_num += len(ref_pages[key]['content'])
            qa_info['word_num'] = word_num
            # 统计site_num
            before_site_list = copy.deepcopy(qa_info['sites'])
            before_site_list += siteList
            qa_info['sites'] = list(set(before_site_list))
            qa_info['site_num'] = len(qa_info['sites'])
            return qa_info

        qa_pair = {
            "_id":data.get('qa_pair_id'),
            'qa_info':{},
            'general_answer':"",
            'timeline_id':"",
            'recommend_query':"",
            'reference':"",
        }
        qa_info = {
            "site_num":0,
            "sites":[],
            "page_num":0,
            "word_num":0,
            "additional_query":{},
            "search_query":[],
            "ref_pages":{},
        }
        # 从前端获取补充信息
        qa_info['additional_query'] = data.get("additional_query")

        text = ''
        # 获取算法侧返回的结果
        qa_pair["reference"] = []
        for chunk in response.iter_lines(chunk_size=1024,decode_unicode=False,delimiter=b"\0"):
            
            if chunk:
                content = chunk.decode('utf-8')
                if content.startswith("data: ") and content != "data: [DONE]\n\n":
                    content = content[len("data: "):]
                    content = json.loads(content.strip())
                    if content['type']=="error":
                        continue
                    if content['type']=="state":
                        continue
                    if content['type']=="intention_query":
                        qa_info['search_query']=content['data']
                        continue
                    if content['type']=="ref_page":
                        qa_info = renew_qa_info(qa_info, content['data'])
                    if content['type']=="ref_answer":
                        qa_pair["reference"] = content['data']
                        continue
                    if content['type']=="text":
                        text += content['data']
                        continue
                    if content['type']=="recommendation":
                        qa_pair['recommend_query']=content['data']
                        continue
                    if content['type']=="timeline":
                        qa_pair['timeline']=content['data']
                        continue
        # 最终的持久化
        log_data={}
        log_data["Response_url"] = "answer_question"
        log_data["Response_data"] = text
        logger.info(log_data)
        qa_pair['general_answer'] = text
        qa_pair["qa_info"] = qa_info
        saveQaPair(qa_pair)

    try:
        response = requests.request("POST", url, headers=headers, json=data, stream=True)
        stream_headers = {"Content-Type": "text/event-stream;charset=utf-8"}
        Response(stream_with_context(process_data(response)), headers=stream_headers, status=HTTPStatus.OK)
        # text = qa_pair_mongo.general_answer
        # return text
        return
    except Exception as e:
        logger.error('subscription err_msg:'+ str(e))
        return 

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
sender_email = "15926312959@163.com"
def send_email(address, query, text):
    logger.info(f"send_email to {address}")
    message = MIMEMultipart("alternative")
    message["Subject"] = f"您订阅的问题【{query}】有新的回答"
    message["From"] = sender_email
    message["To"] = address
    polite_greeting = "尊敬的用户，您好：\n\n"
    text = f"您之前订阅的问题有新的回答，请点击链接跳转官网查看：http://123.57.48.226:5314/qa/{text}"
    full_text = f"{polite_greeting}{text}"
    part1 = MIMEText(full_text, "plain")
    message.attach(part1)
    try:
        # 创建SMTP服务器连接
        with smtplib.SMTP_SSL("smtp.163.com", 465) as server:
            # server.starttls()
            # 登录到邮件服务器
            server.login(sender_email, "SGWFRGEFOWHUTCOA")
            # 发送邮件
            server.sendmail(sender_email, address, message.as_string())
            logger.info("邮件发送成功: " + text)
    except Exception as e:
        logger.error("Error:" + str(e))


# 定时任务
def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    # check_subscriptions()
    # ask("acf02ece-708e-465f-8a1f-6254bb206df6")
    # send_email("zhangzh@iaar.ac.cn", "C919在新加坡航展的预演飞行后，将有哪些后续活动？", "f9a96b2a-228d-4e89-8f29-a8e3d29bc606")

    schedule.every(1).hour.do(check_subscriptions)
    thread = threading.Thread(target=run_schedule)
    thread.start()