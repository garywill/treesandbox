from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量



libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)

def set_nonewpriv(doprint=False):
    PR_SET_NO_NEW_PRIVS = 38
    ret = libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
    errno = ctypes.get_errno() if ret != 0 else None
    errstr = os.strerror(errno) if ret != 0 else None
    log('Setting noNewPrivs', (ret, errno, errstr)) if doprint else None
    return (ret, errno, errstr)

def drop_caps(no_textcheck_after_dropcap=False):
    PR_GET_NO_NEW_PRIVS = 39
    PR_CAPBSET_DROP = 24
    PR_CAPBSET_READ = 23
    PR_CAP_AMBIENT = 47
    PR_CAP_AMBIENT_CLEAR_ALL = 4
    CAP_SETPCAP = 8

    class CapHeader(ctypes.Structure):
        _fields_ = [("version", ctypes.c_uint32), ("pid", ctypes.c_int)]
    cap_hdr = CapHeader(version=0x20080522, pid=0)

    class CapData(ctypes.Structure):
        _fields_ = [ ("effective", ctypes.c_uint32 * 2), ("permitted", ctypes.c_uint32 * 2), ("inheritable", ctypes.c_uint32 * 2), ]

    def get_caps_dict():
        status_text = Path("/proc/self/status").read_text()
        cap_fields = {}
        for cap_field in ["CapInh", "CapPrm", "CapEff", "CapBnd",  "CapAmb", "NoNewPrivs" ]:
            pattern = rf"^{cap_field}:\s*(\S+)"
            match = re.search(pattern, status_text, re.MULTILINE)
            cap_fields[cap_field] = match.group(1)
        return cap_fields

    def capset_clear(eff=False, prm=False, inh=False,  doprint=False):
        cap_data = CapData()
        for i in range(2):
            cap_data.effective[i] = 0    if eff else 0xffffffff
            cap_data.permitted[i] = 0    if prm else 0xffffffff
            cap_data.inheritable[i] = 0  if inh else 0xffffffff
        ret = libc.capset(ctypes.byref(cap_hdr), ctypes.byref(cap_data) )
        errno = ctypes.get_errno() if ret != 0 else None
        errstr = os.strerror(errno) if ret != 0 else None
        log(f"Clearing capability sets {eff=} {prm=} {inh=}", (ret, errno, errstr)) if doprint else None
        return (ret, errno, errstr)

    def amb_clear(doprint=False):
        ret = libc.prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL, 0, 0, 0)
        errno = ctypes.get_errno() if ret != 0 else None
        errstr = os.strerror(errno) if ret != 0 else None
        log('Clearing amb', (ret, errno, errstr)) if doprint else None
        return (ret, errno, errstr)

    def bnd_clear(maxid, doprint=False):
        results = []
        for cap_id in range(maxid + 1):
            ret = libc.prctl(PR_CAPBSET_DROP, cap_id, 0, 0, 0)
            errno = ctypes.get_errno() if ret != 0 else None
            errstr = os.strerror(errno) if ret != 0 else None
            results.append((ret, errno, errstr))
        log('Clearing bnd', results) if doprint else None
        return results



    show_clear_result = False
    capset_clear(eff=False , prm=True, inh=True,  doprint=show_clear_result)
    amb_clear(doprint=show_clear_result)
    set_nonewpriv(doprint=show_clear_result)
    bnd_clear(si.BND_MAX,  doprint=show_clear_result)
    capset_clear(eff=True, prm=True, inh=True,  doprint=show_clear_result)

    # ------验证------------

    # libc验证 no_new_privs
    CHK( libc.prctl(PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0) == 1, 'noNewPrivs clear verification failed')
    # libc验证 bounding set
    for cap_id in range(si.BND_MAX +1): # 内核只支持0~40
        CHK( libc.prctl(PR_CAPBSET_READ, cap_id, 0, 0, 0) == 0, f'cap_id {cap_id} capability drop failed')

    if no_textcheck_after_dropcap:
        return

    # 验证 /proc/self/status 中所有能力字段为 0
    caps_dict = get_caps_dict()
    CHK( caps_dict.pop('NoNewPrivs') == '1' , "NoNewPrivs not successfully set as shown in /proc" ) # 用pop不用get
    for k,v in caps_dict.items(): CHK( re.search(rf"^0+$", v), f"Clearing failed for {k} as shown in /proc ")


def pivot_root(new_root, put_old):
    res = libc.pivot_root(ctypes.c_char_p(new_root.encode()), ctypes.c_char_p(put_old.encode()))
    if res != 0:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno))


MS = types.SimpleNamespace(RDONLY=0x01, NOSUID=0x02, NODEV=0x04, NOEXEC=0x08,  REMOUNT=0x20, NOSYMFOLLOW=0x100, BIND=0x1000, MOVE=0x2000, REC=0x4000,  UNBINDABLE=1<<17, PRIVATE=1<<18, SLAVE=1<<19, SHARED=1<<20, )
def mount(source, target, fstype, flags, data): # source可能空, 或为tmpfs或proc， target一定有
    allowed_nonabs = ['tmpfs', 'proc', 'devpts', 'overlay']
    if not ( (source is None) or (source in allowed_nonabs) or (source.startswith('/')) ):
        raise_exit(f"Mount source {source} is not an absolute path, and not in allowed {allowed_nonabs}")
    if isinstance(source, str) and source.startswith('/'):
        source = napath(source)
    target = napath(target)
    if source and source.startswith('/') and rslvy(source) != source:
        raise_exit(f"Mount source path {source} or one of its parent directories is currently a symlink. Handling for this case not yet implemented")
    if rslvy(target) != target:
        raise_exit(f"Mount target path {target} or one of its parent directories is currently a symlink. Handling for this case not yet implemented")
    # log(f"Executing mount {source} --> {target}")
    ret = libc.mount(
        source.encode() if source else None,
        target.encode(),
        fstype.encode() if fstype else None,
        flags,
        data.encode() if data else None
    )
    if ret != 0:
        log(f"Error during mount {source} -> {target} | {fstype=} {flags=} {data=}")
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno), target)

def mount_overlayfs(lowerdir, upperdir, workdir, target, flags=0):
    def pathEscape(p: str) -> str:
        p = napath(p)
        return p.replace("\\", "\\\\") .replace(",", "\\,") .replace(":", "\\:")

    upperdir = pathEscape(upperdir)
    workdir = pathEscape(workdir)

    if isinstance(lowerdir, list): # lowerdir 是数组
        lowerdir = [pathEscape(x) for x in lowerdir]
    else: # lowerdir不是数组
        lowerdir = [pathEscape(lowerdir) ]
    joined_lowerdir = ':'.join(lowerdir)

    mount('overlay', target, 'overlay', flags=flags,
          data=f"lowerdir={joined_lowerdir},upperdir={upperdir},workdir={workdir}"
          )


MNT = types.SimpleNamespace(FORCE=1, DETACH=2, EXPIRE=4, NOFOLLOW=8) # 缷载（umount2)可能用到的常数
def umount(target, flags=0):
    ret = libc.umount2(
        target.encode(),
        flags
    )
    if ret != 0:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno), target)

mntflag_newrootfs = MS.NODEV | MS.NOSUID
mntflag_proc = MS.NODEV|MS.NOSUID|MS.NOEXEC
mntflag_newsbxdir = MS.NODEV|MS.NOSUID
mntflag_apps = MS.NODEV|MS.NOSUID
mntflag_sbxtemp = MS.NOSUID|MS.NODEV
mntflag_binddir = MS.BIND|MS.REC|MS.NOSUID
mntflag_tmpfs = MS.NOSUID|MS.NODEV # 这里设置nodev也会让/dev有nodev,但因为每个具体的设备是bind进去的，所以好像没问题


def set_pdeathsig(sig): # 由layer1的fork出来的子进程调用, 让真实父进程退出后沙箱内能够收到TERM信号
    PR_SET_PDEATHSIG = 1
    libc.prctl(PR_SET_PDEATHSIG, sig)

def set_proc_dispname(dispname):
    PR_SET_NAME = 15
    CHK( len(name_bytes := dispname.encode("utf-8")) <= 15 , f"Process name {dispname} exceeds 15 bytes")
    libc.prctl(PR_SET_NAME, name_bytes, 0, 0, 0)
