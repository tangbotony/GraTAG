import json
import time
import concurrent.futures
import logging
import requests
import traceback
from loguru import logger as log
from chat_with_GPT import chat_with_gpt
from prompt import PROMPTS

openai_key = "xx"
model = "gpt-4o"

def process_single_answer(answer, model_name):
    start_time = time.time()
    question = answer["question"].strip()
    document = answer['document'].strip()
    # instruction = answer['instruction']
    domain = "[bio_medical_research, general_knowledge, legal_contracts, customer_support, finance, news]"
    # chain = answer.get('chain', [])
    #------------------------------------------------------ Intent detection 
    # intention_prompt = PROMPTS["intention"].replace('{domain}', domain)
    # intention_prompt = PROMPTS["intention"].replace('{question}', question)
    # intention_prompt = PROMPTS["intention"].replace('{document}', document)
    # intention = chat_with_gpt(query=intention_prompt,key=openai_key,model="gpt-4o",json_mode=False)
    # print(intention)
    # end_time = time.time()
    # response_time = end_time - start_time
    # print("Response Time: {:.6f} seconds".format(response_time))
    #------------------------------------------------------ prompt integration
    # entity_type = PROMPTS[f"{intention}"]
    entity_type = PROMPTS["general_knowledge"]
    # print(entity_type)  # eg: ["person", "organization", "location", "event", "time", "number", "product", "policy"]

    instruction_prompt = PROMPTS["entity_extraction"]
    
    for type in entity_type:
        instruction_prompt += f"""\nStep{entity_type.index(type)+1}.""" + PROMPTS[f"entity_extraction_{type}"]
    instruction_prompt += f"""\nStep{len(entity_type)+1}. Return all the entities identified in the above steps as a single list, but do not show the extraction details of each step. Only output the final integrated list of entities, separated by semicolons.\n"""
    instruction_prompt += f"""\nStep{len(entity_type)+2}. When completed, only output the final integrated list of entities without showing the details of each step. End with the completion delimiter <|COMPLETE|>.\n"""
    instruction_prompt = instruction_prompt.replace('{entity_type}', str(entity_type))
    # print(instruction_prompt)
    
    query_ref = f"""
    {{
       "instruction": "{instruction_prompt}",
       "input":"- real data -\n\nquesiton: {question}\n\ndocuments: {document}\noutput: "
    }}"""
    output = chat_with_gpt(query=query_ref,key=openai_key,model="gpt-4o",json_mode=False)
    # reference = model_interface(query=query_ref, model_name=model_name, n=1, temperature=0.0, timeout=10)
    # print(reference)
    end_time = time.time()
    response_time = end_time - start_time
    input_data = f"- real data -\n\nquesiton: {question}\n\nreference：\n{document}"
    print("Response Time: {:.6f} seconds".format(response_time))
    log_data = {
        "instruction": instruction_prompt,
        "input": input_data,
        "output": output
    }
    log_string = str(log_data)

    with open('log_gov.txt', 'a') as file:
        file.write(log_string + '\n')

    return {
        "instruction": instruction_prompt,
        "input":input_data,
        "output": output
    }

def main():
    answer_path = "../data/Benchmark/SFT/govreport.json"
    output_path = '../data/Benchmark/SFT/graphdata/govreport_sft.json'
    results = []
    
    with open(answer_path, 'r', encoding='utf-8') as file:
        answers = json.load(file)
    
    model_name = "gpt-4o"
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=200) as executor:
        future_to_answer = {executor.submit(process_single_answer, answer, model_name): answer for answer in answers}
        
        for future in concurrent.futures.as_completed(future_to_answer):
            answer = future_to_answer[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as exc:
                logging.error(f'Answer {answer["question"]} generated an exception: {exc}')

    with open(output_path, 'w', encoding='utf-8') as output_file:
        json.dump(results, output_file, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
