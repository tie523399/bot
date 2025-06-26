#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化資料庫腳本
"""

from models import Base, engine, SessionLocal, Category, Product, Option
import random

def init_database():
    """初始化資料庫並添加範例數據"""
    print("正在初始化資料庫...")
    
    # 創建所有表格
    Base.metadata.create_all(engine)
    print("✅ 資料表創建完成")
    
    # 創建會話
    session = SessionLocal()
    
    # 檢查是否已有數據
    if session.query(Category).count() > 0:
        print("資料庫已有數據，跳過初始化")
        session.close()
        return
    
    # 創建分類
    categories = [
        {
            "name": "海水", 
            "icon": "🌊", 
            "order": 1,
            "description": "新鮮海水產品",
            "photo_1": "https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=800",
            "photo_2": "https://images.unsplash.com/photo-1682687220742-aba13b6e50ba?w=800",
            "photo_3": "https://images.unsplash.com/photo-1518837695005-2083093ee35b?w=800"
        },
        {
            "name": "不可", 
            "icon": "🚫", 
            "order": 2,
            "description": "特殊商品分類",
            "photo_1": "https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=800"
        },
        {
            "name": "斗量", 
            "icon": "⚖️", 
            "order": 3,
            "description": "計量販售商品",
            "photo_1": "https://images.unsplash.com/photo-1587049352846-4a222e784914?w=800",
            "photo_2": "https://images.unsplash.com/photo-1609692814858-f7cd2f0afa4f?w=800"
        },
        {"name": "淡水", "icon": "💧", "order": 4, "description": "淡水魚類產品"},
        {"name": "飼料", "icon": "🦐", "order": 5, "description": "各類魚飼料"},
        {"name": "設備", "icon": "🔧", "order": 6, "description": "水族設備"}
    ]
    
    category_objs = {}
    for cat_data in categories:
        cat = Category(
            name=cat_data["name"],
            icon=cat_data["icon"],
            order=cat_data["order"],
            display_order=cat_data["order"],
            description=cat_data.get("description", ""),
            is_active=True
        )
        
        # 添加照片URL（如果有）
        for i in range(1, 6):
            photo_key = f"photo_{i}"
            if photo_key in cat_data:
                setattr(cat, photo_key, cat_data[photo_key])
        
        session.add(cat)
        category_objs[cat_data["name"]] = cat
    
    session.flush()
    print(f"✅ 創建了 {len(categories)} 個分類")
    
    # 創建商品數據
    products_data = [
        # 海水類
        {"name": "小丑魚", "price": 200, "stock": 50, "category": "海水", "desc": "尼莫同款，活潑可愛"},
        {"name": "藍倒吊", "price": 800, "stock": 20, "category": "海水", "desc": "藍色優雅，需要大缸"},
        {"name": "黃倒吊", "price": 600, "stock": 25, "category": "海水", "desc": "黃色亮麗，易養"},
        {"name": "火焰仙", "price": 1200, "stock": 10, "category": "海水", "desc": "紅色火焰，觀賞價值高"},
        {"name": "皇帝神仙", "price": 2000, "stock": 5, "category": "海水", "desc": "高貴優雅，需要經驗"},
        
        # 淡水類
        {"name": "孔雀魚", "price": 50, "stock": 200, "category": "淡水", "desc": "入門首選，繁殖容易"},
        {"name": "鬥魚", "price": 100, "stock": 100, "category": "淡水", "desc": "美麗好養，需單獨飼養"},
        {"name": "神仙魚", "price": 150, "stock": 80, "category": "淡水", "desc": "優雅美麗，需要高缸"},
        {"name": "七彩神仙", "price": 500, "stock": 30, "category": "淡水", "desc": "色彩繽紛，需要軟水"},
        {"name": "紅蓮燈", "price": 20, "stock": 500, "category": "淡水", "desc": "群游美麗，適合草缸"},
        
        # 飼料類
        {"name": "海水魚飼料", "price": 150, "stock": 100, "category": "飼料", "desc": "營養均衡，適合所有海水魚"},
        {"name": "淡水魚飼料", "price": 80, "stock": 150, "category": "飼料", "desc": "高蛋白配方，促進生長"},
        {"name": "冷凍紅蟲", "price": 50, "stock": 200, "category": "飼料", "desc": "天然飼料，營養豐富"},
        {"name": "豐年蝦", "price": 100, "stock": 100, "category": "飼料", "desc": "活餌首選，提高活力"},
        
        # 設備類
        {"name": "外掛過濾器", "price": 300, "stock": 50, "category": "設備", "desc": "小缸適用，安裝簡單"},
        {"name": "圓筒過濾器", "price": 800, "stock": 30, "category": "設備", "desc": "大缸必備，過濾強大"},
        {"name": "LED燈具", "price": 500, "stock": 40, "category": "設備", "desc": "省電高亮，可調光"},
        {"name": "加溫棒", "price": 200, "stock": 60, "category": "設備", "desc": "恆溫控制，安全可靠"},
        {"name": "打氣機", "price": 150, "stock": 70, "category": "設備", "desc": "增加溶氧，靜音設計"}
    ]
    
    product_objs = []
    for prod_data in products_data:
        prod = Product(
            name=prod_data["name"],
            price=prod_data["price"],
            stock=prod_data["stock"],
            category_id=category_objs[prod_data["category"]].id,
            description=prod_data["desc"],
            is_active=True
        )
        session.add(prod)
        product_objs.append(prod)
    
    session.flush()
    print(f"✅ 創建了 {len(products_data)} 個商品")
    
    # 為部分商品添加選項
    options_data = [
        # 魚類尺寸選項
        {"products": ["小丑魚", "孔雀魚", "鬥魚"], "options": [
            {"name": "小型 (2-3cm)", "price": 0},
            {"name": "中型 (3-5cm)", "price": 50},
            {"name": "大型 (5cm+)", "price": 100}
        ]},
        
        # 飼料包裝選項
        {"products": ["海水魚飼料", "淡水魚飼料"], "options": [
            {"name": "100g裝", "price": 0},
            {"name": "250g裝", "price": 50},
            {"name": "500g裝", "price": 80},
            {"name": "1kg裝", "price": 150}
        ]},
        
        # 設備功率選項
        {"products": ["外掛過濾器", "圓筒過濾器"], "options": [
            {"name": "適用1尺缸", "price": 0},
            {"name": "適用2尺缸", "price": 100},
            {"name": "適用3尺缸", "price": 200}
        ]},
        
        # 加溫棒功率
        {"products": ["加溫棒"], "options": [
            {"name": "50W", "price": 0},
            {"name": "100W", "price": 50},
            {"name": "200W", "price": 100},
            {"name": "300W", "price": 150}
        ]}
    ]
    
    for opt_group in options_data:
        for prod_obj in product_objs:
            if prod_obj.name in opt_group["products"]:
                for opt_data in opt_group["options"]:
                    option = Option(
                        product_id=prod_obj.id,
                        name=opt_data["name"],
                        price=opt_data["price"]
                    )
                    session.add(option)
    
    print("✅ 為商品添加了選項")
    
    # 提交所有更改
    session.commit()
    session.close()
    
    print("\n✅ 資料庫初始化完成！")
    print("\n可用的分類：")
    for cat in categories:
        print(f"  {cat['icon']} {cat['name']}")
    print(f"\n共創建了 {len(products_data)} 個商品")
    print("\n現在可以啟動機器人了！")

if __name__ == "__main__":
    init_database() 