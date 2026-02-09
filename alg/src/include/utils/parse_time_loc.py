import time
import re
import copy
from datetime import datetime
from include.config import ModuleConfig


def get_date(timeStamp):
    assert isinstance(timeStamp, int) or isinstance(timeStamp, float)
    timeArray = time.localtime(timeStamp)
    date = time.strftime("%Y年%m月%d日", timeArray)
    return date


def get_date_info(timeStamp):
    assert isinstance(timeStamp, int) or isinstance(timeStamp, float)
    timeArray = time.localtime(timeStamp)

    # 从timeArray中提取年、月、日信息
    year = timeArray.tm_year
    month = timeArray.tm_mon
    day = timeArray.tm_mday
    return year, month, day

# 找到最新的日期
def parse_web_date(web_summary): # web_summary = ["2024-11-11 11:29:00", ""]
    date_objects = [datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S") for datetime_str in web_summary]
    latest_date = max(date_objects)
    latest_date_str = [latest_date.year, latest_date.month, latest_date.day]
    return latest_date_str


def filter_web_summary_with_date(web_summary): # web_summary = ["2024-11-11 11:29:00", ""]
    select_web_summary = []
    for obj in web_summary:
        try:
            tmp = datetime.strptime(obj["publish_time"], "%Y-%m-%d %H:%M:%S")   
            select_web_summary.append(obj)
        except:
            pass
    return select_web_summary


# 查询IP地址对应的物理地址
def ip_get_location(ip_address):
    # 载入指定IP相关数据
    response = ModuleConfig.geo_lite.city(ip_address)
 
    # #读取国家代码
    # Country_IsoCode = response.country.iso_code
    # #读取国家名称
    # Country_Name = response.country.name
    # #读取国家名称(中文显示)
    # Country_NameCN = response.country.names['zh-CN']
    # #读取州(国外)/省(国内)名称
    # Country_SpecificName = response.subdivisions.most_specific.name
    # #读取州(国外)/省(国内)代码
    # Country_SpecificIsoCode = response.subdivisions.most_specific.iso_code
    #读取城市名称
    City_Name = response.city.name
    city_name = ModuleConfig.pinyin_city.get(City_Name, None)
    #读取邮政编码
    # City_PostalCode = response.postal.code
    # #获取纬度
    # Location_Latitude = response.location.latitude
    # #获取经度
    # Location_Longitude = response.location.longitude
    

    return city_name




# 检验和处理ip地址
def seperate_ip(ip_address):
    ip_match = r"^(?:(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|0?[0-9]?[1-9]|0?[1-9]0)\.)(?:(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){2}(?:25[0-4]|2[0-4][0-9]|1[0-9][0-9]|0?[0-9]?[1-9]|0?[1-9]0)$"
    ip_match_list = r"^(?:(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|0?[0-9]?[1-9]|0?[1-9]0)\.)(?:(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){2}(?:25[0-4]|2[0-4][0-9]|1[0-9][0-9]|0?[0-9]?[1-9])-(?:25[0-4]|2[0-4][0-9]|1[0-9][0-9]|0?[0-9]?[1-9]|0?[1-9]0)$"
 
    if re.match(ip_match, ip_address):
        try:
            cityname = ip_get_location(ip_address)
            return cityname
        except Exception as e:
            return ""
            # raise ValueError(e)
    elif re.match(ip_match_list, ip_address):
        ip_start =  ip_address.split('-')[0].split('.')[3]
        ip_end = ip_address.split('-')[1]
        # 如果ip地址范围一样，则直接执行
        if(ip_start == ip_end):
            try:
                seperate_ip(ip_address.split('-')[0])
            except Exception as e:
                raise ValueError(e)
        elif ip_start > ip_end:
            raise ValueError(f"the value of ip {ip_address} has been wrong! try again!")
        else:
            ip_num_list =  ip_address.split('-')[0].split('.')
            ip_num_list.pop()
            for ip_last in range(int(ip_start), int(ip_end)+1):
                ip_add = '.'.join(ip_num_list)+'.'+str(ip_last)
                try:
                    cityname = ip_get_location(ip_add)
                    return cityname
                except Exception as e:
                    raise ValueError(e)
    else:
        raise ValueError(f"The format of ip {ip_address} has been wrong! try again!")
        


def parse_time_location(User_info):
    """
    解析用户的IP和时间 {"User_Date":'123456', "User_IP":'39.99.228.188'}
    """
    User_info_parsed = copy.deepcopy(User_info)
    ori_time = User_info_parsed["User_Date"]
    ori_time = float(ori_time)
    new_time = get_date(ori_time)
    ori_loc = User_info_parsed["User_IP"]
    new_loc = seperate_ip(ori_loc)
    if new_time:
        User_info_parsed["User_Date"] = new_time
    if new_loc:
        User_info_parsed["User_IP"] = new_loc
    return User_info_parsed


if __name__ == "__main__":
    # ip_address = '39.99.228.188'
    # res = seperate_ip(ip_address)
    # print(res)


    # res = parse_time_location({"User_Date":'123456', "User_IP":'39.99.228.188'})
    # print(res)

    res = parse_web_date(['2023-11-11 11:29:00', '2024-07-23 05:27:00'])
    print(res)