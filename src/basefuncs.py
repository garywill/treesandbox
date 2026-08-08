from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量


def jsondumps_mycompat(obj):
    if isinstance(obj, dict):
        json_str = '\n'.join(['{',
            '\n,\n'.join([f'"{k}" : {json.dumps(v)}' for k,v in dict.items(obj) ]) ,
            '}'])
    elif isinstance(obj, list):
        json_str = '\n'.join(['[', '\n,\n'.join([json.dumps(x) for x in obj]) ,']'])
    else: json_str = json.dumps(obj)
    return json_str


def eq_ignore_order(v1, v2):
    # 防止d D dn dict差异造成误判断，统一为dict
    if isinstance(v1, dict): v1 = dict(v1)
    if isinstance(v2, dict): v2 = dict(v2)

    if type(v1) != type(v2): return False
    if isinstance(v1, dict): return v1.keys() == v2.keys() and all(eq_ignore_order(v1[k], v2[k]) for k in v1)
    if isinstance(v1, list): return len(v1) == len(v2) and sorted(v1, key=str) == sorted(v2, key=str)
    return v1 == v2


def read_alltext_from_fd(fd:int) -> str:
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        return os.pread(fd, os.fstat(fd).st_size, 0).decode()
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)

def read_all_from_fd_then_jsonloads(fd) -> list|dict :
    return json.loads( read_alltext_from_fd(fd) )

def write_to_fd_override(fd:int, text:str):
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.ftruncate(fd, 0)
        os.pwrite(fd, text.encode(), 0)
    finally:
        fcntl.flock(fd,  fcntl.LOCK_UN)




def hash_blake2b(in_str):
    return hashlib.blake2b(in_str).hexdigest()


def try_pass(func):
    try:    return func()
    except: pass

def try_showerr(func):
    try:
        return func()
    except Exception as err:
        print_exc()

def warn_exit(err_msg, no_cleanup=False):
    print(loghead + err_msg, file=sys.stderr)
    if not no_cleanup:
        sys.exit(1)
    else: os._exit(1)
def raise_exit(err_msg, no_cleanup=False):
    print_stack()
    try_pass(lambda: wlog('error', errmsg=err_msg) )
    warn_exit(err_msg, no_cleanup)

def CHK( condition, errmsg='Some check failed', action='raise_exit'):
    if not condition:
        if action == 'raise_exit': raise_exit(errmsg)
        elif action == 'warn': log_warn(f"{errmsg}")
