# Please install OpenAI SDK first: `pip3 install openai`
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
from pathlib import Path
import json

load_dotenv(Path(__file__).parent.parent.parent / ".env")
client = AsyncOpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)
async def llm_query(query: str):
    try:
        response = await client.chat.completions.create(
            model="deepseek-v4-pro",
            messages=[
                {"role": "system", "content": "你是一个蛇类专家，你需要回答用户关于蛇的类的知识，要做到客观，科学，有依据的回答"},
                {"role": "user", "content": query},
            ],
            reasoning_effort="high",
            temperature=0,
            extra_body={"thinking": {"type": "enabled"}},
            stream=True
        )
        async for chunk in response:
            delta = chunk.choices[0].delta
            # 推理过程（思考链）
            if getattr(delta, "reasoning_content", None):
                yield f"data: {json.dumps({'type': 'thinking', 'content': delta.reasoning_content})}\n\n"
            # 最终回复
            if delta.content:
                yield f"data: {json.dumps({'type': 'content', 'content': delta.content})}\n\n"
    except Exception:
        yield f"data: {json.dumps({'type': 'content', 'content': 'AI 服务暂时不可用，请稍后重试。'})}\n\n"
    finally:
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
