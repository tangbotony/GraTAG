import json

def post_porcessing_model(results):
    """
    后处理model 生成结果
    """
    return_reuslts = []
    datalines = eval(results)
    for dataline in datalines:
        if type(dataline)==list and dataline:
            return_reuslts.append(dataline[0])
        else:
            return_reuslts.append(dataline)
    return return_reuslts