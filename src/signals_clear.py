from heads import *

whoCleanupRegister = None
def reg_cleanup_func(cleanup_func):
    global whoCleanupRegister
    if not whoCleanupRegister is None: raise_exit('Cleanup function already registered', no_cleanup=True)
    whoCleanupRegister = (os.getpid(), get_nstypes('/proc/self/ns').pid)
    atexit.register(cleanup_func)
def unreg_cleanup_func():
    global whoCleanupRegister
    atexit._clear()
    whoCleanupRegister = None
def isMeThatRegedCleanup(): # TODO 把stat里的时间也加入要素
    if (os.getpid(), get_nstypes('/proc/self/ns').pid) == whoCleanupRegister : return True
    else: log_warn('I am not the process that registered cleanup function. Cleanup function might not unregistered in time'); return False

cleanup_symlinks_to_rm = set()
def cleanup_outest():
    atexit._clear()
    if not isMeThatRegedCleanup(): return
    if os.getpid() == 1: return
    log(f"About to exit, waiting for all child processes to finish, before cleanup...")
    try_showerr(lambda: Path(f'{si.outest_sbxdir}_exit').touch() ) # 设个正在退出的标记
    try_showerr(lambda: Path(f'{si.outest_sbxdir}/EXITING').touch() )
    try_pass(lambda: OutsideServ.skt_OServLsn.close() )
    # if OG and OG.layer1_pid: try_pass(lambda: os.setpgid(OG.layer1_pid, 0) )
    try_pass(lambda: OutestProcsMonitor.sbx_exit_broadcast())

    cleanup_startat = time.monotonic()
    while time.monotonic() <= cleanup_startat+5:
        time.sleep(0.1)
        if not exist_childtree() : break
    else: log_warn('Child processes did not exit within timeout. Sandbox management process exiting first')

    for slkItem in cleanup_symlinks_to_rm:
        if Path(slkItem).is_symlink() :
            linkto = os.readlink(slkItem)
            if linkto == si.outest_sbxdir or linkto.startswith(f'{si.outest_sbxdir}/'):
                try_showerr(lambda: Path(slkItem).unlink() )

    if si.nocleanup:
        return

    # NOTE 不要对那些可能挂载的目录用递归删除!  # 要删除那种目录的话只能用 rmdir （只删空的目录）
    # 因为有挂载，递归删除可能会误删重要文件。危险！ # 例如:
        # new.*.rootfs/
        # apps/*/
    paths_rm_sub_files = [ #准备删这些目录的一级子文件和目录本身
        *glob(f'{si.outest_sbxdir}/temp'),
        *glob(f'{si.outest_sbxdir}/apps'),
        *glob(f'{si.outest_sbxdir}/new.*.rootfs'),
        *glob(f'{si.outest_sbxdir}'),
    ]
    def safe_call(f):
        try: return f()
        except Exception as err: print_exc(); return []
    for dirpath in paths_rm_sub_files:
        for f in safe_call(lambda: Path(dirpath).iterdir() ):
            if is_file(f) or f.is_symlink() or f.is_socket():
                try_showerr(lambda: f.unlink() )
        try_showerr(lambda: os.rmdir(dirpath) )

    if exist_childtree(): log_warn('cgroup directory for this sandbox instance not cleaned up')
    else:
        try:
            Path(f'{si.CG_TSBXS}/cgroup.procs').write_text(str(os.getpid()))
            os.rmdir(si.CG_SBX)
        except Exception as err:
            log_warn(err)
    try_pass(lambda: os.rmdir(si.sharedir_onhost))

    if not os.path.lexists(si.outest_sbxdir): os.unlink(f'{si.outest_sbxdir}_exit') # 清除正在退出标记

def cleanup_pidnsleader():
    atexit._clear()
    if not isMeThatRegedCleanup(): return
    if os.getpid() != 1 : log_warn("pid != 1. Only the leader process should run this cleanup function"); return
    for u in range(3):
        if not exist_childtree(): break
        os.kill(-1, signal.SIGTERM)
        for i in range(10):
            if (clear := not exist_childtree()): break
            time.sleep(0.1)
        if clear: break
    else:
        os.kill(-1, signal.SIGKILL)


def unregister_sig_handlers():
    for signum in signal.valid_signals():
        if signum not in (signal.SIGKILL, signal.SIGSTOP):
            signal.signal(signum, signal.SIG_DFL)

# NOTE HUP < INT < TERM 退出强烈程度 # TODO SIGHUP 是关闭终端窗口时的信号 ，由用户配置决定外层动作
SIGS_TO_IGN = []
SIGS_TO_PASSBY = [signal.SIGINT, signal.SIGHUP, signal.SIGUSR1, signal.SIGUSR2, signal.SIGTSTP]
SIGS_TO_HANDLE = SIGS_TO_PASSBY + [signal.SIGTERM, signal.SIGCHLD]
def register_sig_handlers(outest=False, pidnsleader=False):
    for sig in SIGS_TO_IGN:     signal.signal(sig, signal.SIG_IGN)
    if pidnsleader:
        for sig in SIGS_TO_HANDLE:  signal.signal(sig, signals_handler_pidnsleader)
    if outest:
        for sig in SIGS_TO_HANDLE:  signal.signal(sig, signals_handler_outest)
def signals_handler_outest(signum, frame):
    _signals_handler(signum, is_outest=True)
def signals_handler_pidnsleader(signum, frame):
    _signals_handler(signum)

def _signals_handler(signum, is_outest=False):
    # NOTE 不能print 不能sleep 不能sys.exit . 只能 os._exit ， 但不要os._exit, 设置should_exit)
    if signum in SIGS_TO_PASSBY:
        pass # TODO
    elif signum == signal.SIGTERM:
        g.sig_say_exit = True
    elif signum == signal.SIGCHLD:
        while True:
            try:
                # -1 表示等待任意子进程 # os.WNOHANG 表示非阻塞：如果没有可回收的子进程，立即返回 (0, 0)
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0: break  # 没有进程退出, 可能是子进程被暂停（STOP）触发的SIGCHLD，我们忽略它，也可能已经处理完了僵尸
            except ChildProcessError:
                if not tlcfg.is_mainlyr or not si.idleKeepSbxTime: g.sig_say_exit = True ;
                break


def exist_childtree(): # 不需要自己pid=1也可以用
    try:
        pid, status = os.waitpid(-1, os.WNOHANG)
        return True
    except ChildProcessError:
        return False


# os.waitpid(-1, os.WNOHANG) 的结果说明：
#     (child_pid, exit_status)	成功回收一个僵尸进程
#     (0, 0)	无僵尸可回收，但子进程仍存在
#     抛出 ChildProcessError（继承自 OSError	errno = ECHILD（No child processes） 值通常为 10 ）
