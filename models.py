from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Float,
    Boolean, ForeignKey, Table, create_engine, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from config import DATABASE_URL

Base = declarative_base()

# 關聯表：CartItem ↔ Option, OrderItem ↔ Option
cartitem_option = Table(
    'cartitem_option', Base.metadata,
    Column('cartitem_id', ForeignKey('cart_items.id'), primary_key=True),
    Column('option_id', ForeignKey('options.id'),   primary_key=True)
)

orderitem_option = Table(
    'orderitem_option', Base.metadata,
    Column('orderitem_id', ForeignKey('order_items.id'), primary_key=True),
    Column('option_id', ForeignKey('options.id'), primary_key=True)
)

class User(Base):
    """用戶模型"""
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)  # Telegram user ID
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    last_active = Column(DateTime, default=datetime.now)

class Category(Base):
    """商品分類模型"""
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)  # 分類名稱
    icon = Column(String, default='📦')
    description = Column(String)
    display_order = Column(Integer, default=0)  # 顯示順序
    order = Column(Integer, default=0)  # 排序順序（別名）
    is_active = Column(Boolean, default=True)  # 是否啟用
    created_at = Column(DateTime, default=datetime.now)
    
    # 新增分類照片欄位（最多5張）
    photo_1 = Column(String)
    photo_2 = Column(String)
    photo_3 = Column(String)
    photo_4 = Column(String)
    photo_5 = Column(String)
    
    products = relationship("Product", back_populates="category_rel")

class Product(Base):
    __tablename__ = 'products'
    id         = Column(Integer, primary_key=True)
    name       = Column(String, nullable=False)
    price      = Column(Float, nullable=False)    # 本體價格 (a)
    image_url  = Column(String, nullable=True)
    category   = Column(String, nullable=True)  # 舊的分類欄位（保留向後兼容）
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)  # 新的分類外鍵
    description = Column(String, nullable=True)  # 新增描述欄位
    stock      = Column(Integer, default=0)  # 庫存欄位
    is_active  = Column(Boolean, default=True)  # 商品是否啟用
    options    = relationship("Option", back_populates="product")
    category_rel = relationship("Category", back_populates="products")  # 分類關聯

class Option(Base):
    __tablename__ = 'options'
    id         = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    name       = Column(String, nullable=False)
    price      = Column(Float, nullable=False)    # 附加選項價格 (b)
    product    = relationship("Product", back_populates="options")

class CartItem(Base):
    __tablename__ = 'cart_items'
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity   = Column(Integer, default=1)
    options    = relationship("Option", secondary=cartitem_option)

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    order_no = Column(String, unique=True, nullable=False)
    user_id = Column(Integer, nullable=False)
    store_code = Column(String, nullable=False)
    status = Column(String, default='待付款')
    tracking_number = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    
    # 新增支付相關欄位
    payment_method = Column(String)  # 'cash_on_delivery', 'credit_card', 'bank_transfer'
    payment_status = Column(String, default='pending')  # 'pending', 'paid', 'failed', 'refunded'
    paid_at = Column(DateTime)
    payment_amount = Column(Float, default=0)
    payment_reference = Column(String)  # 支付交易號
    
    # 訂單追蹤
    confirmed_at = Column(DateTime)
    shipped_at = Column(DateTime)
    arrived_at = Column(DateTime)
    completed_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    cancel_reason = Column(String)
    
    # 客戶資訊
    customer_name = Column(String)
    customer_phone = Column(String)
    
    items = relationship("OrderItem", back_populates="order", lazy='joined')

class OrderItem(Base):
    __tablename__ = 'order_items'
    id         = Column(Integer, primary_key=True)
    order_id   = Column(Integer, ForeignKey('orders.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity   = Column(Integer, default=1)
    price      = Column(Float, nullable=False)  # 計算後單價 = a + sum(b_i)
    options    = relationship("Option", secondary=orderitem_option)
    order      = relationship("Order", back_populates="items")

class Favorite(Base):
    """用戶收藏模型"""
    __tablename__ = 'favorites'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'))
    created_at = Column(DateTime, default=datetime.now)
    product = relationship("Product")

class Review(Base):
    """商品評價模型"""
    __tablename__ = 'reviews'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'))
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)
    rating = Column(Integer, nullable=False)  # 1-5 星評分
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    product = relationship("Product")
    order = relationship("Order")

# 新增系統設定表
class SystemConfig(Base):
    __tablename__ = 'system_config'
    
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String)
    description = Column(String)
    
# 新增門市資料表
class Store(Base):
    __tablename__ = 'stores'
    
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    type = Column(String)  # '7-11', 'FamilyMart', 'Hi-Life', 'OK'
    address = Column(String)
    phone = Column(String)
    is_active = Column(Boolean, default=True)
    
# 新增支付記錄表
class PaymentLog(Base):
    __tablename__ = 'payment_logs'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    amount = Column(Float)
    method = Column(String)
    status = Column(String)
    reference = Column(String)
    request_data = Column(Text)
    response_data = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    order = relationship("Order")

# 建立 Engine 與 Session
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)