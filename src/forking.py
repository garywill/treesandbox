from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量


def execvp(*args, **kwargs):
    CHK(not os.path.lexists('/boot') and not os.path.lexists('/srv'), 'Before exec, found /boot or /srv. Filesystem might not be protected')
    CHK(is_dir_inaccessible('/zrootfs'), 'Before exec, found /zrootfs accessible. Filesystem not protected' )
    os.execvp(*args, **kwargs)

def is_dir_inaccessible(path):
    return not (os.access(path, os.R_OK) or os.access(path, os.W_OK) or os.access(path, os.X_OK))




# TODO 清理环境变量
def fork(cut_stdin=False, create_socketpair=False, loghead=None, proc_dispname=None,
         close_fds=False, close_keep_fds=[] ,
         set_fds_CLOEXEC=False, CLOEXEC_keep_fds=[]
         ):
    sktpair = None
    if create_socketpair:
        sktpair = TmpSocketPair()
        set_fd_keep_on_exec(sktpair._skt_chd.fileno(), False)
        set_fd_keep_on_exec(sktpair._skt_pa .fileno(), False)
    sys.stdout.flush() ; sys.stderr.flush()
    pid = os.fork()
    CHK(pid >= 0, 'fork failed')
    if pid == 0 : # 子进程
        unreg_cleanup_func()
        unregister_sig_handlers()
        if close_fds:
            if create_socketpair: close_keep_fds += [sktpair._skt_chd.fileno() ]
            close_3ge_fds(keep_fds=close_keep_fds)
        if set_fds_CLOEXEC: set_3ge_fds_cloexec(keep_fds=CLOEXEC_keep_fds)
        if cut_stdin:
            devnull = os.open('/dev/null', os.O_RDWR)
            os.dup2(devnull, 0)
            os.close(devnull)
            os.setsid()
            # os.setpgid(0, 0)
        if loghead is not None: set_loghead(loghead)
        if proc_dispname is not None: set_proc_dispname(proc_dispname)
        if create_socketpair: sktpair.i_am_chd()
    else: # 原进程
        if create_socketpair: sktpair.i_am_pa()
    return pid, sktpair




class TmpSocketPair:
    def __init__(self):
        self._skt_chd, self._skt_pa = socket.socketpair()
        set_fd_keep_on_exec(self._skt_chd.fileno(), False)
        set_fd_keep_on_exec(self._skt_pa.fileno(), False)
        self.I_AM_PA = False ; self.I_AM_CHD = False
    def i_am_pa(self):
        CHK(not self.I_AM_CHD, "Already set as child's end of pipe")
        self._skt_chd.close() ; self.I_AM_PA = True
    def i_am_chd(self):
        CHK(not self.I_AM_PA, "Already set as parent's end of pipe")
        self._skt_pa.close() ; self.I_AM_CHD = True
    def pa_send(self, data):
        CHK(self.I_AM_PA, "Called not by the parent process of fork")
        if isinstance(data, BS): data = data.value
        self._skt_pa.send(data)
    def chd_send(self, data):
        CHK(self.I_AM_CHD, "Called not by the child process of fork")
        if isinstance(data, BS): data = data.value
        self._skt_chd.send(data)
    def pa_recv(self, byte_cnt, timeout, expect_data=None):
        CHK(select.select([self._skt_pa], [], [], timeout)[0], "Parent process of fork timed out waiting for signal from child")
        if isinstance(expect_data, BS): expect_data = expect_data.value
        data = self._skt_pa.recv(byte_cnt)
        if expect_data is not None: CHK(data == expect_data, f"Parent process of fork received an unexpected signal: got {data!r}, expect {expect_data!r}")
        return data
    def chd_recv(self, byte_cnt, timeout, expect_data=None):
        CHK(select.select([self._skt_chd], [], [], timeout)[0], "Child process of fork timed out waiting for signal from parent")
        if isinstance(expect_data, BS): expect_data = expect_data.value
        data = self._skt_chd.recv(byte_cnt)
        if expect_data is not None: CHK(data == expect_data, f"Child process of fork received an unexpected signal: got {data!r}, expect {expect_data!r}")
        return data
    def close(self):
        if self.I_AM_PA  and self._skt_pa:  self._skt_pa.close() ;  self._skt_pa = None
        if self.I_AM_CHD and self._skt_chd: self._skt_chd.close() ; self._skt_chd = None



class BS(enum.Enum): # fork前后父子进程之间通信用的，以及 最外层和内层之间通信用的单字节信号
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return bytes([count])  # 或者 bytes([count & 0xFF]) 防止溢出
    SetMeUidRoot = enum.auto()
    SetYouUidRootDone = enum.auto()
    SetMeUidUser = enum.auto()
    SetYouUidUserDone = enum.auto()
    IChdBorn = enum.auto()
    YouChdGo = enum.auto()



def set_fd_keep_on_exec(fd:int, keep:bool):
    if keep: new_fdflag = fcntl.fcntl(fd, fcntl.F_GETFD) & (~fcntl.FD_CLOEXEC)
    else:    new_fdflag = fcntl.fcntl(fd, fcntl.F_GETFD) | fcntl.FD_CLOEXEC
    fcntl.fcntl(fd, fcntl.F_SETFD, new_fdflag)


def get_all_3ge_fds() -> list:
    CHK( os.fstat(si.fdnull).st_ino == os.stat('/dev/null').st_ino, 'si.fdnull st_ino does not match /dev/null')
    CHK( os.fstat(si.fdnull).st_dev == os.stat('/dev/null').st_dev, 'si.fdnull st_dev does not match /dev/null')
    soft_limit, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
    result = []
    for fd in range(3, soft_limit): # 可以包括fdnull自己，因为dup2自己也没问题
        try:
            fcntl.fcntl(fd, fcntl.F_GETFD)
            result.append(fd)
        except OSError as e:
            if e.errno != errno.EBADF: raise
    return result

def set_3ge_fds_cloexec(keep_fds=[] , action='default'):
    if action == 'default': KEEP=False
    elif action == 'keepall' : KEEP=True
    for fd in get_all_3ge_fds() :
        if fd in keep_fds:
            continue
        try: set_fd_keep_on_exec(fd, KEEP)
        except OSError as e:
            # 9 错误 EBADF 错误表示可能已关闭 （Bad file descriptor）
            if e.errno == 9: pass; #  log_warn(f'尝试设置{fd=}为CLOEXEC但发现刚刚已被关闭')
            else: raise


def close_3ge_fds(keep_fds=[] ):
    for fd in get_all_3ge_fds() :
        if fd in keep_fds:
            continue
        # log(f'Closing {fd=}')
        try:
            os.dup2(si.fdnull, fd) # 不用os.close
            set_fd_keep_on_exec(fd, False)
        except OSError as e:
            # 9 错误 EBADF 错误表示可能已关闭 （Bad file descriptor）
            if e.errno == 9: pass; # log_warn(f'尝试关闭{fd=}但发现刚刚已被关闭')
            else: raise

