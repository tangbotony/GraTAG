from http import HTTPStatus
from flask import jsonify, request, Response, stream_with_context
import time
from include.logger import pipeline_log as pipline_logger
from include.utils.skywalking_utils import trace_new, start_sw
from modules import *
import traceback
from pipeline import functions
from pipeline_doc import functions_doc_qa

# 自定义prometheus指标
from prometheus_client import Counter, Histogram
function_counter = Counter('http_requests_total', 'Total HTTP requests', ['method', 'path', 'function'])
function_histogram = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'path', 'function'])

function_map = {
    "recommend_query": functions.recommend_query,
    "recommend_question": functions.recommend_question,
    "extract_pdf": functions.extract_pdf,
    "supply_question": functions.supply_question,
    "answer": functions.answer,
    "doc_supply_question": functions_doc_qa.supply_question,
    "doc_answer": functions_doc_qa.answer,
    "receive_heartbeat": functions.receive_heartbeat
}


def execute():
    data = {}
    if request.content_length != 0 or request.data:
        data = request.json
    input_headers = request.headers

    if 'function' not in input_headers:
        return jsonify({'err_msg': "not find function in header"}), HTTPStatus.BAD_REQUEST
    func = input_headers.get('function', '')
    if func not in function_map:
        return jsonify({'err_msg': "function name not in function_map, please input right function"}), HTTPStatus.BAD_REQUEST

    try:
        with function_histogram.labels(request.method, request.path, func).time():
            res = function_map[func](data, input_headers)
        function_counter.labels(request.method, request.path, func).inc()

        # res = function_map[func](data, input_headers)
        return res, HTTPStatus.OK
    except Exception as e:
        pipline_logger.error(traceback.format_exc())
        pipline_logger.error(e)
        return jsonify({'err_msg': e}), HTTPStatus.INTERNAL_SERVER_ERROR
    

def stream_execute():
    data = {}
    if request.content_length != 0 or request.data:
        data = request.json
    input_headers = request.headers

    if 'function' not in input_headers:
        return jsonify({'err_msg': "not find function in header"}), HTTPStatus.BAD_REQUEST
    func = input_headers.get('function', '')
    if func not in function_map:
        return jsonify({'err_msg': "function name not in function_map, please input right function"}), HTTPStatus.BAD_REQUEST
    
    try:
        start_time = time.time()
        res = function_map[func](data, input_headers)
        
        def generate():
            nonlocal start_time
            for item in res:
                yield item
                if item == b'data: [DONE]\n\n':
                    function_counter.labels(request.method, request.path, func).inc()
                    function_histogram.labels(request.method, request.path, func).observe(time.time() - start_time)
                    break
        
        headers = {'Content-Type': request.headers['Content-Type']}
        return Response(stream_with_context(generate()), headers=headers, content_type="text/event-stream")
    except Exception as e:
        pipline_logger.error(traceback.format_exc())
        pipline_logger.error(e)
        return jsonify({'err_msg': e}), HTTPStatus.INTERNAL_SERVER_ERROR
    



if __name__ == "__main__":
    # start_sw()
    # recommend_question()
    start_sw()
    execute()

