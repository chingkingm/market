import yaml,os,random
from hoshino.util import DailyNumberLimiterInFile
"""消息入口依旧为manager,当物品不在mgr.products中时,调用Shop.ensure,判断是否为商店道具.

"""
# todo 效果展示,限购
class Shop():
    """派蒙商店Beta"""    
    @staticmethod
    def __load_items() -> dict:
        with open(os.path.join(os.path.dirname(__file__),'items.yaml'),'r',encoding='utf8') as f:
            data = yaml.load(f,Loader=yaml.FullLoader)
            f.close()
        return data
    
    @staticmethod
    def format_items_list() -> str:
        """格式化道具及价格列表"""
        ret = f'\n以下为道具列表:\n'
        data = Shop.__load_items()
        if data is None:
            ret += f'现在没有道具在售.'
        else:
            temp_ret = ''
            for items in data:
                    price = data[items]['price']
                    temp_ret += f'{items} 当前价格 {price}'
                    rate = price / data[items]['origin']
                    if rate < 1:
                        rate = 1 - rate
                        temp_ret += f'|{round(round(rate,2)*100)}%off\n'
                    else:
                        temp_ret += '\n'
            ret += temp_ret
            ret += f'注意:道具只能使用,不可出售.'
        return ret
    
    def __init__(self) -> None:
        self.__list = Shop.__load_items()
        

    def ensure(self,item) -> bool:
        """检验item是否为商店道具"""
        if item in self.__list:
            return True
        else:
            return False
    
    def price(self,item):
        return self.__list[item]['price']    
    
    def limit(self,item):
        """限购"""
    @staticmethod
    def gen_price() -> None:
        """每日特价?"""
        items_data = Shop.__load_items()
        price = {item:items_data[item]['origin'] for item in items_data}
        for item in price:
            r = random.random()
            if r >= 0.75:
                price[item] *= r
                price[item] = round(price[item],2)
            items_data[item].update({'price':price[item]})
        with open(os.path.join(os.path.dirname(__file__),'items.yaml'),'w',encoding='utf8') as f:
            yaml.dump(items_data,f,allow_unicode=True)
            f.close()