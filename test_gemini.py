import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

print("=== 你的 key 能访问、且支持 generateContent 的模型 ===")
usable = []
for m in client.models.list():
    actions = getattr(m, "supported_actions", []) or []
    if "generateContent" in actions:
        print(" ", m.name)
        usable.append(m.name)

print("\n=== 逐个实测 ===")
for model in usable:
    try:
        resp = client.models.generate_content(model=model, contents="Reply with exactly: OK")
        print(f"[OK]   {model} -> {resp.text.strip()}")
    except Exception as e:
        print(f"[FAIL] {model} -> {str(e)[:90]}")