import os
import json
import re
from pathlib import Path

# 使用相对路径定位
PROJECT_ROOT = Path(__file__).parent.absolute()
BASE_DIR = PROJECT_ROOT / "pools"  # pools根目录
JIUSAIJI_DIR = BASE_DIR / "jiusaiji"  # 结果目录
LIST_JSON_PATH = JIUSAIJI_DIR / "list.json"
EXTRA_JSON_PATH = JIUSAIJI_DIR / "extra.json"
OUTPUT_POOL_PATH = JIUSAIJI_DIR / "pool.json"

print(f"Looking for list.json at: {LIST_JSON_PATH}")
print(f"Looking for extra.json at: {EXTRA_JSON_PATH}")
print(f"Scanning base directory: {BASE_DIR}")

# 检查必要文件是否存在
if not EXTRA_JSON_PATH.exists():
    print(f"❌ Error: extra.json not found at {EXTRA_JSON_PATH}")
    exit(1)

# 读取需要排除的文件夹列表
excluded_folders = set()
if LIST_JSON_PATH.exists():
    try:
        with open(LIST_JSON_PATH, "r", encoding="utf-8") as f:
            list_content = json.load(f)
            # 支持两种格式：数组或对象中的exclude字段
            if isinstance(list_content, list):
                excluded_folders = set(list_content)
            elif isinstance(list_content, dict) and "exclude" in list_content:
                excluded_folders = set(list_content["exclude"])
            print(f"Excluded folders: {excluded_folders}")
    except Exception as e:
        print(f"Warning: Failed to read list.json: {e}")

# 获取所有潜在的池子
potential_pools = []

# 更灵活的正则表达式定义分类规则
pattern_type_b = re.compile(r"^S\d{1,2}Rank$")
pattern_type_a_file = re.compile(r"^S\d{1,2}E\d{1,2}$")  # 注意这里不带.json，因为是文件夹名

print(f"\n=== Scanning for pools in {BASE_DIR} ===")
# 遍历 pools 根目录下的所有文件夹，收集所有符合条件的池子
for entry in BASE_DIR.iterdir():
    entry_name = entry.name
    print(f"Checking: {entry_name} (is_dir: {entry.is_dir()}, is_file: {entry.is_file()})")
    
    # 排除 jiusaiji 和其他系统文件夹
    if entry_name == "jiusaiji":
        print(f"  -> Skipping result directory: {entry_name}")
        continue
    
    # 排除在 list.json 中明确提到的文件夹
    if entry_name in excluded_folders:
        print(f"  -> Skipping excluded item: {entry_name}")
        continue

    if entry.is_dir():
        if pattern_type_b.match(entry_name):
            # 符合 SxRank 或 SxxRank 形式的文件夹 -> typeB
            pool_json_path = entry / "pool.json"
            if pool_json_path.exists():
                potential_pools.append({
                    "type": "B",
                    "path": entry,
                    "name": entry_name
                })
                print(f"  -> Found B-type pool: {entry_name}")
            else:
                print(f"  -> Folder matches pattern but no pool.json: {entry_name}")
        elif pattern_type_a_file.match(entry_name):
            # 符合 SxEyy 或 SxxEyy 形式的文件夹 -> typeA
            pool_json_path = entry / "pool.json"
            if pool_json_path.exists():
                potential_pools.append({
                    "type": "A",
                    "path": entry,
                    "name": entry_name
                })
                print(f"  -> Found A-type pool: {entry_name}")
            else:
                print(f"  -> Folder matches pattern but no pool.json: {entry_name}")

print(f"\nTotal pools to process: {len(potential_pools)}")
for pool in potential_pools:
    print(f"  - {pool['type']}-type: {pool['name']}")

# 读取 extra.json 获取 C、D 品质物品
with open(EXTRA_JSON_PATH, "r", encoding="utf-8") as f:
    extra_data = json.load(f)

# 提取 C、D 品质物品（仅来自 extra.json）
extra_c_items = extra_data.get("C", [])
extra_d_items = extra_data.get("D", [])

print(f"\nLoaded {len(extra_c_items)} C items and {len(extra_d_items)} D items from extra.json")

# 初始化合并池（暂时不含 C）
merged_pool = {
    "S": [],
    "A": [],
    "B": [],
    "D": extra_d_items  # D 只来源于 extra.json
}

# 记录收集到的 C 类型物品
collected_c_items = []

# 定义各稀有度的过滤规则函数
def filter_items_by_rarity(items, rarity, pool_category):
    """
    根据池子类别和稀有度进行筛选
    """
    filtered = []

    if rarity == "A":
        if pool_category == "A":
            filtered = [item for item in items if item.get("type") == "时装"]
    elif rarity == "S":
        if pool_category == "S":
            filtered = [item for item in items if item.get("type") == "随身物品"]
    elif rarity == "B":
        allowed_types = {"等待动作", "个性动作", "时装"}
        filtered = [item for item in items if item.get("type") in allowed_types]
    elif rarity == "C":
        allowed_types = {"等待动作", "个性动作", "时装"}
        filtered = [item for item in items if item.get("type") in allowed_types]

    return filtered

print("\n=== Processing pools ===")
# 处理所有找到的池子
for pool_info in potential_pools:
    pool_type = pool_info["type"]
    pool_path = pool_info["path"]
    pool_name = pool_info["name"]
    
    print(f"\nProcessing {pool_type}-type pool: {pool_name}")
    
    pool_json_path = pool_path / "pool.json"
    print(f"  Looking for pool.json at: {pool_json_path}")
    
    try:
        with open(pool_json_path, 'r', encoding='utf-8') as f:
            pool_data = json.load(f)
        print(f"  -> Loaded pool data successfully")
    except Exception as e:
        print(f"  -> [ERROR] Failed to load pool.json in {pool_path}: {e}")
        continue

    pool_items = pool_data.get("items", {})
    print(f"  -> Pool items keys: {list(pool_items.keys())}")
    
    # 根据池子类型应用不同的过滤规则
    category = "A" if pool_type == "A" else "S"
    
    for rarity in ["S", "A", "B", "C"]:
        raw_items = pool_items.get(rarity, [])
        filtered_items = filter_items_by_rarity(raw_items, rarity, category)
        print(f"  -> Rarity {rarity}: {len(raw_items)} raw, {len(filtered_items)} filtered")
        
        if rarity == "C":
            collected_c_items.extend(filtered_items)
        else:
            merged_pool[rarity].extend(filtered_items)

print(f"\n=== Final results ===")
print(f"C items collected: {len(collected_c_items)}")
print(f"A items: {len(merged_pool['A'])}")
print(f"B items: {len(merged_pool['B'])}")
print(f"S items: {len(merged_pool['S'])}")
print(f"D items: {len(merged_pool['D'])}")

# 合并 collected_c_items 和 extra_c_items 并去重
merged_pool["C"] = extra_c_items + collected_c_items

seen_keys = set()
unique_merged_pool = {}
for rarity, items in merged_pool.items():
    unique_items = []
    for item in items:
        if isinstance(item, dict) and "name" in item and "type" in item:
            key = (item["name"], item["type"])
            if key not in seen_keys:
                seen_keys.add(key)
                unique_items.append(item)
        else:
            print(f"[WARNING] Invalid item format skipped: {item}")
    unique_merged_pool[rarity] = unique_items
    print(f"Final count for rarity {rarity}: {len(unique_merged_pool[rarity])} items")

# 构造最终输出结构
existing_config = {}
existing_pool_path = JIUSAIJI_DIR / "pool.json"
if existing_pool_path.exists():
    try:
        with open(existing_pool_path, "r", encoding="utf-8") as f:
            existing_config = json.load(f)
    except:
        pass

# 读取 list.json 中的基础配置信息
base_config = {}
if LIST_JSON_PATH.exists():
    try:
        with open(LIST_JSON_PATH, "r", encoding="utf-8") as f:
            list_content = json.load(f)
            if isinstance(list_content, dict):
                base_config = list_content
    except:
        pass

output_data = {
    "id": base_config.get("id", existing_config.get("id", "jiusaiji")),
    "name": base_config.get("name", existing_config.get("name", "记忆珍宝·旧赛季")),
    "essenceImage": base_config.get(
        "essenceImage",
        existing_config.get(
            "essenceImage",
            "/resource/f8d697b2b3c07042082adeb9fdc12737.png"
        )
    ),
    "pitySettings": base_config.get("pitySettings", existing_config.get("pitySettings", {
        "gold": 250,
        "purple": 60,
        "blue": 10
    })),
    "items": unique_merged_pool,
    "diff_A": base_config.get("diff_A", existing_config.get("diff_A", 0)),
    "discounts": base_config.get("discounts", existing_config.get("discounts", [])),
    "fragmentsInfo": base_config.get("fragmentsInfo", existing_config.get("fragmentsInfo", {
        "name": "碎片",
        "img": "/resource/abb5919fc5926eb8e2da46469ff98487.png"
    }))
}

# 写入输出文件
try:
    with open(OUTPUT_POOL_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ SUCCESS: Merged pool generated at: {OUTPUT_POOL_PATH}")
except Exception as e:
    print(f"❌ Failed to write output file: {e}")
