import json


data = []
with open("/data/xxx/log/time_logger.log") as file:
    for line in file:
        item = line.strip().split(" ##｜## ")[-1]
        data.append(json.loads(item))


total_num = 0

module_dict = {}

for item in data:
    module_name, cost_time, model_name, is_stream = item.get('module_name'), item.get('cost_time'), item.get('model_name', None), item.get('is_stream', None)
    if item.get('module_name') == "router_answer":
        total_num += 1
    if model_name:
        module_name = model_name + "_" + str(is_stream)
    if module_name not in module_dict:
        module_dict[module_name] = []
    module_dict[module_name].append(cost_time)

res = []

for item in module_dict:
    res.append((item, sum(module_dict[item]) / (total_num), len(module_dict[item])))

res.sort(key=lambda x: x[1], reverse=True)

print(total_num)
for item in res:
    if 'modules' in item[0] or 'include' in item[0]:
        continue
    print(item)