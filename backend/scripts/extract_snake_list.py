# scripts/extract_snake_list.py
"""
从《中国蛇类》md文件提取蛇类名录。

解析图片说明，提取中文名和拉丁学名。
"""

import re
import json
from pathlib import Path

SOURCE_MD_PATH = Path(__file__).parent.parent / "中国蛇类（上下） (赵尔宓) (Z-Library)" / "auto" / "中国蛇类（上下） (赵尔宓) (Z-Library).md"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "snake_list_raw.json"


def extract_snake_entries(md_content: str) -> list[dict]:
    """从md内容提取蛇类条目"""
    lines = md_content.split('\n')
    
    entries = []
    seen = set()
    
    pattern1 = re.compile(
        r'图\s*\d+[-–]\d+\s*'
        r'([\u4e00-\u9fa5]+)'
        r'\s+([A-Z][a-z]+\s+[a-z]+)'
    )
    
    pattern2 = re.compile(
        r'图\s*\d+[-–]\d+\s*'
        r'([\u4e00-\u9fa5]+)'
        r'([A-Z][a-z]+[a-z\s]+)'
    )
    
    for line in lines:
        line = line.strip()
        if not line.startswith('图'):
            continue
        
        match = pattern1.search(line)
        if not match:
            match = pattern2.search(line)
        
        if match:
            chinese_name = match.group(1).strip()
            latin_name = match.group(2).strip() if match.group(2) else ""
            
            chinese_name = re.sub(r'[（\(].*?[）\)]', '', chinese_name)
            chinese_name = chinese_name.strip()
            
            if not chinese_name or len(chinese_name) < 2:
                continue
            
            latin_name = ' '.join(latin_name.split()[:3])
            
            key = (chinese_name, latin_name)
            if key not in seen:
                seen.add(key)
                entries.append({
                    "chinese_name": chinese_name,
                    "latin_name": latin_name,
                    "source_line": line[:100]
                })
    
    return entries


def main():
    print(f"[INFO] 读取源文件: {SOURCE_MD_PATH}")
    
    with open(SOURCE_MD_PATH, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    print(f"[INFO] 文件大小: {len(md_content)} 字符")
    
    entries = extract_snake_entries(md_content)
    
    cleaned_entries = []
    seen_names = set()
    
    for entry in entries:
        chinese = entry["chinese_name"]
        latin = entry["latin_name"]
        
        if chinese in seen_names:
            continue
        seen_names.add(chinese)
        
        cleaned_entries.append({
            "chinese_name": chinese,
            "latin_name": latin
        })
    
    print(f"[INFO] 提取到 {len(cleaned_entries)} 种蛇类")
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(cleaned_entries, f, ensure_ascii=False, indent=2)
    
    print(f"[SUCCESS] 保存到: {OUTPUT_PATH}")
    
    print("\n前20种蛇类:")
    for i, entry in enumerate(cleaned_entries[:20]):
        print(f"  {i+1}. {entry['chinese_name']} ({entry['latin_name']})")


if __name__ == "__main__":
    main()
