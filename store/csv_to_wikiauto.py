#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 wiki_store_items.csv 转换为 wikiauto.json 格式
"""

import csv
import json
import re

# 货币名称映射
CURRENCY_MAP = {
    "回声": "inspiration",  # 回声视作灵感
    "灵感": "inspiration",
    "碎片": "fragments",
    "线索": "clue",
    "火气": "huoqi",
    "火漆": "huoqi",
    "赛季珍宝": "rank_treasure",
    "记忆珍宝": "rank_treasure",
}

# 默认图片
DEFAULT_IMG = "https://patchwiki.biligame.com/images/dwrg/thumb/4/41/h7j1qqr29rcsubf0nxfm8w9uduna7nt.png/120px-%E7%AC%AC%E5%9B%9B%E5%8D%81%E4%B8%80%E8%B5%9B%E5%AD%A3%C2%B7%E7%B2%BE%E5%8D%8E1.png"

# 品质映射到稀有度
QUALITY_RARITY_MAP = {
    "稀世": "S",
    "奇珍": "A",
    "独特": "B",
    "罕见": "C",
}

def get_rarity_from_quality(quality: str, prices: list) -> str:
    """
    根据品质和价格返回稀有度
    映射：稀世->S, 奇珍->A, 独特->B, 罕见->C
    
    如果没有品质信息，根据价格判断：
    - 价格 > 1500 回声 → 稀世（S）
    - 价格 > 800 回声 → 奇珍（A）
    - 其余 → 独特（B）
    """
    # 优先使用品质信息
    if quality:
        return QUALITY_RARITY_MAP.get(quality.strip(), "C")
    
    # 没有品质信息，根据价格判断
    if not prices:
        return "B"  # 默认独特
    
    # 找到回声价格（回声映射为inspiration）
    for price in prices:
        if price.get("currency") == "inspiration":
            amount = price.get("amount", 0)
            if amount > 1500:
                return "S"  # 稀世
            elif amount > 800:
                return "A"  # 奇珍
    
    return "B"  # 默认独特

def clean_item_type(item_type: str) -> str:
    """
    清理物品类型，移除多余的关键词
    """
    if not item_type:
        return "商品"
    
    # 需要移除的关键词
    keywords_to_remove = ["限时", "限定", "奇珍", "稀世", "独特", "罕见", "品质", "商城"]
    
    result = item_type
    for keyword in keywords_to_remove:
        result = result.replace(keyword, "")
    
    # 清理多余的空格
    result = result.strip()
    
    # 如果清理后为空，返回默认值
    if not result:
        return "商品"
    
    return result

def parse_price(price_str: str) -> dict:
    """
    解析价格字符串，返回货币类型和数量
    例如: "1388回声" -> {"currency": "echo", "amount": 1388}
    """
    if not price_str:
        return None
    
    price_str = price_str.strip()
    
    # 尝试匹配: 数字+货币名
    # 例如: 1388回声, 100灵感, 50碎片
    for currency_name, currency_key in CURRENCY_MAP.items():
        pattern = r'(\d+)\s*' + re.escape(currency_name)
        match = re.search(pattern, price_str)
        if match:
            return {
                "currency": currency_key,
                "amount": int(match.group(1))
            }
    
    # 尝试匹配: 货币名+数字
    # 例如: 回声1388
    for currency_name, currency_key in CURRENCY_MAP.items():
        pattern = re.escape(currency_name) + r'\s*(\d+)'
        match = re.search(pattern, price_str)
        if match:
            return {
                "currency": currency_key,
                "amount": int(match.group(1))
            }
    
    # 尝试直接提取数字和中文
    match = re.search(r'(\d+)\s*([^\d\s]+)', price_str)
    if match:
        amount = int(match.group(1))
        currency_name = match.group(2)
        # 尝试映射
        for cn_name, currency_key in CURRENCY_MAP.items():
            if cn_name in currency_name:
                return {
                    "currency": currency_key,
                    "amount": amount
                }
    
    return None

def generate_id(name: str, index: int) -> str:
    """
    生成商品ID
    """
    # 简单处理：移除特殊字符，转为拼音或使用序号
    # 这里使用序号：wiki_001, wiki_002, ...
    return f"wiki_{index:03d}"

def csv_to_wikiauto(csv_file: str, output_file: str = "wikiauto_from_wiki.json"):
    """
    将CSV转换为wikiauto格式
    """
    items = []
    
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for index, row in enumerate(reader, 1):
            name = row.get("名称", "").strip()
            quality = row.get("品质", "").strip()
            price_str = row.get("商城价格", "").strip()
            price_str2 = row.get("商城价格2", "").strip()
            description = row.get("具体描述", "").strip()
            item_type = row.get("物品类型", "").strip()
            
            # 跳过空名称
            if not name:
                continue
            
            # 清理物品类型
            item_type = clean_item_type(item_type)
            
            # 解析价格（支持多种支付方式）
            prices = []
            parsed_price = parse_price(price_str)
            if parsed_price:
                prices.append(parsed_price)
            
            # 解析第二种价格
            if price_str2:
                parsed_price2 = parse_price(price_str2)
                if parsed_price2:
                    prices.append(parsed_price2)
            
            # 跳过没有价格的商品
            if not prices:
                print(f"✗ [{index}] {name} - 无商城价格，跳过")
                continue
            
            # 构建商品对象
            item = {
                "id": generate_id(name, index),
                "name": name,
                "type": item_type or "商品",
                "rarity": get_rarity_from_quality(quality, prices),
                "img": DEFAULT_IMG,
                "description": description,
                "prices": prices,
                "tag": "新品",
                "discount": "",
                "timeLeft": "",
                "limit": 1
            }
            
            items.append(item)
            price_display = " / ".join([f"{p['currency']}:{p['amount']}" for p in prices]) if prices else "无"
            print(f"✓ [{index}] {name} - {price_display}")
    
    # 输出JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    
    print(f"\n转换完成！共 {len(items)} 条记录")
    print(f"输出文件: {output_file}")
    
    return items

def main():
    """
    主函数
    """
    csv_file = "wiki_store_items.csv"
    output_file = "wikiauto.json"
    
    print("=" * 60)
    print("将 CSV 转换为 wikiauto.json 格式")
    print("=" * 60)
    
    try:
        csv_to_wikiauto(csv_file, output_file)
    except FileNotFoundError:
        print(f"错误: 找不到文件 {csv_file}")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    main()