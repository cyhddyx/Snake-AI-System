# backend/scripts/ingest_md.py
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.md_loader import md_loader
from services.milvus_service import chroma_service


def main():
    md_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'knowledge')
    chunks = md_loader.load_directory(md_dir)

    if not chunks:
        print("❌ 没有解析到任何内容")
        return

    print(f"📦 准备入库 {len(chunks)} 个片段...")
    chroma_service.ingest_chunks(chunks)
    print(f"📊 当前知识库总量: {chroma_service.count()} 条")


if __name__ == "__main__":
    main()