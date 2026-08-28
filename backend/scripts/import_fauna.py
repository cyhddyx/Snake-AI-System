# scripts/import_fauna.py
"""
Import snake data from 《中国动物志爬行纲第三卷》 into knowledge base.

Parses the MD file and extracts structured data for each snake species,
then integrates with the RAG knowledge system.
"""

import json
import re
import sys
import os
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import BASE_DIR

FAUNA_MD_PATH = BASE_DIR / "中国动物志爬行纲第三卷有鳞目蛇亚目FAUNASINICA-REPTILIAVol.3SquamataSerpentes(赵尔宓ZHAOErmi等etal.)(Z-Library)" / "auto" / "中国动物志爬行纲第三卷有鳞目蛇亚目FAUNASINICA-REPTILIAVol.3SquamataSerpentes(赵尔宓ZHAOErmi等etal.)(Z-Library).md"
OUTPUT_JSON_PATH = BASE_DIR / "data" / "fauna_snakes.json"


def parse_latin_name(header_line: str) -> tuple[str, str, str]:
    """Extract Chinese name, Latin name, and author info from species header."""
    match = re.search(
        r'^#\s*[（(](\d+)[)）]\s*(.+?)\s+([A-Z][a-z]+\s+[a-z]+(?:\s+[a-z]+)?)\s*(.*)$',
        header_line.strip()
    )
    if match:
        seq_num = match.group(1)
        chinese_name = match.group(2).strip()
        latin_name = match.group(3).strip()
        author_info = match.group(4).strip()
        return chinese_name, latin_name, author_info
    return "", "", ""


def extract_section(content: str, section_name: str, next_sections: list[str]) -> str:
    """Extract a specific section from the content."""
    pattern = rf'{section_name}[:\s]*(.*?)(?={"|".join(next_sections)}|$)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def find_all_species_blocks(content: str) -> list[dict]:
    """Find all species blocks in the MD content."""
    species_pattern = re.compile(
        r'^#\s*[（(](\d+)[)）]\s*(.+?\n(?:.*?\n)*?)(?=^#\s*[（(]\d+[)）]|^#\s*\d+[．.]|^#\s*[IVX]+[．.]|$)',
        re.MULTILINE
    )
    
    blocks = []
    for match in species_pattern.finditer(content):
        seq_num = match.group(1)
        block_content = match.group(2)
        blocks.append({
            'seq_num': int(seq_num),
            'content': block_content,
            'start': match.start(),
            'end': match.end()
        })
    
    return blocks


def parse_species_block(block: dict, current_family: str, current_genus: str) -> Optional[dict]:
    """Parse a single species block and extract structured data."""
    content = block['content']
    lines = content.split('\n')
    
    if not lines:
        return None
    
    header = lines[0]
    chinese_name, latin_name, author_info = parse_latin_name(f"# （{block['seq_num']}）{header}")
    
    if not chinese_name or not latin_name:
        alt_match = re.match(r'^([^\s]+)\s+([A-Z][a-z]+\s+[a-z]+)', header)
        if alt_match:
            chinese_name = alt_match.group(1)
            latin_name = alt_match.group(2)
        else:
            return None
    
    remaining_content = '\n'.join(lines[1:])
    
    aliases = []
    alias_match = re.search(r'地方名[：:]\s*(.+?)(?:\n|鉴别特征|$)', remaining_content)
    if alias_match:
        alias_text = alias_match.group(1)
        aliases = [a.strip() for a in re.split(r'[、，,]', alias_text) if a.strip()]
    
    # 定义所有可能的字段标记及其变体
    field_patterns = [
        ('地方名', r'地方名[：:]\s*(.+?)(?=\n\S|$)'),
        ('鉴别特征', r'鉴别特征[：:\s]*(.+?)(?=\n(?:描述依据标本|描述依据|形态描述|生物学资料|垂直分布|地理分布|经济意义|分类讨论|种下分类|保护问题|$))'),
        ('描述依据标本', r'描述依据标本[：:\s]*(.+?)(?=\n(?:鉴别特征|形态描述|生物学资料|垂直分布|地理分布|经济意义|分类讨论|种下分类|保护问题|$))'),
        ('描述依据', r'描述依据[：:\s]*(.+?)(?=\n(?:鉴别特征|形态描述|生物学资料|垂直分布|地理分布|经济意义|分类讨论|种下分类|保护问题|$))'),
        ('形态描述', r'形态描述[：:\s]*(.+?)(?=\n(?:鉴别特征|描述依据标本|描述依据|生物学资料|垂直分布|地理分布|经济意义|分类讨论|种下分类|保护问题|$))'),
        ('生物学资料', r'生物学资料[：:\s]*(.+?)(?=\n(?:鉴别特征|描述依据标本|描述依据|形态描述|垂直分布|地理分布|经济意义|分类讨论|种下分类|保护问题|$))'),
        ('垂直分布', r'垂直分布[：:\s]*(.+?)(?=\n(?:鉴别特征|描述依据标本|描述依据|形态描述|生物学资料|地理分布|经济意义|分类讨论|种下分类|保护问题|$))'),
        ('地理分布', r'地理分布[：:\s]*(.+?)(?=\n(?:鉴别特征|描述依据标本|描述依据|形态描述|生物学资料|垂直分布|经济意义|分类讨论|种下分类|保护问题|$))'),
        ('经济意义', r'经济意义[：:\s]*(.+?)(?=\n(?:鉴别特征|描述依据标本|描述依据|形态描述|生物学资料|垂直分布|地理分布|分类讨论|种下分类|保护问题|$))'),
        ('分类讨论', r'分类讨论[：:\s]*(.+?)(?=\n(?:鉴别特征|描述依据标本|描述依据|形态描述|生物学资料|垂直分布|地理分布|经济意义|种下分类|保护问题|$))'),
        ('种下分类', r'种下分类[：:\s]*(.+?)(?=\n(?:鉴别特征|描述依据标本|描述依据|形态描述|生物学资料|垂直分布|地理分布|经济意义|分类讨论|保护问题|$))'),
        ('保护问题', r'保护问题[：:\s]*(.+?)(?=\n(?:鉴别特征|描述依据标本|描述依据|形态描述|生物学资料|垂直分布|地理分布|经济意义|分类讨论|种下分类|$))'),
    ]
    
    # 初始化所有字段为空
    field_values = {name: '' for name, _ in field_patterns}
    
    # 提取字段内容
    for field_name, pattern in field_patterns:
        match = re.search(pattern, remaining_content, re.DOTALL)
        if match:
            field_values[field_name] = match.group(1).strip()
    
    # 别名已单独提取，这里只需获取其他字段
    identification = field_values['鉴别特征']
    specimen_info = field_values['描述依据标本'] or field_values['描述依据']
    morphology = field_values['形态描述']
    biology = field_values['生物学资料']
    vertical_dist = field_values['垂直分布']
    distribution = field_values['地理分布']
    economic = field_values['经济意义']
    conservation = field_values['保护问题']
    
    # 处理地理分布中的国内/国外分布
    domestic_dist = ""
    abroad_dist = ""
    if distribution:
        # 尝试提取国外分布
        abroad_match = re.search(r'国外分布于[：:]?\s*(.+?)(?:\n|$)', distribution, re.DOTALL)
        if abroad_match:
            abroad_dist = abroad_match.group(1).strip()
            # 国内分布是国外分布之前的部分
            domestic_dist = distribution[:abroad_match.start()].strip()
            # 清理国内分布字符串，移除可能的前缀
            domestic_dist = re.sub(r'^地理分布[：:\s]*', '', domestic_dist)
        else:
            domestic_dist = distribution
            domestic_dist = re.sub(r'^地理分布[：:\s]*', '', domestic_dist)
    
    original_text = remaining_content.strip()
    
    venom_type = "未知"
    if current_family:
        if '眼镜蛇科' in current_family:
            if '扁尾海蛇亚科' in current_family or '海蛇亚科' in current_family:
                venom_type = "剧毒"
            else:
                venom_type = "剧毒"
        elif '蝰科' in current_family:
            venom_type = "剧毒"
        elif '游蛇科' in current_family:
            if '颈槽蛇属' in current_genus or 'Rhabdophis' in latin_name:
                venom_type = "后毒牙，有毒"
            elif '林蛇属' in current_genus or 'Boiga' in latin_name:
                venom_type = "后毒牙，有毒"
            elif '紫沙蛇属' in current_genus or 'Psammodynastes' in latin_name:
                venom_type = "后毒牙，有毒"
            elif '花条蛇属' in current_genus or 'Psammophis' in latin_name:
                venom_type = "后毒牙，有毒"
            elif '金花蛇属' in current_genus or 'Chrysopelea' in latin_name:
                venom_type = "后毒牙，微毒"
            elif '瘦蛇属' in current_genus or 'Ahaetulla' in latin_name:
                venom_type = "后毒牙，微毒"
            elif '水蛇属' in current_genus or 'Enhydris' in latin_name:
                venom_type = "后毒牙，微毒"
            else:
                venom_type = "无毒"
        elif '盲蛇科' in current_family:
            venom_type = "无毒"
        elif '蟒科' in current_family:
            venom_type = "无毒"
        elif '闪鳞蛇科' in current_family:
            venom_type = "无毒"
        elif '瘰鳞蛇科' in current_family:
            venom_type = "无毒"
        elif '盾尾蛇科' in current_family:
            venom_type = "无毒"
    
    return {
        'id': f"fauna_{block['seq_num']:03d}",
        'chinese_name': chinese_name,
        'latin_name': latin_name,
        'author_info': author_info,
        'family': current_family,
        'genus': current_genus,
        'aliases': aliases,
        'venom_type': venom_type,
        'identification': identification,
        'specimen_info': specimen_info,
        'morphology': morphology,
        'biology': biology,
        'vertical_distribution': vertical_dist,
        'distribution': domestic_dist,
        'distribution_abroad': abroad_dist,
        'economic_value': economic,
        'conservation': conservation,
        'source': '中国动物志爬行纲第三卷',
        'original_text': original_text
    }


def find_family_and_genus(content: str, position: int) -> tuple[str, str]:
    """Find the current family and genus based on position in document."""
    family_pattern = re.compile(
        r'^#\s*[IVX]+[．.．]\s*(.+?科)\s*[A-Z]+',
        re.MULTILINE
    )
    subfamily_pattern = re.compile(
        r'^#\s*(.+?亚科)\s*[A-Z]+',
        re.MULTILINE
    )
    genus_pattern = re.compile(
        r'^#\s*\d+[．.．]\s*(.+?属)\s+[A-Z]',
        re.MULTILINE
    )
    
    current_family = ""
    current_genus = ""
    
    for match in family_pattern.finditer(content):
        if match.start() < position:
            current_family = match.group(1).strip()
    
    for match in subfamily_pattern.finditer(content):
        if match.start() < position:
            if current_family:
                current_family = current_family.split('（')[0].strip() + f"（{match.group(1)}）"
            else:
                current_family = match.group(1).strip()
    
    for match in genus_pattern.finditer(content):
        if match.start() < position:
            current_genus = match.group(1).strip()
    
    return current_family, current_genus


def parse_fauna_md(filepath: Path) -> list[dict]:
    """Parse the full fauna MD file and extract all snake species data."""
    print(f"[INFO] Reading: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"[INFO] File size: {len(content)} characters")
    
    species_blocks = find_all_species_blocks(content)
    print(f"[INFO] Found {len(species_blocks)} species blocks")
    
    species_list = []
    for i, block in enumerate(species_blocks):
        family, genus = find_family_and_genus(content, block['start'])
        species_data = parse_species_block(block, family, genus)
        
        if species_data:
            species_list.append(species_data)
            if (i + 1) % 20 == 0:
                print(f"  [PROGRESS] Parsed {i + 1}/{len(species_blocks)} species...")
    
    print(f"\n[SUCCESS] Parsed {len(species_list)} species")
    return species_list


def save_to_json(species_list: list[dict], output_path: Path):
    """Save the parsed data to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(species_list, f, ensure_ascii=False, indent=2)
    
    print(f"[SAVED] Output: {output_path}")


def print_summary(species_list: list[dict]):
    """Print a summary of the parsed data."""
    families = {}
    for s in species_list:
        fam = s.get('family', '未知') or '未知'
        families[fam] = families.get(fam, 0) + 1
    
    print("\n" + "=" * 50)
    print("SUMMARY BY FAMILY:")
    print("=" * 50)
    for fam, count in sorted(families.items(), key=lambda x: -x[1]):
        print(f"  {fam}: {count}种")
    print("=" * 50)
    print(f"TOTAL: {len(species_list)}种")
    
    print("\nSAMPLE (first 3):")
    for i, s in enumerate(species_list[:3]):
        print(f"\n{i+1}. {s['chinese_name']} ({s['latin_name']})")
        print(f"   科: {s['family']}")
        print(f"   属: {s['genus']}")
        print(f"   毒性: {s['venom_type']}")
        print(f"   别名: {s['aliases']}")


def main():
    """Main entry point."""
    print("=" * 60)
    print("FAUNA SINICA SNAKE DATA IMPORTER")
    print("=" * 60)
    
    if not FAUNA_MD_PATH.exists():
        print(f"[ERROR] File not found: {FAUNA_MD_PATH}")
        return
    
    species_list = parse_fauna_md(FAUNA_MD_PATH)
    
    if species_list:
        save_to_json(species_list, OUTPUT_JSON_PATH)
        print_summary(species_list)
    else:
        print("[ERROR] No species data extracted")


if __name__ == "__main__":
    main()
