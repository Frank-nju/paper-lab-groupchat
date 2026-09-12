import json, re
from pathlib import Path

def read_text_ro(path: str, max_chars: int=120000) -> str:
    p=Path(path)
    with p.open('r', encoding='utf-8', errors='replace') as f:
        return f.read(max_chars)

def extract_json(text):
    if isinstance(text, dict): return text
    if text is None: raise ValueError('empty model response')
    s=str(text).strip()
    if s.startswith('```'):
        s=re.sub(r'^```(?:json)?\s*','',s); s=re.sub(r'\s*```$','',s)
    try: return json.loads(s)
    except Exception: pass
    starts=[i for i,c in enumerate(s) if c=='{']
    for st in starts:
        depth=0; in_str=False; esc=False
        for i in range(st,len(s)):
            c=s[i]
            if in_str:
                if esc: esc=False
                elif c=='\\': esc=True
                elif c=='"': in_str=False
                continue
            if c=='"': in_str=True
            elif c=='{': depth+=1
            elif c=='}':
                depth-=1
                if depth==0:
                    return json.loads(s[st:i+1])
    raise ValueError('no valid JSON object found')

def dump_json(path, obj):
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
