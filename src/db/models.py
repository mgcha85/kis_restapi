from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class HoldList(Base):
    __tablename__ = 'hold_list'
    code = Column(String, primary_key=True)
    qty = Column(Integer, nullable=False)
    avg_price = Column(Integer, nullable=False)
    remain_qty = Column(Integer, default=0)
    order_id = Column(String, ForeignKey('order_list.order_id'))
    num_buy = Column(Integer, default=1)
    buy_time = Column(DateTime, server_default=func.current_timestamp())
    due_date = Column(DateTime)
    stop_price = Column(Integer, default=0)
    fee = Column(Float, default=0)
    tax = Column(Float, default=0)

class OrderList(Base):
    __tablename__ = 'order_list'
    order_id = Column(String, primary_key=True)
    code = Column(String, nullable=False)
    name = Column(String)
    order_type = Column(String, nullable=False)
    qty = Column(Integer, nullable=False)
    remain_qty = Column(Integer)
    cum_price = Column(Integer)
    fee = Column(Float, default=0)
    tax = Column(Float, default=0)
    order_time = Column(DateTime, server_default=func.current_timestamp())
    status = Column(String)

class TradeHistory(Base):
    __tablename__ = 'trade_history'
    trade_id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False)
    회사명 = Column(String)
    avg_price = Column(Integer, nullable=False)
    qty = Column(Integer, nullable=False)
    sell_price = Column(Integer, nullable=False)
    stop_price = Column(Integer, default=0)
    num_buy = Column(Integer, default=1)
    buy_price = Column(Integer, nullable=False)
    profit = Column(Integer)
    fee = Column(Float, default=0)
    tax = Column(Float, default=0)
    buy_time = Column(DateTime)
    due_date = Column(DateTime)
    sell_time = Column(DateTime, server_default=func.current_timestamp())
    order_id = Column(String, ForeignKey('order_list.order_id'))

class AllStockCode(Base):
    __tablename__ = 'allStockCode'
    index = Column(Integer, primary_key=True)
    회사명 = Column(String)
    종목코드 = Column(String)
    업종 = Column(String)
    주요제품 = Column(String)
    상장일 = Column(String)
    결산월 = Column(String)
    대표자명 = Column(String)
    홈페이지 = Column(String)
    지역 = Column(String)
    type = Column(String)
