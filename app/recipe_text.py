# app/recipe_text.py
"""把 AI 回复里的 recipe JSON 转成可读文本。

后端流式输出的菜谱是单行 JSON（放在 ```recipe``` 代码块里），Web 前端会
解析成卡片渲染。但 CLI / Streamlit 没有卡片渲染，会把 JSON 原样打印出来。
这个模块提供 format_recipe_blocks()，把这些 JSON 块替换成人类可读的文本，
解析逻辑与前端 MessageBubble.tsx 保持一致。
"""
import json
import re

# 匹配 ```recipe / ```json / ``` 代码块（与前端 codeBlockRegex 对应）
_FENCE_RE = re.compile(r"```(?:recipe|json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


def _clean_json(s: str) -> str:
    """清理 servings 字段（可能被模型写成 "2人" 之类），与前端 cleanJsonStr 一致。"""
    return re.sub(r'"servings"\s*:\s*"?(\d+)\s*[^,}\]]*"?', r'"servings":\1', s)


def _try_parse(s: str):
    """尝试把字符串解析成菜谱 dict；必须含 name/ingredients/steps 才算菜谱。"""
    try:
        parsed = json.loads(_clean_json(s.strip()))
    except (json.JSONDecodeError, ValueError):
        return None
    if (
        isinstance(parsed, dict)
        and parsed.get("name")
        and parsed.get("ingredients")
        and parsed.get("steps")
    ):
        return parsed
    return None


def _extract_json_objects(text: str):
    """扫描全文，按括号深度提取顶层 JSON 对象（与前端 extractJsonObjects 一致）。"""
    results = []
    i, n = 0, len(text)
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        depth = 0
        in_string = False
        escaped = False
        for j in range(i, n):
            ch = text[j]
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    results.append(text[i : j + 1])
                    i = j + 1
                    break
        else:
            # 没找到匹配的 }，跳过这个 {
            i += 1
    return results


def _format_recipe(recipe: dict, markdown: bool) -> str:
    """把菜谱 dict 渲染成多行文本。markdown=True 用于 Streamlit，False 用于 CLI。"""
    b = (lambda s: f"**{s}**") if markdown else (lambda s: s)
    lines = [f"🍳 {b(recipe.get('name', '菜谱'))}"]

    desc = recipe.get("description")
    if desc:
        lines.append(f"_{desc}_" if markdown else desc)

    meta = []
    if recipe.get("difficulty"):
        meta.append(f"难度：{recipe['difficulty']}")
    if recipe.get("cookingTime"):
        meta.append(f"时间：{recipe['cookingTime']}")
    if recipe.get("servings"):
        meta.append(f"{recipe['servings']} 人份")
    if meta:
        lines.append(" · ".join(meta))

    ingredients = recipe.get("ingredients") or []
    if ingredients:
        lines.append("")
        lines.append(f"📋 {b('食材')}")
        for ing in ingredients:
            if isinstance(ing, dict):
                emoji = ing.get("emoji") or ""
                name = ing.get("name", "")
                amount = ing.get("amount", "")
            else:
                emoji, name, amount = "", str(ing), ""
            prefix = f"{emoji} " if emoji else ""
            lines.append(f"- {prefix}{name}　{amount}".rstrip())

    steps = recipe.get("steps") or []
    if steps:
        lines.append("")
        lines.append(f"👨‍🍳 {b('步骤')}")
        for idx, step in enumerate(steps, 1):
            lines.append(f"{idx}. {step}")

    tips = recipe.get("tips")
    if tips:
        lines.append("")
        lines.append(f"💡 {tips}")

    tags = recipe.get("tags") or []
    if tags:
        lines.append("")
        if markdown:
            lines.append(" ".join(f"`{t}`" for t in tags))
        else:
            lines.append("标签：" + " ".join(str(t) for t in tags))

    return "\n".join(lines)


def format_recipe_blocks(text: str, markdown: bool = True) -> str:
    """把文本中的 recipe JSON 块替换成可读文本，其余内容原样保留。"""
    if not text:
        return text

    found = False

    def repl(match):
        nonlocal found
        recipe = _try_parse(match.group(1))
        if recipe:
            found = True
            return _format_recipe(recipe, markdown)
        return match.group(0)

    result = _FENCE_RE.sub(repl, text)
    if found:
        return result

    # 没有代码块匹配时，扫描全文找裸 JSON 对象
    for obj in _extract_json_objects(text):
        recipe = _try_parse(obj)
        if recipe:
            return text.replace(obj, _format_recipe(recipe, markdown), 1)

    return text


def extract_first_recipe_name(text: str):
    """从文本中取出第一个菜谱的名字，找不到返回 None。"""
    if not text:
        return None
    for match in _FENCE_RE.finditer(text):
        recipe = _try_parse(match.group(1))
        if recipe:
            return recipe.get("name")
    for obj in _extract_json_objects(text):
        recipe = _try_parse(obj)
        if recipe:
            return recipe.get("name")
    return None
