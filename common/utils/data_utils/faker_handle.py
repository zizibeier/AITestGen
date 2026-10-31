
# 标准库导入
import random
import re
import csv
from thefuzz import process

from datetime import datetime

# 第三方库导入
import faker
from common.utils.logger import log


class FakerData:
    """
    测试数据生成类
    官方文档：https://faker.readthedocs.io/en/master/index.html
    """

    def __init__(self):
        self.fk_zh = faker.Faker(locale='zh_CN')
        self.fake = faker.Faker()

    @classmethod
    def generate_random_int(cls, *args) -> int:
        """
        :return:随机数
        """
        if not args:
            return random.randint(0, 5000)

        min_val = min(args)
        max_val = max(args)
        return random.randint(min_val, max_val)

    def generate_phone(self, lan='en') -> int:
        """
        :return: 随机生成手机号码
        """
        if lan == 'zh':
            phone = self.fk_zh.phone_number()
        else:
            phone = self.fake.phone_number()
        return phone

    def generate_female_name(self, lan='en') -> str:
        """
        :return: 女生姓名
        """
        if lan == 'zh':
            female_name = self.fk_zh.name_female()
        else:
            female_name = self.fake.name_female()

        return female_name

    def generate_male_name(self, lan='en') -> str:
        """
        :return: 男生姓名
        """

        if lan == 'zh':
            male_name = self.fk_zh.name_male()
        else:
            male_name = self.fake.name_male()
        return male_name

    def generate_name(self, lan="en") -> str:
        """
        生成人名
        :return: 人名
        """
        if lan == "zh":
            name = self.fk_zh.name()
        else:
            name = self.fake.name()
        return name

    def generate_company_name(self, lan: str = "en", fix: str = None) -> str:
        """
        生成公司名
        :param lan: 语言类型，可选：en, zh； zh表示中文，en表示英文，默认是en
        :param fix: 前后缀，可选pre， suf； pre表示公司前缀，suf标识公司后缀
        :return: 公司名
        """
        if lan == "zh":
            if fix == "pre":
                name = self.fk_zh.company_prefix()
            elif fix == "suf":
                name = self.fk_zh.company_suffix()
            else:
                name = self.fk_zh.company()
        else:
            if fix == "pre":
                name = self.fake.company_prefix()
            elif fix == "suf":
                name = self.fake.company_suffix()
            else:
                name = self.fake.company()

        return name
    def generate_email(self, lan="en") -> str:
        """

        :return: 生成邮箱
        """
        if lan == "zh":
            email = self.fk_zh.email()
        else:
            email = self.fake.email()
        return email

    def generate_identifier(self, lan="en", char_len=8):
        """
        :return:生成随机标识，满足要求：长度为2~100， 只能包含数字，字母，下划线(_)，中划线(-)，英文句号(.)，必须以数字和字母开头，不能以下划线/中划线/英文句号开头和结尾
        """
        if lan == "zh":
            fk = self.fk_zh
        else:
            fk = self.fake
        while True:
            identifier = fk.slug()  # 生成随机的slug标识

            if (
                    re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,98}[a-zA-Z0-9]$', identifier) and
                    not (identifier.startswith('_') or identifier.startswith('-') or identifier.startswith('.')) and
                    not (identifier.endswith('_') or identifier.endswith('.'))
            ) and len(identifier) >= char_len:
                return identifier[:char_len]

    def generate_city(self, lan="en", full: bool = True) -> str:
        """
        :return: 随机生成城市名
        """
        if lan == "zh":
            faker = self.fk_zh
        else:
            faker = self.fake

        if full:
            city = faker.city()
        else:
            city = faker.city_name()

        return city

    def generate_province(self, lan="en") -> str:
        """
        :return: 随机生成城市名
        """
        if lan == "zh":
            faker = self.fk_zh
        else:
            faker = self.fake

        return faker.province()

    def generate_str(self,lan="en") -> str:
        """
        :return: 随机生成字符串
        """
        if lan == "zh":
            faker = self.fk_zh
        else:
            faker = self.fake

        return faker.pystr()


    @classmethod
    def generate_time(cls, fmt='%Y-%m-%d %H:%M:%S') -> str:
        """
        计算当前时间
        :return:
        """
        now_time = datetime.now().strftime(fmt)
        return now_time


    @classmethod
    def remove_special_characters(cls, target: str):
        """
        移除字符串中的特殊字符。
        在Python中用replace()函数操作指定字符
        常用字符unicode的编码范围：
        数字：\u0030-\u0039
        汉字：\u4e00-\u9fa5
        大写字母：\u0041-\u005a
        小写字母：\u0061-\u007a
        英文字母：\u0041-\u007a
        """
        pattern = r'([^\u4e00-\u9fa5])'
        result = re.sub(pattern, '', target)
        return result



if __name__ == '__main__':

    text = FakerData()
    s=text.generate_phone('zh')
    file=text.generate_str()
    print(file)
