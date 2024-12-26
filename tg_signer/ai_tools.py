import base64
import json
import os
from typing import Optional

from openai import AsyncOpenAI, OpenAIError


def encode_image(image: bytes):
    return base64.b64encode(image).decode("utf-8")


def get_openai_client(
    api_key: str = None, base_url: str = None, **kwargs
) -> Optional[AsyncOpenAI]:
    try:
        return AsyncOpenAI(api_key=api_key, base_url=base_url, **kwargs)
    except OpenAIError:
        return None


async def choose_option_by_image(
    image: bytes,
    query: str,
    options: list[str],
    client: AsyncOpenAI = None,
    default_model="gpt-4o",
    temperature=0.1,
) -> str:
    sys_prompt = """你是一个**图片识别助手**，可以根据提供的图片和问题选择出**唯一正确**的选项，以如下JSON格式输出你的回复：
{
  "option": "option1",
  "reason": "这么选择的原因，30字以内"
}
option字段表示你选择的选项。
"""
    model = os.environ.get("OPENAI_MODEL", default_model)
    client = client or get_openai_client()
    text_query = f"问题为：{query}, 选项为：{json.dumps(options)}。"
    messages = [
        {"role": "system", "content": sys_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text_query},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpg;base64,{encode_image(image)}"
                    },
                },
            ],
        },
    ]
    completion = await client.chat.completions.create(
        messages=messages,
        model=model,
        response_format={"type": "json_object"},
        stream=False,
        temperature=temperature,
    )
    message = completion.choices[0].message
    result = json.loads(message.content)
    return result["option"]


async def get_reply(
    prompt: str,
    query: str,
    client: AsyncOpenAI = None,
    default_model="gpt-4o",
) -> str:
    model = os.environ.get("OPENAI_MODEL", default_model)
    client = client or get_openai_client()
    messages = [
        {
            "role": "system",
            "content": prompt,
        },
        {"role": "user", "content": f"{query}"},
    ]
    completion = await client.chat.completions.create(
        messages=messages,
        model=model,
        stream=False,
    )
    message = completion.choices[0].message
    return message.content
