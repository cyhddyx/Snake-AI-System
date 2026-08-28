# scripts/init_knowledge.py
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import KNOWLEDGE_DATA_PATH
from services.chroma_service import chroma_service


def build_document(snake_data: dict) -> str:
    """将蛇类数据构建为可检索的文档文本"""
    doc = f"""
蛇类名称：{snake_data['chinese_name']}
学名：{snake_data['latin_name']}
科属：{snake_data['family']}
毒性：{snake_data['venom_type']}
分布区域：{snake_data['distribution']}
形态特征：{snake_data['features']}
栖息环境：{snake_data['habitat']}
食性：{snake_data['diet']}
行为习性：{snake_data['behavior']}
急救措施：{snake_data['first_aid']}
保护等级：{snake_data['conservation']}
    """.strip()
    return doc


def init_knowledge_base():
    """初始化知识库"""
    print(f"[INFO] 读取知识数据: {KNOWLEDGE_DATA_PATH}")
    
    with open(KNOWLEDGE_DATA_PATH, 'r', encoding='utf-8') as f:
        snake_list = json.load(f)
    
    print(f"[INFO] 共读取 {len(snake_list)} 条蛇类数据")
    
    documents = []
    ids = []
    
    for snake in snake_list:
        doc_id = snake['id']
        doc_text = build_document(snake)
        
        documents.append(doc_text)
        ids.append(doc_id)
        print(f"  [OK] {snake['chinese_name']} ({snake['latin_name']})")
    
    print("\n[INFO] 正在生成向量并入库...")
    chroma_service.add_documents(documents, ids)
    
    count = chroma_service.count()
    print(f"\n[SUCCESS] 知识库初始化完成！共收录 {count} 种蛇类")


if __name__ == "__main__":
    init_knowledge_base()