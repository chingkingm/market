import os, hoshino, base64
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
import requests, json
from requests.models import CaseInsensitiveDict
from PIL import Image,ImageDraw,ImageFont
from io import BytesIO
check_lmt = DailyNumberLimiterInFile("dailycheck", 1)
check_time = DailyNumberLimiterInFile("check_time", 50)
lmt_shici = DailyNumberLimiterInFile("shici", 1)
group_num = "965166478"


def daily_shici() -> str:
    token = "3QWh8w2e3M/4rDYU+OLQLuH3oNuGzbtu"
    API = "https://v2.jinrishici.com/sentence"
    headers = CaseInsensitiveDict
    headers = {"X-User-Token": token}
    resp = requests.get(url=API, headers=headers)
    text = json.loads(resp.text)["data"]["content"]
    text = text.replace('，',",").replace('：',":")
    text_source = '文本来自今日诗词'
    font_path = os.path.join(hoshino.config.RES_DIR,r'font\FZXiJinLJW.TTF')
    img_size = [len(text)*40+10,100]
    blank_image = Image.new('RGBA',(img_size[0],img_size[1]),color=(50,50,50))
    img_draw = ImageDraw.Draw(blank_image)
    fnt = ImageFont.truetype(font_path,40)
    img_draw.text(xy=(10,10),text=text,font=fnt,fill=(214,214,214))
    fnt = ImageFont.truetype(font_path,25)
    img_draw.text(xy=(img_size[0]-len(text_source)*26,60),font=fnt,text=text_source,fill=(214,214,214))
    """以下pic2b64来自egenshin"""
    bio = BytesIO()
    data = blank_image.convert("RGB")
    data.save(bio, format='JPEG', quality=80)
    base64_str = base64.b64encode(bio.getvalue()).decode()
    return 'base64://' + base64_str

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
        cost = round(origin + tax, 2)
        return f"{cost}金币" + (f"（含税{manager._format_num(tax)}金币）" if tax > 0 else 0)

    @staticmethod
    def _format_negcost(origin):
        tax = manager._tax_cost(origin)
        cost = round(origin - tax, 2)
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
        cost = round(origin + manager._tax_cost(origin), 2)
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
        cost = round(origin - manager._tax_cost(origin), 2)
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

    def check_money(self, gid, uid):
        """余额查询"""
        money = Score(int(uid)).get_score()
        return f"你还有{money}金币哦。"

    def daily_check(self, uid: int, val: int) -> str:
        """每日签到"""
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
                    if lmt_shici.check(uid):
                        shici = MessageSegment.image(daily_shici())
                        lmt_shici.increase(uid)
                        ret = f'{shici}\n{ret}'
                    return ret
            else:
                return f"你今天已经签到过了哦。"

    def coin_plus(self, gid, uid, val) -> str:
        """ "金币加"""
        gold = Score(int(uid))
        gold.add_score(Decimal(str(val)), "奖励")
        return f"奖励完成"

    def coin_down(self, gid, uid, val):
        """金币减"""
        gold = Score(int(uid))
        current_coin = gold.get_score()
        if current_coin < abs(float(val)):
            gold.spend_score(current_coin, reason="惩罚in{gid}")
            return f"用户金币数量小于扣除数量，金币归零。"
        else:
            gold.spend_score(abs(val), reason="惩罚in{gid}")
            return f"扣除完成"

    def coin_gift(self, gid, sid_g, sid_r, val):
        """赠送金币"""
        gold_g = Score(int(sid_g))
        giver_coin = gold_g.get_score()
        val = round(float(val), 2)
        if val <= 0:
            return f"四舍五入{val}金币,这合适吗?"
        if not gold_g.check_score(val):
            return f"您的金币数量不足."
        gold_g.give_score(val, target_uid=sid_r)
        msg_at = MessageSegment.at(sid_r)
        return f"成功赠予{msg_at}金币{val},剩余金币{gold_g.get_score()}。"


#     # todo: 商店
