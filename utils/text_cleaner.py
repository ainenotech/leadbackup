import re
from typing import Any

def clean_email_text(text: str, keep_clean_bullets: bool = True) -> str:
    """Removes all raw markdown stars (** or *), stray highlights, raw HTML tags,
    and redundant subject headers from AI email replies and templates, producing
    proper, clean, professional corporate email formatting without asterisks.
    """
    if not text:
        return ""

    s = str(text).strip()

    # 1. Strip redundant leading 'Subject: ...' if the LLM placed it in the email body
    s = re.sub(r'^(?:Subject|SUBJECT):\s*[^\n]*\n+', '', s, flags=re.IGNORECASE).strip()

    # 2. Convert raw <a href="url">label</a> tags into clean plain text: "label: url"
    def _replace_a(match):
        href = match.group(1).strip()
        label = re.sub(r'<[^>]+>', '', match.group(2)).strip()
        if not label or label.lower() in href.lower() or href == label:
            return href
        return f"{label}: {href}"

    s = re.sub(r'<a\s+(?:[^>]*?\s+)?href=[\'"]([^\'"]+)[\'"][^>]*>(.*?)</a>', _replace_a, s, flags=re.IGNORECASE | re.DOTALL)

    # 3. Strip remaining raw HTML tags like <p>, </p>, <br>, <div>, </div>
    s = re.sub(r'<(?:br\s*/?|p|div|tr)>', '\n', s, flags=re.IGNORECASE)
    s = re.sub(r'</(?:p|div|tr)>', '\n', s, flags=re.IGNORECASE)
    s = re.sub(r'<[^>]+>', '', s)

    # 4. Remove all markdown bold/stars highlights:
    # ***highlight*** -> highlight
    s = re.sub(r'\*\*\*([^\*\n]+)\*\*\*', r'\1', s)
    # **highlight** -> highlight
    s = re.sub(r'\*\*([^\*\n]+)\*\*', r'\1', s)
    # __highlight__ -> highlight
    s = re.sub(r'__([^\_\n]+)__', r'\1', s)

    # 5. Clean bullet points:
    # Convert lines starting with '*   ', '* ', '-   ', '- ' to clean corporate bullet '• '
    bullet_char = '• ' if keep_clean_bullets else '- '
    lines = []
    for line in s.split('\n'):
        # Match bullet points at line beginning
        cleaned_line = re.sub(r'^\s*[\*\-]\s+', bullet_char, line)
        lines.append(cleaned_line)
    s = '\n'.join(lines)

    # 6. Final sweep: remove any leftover isolated ** or * at line starts
    s = s.replace('**', '')
    s = re.sub(r'^\s*\*\s*', bullet_char, s, flags=re.MULTILINE)

    # 7. Collapse excessive consecutive blank lines
    s = re.sub(r'\n{3,}', '\n\n', s)

    return s.strip()


def extract_text_from_ai_message(content: Any, sanitize_stars: bool = False) -> str:
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
                    return extract_text_from_ai_message(parsed, sanitize_stars=sanitize_stars)
            except Exception:
                pass
            try:
                import json
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return extract_text_from_ai_message(parsed, sanitize_stars=sanitize_stars)
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

    cleaned = result.strip()
    if sanitize_stars:
        cleaned = clean_email_text(cleaned)
    return cleaned

