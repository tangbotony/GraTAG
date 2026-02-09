from app import jwt
from flask import Flask, jsonify
from http import HTTPStatus
from models.jwt import BlackToken



#过期令牌
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({
        'message': 'The token has expired.',
        'error': 'token_expired'
    }), HTTPStatus.UNAUTHORIZED

#无效令牌
@jwt.invalid_token_loader
def invalid_token_callback(error): 
    return jsonify({
        'message': 'Signature verification failed.',
        'error': 'invalid_token'
    }), HTTPStatus.UNAUTHORIZED

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
    jti = jwt_payload["jti"]
    token = BlackToken.objects(jti=jti).first()
    return token is not None

