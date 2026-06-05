# test_mimo_stream.py
# 直接调用 MIMO 接口，验证它是否真·流式（逐 token 返回）。
# 绕过 LangGraph / FastAPI，单独测底层模型接口。
import sys

# 避免 Windows GBK 控制台打印 emoji / 部分字符时报错
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import os
import time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("MIMO_API_KEY"),
    base_url=os.getenv("MIMO_BASE_URL"),
)

print("正在请求 MIMO（stream=True）...\n")

start = time.perf_counter()
first_chunk_at = None
chunk_count = 0
char_count = 0

stream = client.chat.completions.create(
    model="mimo-v2.5",
    messages=[{"role": "user", "content": "用一句话推荐一道家常菜"}],
    stream=True,
    max_tokens=200,
)

for chunk in stream:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta.content
    if not delta:
        continue
    now = time.perf_counter()
    if first_chunk_at is None:
        first_chunk_at = now
    chunk_count += 1
    char_count += len(delta)
    # 打印每块的到达时间（相对开始）+ 内容
    print(f"[+{(now - start) * 1000:7.0f}ms] {delta!r}")

end = time.perf_counter()

print("\n" + "=" * 50)
print(f"总块数 (chunks)  : {chunk_count}")
print(f"总字符数         : {char_count}")
if first_chunk_at is not None:
    print(f"首块延迟 (TTFB)  : {(first_chunk_at - start) * 1000:.0f}ms")
else:
    print("首块延迟 (TTFB)  : 无内容返回")
print(f"总耗时           : {(end - start) * 1000:.0f}ms")
print("=" * 50)

if chunk_count > 1:
    print("结论：✅ 真流式 —— 内容分成多块、随时间陆续到达。")
elif chunk_count == 1:
    print("结论：⚠️  疑似非流式 —— 只收到 1 块，MIMO 可能一次性返回全部内容。")
else:
    print("结论：❌ 没有收到任何内容，检查 API key / base_url / 网络。")
