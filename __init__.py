import math
from .manager import manager
from .Shop import Shop, Item
from .backend import json_backend, balance, duel_backend
from .product import (
    coincap_product,
    sina_product,
    sochain_product,
    cryptocompare_product,
    qq_product,
)
from hoshino.service import Service
from nonebot import on_startup
from hoshino import HoshinoBot, priv
from hoshino.typing import CQEvent
from hoshino.util import FreqLimiter
# json_backend代表独立的json存储
# duel_backend代表与pcrduel金币联动的存储
from loguru import logger
flmt = FreqLimiter(10)
mgr = None

sv = Service(
    "market",
    enable_on_default=True,
    bundle="market",
    help_="""购买大头菜,本金1000
[买入/卖出 商品名*n] 买卖n个某种商品
[市场列表] 看看市场价格
[仓库列表] 看看仓库还剩啥
[金币余额] 看看还有几个金币""",
)


@on_startup
async def _load_manager():  # ensure all plugins have been loaded
    global mgr
    try:
        be = duel_backend()
    except:
        be = json_backend()

    mgr = manager(
        be,
        balance(),
        [
            qq_product("sh601005", "甜甜花"),
            qq_product("sh600276", "霓裳花"),
            qq_product("sh601166", "琉璃百合"),
            qq_product("sh601012", "琉璃袋"),
            qq_product("sh688005","风车菊"),
            qq_product("sh600519", "椰奶"),
            sochain_product("btc:usd","派蒙", multiplier=.1),
            # sochain_product("doge:usd", "优衣", multiplier=10),
            # coincap_product("uniswap", "琉璃百合"),
            # coincap_product("xrp", "琉璃袋"),
        ],
    )

    mgr.schedule_products()


@sv.on_rex(r"^(买入|卖出)(.*?)\*(\d*.?\d*)$")
async def buy_or_sell(bot, ev):
    await bot.finish(
        ev,
        (mgr.sell_products if ev["match"].group(1) == "卖出" else mgr.buy_products)(
            str(ev["group_id"]),
            str(ev["user_id"]),
            ev["match"].group(2).strip(),
            float(ev["match"].group(3)),
        ),
        at_sender=True,
    )


@sv.on_rex(r"^(使用)(.*?)\*(\d*.?\d*)$")
async def use_item(bot, ev):
    gid = "965166478"
    uid = ev["user_id"]
    item = ev["match"].group(2).strip()
    val = float(ev["match"].group(3))
    mes = mgr.use_item(gid, uid, item, val)
    await bot.send(ev, mes, at_sender=True)
    # await bot.finish(ev, mgr.use_item(str(ev['group_id'],str(ev['user_id'],ev['match'].group(2).strip(),float(ev['match'].group(3))))),at_sender=True)


@sv.on_prefix("查看道具")
async def show_item(bot: HoshinoBot, ev: CQEvent):
    item = ev.message.extract_plain_text().strip()
    s = Shop()
    if not s.ensure(item):
        await bot.send(ev, f"找不到道具:{item}")
    else:
        i = Item(item)
        await bot.send(ev, i.show_effect())


@sv.on_rex(r"^市场列表$")
async def listmarket(bot, ev):
    await bot.finish(ev, mgr.list_products(), at_sender=False)


@sv.on_rex(r"^仓库列表$")
async def listbalance(bot, ev):
    await bot.finish(
        ev, mgr.list_balances(str(ev["group_id"]), str(ev["user_id"])), at_sender=True
    )


@sv.on_rex(r"^金币余额$")
async def excoin(bot, ev):
    await bot.finish(
        ev, mgr.check_money(str(ev["group_id"]), str(ev["user_id"])), at_sender=True
    )


@sv.on_prefix('签到')
async def multicheck(bot:HoshinoBot,ev:CQEvent):
    msg = ev.message.extract_plain_text().strip()
    msg = msg.split('*')
    uid = ev["user_id"]
    try:
        val = msg[1]
    except IndexError:
        val = 1
    val = float(val)
    if val > 50:
        await bot .send(ev,f'太多了,会卡住.每次最多50.',at_sender=True)
    else:
        if val == math.floor(val):
            await bot.finish(ev,mgr.daily_check(int(uid),int(val)),at_sender = True)
        else:
            await bot.send(ev,f'小数,你搞什么?',at_sender=True)

@sv.on_prefix(("奖励金币", "增加金币"))
async def coin_u(bot, ev):
    gid = ev.group_id
    if not priv.check_priv(ev, priv.SU):
        await bot.send(ev, "只有管理员可以使用。")
        return
    sid = None
    val = ev.message.extract_plain_text().strip()
    for m in ev.message:
        if m.type == "at":
            sid = int(m.data["qq"])
    if sid:
        await bot.finish(ev, mgr.coin_plus(str(gid), str(sid), val), at_sender=True)


@sv.on_prefix("扣除金币")
async def coin_d(bot, ev):
    gid = ev.group_id
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.send(ev, "扣除金币只能管理员使用！")
        return
    sid = None
    val = ev.message.extract_plain_text().strip()
    for m in ev.message:
        if m.type == "at":
            sid = int(m.data["qq"])
    if sid:
        await bot.finish(ev, mgr.coin_down(str(gid), str(sid), int(val)), at_sender=True)


@sv.on_prefix("赠送金币")
async def coin_g(bot, ev):
    gid = ev.group_id
    sid_g = ev.user_id
    val = ev.message.extract_plain_text().strip()
    for m in ev.message:
        if m.type == "at":
            sid_r = int(m.data["qq"])
    if sid_r:
        await bot.finish(
            ev, mgr.coin_gift(str(gid), str(sid_g), str(sid_r), val), at_sender=True
        )


@sv.scheduled_job("cron", hour=4, minute=30)
async def the_sale():
    """定时生成当日价格"""
    Shop.gen_price()
