import yaml,os,random
from hoshino.util import DailyNumberLimiterInFile
from hoshino import MessageSegment,R
"""消息入口依旧为manager,当物品不在mgr.products中时,调用Shop.ensure,判断是否为商店道具.

"""
def _load_items() -> dict:
    with open(os.path.join(os.path.dirname(__file__),'items.yaml'),'r',encoding='utf8') as f:
        data = yaml.load(f,Loader=yaml.FullLoader)
        f.close()
    return data
# todo 效果展示,item.yaml不存在则新建,使用道具
class Item(object):
    """item"""
    PATH = os.path.join(os.path.dirname(__file__),'image')
    def __init__(self,name) -> None:
        super().__init__()
        self.__list = _load_items()
        if name in self.__list:
            self.name = name
            self.effect = self.__list[name]['effect']
            self.lmt = DailyNumberLimiterInFile(self.__list[name]['limit'],99)
            self.lmt.check(111)
            self.path = os.path.join(self.PATH,self.name)
            self.proj = self.__list[name]['proj']
            self.price = self.__list[name]['price']
    
    
    def __random_pic(self):
        img_list = os.listdir(self.path)
        img = random.choice(img_list)
        img_mes = MessageSegment.image(f'file:///{os.path.join(self.path,img)}')
        return img_mes

    def show_effect(self):
        img_list = os.listdir(self.path)
        img = random.choice(img_list)
        img_mes = MessageSegment.image(f'file:///{os.path.join(self.path,img)}')
        mes = f'道具`{self.name}`效果为\n{img_mes}{self.effect}'
        mes += f'\n今日价格:{self.price}'
        return mes
    def use(self,key,val) -> str:
        """使用道具"""
        if self.name == '人生重来枪':
            if self.lmt.check(key):
                return f'今日{self.proj}奖金获取次数还未达到上限,不可以使用{self.name}.'
            else:
                self.lmt.reset(key)
        else:
            lmt_num = self.lmt.get_num(key)
            self.lmt.set_num(key,lmt_num-val)
        return f'道具{self.name}*{val}使用成功,今日{self.proj}次数剩余{self.lmt.max-self.lmt.get_num(key)}{self.__random_pic()}'
class Shop():
    """派蒙商店Beta"""    
    @staticmethod
    def format_items_list() -> str:
        """格式化道具及价格列表"""
        ret = f'\n目前的道具有:\n'
        data = _load_items()
        if data is None:
            ret += f'现在没有道具在售.'
        else:
            for items in data:
                temp_ret = ''
                price = data[items]['price']
                temp_ret += f'{items} 今日价格 {price}'
                rate = price / data[items]['origin']
                if rate < 1:
                    rate = 1 - rate
                    temp_ret += f'|{round(round(rate,2)*100)}%off\n'
                    temp_ret = temp_ret.replace('价格','特价')
                else:
                    temp_ret += '\n'
                ret += temp_ret
        return ret
    
    def __init__(self) -> None:
        self.__list = _load_items()
        

    def ensure(self,item) -> bool:
        """检验item是否为商店道具"""
        if item in self.__list:
            return True
        else:
            return False
    
    def price(self,item):
        self.__list = _load_items()
        return self.__list[item]['price']    
    
    
    @staticmethod
    def gen_price() -> None:
        """每日特价?"""
        items_data = _load_items()
        price = {item:items_data[item]['origin'] for item in items_data}
        for item in price:
            r = random.random()
            if r >= 0.88:
                price[item] *= r
                price[item] = round(price[item],2)
            items_data[item].update({'price':price[item]})
        with open(os.path.join(os.path.dirname(__file__),'items.yaml'),'w',encoding='utf8') as f:
            yaml.dump(items_data,f,allow_unicode=True)
            f.close()