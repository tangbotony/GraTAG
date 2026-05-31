import json
from datetime import datetime
from http import HTTPStatus

import pymongo
from config import llm_log, config_manager
from controllers import UNKNOW
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from webargs import fields
from webargs.flaskparser import use_args


router_event_tracking = Blueprint('event_tracking', __name__)

mongo_client = pymongo.MongoClient(host=config_manager.mongo_config['Host'], port=int(config_manager.mongo_config['Port']), 
                                   username=config_manager.mongo_config['Username'], password=config_manager.mongo_config['Password'], authSource=config_manager.mongo_config['authDB'])
mong_db = mongo_client[config_manager.mongo_config['DB']]
collection = mong_db['event']

# 埋点
@router_event_tracking.route('/api/event', methods=['POST'])
@use_args({"name": fields.Str(required=True), "site": fields.Str(required=True), "user_id": fields.Str(required=True),
           "url": fields.Str(required=True), "props": fields.Dict(required=True)}, location="json")
def event_tracking(data):
    data['create_time'] = datetime.now()
    collection.insert_one(data)
    return jsonify({'message': "", 'status': 1}), HTTPStatus.OK


# 查询埋点数据
@router_event_tracking.route('/api/stats', methods=['POST'])
def event_get():
    data = request.get_json()

    start_date = datetime(2003, 1, 1)
    end_date = datetime.now()
    if 'date' in data:
        date = data.pop('date')
        start_date = datetime.strptime(date[0], "%Y-%m-%d")
        end_date = datetime.strptime(date[1], "%Y-%m-%d")
    
    props = {}
    if 'props' in data:
        for k in data['props']:
            data['props.{}'.format(k)] = data['props'][k]
        props = data.pop('props')


    data["create_time"] = {"$gte" :start_date ,"$lte": end_date}
    events = collection.find(data)
    res = []
    for item in events:
        item.pop("_id")
        item['create_time'] = item['create_time'].strftime('%Y-%m-%d %H:%M:%S') 
        res.append(item)
    return jsonify({'message': "", 'res': res}), HTTPStatus.OK

