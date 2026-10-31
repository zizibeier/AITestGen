import os

from data_utils.glob_data import GData
from tools.logger import log

def set_data(attr,data):
    setattr(GData,attr,data)
    log.info(f"设置全局变量，变量名{attr},变量值{data}")


def get_glob_data(attr):
    try:
        if hasattr(GData,attr):
            value = getattr(GData,attr)
            log.info(f"获取全局变量，变量名{attr},变量值{value}")
            return value
        else:
            log.debug(f"未找到该属性:{attr}")
    except Exception as e:
        log.debug(f"错误信息：{e}")





if __name__ == '__main__':
    data={"token":"sss","id":"121212222"}
    set_data("sheet1",data)
    set_data("token", os.getenv("DEMO_TOKEN", ""))
    value=get_glob_data("sheet1")
    print(value)
