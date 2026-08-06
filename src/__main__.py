

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

def _update_funcs_globals():
    current_globals = globals()
    for itemname in current_globals:
        itemobj = current_globals[itemname]
        if type(itemobj).__name__ == 'function' \
        and hasattr(itemobj, '__globals__') \
        and hasattr(itemobj, '__name__') \
            :
            # print(itemname)
            itemobj.__globals__.update(current_globals)

_update_funcs_globals()
del _update_funcs_globals

if __name__ == "__main__":
    CHK( platform.system() == 'Linux' and tuple(map(int, platform.release().split('.')[:2])) >= (6, 3) , 'Require Linux >= 6.3')
    set_nonewpriv()
    lyrcfg_to_use = 'notready'
    while lyrcfg_to_use:
        tlcfg = None
        LG = d()
        if isinstance(lyrcfg_to_use, dict):
            log(f'Sublayer {lyrcfg_to_use.layer_name}')
            set_proc_dispname(lyrcfg_to_use.layer_name)
        try:
            lyrcfg_to_use = main(lyrcfg_to_use)
        except Exception as err:
            try_pass(lambda: wlog('error', errmsg=err) )
            raise
