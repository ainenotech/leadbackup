from typing import Any

def extract_text_from_ai_message(content: Any) -> str:
    """Safely extracts clean human string text from LLM response content across all providers
    (string, list of dicts, Anthropic/Claude/Gemini content blocks, or stringified repr),
    guaranteeing no raw Python dicts, extras, or base64 signatures are ever returned.
    """
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text_val = block.get("text", "")
                if text_val:
                    parts.append(text_val)
            elif hasattr(block, "text"):
                text_val = getattr(block, "text", "")
                if text_val:
                    parts.append(text_val)
            else:
                parts.append(str(block))
        result = "\n".join(parts).strip()
    elif isinstance(content, str):
        s = content.strip()
        # Check if the string is a stringified list of dicts: "[{'type': 'text', 'text': ..."
        if (s.startswith("[{") and ("'text'" in s or '"text"' in s)):
            try:
                import ast
                parsed = ast.literal_eval(s)
                if isinstance(parsed, list):
                    return extract_text_from_ai_message(parsed)
            except Exception:
                pass
            try:
                import json
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return extract_text_from_ai_message(parsed)
            except Exception:
                pass
            import re
            m = re.search(r"['\"]text['\"]\s*:\s*(['\"])(.*?)\1(?:,\s*['\"]extras|\}\])", s, re.DOTALL)
            if m:
                try:
                    return m.group(2).encode().decode("unicode-escape").strip()
                except Exception:
                    return m.group(2).strip()
        result = s
    else:
        result = str(content).strip()

    # Safety: strip any stray 'extras': {'signature': ...} if present
    if "'extras':" in result:
        idx = result.find("'extras':")
        result = result[:idx].rstrip(", '\"{")
    if '"extras":' in result:
        idx = result.find('"extras":')
        result = result[:idx].rstrip(', \'"{')

    return result.strip()
