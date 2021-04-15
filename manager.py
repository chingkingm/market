from logging import getLogger
from typing import List
from .product import product
from .backend import backend, balance
from math import ceil, floor

class manager:
    @staticmethod
    def _tax_cost(origin):
        return 0.01 * origin

    @staticmethod
    def _format_cost(origin):
        tax = manager._tax_cost(origin)
        cost = ceil(origin + tax)
        return f'{cost}金币' + (f'（含税{tax:.2f}金币）' if tax > 0 else 0)

    @staticmethod
    def _format_negcost(origin):
        tax = manager._tax_cost(origin)
        cost = floor(origin - tax)
        return f'{cost}金币' + (f'（已去除税{tax:.2f}金币）' if tax > 0 else 0)

    def __init__(self, backend: backend, balance: balance, products: List[product]):
        self.products = {}
        self.logger = getLogger('marketmanager')

        for product in products:
            product.logger = self.logger
            self.products[product.name] = product
        self.backend = backend
        self.balance = balance
    
    def buy_products(self, gid, uid, item, val) -> str:
        if val <= 0:
            return "数量必须是正数！"
        if item not in self.products:
            return f"找不到物品{item}"
        origin = self.products[item].price * val
        cost = ceil(origin + manager._tax_cost(origin))
        bal = self.backend[gid, uid]
        if bal < cost:
            return f"余额不足，需要{manager._format_cost(origin)}，你只有{bal}金币"
        
        self.backend[gid, uid] = bal - cost
        self.balance[gid, uid, item] += val

        return f"成功花费{manager._format_cost(origin)}购买了{item}x{val:.2f}"
    
    def sell_products(self, gid, uid, item, val) -> str:
        if val <= 0:
            return "数量必须是正数！"
        if item not in self.products:
            return f"找不到物品{item}"
        bal = self.balance[gid, uid, item]
        if bal < val:
            return f"物品不足，你只有{item}x{bal:.2}"
        
        origin = self.products[item].price * val
        cost = floor(origin - manager._tax_cost(origin))
        self.balance[gid, uid, item] = bal - val
        self.backend[gid, uid] += cost

        return f"成功卖出了{item}x{val:.2}，获得了{manager._format_negcost(origin)}"
    
    def list_products(self):
        content = '\n'.join([f'{product} 当前价格 {self.products[product].price:.2f}'for product in self.products])
        return f'目前的商品有：\n{content}'

    def list_balances(self, gid, uid):
        bal = self.balance[gid, uid]
        contents = []
        for product in bal:
            if bal[product] > 0:
                contents.append(f'{product}x{bal[product]:.2f}')
        content = '\n'.join(contents)
        return f'目前你仓库内有：\n{content}' if contents else f'你仓库里面除了灰尘什么都没！' 
    
    def schedule_products(self):
        for name in self.products:
            prod: product = self.products[name]
            prod.schedule()

            

    
