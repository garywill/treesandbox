

# Tree Sandbox for Linux
# Licensed under GPL.  https://github.com/garywill/treesandbox
# This project comes with no warranty. Use on your own risk.

import sys
sys.path.insert(0, '.')
from heads import *



from basefuncs import *
from basetypes import *
from clipbd import *
from const_strs import *
from dyncfg import *
from forking import *
from fs_sbx import *
from initializing import *
from maybe_instance import *
from layer1 import *
from layer2c import *
from layer2 import *
from layer2z import *
from layer3 import *
from layer4c import *
from layer4 import *
from libcfuncs import *
from logprint import *
from mainfuncs import *
from netns_tun import *
from pathfuncs import *
from pidnsleader import *
from signals_clear import *
from toolfuncs import *
from userns_unpri import *
from wlog import *



from userconfig import userconfig


# 这里的全局变量只能 dict.clear dict.update ， 不能重新赋值，否则破坏引用
si = d() # sbxinfo , sandbox info
tlcfg = d() # thislyr_cfg , this layer config
OG = d() # outest global dynamic info
LG = d() # layer global dynamic info



def _update_funcs_globals():
    current_globals = globals()
    def update_func(func):
        if hasattr(func, '__globals__'):
            func.__globals__.update(current_globals)
    for name, obj in current_globals.items():
        # 模块级函数
        if type(obj).__name__ == 'function':
            update_func(obj)
        # 类
        elif isinstance(obj, type):
            for attr_name, attr_obj in obj.__dict__.items():
                # 实例方法：类字典里实际存的是 function
                if type(attr_obj).__name__ == 'function':
                    update_func(attr_obj)
                # @classmethod：要取 __func__
                elif isinstance(attr_obj, classmethod):
                    update_func(attr_obj.__func__)
                # @staticmethod：也取 __func__
                elif isinstance(attr_obj, staticmethod):
                    update_func(attr_obj.__func__)

_update_funcs_globals()
del _update_funcs_globals




if __name__ == "__main__":
    CHK( platform.system() == 'Linux' and tuple(map(int, platform.release().split('.')[:2])) >= (6, 3) , 'Require Linux >= 6.3')
    set_nonewpriv()
    lyrcfg_to_use = 'notready'
    while lyrcfg_to_use:
        dict.clear(tlcfg)
        dict.clear(LG)
        if isinstance(lyrcfg_to_use, dict):
            log(f'Sublayer {lyrcfg_to_use.layer_name}')
            set_proc_dispname(lyrcfg_to_use.layer_name)
        try:
            lyrcfg_to_use = main(lyrcfg_to_use)
        except Exception as err:
            try_pass(lambda: wlog('error', errmsg=err) )
            raise
