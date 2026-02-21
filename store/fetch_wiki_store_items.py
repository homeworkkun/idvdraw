#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 Mediawiki API 读取"分类:商城新品"的信息并输出为 CSV
"""

import requests
import csv
import re
import json
import time
from typing import List, Dict, Optional
from urllib.parse import quote

# API 配置
API_URL = "/resource/32d03bbcb9749c9731a67ab38778d950.php"
CATEGORY_NAME = "商城新品"
MAX_ITEMS = None  # 设置为数字可限制读取的页面数，None 表示读取全部

# 请求头配置
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "/resource/99b81b5b0f42f69db80d3289ca2c27fe.html",
    "Origin": "/resource/052624179b597323f46bc3b02e98aad6.html"
}

def fetch_category_members(category: str) -> List[str]:
    """
    获取指定分类下的所有页面标题
    """
    print(f"正在获取分类: {category} 下的页面...")
    
    members = []
    cmcontinue = ""
    
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmlimit": "500",
            "format": "json"
        }
        
        if cmcontinue:
            params["cmcontinue"] = cmcontinue
        
        response = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
        
        # 检查响应状态
        if response.status_code != 200:
            print(f"  错误: HTTP {response.status_code}")
            print(f"  响应内容: {response.text[:500]}")
            break
        
        # 检查是否返回 JSON
        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"  错误: 无法解析 JSON 响应")
            print(f"  响应内容: {response.text[:500]}")
            break
        
        if "query" in data and "categorymembers" in data["query"]:
            for member in data["query"]["categorymembers"]:
                if member.get("ns") == 0:  # 只获取主命名空间的页面
                    members.append(member["title"])
        
        if "continue" in data and "cmcontinue" in data["continue"]:
            cmcontinue = data["continue"]["cmcontinue"]
        else:
            break
    
    print(f"找到 {len(members)} 个页面")
    return members

def parse_template_params(content: str) -> Dict[str, str]:
    """
    解析模板参数
    支持格式: {{模板名|参数1=值1|参数2=值2}}
    """
    params = {}
    
    # 尝试匹配商城模板或其他相关模板
    # 常见模板名: 商城信息、商城、商品、Shop等
    patterns = [
        r'\{\{商城信息\s*\|([^}]+)\}\}',
        r'\{\{商城\s*\|([^}]+)\}\}',
        r'\{\{商品\s*\|([^}]+)\}\}',
        r'\{\{Shop\s*\|([^}]+)\}\}',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            param_str = match.group(1)
            # 解析参数
            for item in re.split(r'\|\s*', param_str.strip()):
                item = item.strip()
                if '=' in item:
                    key, value = item.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # 移除模板嵌套和链接标记
                    value = re.sub(r'\[\[([^\]|]+)(\|[^\]]+)?\]\]', r'\1', value)
                    value = re.sub(r'\{\{([^|}]+)(\|[^}]*)?\}\}', '', value)
                    # 移除 HTML 标签
                    value = re.sub(r'<[^>]+>', '', value)
                    value = value.strip()
                    if key and value:
                        params[key] = value
    
    return params

def extract_item_info(title: str, content: str) -> Dict[str, str]:
    """
    从页面内容中提取物品信息
    """
    params = parse_template_params(content)
    
    # 映射可能的各种参数名到标准字段
    info = {
        "名称": title,
        "品质": "",
        "商城价格": "",
        "具体描述": "",
        "物品类型": ""
    }
    
    # 品质字段可能的名称
    quality_keys = ["品质", "quality", "稀有度", "rarity"]
    for key in quality_keys:
        if key in params and params[key]:
            info["品质"] = params[key]
            break
    
    # 价格字段可能的名称
    price_keys = ["商城价格", "价格", "price", "售价", "cost", "costPrice", "costprice"]
    for key in price_keys:
        if key in params and params[key]:
            info["商城价格"] = params[key]
            break
    
    # 描述字段可能的名称
    desc_keys = ["具体描述", "描述", "description", "desc", "简介", "介绍"]
    for key in desc_keys:
        if key in params and params[key]:
            info["具体描述"] = params[key]
            break
    
    # 类型字段可能的名称
    type_keys = ["物品类型", "类型", "type", "物品", "category"]
    for key in type_keys:
        if key in params and params[key]:
            info["物品类型"] = params[key]
            break
    
    # 如果模板解析失败，尝试从页面内容中提取
    if not info["具体描述"]:
        # 尝试从页面内容中找到描述
        desc_match = re.search(r'具体描述\s*[=：]\s*([^\n|]+)', content)
        if desc_match:
            info["具体描述"] = desc_match.group(1).strip()
    
    # 尝试从物品类型中提取品质（如"奇珍品质时装"中的"奇珍"）
    if not info["品质"] and info["物品类型"]:
        quality_match = re.search(r'(奇珍|稀世|独特|罕见|普通)品质', info["物品类型"])
        if quality_match:
            info["品质"] = quality_match.group(1)
    
    return info

def fetch_pages_batch(titles: List[str]) -> Dict[str, Optional[str]]:
    """
    批量获取多个页面内容
    返回字典: {标题: 内容}
    """
    if not titles:
        return {}
    
    # Mediawiki API 支持用 | 分隔多个标题
    titles_str = "|".join(titles)
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "titles": titles_str,
        "format": "json"
    }
    
    result = {}
    
    try:
        response = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
        
        # 检查响应状态
        if response.status_code != 200:
            print(f"  批量请求错误: HTTP {response.status_code}")
            return {title: None for title in titles}
        
        # 检查是否返回 JSON
        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"  批量请求错误: 无法解析 JSON 响应")
            return {title: None for title in titles}
        
        # 检查页面是否存在
        if "query" in data and "pages" in data["query"]:
            pages = data["query"]["pages"]
            for page_id, page_data in pages.items():
                title = page_data.get("title", "")
                if "missing" in page_data:
                    result[title] = None
                elif "revisions" in page_data:
                    result[title] = page_data["revisions"][0]["slots"]["main"]["*"]
                else:
                    result[title] = None
        
        # 为没有返回的页面填充 None
        for title in titles:
            if title not in result:
                result[title] = None
        
        return result
    except Exception as e:
        print(f"批量获取页面内容失败: {e}")
        return {title: None for title in titles}

def main():
    """
    主函数
    """
    print("=" * 60)
    print("从 Mediawiki API 读取商城新品信息")
    print("=" * 60)
    
    # 1. 获取分类下的所有页面
    page_titles = fetch_category_members(CATEGORY_NAME)
    
    if not page_titles:
        print("未找到任何页面")
        return
    
    # 限制读取数量（用于测试）
    if MAX_ITEMS and len(page_titles) > MAX_ITEMS:
        page_titles = page_titles[:MAX_ITEMS]
        print(f"（限制模式：仅读取前 {MAX_ITEMS} 个页面）")
    
    # 2. 批量获取页面信息（一次10个）
    BATCH_SIZE = 10
    items = []
    
    total_batches = (len(page_titles) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_num in range(total_batches):
        start_idx = batch_num * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, len(page_titles))
        batch_titles = page_titles[start_idx:end_idx]
        
        print(f"\n正在获取批次 {batch_num + 1}/{total_batches} (第 {start_idx + 1}-{end_idx} 个页面)...")
        
        # 批量获取页面内容
        batch_contents = fetch_pages_batch(batch_titles)
        
        # 处理每个页面
        for title in batch_titles:
            content = batch_contents.get(title)
            if content:
                item_info = extract_item_info(title, content)
                items.append(item_info)
                print(f"  ✓ {title}")
            else:
                print(f"  ✗ {title} (无法获取内容)")
        
        # 批次之间间隔1秒（除了最后一批）
        if batch_num < total_batches - 1:
            time.sleep(1)
    
    # 3. 输出为 CSV
    output_file = "wiki_store_items.csv"
    print(f"\n正在写入 CSV 文件: {output_file}")
    
    fieldnames = ["名称", "品质", "商城价格", "具体描述", "物品类型"]
    
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(items)
    
    print(f"完成! 共写入 {len(items)} 条记录")
    print(f"输出文件: {output_file}")

if __name__ == "__main__":
    main()