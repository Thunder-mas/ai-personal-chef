# app/tracing.py
"""LangSmith 链路追踪：env-gated 接入，未配 key 时完全 no-op（线上 demo 行为零变化）。

为什么几乎零代码：本项目用 langchain ChatOpenAI + langgraph，LangSmith 的追踪
完全由环境变量驱动 —— 设了 key 就自动记录每次 LLM 调用、每个 graph 节点
（营养师→主厨→采购）的输入输出 / 延迟 / token / 成本，无需改任何业务代码。

本模块只做三件小事，让"接入"在代码里可见、可控、可复述：
  1) 兼容新旧两套环境变量名（LANGSMITH_* 新 / LANGCHAIN_* 旧），任意一套有 key 即可；
  2) 没配 project 时给个默认项目名；
  3) 启动时打一行日志，明确"追踪开了没 / 进哪个 project"（绝不打印 key）。

启用方式（写本地 .env 或部署环境变量，密钥绝不入库）：
    LANGSMITH_TRACING=true
    LANGSMITH_API_KEY=ls__xxxxxxxx
    LANGSMITH_PROJECT=ai-personal-chef     # 可选，默认同名
未设 key 或未设 TRACING=true → 自动关闭，主流程不受任何影响。
"""
import os
import logging

logger = logging.getLogger(__name__)

_DEFAULT_PROJECT = "ai-personal-chef"
_TRUTHY = {"true", "1", "yes", "on"}


def init_tracing() -> bool:
    """按环境变量启用 LangSmith 追踪；返回是否启用。best-effort，绝不抛错影响启动。"""
    try:
        # 新旧变量名兼容：任意一套有 key / 开关即可
        api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
        tracing = (os.getenv("LANGSMITH_TRACING") or os.getenv("LANGCHAIN_TRACING_V2") or "").lower()

        # 必须同时具备 key 且显式开启，才打开（避免无 key 配置报错、或意外产生追踪开销）
        if not api_key or tracing not in _TRUTHY:
            # 用 print 而非 logger：uvicorn 的日志配置会吞掉非 uvicorn logger 的 INFO；
            # 纯 ASCII 以兼容 Windows GBK 控制台（中文/emoji 可能乱码甚至抛 UnicodeEncodeError）。
            print("[tracing] LangSmith disabled "
                  "(set LANGSMITH_API_KEY + LANGSMITH_TRACING=true to enable)", flush=True)
            return False

        # langchain 实际读取的是这套变量；两套名字都补齐，并给默认 project
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ.setdefault("LANGCHAIN_API_KEY", api_key)
        os.environ.setdefault("LANGSMITH_API_KEY", api_key)
        project = (os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT")
                   or _DEFAULT_PROJECT)
        os.environ["LANGCHAIN_PROJECT"] = project
        os.environ["LANGSMITH_PROJECT"] = project

        print(f"[tracing] LangSmith tracing ENABLED -> project={project}", flush=True)
        return True
    except Exception as e:  # 观测性绝不能拖垮主流程
        logger.warning("LangSmith 追踪初始化失败（已忽略，不影响主流程）：%s", e)
        return False
