import re

from httpx import AsyncClient


async def sc_send(sendkey, title, desp="", options=None):
    if options is None:
        options = {}
    # 判断 sendkey 是否以 'sctp' 开头，并提取数字构造 URL
    if sendkey.startswith("sctp"):
        match = re.match(r"sctp(\d+)t", sendkey)
        if match:
            num = match.group(1)
            url = f"https://{num}.push.ft07.com/send/{sendkey}.send"
        else:
            raise ValueError("Invalid sendkey format for sctp")
    else:
        url = f"https://sctapi.ftqq.com/{sendkey}.send"
    params = {"title": title, "desp": desp, **options}
    headers = {"Content-Type": "application/json;charset=utf-8"}
    async with AsyncClient(headers=headers) as client:
        response = await client.post(url, json=params)
        result = response.json()
    return result
