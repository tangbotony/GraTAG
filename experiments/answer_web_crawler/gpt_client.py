import json
import os
import requests

KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")


def chat_with_gpt(query: str,
                  key: str = KEY,
                  model: str = MODEL,
                  system_message: str = None,
                  temperature: float = 0.2,
                  retry_time: int = 5,
                  json_mode: bool = False
                  ):
    url = os.environ.get("OPENAI_API_BASE", "http://xxxxxxxxx:3001") + "/v1/chat/completions"
    if system_message:
        message = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": query}
        ]
    else:
        message = [{"role": "user", "content": query}]

    payload = {
        "model": model,
        "messages": message,
        "temperature": temperature
    }
    if json_mode:
        payload.update(response_format={"type": "json_object"})
    payload = json.dumps(payload)
    headers = {
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    }
    count = 0
    while True:
        try:
            response = requests.request("POST", url, headers=headers, data=payload, timeout=300)
            result = json.loads(response.text)["choices"][0]["message"]["content"]
            break
        except Exception as e:
            count += 1
            print(e)
            if count > retry_time:
                raise Exception('ReturnCode.LLM_ERROR')
    return result


if __name__ == "__main__":
    a = chat_with_gpt(
        query="2022年北京冬奥会期间，中国代表队共获得了几枚金牌？",
        key=KEY,
        model=MODEL,
        json_mode=False)
    print(a)
