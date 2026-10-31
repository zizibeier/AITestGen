import os
from pathlib import Path

from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv

# 支持从仓库根目录的 .env 读取密钥（与 common/config/settings.py 保持一致）
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

client = Cerebras(
    api_key=os.getenv("CEREBRAS_API_KEY", ""),
)


chat_completion = client.chat.completions.create(
    messages=[
        {"role": "system", "content": "你是一个有帮助的助手"},
        {"role": "user", "content": "你好，请介绍一下自己"}
    ],
    model=os.getenv("CEREBRAS_MODEL", "qwen-3-235b-a22b-instruct-2507"),
)

print(chat_completion.choices[0].message.content)
