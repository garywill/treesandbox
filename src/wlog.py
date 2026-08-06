from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量


def wlog(event, me_proc_info=False, **kw_args) :
    if not (si and si.file_fds and si.file_fds.layerslog_a): return False
    kw_args = d(kw_args)
    if kw_args.errmsg: event = 'error' ; kw_args.errmsg=str(kw_args.errmsg)
    logObj = d(
        logger = loghead or tlcfg.layer_name if tlcfg else '',
        event = event,
        **kw_args
    )
    if me_proc_info:
        logObj.self_see_pid=os.getpid()
        logObj.start_tick=get_start_tick('/proc/self/stat')
        logObj.ns = get_nstypes(f'/proc/self/ns')
    try:
        fcntl.flock(si.file_fds.layerslog_a, fcntl.LOCK_EX)
        os.write(si.file_fds.layerslog_a, ''.join([json.dumps(logObj), '\n\n']).encode())
    except Exception as err:
        print_exc()
    finally:
        fcntl.flock(si.file_fds.layerslog_a, fcntl.LOCK_UN)


class WlogReader():
    wlogf = None
    @classmethod
    def init(cls):
        cls.wlogf = open(f'{si.outest_sbxdir}/events.layers.log', 'r')
    @classmethod
    def _read(cls):
        try:
            fcntl.flock(cls.wlogf.fileno(), fcntl.LOCK_EX)
            return cls.wlogf.read()
        finally:
            fcntl.flock(cls.wlogf.fileno(), fcntl.LOCK_UN)
    @classmethod
    def readnew(cls) -> list:
        new_logs = []
        for line in cls._read().splitlines():
            if not line.strip(): continue
            new_logs.append(json.loads(line))
        return new_logs
