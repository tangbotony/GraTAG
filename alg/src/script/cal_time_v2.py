import json
import argparse
parser = argparse.ArgumentParser(
        description="."
    )
parser.add_argument("--path", type=str,required=True)

args = parser.parse_args()


data = []
with open(args.path) as file:
    for line in file:
        item = line.strip().split("##|##")[-1]
        data.append(json.loads(item))


total_num = 0

session_dict = {}

for item in data:
    session_id, module_name, cost_time = item.get('session_id'), item.get('module_name'), item.get('cost_time')
    if not session_id:
        continue
    if session_id not in session_dict:
        session_dict[session_id] = {}
    if module_name not in session_dict[session_id]:
        session_dict[session_id][module_name] = []
    session_dict[session_id][module_name].append(cost_time)

session_res_dict = {}
answer_cost_time = []
for item in session_dict:
    print('router_answer' not in session_dict[item])
    print(sum(session_dict[item]['router_answer']))
    answer_cost_time.append((item, sum(session_dict[item]['router_answer'])))
    if 'router_answer' not in session_dict[item] or sum(session_dict[item]['router_answer']) < 20:
        continue
    session_res_dict[item] = session_dict[item]

total_num = len(session_res_dict)
failed_num = len(session_dict) - total_num

module_dict = {}
for inst in session_res_dict:
    for item in session_res_dict[inst]:
        if item not in module_dict:
            module_dict[item] = []
        module_dict[item].extend(session_res_dict[inst][item])

res_dict = []
for item in module_dict:
    res_dict.append((item, sum(module_dict[item]) / len(module_dict[item])))

res_dict.sort(key=lambda x: x[1], reverse=True)

for item in res_dict:
    print(item)

print("total num: ", total_num)
print("failed_num: ", failed_num)

answer_cost_time.sort(key=lambda x: x[1], reverse=True)
print(answer_cost_time)

