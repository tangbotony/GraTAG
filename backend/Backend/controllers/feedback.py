import datetime
import json
import uuid
from http import HTTPStatus

import requests
from config import config_manager
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from models.feedback import CONTENT, Feedback
from models.user import User

router_feedback= Blueprint('feedback', __name__)



# 反馈
@router_feedback.route('/api/feedback', methods=['POST'])
@jwt_required()
def feedback():
    data = request.get_json()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_id = get_jwt_identity()
    id = str(uuid.uuid4())
    brief, description, contact, pic_list, type = \
        data.get('brief', ""), data.get('description', ""), data.get("contact", ""), data.get("pic_list"), data.get("type")
    
    if not brief and not description:
        return jsonify({'message': "brief and description can not be empty"}), HTTPStatus.BAD_REQUEST
    doc = Feedback(_id=id, user_id=user_id, brief=brief, description=description, type=type,
                   contact=contact, pic_list=pic_list, create_time=now)
    doc.save()
    # message = create_tapd_task(doc)
    # if message:
    #     return jsonify({'message': message}), HTTPStatus.INTERNAL_SERVER_ERROR
    return jsonify({'message': "", 'feedback': doc}), HTTPStatus.OK


def create_tapd_task(feedback: Feedback):
    pass