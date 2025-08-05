import requests
import os

# 从环境变量获取 API Key
api_key = "260ed1d7-53c9-4f3b-a164-68c9968902ef"

url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

data = {
    "model": "doubao-1.5-vision-pro-250328",
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": "Hello!"
        }
    ]
}

# 发送请求
response = requests.post(url, json=data, headers=headers)

# 打印结果
if response.status_code == 200:
    print(response.json())
else:
    print(f"请求失败: {response.status_code}")
    print(response.text)

