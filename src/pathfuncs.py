from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量



def napath(pstr):
    pstr = str(pstr)
    if not str(pstr.startswith('/')): raise_exit(f"Not an absolute path: {pstr}")
    return  ''.join( [ '/' , os.path.normpath(pstr).strip('/') ] )

def which_and_resolve_exist(cmd):
    path = shutil.which(cmd)
    if not path:
        return None
    try:
        return rslvy(path)
    except FileNotFoundError:
        return None

def rslvn(path):
    return str(Path(napath(path)).resolve(strict=False))

def rslvy(path):
    return str(Path(napath(path)).resolve(strict=True))



def padir(path):
    if napath(path) == '/': raise_exit(f"{path} is already the root path, cannot get parent directory")
    return str(Path(path).parent)

def is_file(path):
    return not Path(path).is_symlink() and Path(path).is_file()
def is_dir(path):
    return not Path(path).is_symlink() and Path(path).is_dir()
def is_blockdev(path):
    return not Path(path).is_symlink() and Path(path).is_block_device()
def is_chardev(path):
    return not Path(path).is_symlink() and Path(path).is_char_device()
def is_dev(path):
    return is_chardev(path) or is_blockdev(path)
def is_fifo(path):
    return not Path(path).is_symlink() and Path(path).is_fifo()
def is_socket(path):
    return not Path(path).is_symlink() and Path(path).is_socket()
def is_ro(path):
    return os.statvfs(path).f_flag & MS.RDONLY




def mkdirp(dirpath):
    os.makedirs(dirpath, exist_ok=True)

def make_file_exist(path): # 路径不能已有目录
    if is_dir(path): raise_exit(f"{path} is already a directory")
    if not os.path.exists(path):
        mkdirp(Path(path).parent)
        Path(path).touch()

def symlink(linkto, dest):  # linkto：要创建的软链的指向 .  dest: 在哪个位置创建软链。
    if Path(dest).is_symlink() and Path(dest).readlink() == linkto: return
    mkdirp(Path(dest).parent)
    os.symlink(linkto, dest)
