#!/usr/bin/env -S python3 -IBS

# Tree Sandbox for Linux
# Licensed under GPL.  https://github.com/garywill/treesandbox
# This project comes with no warranty. Use on your own risk.

globals_0 = set(globals().keys()) ########################

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




sbxPyEntrance = os.path.dirname(os.path.abspath(__file__)) # 取得 __main__.py 文件 的 所在目录路径。可能真是目录（非pyz时），可能是pyz文件
if zipfile.is_zipfile ( sbxPyEntrance ):
    si.pyz = True
else: si.pyz = False
sbxPyEntranceDirpath = os.path.dirname(sbxPyEntrance)  # 所在目录完整路径
sbxPyEntranceDirname = os.path.basename(sbxPyEntranceDirpath) # 所在目录名
sbxPyEntranceName = os.path.basename(sbxPyEntrance)  # 文件名含扩展名（pyz时） 或 入口目录名（如src）
sbxPyEntranceNameNoext = os.path.splitext(sbxPyEntranceName)[0]



globals_1 = set(globals().keys()) ########################





def _update_funcs_globals():
    new_names = (globals_1 - globals_0) - { 'globals_0', 'globals_1', '_update_funcs_globals' }
    # print(f'{new_names=}')

    def update_to_func(func):
        if not hasattr(func, '__globals__'):
            print(f'WARNING:  A function to patch does not have __globals__ attr', file=sys.stderr)
            return
        for name in new_names:
            if name not in func.__globals__:
                func.__globals__[name] = globals()[name]

    for name, obj in globals().items():
        if name not in new_names :
            continue
        if type(obj).__name__ == 'function':  # 函数
            update_to_func(obj)
        elif isinstance(obj, type):  # 类
            for attr_name, attr_obj in obj.__dict__.items():
                if type(attr_obj).__name__ == 'function':
                    update_to_func(attr_obj)
                elif isinstance(attr_obj, (staticmethod, classmethod)):
                    update_to_func(attr_obj.__func__)
                elif isinstance(attr_obj, property):
                    for f in (attr_obj.fget, attr_obj.fset, attr_obj.fdel):
                        if f is not None:
                            update_to_func(f)


_update_funcs_globals()
del _update_funcs_globals, globals_1, globals_0




if __name__ == "__main__":
    CHK( platform.system() == 'Linux' and tuple(map(int, platform.release().split('.')[:2])) >= (6, 3) , 'Require Linux >= 6.3')

    set_nonewpriv()

    lyrcfg_to_use = 'wait-for-ready'
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
