import re


def matches_keyword_logic(content: str, keyword_logic: str) -> bool:
    logic = (keyword_logic or "").replace("\n", " ").strip()
    if not logic:
        return True

    script = re.sub(
        r'"{([^"]*)}"',
        r"('\g<1>' in content)",
        logic,
    )
    script = re.sub(
        r'"([^"]*)"',
        r"('\g<1>'.lower() in content.lower())",
        script,
    )

    try:
        return bool(eval(script, {"__builtins__": {}}, {"content": content}))
    except Exception:
        return False
