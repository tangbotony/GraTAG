import requests
import time
import numpy as np
import copy
from include.config import DocQAConfig
from include.logger import log
import traceback


def chart_understanding(image_ossid_list,query_list,image_desc_list,pdf_ossid_list,figure_ft_info_list):

    try:
        url = DocQAConfig["CHART_UNDERSTANDING"]["url"] # 视具体情况而定
        input = {
            "image_oss_id": image_ossid_list,# 图片的oss地址
            "query": query_list, #检索词
            "image_desc": image_desc_list,# 图片的简单描述
        }
        response = requests.post(url,
                                 json=input,
                                 headers={"token": DocQAConfig["CHART_UNDERSTANDING"]["token"]})
        ans = response.json()  # 是一个字典，包含 use_flag, image_text, image_metadata, time 等4个key，对应的value是一个列表
        ans_use_flag=ans.get("use_flag",[])
        ans_image_text=ans.get("image_text",[])
        final_res=[]
        if len(ans_use_flag)>0:
            for ans_idx in range(len(ans_use_flag)):
                if ans_use_flag[ans_idx]:
                    tmp_res={"query":query_list[ans_idx],"ans":ans_image_text[ans_idx],"caption":image_desc_list[ans_idx],"type":"figure","oss_id":pdf_ossid_list[ans_idx],"ft_info":figure_ft_info_list[ans_idx]}
                    final_res.append(tmp_res)
        return final_res
    except Exception as e:
        log.warning(traceback.print_exc())
        return []


if __name__=="__main__":

    image_oss_id=[
        "https://public-pdf-extract-kit.oss-cn-shanghai.aliyuncs.com/pdf-extracted-element/-5MW42Le_nUJ/afebc85f-1358-455f-896b-8cbf36d3717f.jpg",
        "https://public-pdf-extract-kit.oss-cn-shanghai.aliyuncs.com/pdf-extracted-element/-5MW42Le_nUJ/612a2e1c-1ccf-4145-8cad-a575e92846ff.jpg",
    ]
    query=[
        None,
        None,
    ]
    image_desc=[
        None,
        "不同实验组硫化物浓度随暴露时间的对数变化趋势分析",
    ]




    ans = chart_understanding(image_oss_id,query,image_desc)
    print(ans)
    use_flag_list = ans['use_flag']  # 是否是图表（true or false）
    time_list = ans['time']  # 推理用时
    text_list = ans['image_text']  # 图片描述信息
    metadata_list = ans['image_metadata']  # 图片元数据

    # 打印结果
    for i in range(len(use_flag_list)):
        print("image ", i + 1)
        print("use_flag: ", use_flag_list[i])
        print("time: ", time_list[i])
        print("image_text: ", text_list[i])
        print("image_metadata: ", metadata_list[i])





