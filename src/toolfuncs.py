from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量



UNSHR_MAP = types.SimpleNamespace( pid='PID', mnt='NS', user='USER', cgroup='CGROUP', ipc='IPC', time='TIME', uts='UTS', net='NET', )
def lyrcfg_to_unshrcfg(lyrcfg):
    unshr_cfg = d({k.removeprefix('unshare_'):v for k,v in dict.items(lyrcfg) if k.startswith('unshare_')})
    for x in dict.keys(unshr_cfg): CHK(x in UNSHR_MAP.__dict__.keys(), f'This unshare flag is unknown: {x}')
    return unshr_cfg
def unshrflg(unshr_cfg):
    unshr_flg = 0
    for k,v in dict.items(unshr_cfg):
        if v: unshr_flg |= os.__dict__['CLONE_NEW' + UNSHR_MAP.__dict__[k]]
    return unshr_flg




def run_a_cmd(cmdv, print_output=False):
    prc = subprocess.Popen(cmdv,
            preexec_fn=subprocess_preexec, close_fds=True, restore_signals=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            text=True, bufsize=1, universal_newlines=True,
        )
    stdout_data, _ = prc.communicate()
    # prc.wait()
    if print_output: log(stdout_data)
    if prc.returncode != 0: raise_exit(f"Command was not successful (return code {prc.returncode}) {stdout_data}")

def subprocess_preexec():
    unreg_cleanup_func()
    unregister_sig_handlers()
    set_pdeathsig(signal.SIGKILL)



def is_XId_available(newXId):  # TODO 搞清楚xpra在run里面创建什么与XID有关的文件，也检查它们
    if  not os.path.lexists(f'/tmp/.X11-unix/X{newXId}')  \
    and not os.path.lexists(f'{getenv("XDG_RUNTIME_DIR")}/wayland-{newXId}')  \
    and not re.search(rf':{newXId}(?:\.|$)', getenv('DISPLAY')) \
    and not getenv('WAYLAND_DISPLAY',allow_no=True) == f'wayland-{newXId}' \
    and not re.search(rf'\/tmp/\.X11-unix\/X{newXId}\b', Path('/proc/net/unix').read_text(), re.MULTILINE) :
        return True
    else: return False


def getenv(env_var_name, allow_no=False):
    r = os.getenv(env_var_name, None)
    if not allow_no:
        CHK ( r is not None, f'No Environment variable {env_var_name}')
    if r is None: r = ''
    return r


def is_unix_socket_listened(sock_path):
    if not os.path.exists(sock_path):
        return False
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(sock_path)
        sock.close()
        return True
    except (FileNotFoundError, ConnectionRefusedError):
        sock.close()
        return False
    finally:
        sock.close()


def bring_lo_up():
    SIOCGIFFLAGS = 0x8913 # Get Interface Flags，读取网络接口的状态标志。
    SIOCSIFFLAGS = 0x8914 # Set Interface Flags，设置网络接口的状态标志。
    IFF_UP = 0x0001
    IFNAMSIZ = 16 # 介面名称大小

    lo = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # struct ifreq:
        #   char ifr_name[16];
        #   union { short flags; ... };
        # 分配完整的 ifreq 缓冲区，避免不同架构下长度不足。
        ifr = bytearray(40) # 64 位 ABI 用40字节够了，目前没有比这个更多的
        ifr[:IFNAMSIZ] = b"lo\0" +   b"\0" * (IFNAMSIZ - 3)

        fcntl.ioctl(lo.fileno(), SIOCGIFFLAGS, ifr, True)
        flags = struct.unpack_from("H", ifr, IFNAMSIZ)[0]

        if not (flags & IFF_UP):
            struct.pack_into("H", ifr, IFNAMSIZ, flags | IFF_UP)
            fcntl.ioctl(lo.fileno(), SIOCSIFFLAGS, ifr, True)
    finally:
        lo.close()
