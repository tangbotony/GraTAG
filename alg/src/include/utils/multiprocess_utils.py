import concurrent.futures
import traceback
import time

# # 多线程
# def pool_async(func, *args, **kwargs):
#     if isinstance(args[0], list) and len(args) == 1:
#         args = args[0]
#     res_lis = []
#     try:
#         with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
#             call_lis = []
#             res_lis = []
#             for obj in args:
#                 func_call = executor.submit(func, obj, **kwargs)
#                 call_lis.append(func_call)

#             for func_call in call_lis:
#                 res = func_call.result()
#                 res_lis.append(res)
#     except Exception as e:
#         raise ValueError(f"多线程运行错误,error_info:{traceback.format_exc()}")
#     return res_lis

def pool_async(func, *args, **kwargs):
    # 检查输入参数是否只有一个列表
    if len(args) == 1 and isinstance(args[0], list):
        args = [[obj] for obj in args[0]]
    elif len(args) > 1:
        args = list(zip(*args))
    else:
        args = [args]

    res_lis = []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            call_lis = []
            for obj in args:
                func_call = executor.submit(func, *obj, **kwargs)
                call_lis.append(func_call)

            for func_call in concurrent.futures.as_completed(call_lis):
                res = func_call.result()
                res_lis.append(res)
    except Exception as e:
        raise ValueError(f"多线程运行错误, error_info: {traceback.format_exc()}")
    return res_lis

def sleep(x, log = "hh"):
    print(x, log)
    time.sleep(2)

if __name__ == "__main__":
    pool_async(sleep, ["you", "I", "this"], log = "here")