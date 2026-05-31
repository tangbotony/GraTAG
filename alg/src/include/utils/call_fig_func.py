# coding:utf-8
import copy
import json
import requests
import traceback
from include.logger import log
from include.config import RagQAConfig
from include.utils.time_utils import TimeCounter

# time_use_in_fig = []


def get_fig_filter(text_list, timeout=5, min_context_len=20, application="", max_num_fig: int = 200):
    text_list['candidate_images'] = copy.deepcopy(text_list.get('candidate_images', list())[:max_num_fig])

    all_candidate_images = text_list.get('candidate_images_dict', dict())
    chosen_candidate_images_dict = dict()
    for candidate_image in text_list.get('candidate_images', list()):
        chosen_candidate_images_dict[candidate_image] = all_candidate_images.get(candidate_image, dict())
    text_list['candidate_images_dict'] = copy.deepcopy(chosen_candidate_images_dict)
    time_counter = TimeCounter()
    time_counter.add_task("get_fig")
    time_counter.add_time_stone("get_fig", "start")
    is_return_config = False
    try:

        url = RagQAConfig['FIG_CONFIG']['url_duplicate']
        headers = {
            'token': RagQAConfig['FIG_CONFIG']['token'],
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'Connection': 'keep-alive',
            "Authorization": "xxx"
        }
        if application == "timeline":
            if "strategy_config" in text_list:
                text_list["strategy_config"].update({"thresh_hold": 0.2})
            else:
                text_list["strategy_config"] = {"thresh_hold": 0.2}
        else:
            text_list["strategy_config"] = {"thresh_hold": 0.2}
        payload = json.dumps(text_list)

        response = requests.request("POST", url, headers=headers, data=payload, timeout=timeout)
        res = response.json()
        assert 'error' not in res, res['error']
        return res
    except Exception as e:
        log.warning(traceback.print_exc())
        log.debug(time_counter.time_since_last_stone("get_fig"))
        return text_list['candidate_images'], []


def get_fig(text_list, timeout=6, min_context_len=20):
    all_candidate_images = text_list.get('candidate_images_dict', dict())
    time_counter = TimeCounter()
    chosen_candidate_images_dict = dict()
    for candidate_image in text_list.get('candidate_images', list()):
        chosen_candidate_images_dict[candidate_image] = all_candidate_images.get(candidate_image, dict())
    text_list['candidate_images_dict'] = copy.deepcopy(chosen_candidate_images_dict)
    time_counter.add_task("get_fig")
    time_counter.add_time_stone("get_fig", "start")
    is_return_config = False
    try:
        last_context = text_list.get('contexts', list())[-1]
        output_line = last_context['content']
        # 如果最后一个output_line大于最小接受的输入长度：
        if len(output_line) >= min_context_len:
            url = RagQAConfig['FIG_CONFIG']['url']
            headers = {
                'token': RagQAConfig['FIG_CONFIG']['token'],
                'Content-Type': 'application/json',
                'Accept': '*/*',
                'Connection': 'keep-alive',
                "Authorization": "xxx"
            }
            text_list["strategy_config"] = dict()
            payload = json.dumps(text_list)

            response = requests.request("POST", url, headers=headers, data=payload, timeout=timeout)
            res = response.json()
            assert 'error' not in res, res['error']
            for res_i in res:
                if res_i['type'] == 'image':
                    is_return_config = True
            # log.debug(time_counter.time_since_last_stone("get_fig"))
            # time_use_in_fig.append(
            #     {
            #         "text_list": text_list,
            #         "time": time_counter.time_since_last_stone("get_fig"),
            #         "res": res
            #     }
            # )
            # with open("fig_time_log.json", 'w', encoding="utf-8") as f:
            #     json.dump(time_use_in_fig, f, indent=4, ensure_ascii=False)
            return res, is_return_config
        else:
            res = text_list.get("contexts", []), is_return_config
    except Exception as e:
        # log.warning(traceback.print_exc())
        log.debug(time_counter.time_since_last_stone("get_fig"))
        # time_use_in_fig.append(
        #     {
        #         "text_list": text_list,
        #         "time": time_counter.time_since_last_stone("get_fig")
        #     }
        # )
        # with open("fig_time_log.json", 'w', encoding="utf-8") as f:
        #     json.dump(time_use_in_fig, f, indent=4, ensure_ascii=False)
        return text_list.get("contexts", []), is_return_config
    return res, is_return_config


if __name__ == '__main__':
    test_input = {
        "session_id": "1234",
        "request_id": "1234",
        "question": "xxx",
        "contexts": [
                {
                    "type": "text",
                    "content": " "
                },
                {
                    "type": "text",
                    "content": " \n山西省农业农村厅制定的技术支撑文件中包含的主要内容可以概括为以下几个方面：\n"
                },
                {
                    "type": "text",
                    "content": " \n山西省农业农村厅制定的技术支撑文件中包含的主要内容可以概括为以下几个方面：\n\n1"
                },
                {
                    "type": "text",
                    "content": " \n山西省农业农村厅制定的技术支撑文件中包含的主要内容可以概括为以下几个方面：\n\n1. **现代种业类**："
                },
                {
                    "type": "text",
                    "content": " \n山西省农业农村厅制定的技术支撑文件中包含的主要内容可以概括为以下几个方面：\n\n1. **现代种业类**：\n   - 包含19项内容，主要涉及耐旱、抗病、宜机收玉米新品种等，旨在通过改良作物品种，提升农业生产的质量和效率。\n"
                },
                {
                    "type": "text",
                    "content": " \n山西省农业农村厅制定的技术支撑文件中包含的主要内容可以概括为以下几个方面：\n\n1. **现代种业类**：\n   - 包含19项内容，主要涉及耐旱、抗病、宜机收玉米新品种等，旨在通过改良作物品种，提升农业生产的质量和效率。\n\n2"
                },
                {
                    "type": "text",
                    "content": " \n山西省农业农村厅制定的技术支撑文件中包含的主要内容可以概括为以下几个方面：\n\n1. **现代种业类**：\n   - 包含19项内容，主要涉及耐旱、抗病、宜机收玉米新品种等，旨在通过改良作物品种，提升农业生产的质量和效率。\n\n2. **有机旱作类**："
                },
                {
                    "type": "text",
                    "content": " \n山西省农业农村厅制定的技术支撑文件中包含的主要内容可以概括为以下几个方面：\n\n1. **现代种业类**：\n   - 包含19项内容，主要涉及耐旱、抗病、宜机收玉米新品种等，旨在通过改良作物品种，提升农业生产的质量和效率。\n\n2. **有机旱作类**：\n   - 包括5项技术，如冬小麦—夏玉米水肥一体化高产栽培技术，重点在于通过优化水肥管理，提升作物产量和资源利用效率。\n"
                }
            ],
            "candidate_images": [
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/1216d22eeee536915e1417f965a5176a.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/0a811975c80d527f8866eb409a07b2ca.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/af4c45552cf5288d86c8cb26e4344b71.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/f35aee300061fa01833013cdfef5540b.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/010a1dabe7e5a5127fac618ad19e362b.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/3cb8a688305cb40a68310cd6abb5bd1f.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/e20368a0b85b8f20c822f950f2db8826.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/29728eb709ae9fb239bcd99d60bc666a.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/fb8f4724dc8a30cb0fa42a1a01919e6b.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/6dfb672a9c691f9dbe6f735d7f9b1073.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/c35967a52975ba77e0b0604a53c50de5.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/942e442819d913a287c85765c829af7f.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/f78aea0fb64c5613ef72cf5b489c509f.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/804ccfca772ed93225264235011eaf2c.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/d2eda11889ddd2e4be31bc4b29b88e5a.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/2c9f52453ab0a7fdf026d5976f4243ec.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/08e5aeaa191229eefd6e7e57a875bf37.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/d97ba1923e4f36159439905b68001592.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/2621a2b36492b2a0baec3f4b37a89cba.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/677557d89d68be8574046f6390e90799.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/139266dcd5d170a835a69305e2ce18fb.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/788cec0eecb55d447861b89e002157be.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/42f2bf73c41883745b42b65a07840f8c.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/abfc910df5a001db0f4728eb9760108a.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/f3a8094933f0dee4b33497e904f2d70a.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/43db28bf3221beab9ab16ab2d0dc7110.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/765f00c99ea36d5276339f6c4c252dee.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/7d86d48fe073195a15cde681a466d8a4.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/d07441731660e784590e1951313662b7.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/afd7a7ad6b0791d9fb5c7c9df8eecb16.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/e2e4252d854e0ce1246c00bd029f1983.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/df2bf45f9390b6ebc4971a8170ad86c9.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/79a4fddaa8dfdadfd32a5fe24d1dff4f.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/7ac9d326645f0bd8e108add484dba1db.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/63b27216f943e4d83888aed7d0f9205a.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/26a78f63f2902fd9bf947f441bb33fb4.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/140043b989430725eacbf5c8f8c563a0.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/11f0a341ba602a2468c62a1c293ef22f.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/ea45e7cf38de7439628fbe92245465d7.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/9fe471bdcc445ddab69ed32b2904241b.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/1638e1df984d1d5a58215b06bacfc1a0.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/9294b6c8433f37d70bfb3d249c9a2cbd.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/848675ee86acfc0a68c2f590ea0b60f9.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/2b8f164965b7960ddf73ab62688bc1a2.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/b19d0b01254446b49aa245573522e1b3.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/a84bf66b0857b148225853958a85fc8f.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/d902d7768b947e4dda38e7f7925c7282.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/4cbcac5a9a5c0ba853f4e44e5e5e5b84.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/719ef0966bf85513d664a2eeb173bebb.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/f69deffe5f32888b9e45f751e77408ba.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/8221127cf233237b66794936d3254cb5.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/1dac666725ae44eca82f4eccfb573dd4.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/cd0da029cd209a2ee86562bcaec206e4.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/a1077c162230d4a7e4deda447bceca3f.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/084f0337f486c01fd8e9af06130a2f11.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/4a318b0d0f4399beccae94e2018b2a6c.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/30461a3902059c3b69400077ccea13c5.jpg",
                "https://public-crawler.oss-cn-shanghai.aliyuncs.com/img/677a879ebe8208d90f31981fc4f67bad.jpg"
            ],
            "strategy_config": {
                "thresh_hold": 0.2
            }}
    res, is_fig = get_fig(test_input)
    if is_fig:
        print("找到了合适的图片！！")
        print("url: {}".format(res[-1]['url']))

    print("*" * 30)
    print(res)
