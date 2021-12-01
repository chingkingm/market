from logging import getLogger
from typing import List
from .product import product
from .backend import backend, balance
from .Shop import Item, Shop
from math import ceil, floor
from hoshino.util import DailyNumberLimiterInFile
import random
from hoshino import MessageSegment
from hoshino.util.score import Score
from decimal import *

check_lmt = DailyNumberLimiterInFile("dailycheck", 1)
check_time = DailyNumberLimiterInFile("check_time", 300)
group_num = "965166478"


class manager:
    @staticmethod
    def _tax_cost(origin):
        return 0.003 * origin

    @staticmethod
    def _format_num(x):
        x = float(x)
        if x > 1000:
            return f"{x:.1f}"
        else:
            return f"{x:.4}"

    @staticmethod
    def _format_cost(origin):
        tax = manager._tax_cost(origin)
        cost = ceil(origin + tax)
        return f"{cost}金币" + (f"（含税{manager._format_num(tax)}金币）" if tax > 0 else 0)

    @staticmethod
    def _format_negcost(origin):
        tax = manager._tax_cost(origin)
        cost = floor(origin - tax)
        return f"{cost}金币" + (f"（已去除税{manager._format_num(tax)}金币）" if tax > 0 else 0)

    def __init__(self, backend: backend, balance: balance, products: List[product]):
        self.products = {}
        self.logger = getLogger("marketmanager")

        for product in products:
            product.logger = self.logger
            self.products[product.name] = product
        self.backend = backend
        self.balance = balance
        self.shop = Shop()

    def buy_products(self, gid, uid, item, val) -> str:
        gold = Score(int(uid))
        val = round(val, 2)
        if item not in self.products:
            if not self.shop.ensure(item):
                return f"找不到物品{item}"
        if val <= 0:
            return "数量必须是正数！"
        elif val < 0.01:
            return "太少了,不卖!"
        try:
            origin = self.products[item].price * val
        except KeyError:
            origin = self.shop.price(item) * val
        cost = ceil(origin + manager._tax_cost(origin))
        bal = gold.get_score()
        if bal < cost:
            return f"余额不足，需要{manager._format_cost(origin)}，你只有{bal}金币"
        gold.spend_score(cost, reason=f"{gid}群购买{item}*{val}")

        self.balance[group_num, uid, item] += val
        return f"成功花费{manager._format_cost(origin)}购买了{item}x{manager._format_num(val)}，剩余{gold.get_score()}金币"

    def sell_products(self, gid, uid, item, val) -> str:
        gold = Score(int(uid))
        val = round(val, 2)
        if val <= 0:
            return "数量必须是正数！(太小的小数也不行,那么点儿货谁要啊?"
        if item not in self.products:
            if self.shop.ensure(item):
                return f"商店道具不支持出售."
            else:
                return f"找不到物品{item}"
        bal = self.balance[group_num, uid, item]
        if bal < val:
            return f"物品不足，你只有{item}x{manager._format_num(bal)}"

        origin = self.products[item].price * val
        cost = floor(origin - manager._tax_cost(origin))
        self.balance[group_num, uid, item] = bal - val
        gold.add_score(cost, reason=f"{gid}群卖出{item}*{val}")
        return f"成功卖出了{item}x{manager._format_num(val)}，获得了{manager._format_negcost(origin)}，现有{gold.get_score()}金币"

    def use_item(self, gid, uid, item, val):
        if not self.shop.ensure(item):
            return f"找不到道具{item}"
        bal = self.balance[group_num, str(uid), item]
        val = floor(val)
        if val <= 0:
            return f"使用数量仅支持正数."
        if item == "人生重来枪" and val > 1:
            return f"{item}每次最多使用一个."
        if bal < val:
            return f"道具不足,你只有{item}x{manager._format_num(bal)}."
        it = Item(item)
        ret = it.use(uid, val)
        if "成功" in ret:
            self.balance[group_num, str(uid), item] = bal - val
        return ret

    def list_products(self):
        contents = []
        for product in self.products:
            try:
                contents.append(
                    f"{product} 当前价格 {manager._format_num(self.products[product].price)}"
                )
            except RuntimeError:
                pass

        content = "\n".join(contents)
        content += self.shop.format_items_list()
        return f"目前的商品有：\n{content}"

    def list_balances(self, gid, uid):
        bal = self.balance[group_num, uid]
        contents = []
        for product in bal:
            if bal[product] > 0:
                contents.append(f"{product}x{manager._format_num(bal[product])}")
        content = "\n".join(contents)
        return f"目前你仓库内有：\n{content}" if contents else f"你仓库里面除了灰尘什么都没！"

    def schedule_products(self):
        for name in self.products:
            prod: product = self.products[name]
            prod.schedule()

    # 余额查询
    def check_money(self, gid, uid):
        money = Score(int(uid)).get_score()
        return f"你还有{money}金币哦。"

    # 每日签到
    def daily_check(self, uid: int, val: int) -> str:
        uid = int(uid)
        gold = Score(uid)
        if not check_time.check(uid):
            return f"今天已经签了{check_time.get_num(uid)}次了,该收手了"
        else:
            if check_lmt.check(uid):
                current_num = check_lmt.get_num(key=uid)
                current_num = check_lmt.max - current_num
                if val > current_num:
                    return f"剩余次数不足,你还可以签到{current_num}次."
                else:
                    sum = 0
                    ret = ""
                    for n in range(val):
                        rand = random.randint(10, 30) * 10 + random.randint(1, 9) * 5
                        if random.random() < 0.008:
                            rand *= 10
                            ret += f"第{n+1}次签到，运气爆棚，获得{rand}金币.\n"
                        sum += rand
                    gold.add_score(sum, reason="签到")
                    if val > 1:
                        ret += f"{val}次签到完成,共获得{sum}金币.\n现有金币{gold.get_score()}."
                    else:
                        print(ret)
                        if ret == "":
                            ret = f"签到完成,获得{rand}金币,"
                        ret += f"现有金币{gold.get_score()}."
                    check_lmt.set_num(uid, check_lmt.get_num(uid) + val)
                    check_time.set_num(uid, check_time.get_num(uid) + val)
                    ret += f"\n今日签到{check_time.get_num(uid)}/{check_time.max}."
                    return ret
            else:
                return f"你今天已经签到过了哦。"

    # 金币加
    def coin_plus(self, gid, uid, val) -> str:
        gold = Score(int(uid))
        gold.add_score(Decimal(str(val)), "奖励")
        return f"奖励完成"

    # 金币减
    def coin_down(self, gid, uid, val):
        gold = Score(int(uid))
        current_coin = gold.get_score()
        if current_coin < abs(float(val)):
            gold.spend_score(current_coin, reason="惩罚in{gid}")
            return f"用户金币数量小于扣除数量，金币归零。"
        else:
            gold.spend_score(abs(val), reason="惩罚in{gid}")
            return f"扣除完成"

    # 送金币
    def coin_gift(self, gid, sid_g, sid_r, val):
        gold_g = Score(int(sid_g))
        giver_coin = gold_g.get_score()
        val = round(float(val), 2)
        if val <= 0:
            return f"四舍五入{val}金币,这合适吗?"
        if not gold_g.check_score(val):
            return f"您的金币数量不足."
        gold_g.give_score(val, target_uid=sid_r)
        msg_at = MessageSegment.at(sid_r)
        return f"成功赠予{msg_at}金币{val}剩余金币{gold_g.get_score()}。"


#     # todo: 商店
