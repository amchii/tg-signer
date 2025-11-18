import base64
import json
import os
import pathlib
from typing import TYPE_CHECKING, Union

import json_repair
from pydantic import TypeAdapter
from typing_extensions import Optional, Required, TypedDict

if TYPE_CHECKING:
    from openai import AsyncOpenAI  # 在性能弱的机器上导入openai包实在有些慢

from tg_signer.utils import UserInput, print_to_user

DEFAULT_MODEL = "gpt-4o"


def encode_image(image: bytes):
    return base64.b64encode(image).decode("utf-8")


class OpenAIConfig(TypedDict, total=False):
    api_key: Required[str]
    base_url: Optional[str]
    model: Optional[str]


class OpenAIConfigManager:
    def __init__(self, workdir: Union[str, pathlib.Path]):
        self.workdir = pathlib.Path(workdir)

    def get_config_file(self) -> pathlib.Path:
        return self.workdir / ".openai_config.json"

    def has_env_config(self):
        return bool(os.environ.get("OPENAI_API_KEY"))

    def has_config(self) -> bool:
        return self.has_env_config() and bool(self.load_file_config())

    def load_file_config(self) -> Optional[dict]:
        config_file = self.get_config_file()
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as fp:
                c = json.load(fp)
            return TypeAdapter(OpenAIConfig).validate_python(c)
        return None

    def save_config(self, api_key: str, base_url: str = None, model: str = None):
        config_file = self.get_config_file()
        config = OpenAIConfig(api_key=api_key, base_url=base_url, model=model)
        with open(config_file, "w", encoding="utf-8") as fp:
            json.dump(config, fp, ensure_ascii=False, indent=2)

    def load_config(self) -> Optional[OpenAIConfig]:
        # 环境变量优先
        if self.has_env_config():
            return OpenAIConfig(
                api_key=os.environ["OPENAI_API_KEY"],
                base_url=os.environ.get("OPENAI_BASE_URL"),
                model=os.environ.get("OPENAI_MODEL", DEFAULT_MODEL),
            )
        return self.load_file_config()

    def ask_for_config(self):
        print_to_user("开始配置OpenAI API并保存至本地。")
        input_ = UserInput()
        api_key = input_("请输入 OPENAI_API_KEY: ").strip()
        while not api_key:
            print_to_user("API Key不能为空！")
            api_key = input_("请输入 OPENAI_API_KEY: ").strip()

        base_url = (
            input_(
                "请输入 OPENAI_BASE_URL (可选，直接回车使用默认OpenAI地址): "
            ).strip()
            or None
        )
        model = (
            input_(
                f"请输入 OPENAI_MODEL (可选，直接回车使用默认模型({DEFAULT_MODEL})): "
            ).strip()
            or None
        )
        self.save_config(api_key, base_url=base_url, model=model)
        print_to_user("OpenAI配置已保存。")
        return self.load_config()


def get_openai_client(
    api_key: str = None,
    base_url: str = None,
    **kwargs,
) -> Optional["AsyncOpenAI"]:
    from openai import AsyncOpenAI, OpenAIError

    try:
        return AsyncOpenAI(api_key=api_key, base_url=base_url, **kwargs)
    except OpenAIError:
        return None


class AITools:
    def __init__(self, cfg: OpenAIConfig):
        self.client = get_openai_client(
            api_key=cfg["api_key"], base_url=cfg.get("base_url")
        )
        self.default_model = cfg.get("model") or DEFAULT_MODEL

    async def choose_option_by_image(
        self,
        image: bytes,
        query: str,
        options: list[tuple[int, str]],
        client: "AsyncOpenAI" = None,
        model: str = None,
        temperature=0.1,
    ) -> int:
        sys_prompt = """你是一个**图片识别助手**，可以根据提供的图片和问题选择出**唯一正确**的选项，如果你觉得每个都不对，也要给出一个你认为最符合的答案，以如下JSON格式输出你的回复：
    {
      "option": 1,  // 整数，表示选项的序号，从0开始。
      "reason": "这么选择的原因，30字以内"
    }
    option字段表示你选择的选项。
    """
        client = client or self.client
        model = model or self.default_model
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
                            "url": f"data:image/jpeg;base64,{encode_image(image)}"
                        },
                    },
                ],
            },
        ]
        # noinspection PyTypeChecker
        completion = await client.chat.completions.create(
            messages=messages,
            model=model,
            response_format={"type": "json_object"},
            stream=False,
            temperature=temperature,
        )
        message = completion.choices[0].message
        result = json_repair.loads(message.content)
        return int(result["option"])

    async def calculate_problem(
        self,
        query: str,
        client: "AsyncOpenAI" = None,
        model: str = None,
        temperature=0.1,
    ) -> str:
        sys_prompt = """你是一个**答题助手**，可以根据用户的问题给出正确的回答，只需要回复答案，不要解释，不要输出任何其他内容。"""
        model = model or self.default_model
        client = client or self.client
        text = f"问题是: {query}\n\n只需要给出答案，不要解释，不要输出任何其他内容。The answer is:"
        # noinspection PyTypeChecker
        completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": text},
            ],
            model=model,
            stream=False,
            temperature=temperature,
        )
        return completion.choices[0].message.content.strip()

    async def get_reply(
        self,
        prompt: str,
        query: str,
        client: "AsyncOpenAI" = None,
        model: str = None,
    ) -> str:
        model = model or self.default_model
        client = client or self.client
        messages = [
            {
                "role": "system",
                "content": prompt,
            },
            {"role": "user", "content": f"{query}"},
        ]
        # noinspection PyTypeChecker
        completion = await client.chat.completions.create(
            messages=messages,
            model=model,
            stream=False,
        )
        message = completion.choices[0].message
        return message.content
