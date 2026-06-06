# app/vision.py
# 拍照识别食材：用多模态模型 mimo-v2-omni 把"冰箱/食材照片"识别成食材清单。
# 这是 agent 的"感知前置步骤"——识别出的食材文字再交给主 agent(mimo-v2.5)走 RAG 推荐菜谱。
import os
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI

_VISION_MODEL = "mimo-v2-omni"  # MiMo 的多模态模型（mimo-v2.5 不支持图片）
_client = OpenAI(
    api_key=os.getenv("MIMO_API_KEY"),
    base_url=os.getenv("MIMO_BASE_URL"),
)

_PROMPT = (
    "你是食材识别助手。识别这张图片里所有可见的食材，"
    "只输出食材名称，用顿号（、）分隔。不要编号、不要描述、不要多余的话。"
    "如果图中没有可识别的食材，回复：未识别到食材。"
)


def recognize_ingredients(image_urls, hint_text: str = "") -> str:
    """识别图片中的食材，返回顿号分隔的食材名称字符串。

    image_urls: data URL（"data:image/...;base64,xxx"）或普通图片 URL 的列表。
    hint_text:  用户随图片附带的文字（可选），作为补充提示。
    """
    if not image_urls:
        return ""

    content = [{"type": "text", "text": _PROMPT}]
    if hint_text:
        content.append({"type": "text", "text": f"用户补充：{hint_text}"})
    for url in image_urls:
        content.append({"type": "image_url", "image_url": {"url": url}})

    resp = _client.chat.completions.create(
        model=_VISION_MODEL,
        messages=[{"role": "user", "content": content}],
        max_tokens=1500,   # omni 是推理模型，会先产生 reasoning，需留足额度
        temperature=0.2,
    )
    msg = resp.choices[0].message
    text = (msg.content or "").strip()
    if not text:  # 极端情况下额度被推理吃光，退而取推理内容
        text = (getattr(msg, "reasoning_content", "") or "").strip()
    return text
