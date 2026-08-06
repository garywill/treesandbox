from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量



# 「self_see_pid, start_tick, pidns(inode) = 必备认证3要素」 。仅那些能从主机读出ns目录的可以认证
class OutestProcsMonitor:
    I_AM_OUTEST=None
    @classmethod
    def i_am_outest(cls):
        cls.I_AM_OUTEST=True
        cls.procs_alive = [] # 最外层从主机/proc中读出的。NSpid, start_tick, ns(含各类，但可能无)， cmdvec
        cls.procs_heared = D() # 收到过WLOG且WLOG带ready_proc_name, 但由于可能太快结束，不一定被alive捉到，那样就不进入seen. 格式为WLOG的内容
        cls.procs_seen = D() # WLOG收到信息并与alive对比上后的，NSpid(来自alive), 「self_see_pid, start_tick, pidns(inode) = 必备认证3要素」。可能来自WLOG的pidns_tree, pidns_depth
        cls.procs_wdgsee = D() # 格式同seen, 但只收录需要保活的
        cls.logs_should_match_soon = []
        cls.fd_wr_alive = os.open(f'{si.outest_sbxdir}/procs.alive.json', os.O_WRONLY)
        cls.fd_wr_seen = os.open(f'{si.outest_sbxdir}/procs.seen.json', os.O_WRONLY)
        cls.fd_wr_heared = os.open(f'{si.outest_sbxdir}/procs.heared.json', os.O_WRONLY)
        cls.fd_wr_wdgsee = os.open(f'{si.outest_sbxdir}/procs.wdgsee.json', os.O_WRONLY)

        cls.oPaSkts = d()
        for lyrn, fdpair in dict.items(si.oSkt_fds):
            cls.oPaSkts[lyrn] = socket.socket(fileno=fdpair.pa)

        # 不需等主层启动就发，保证主层收到的第一条信息是这个mainApp的命令
        cls.tell_lyr_runsubp(si.specialLyrs.mainLyr,
            d(
                cmdvec=OG.mainApp_cmdvec,
                subp_name='mainApp',
                workdir     = OG.chosen_workdir     or OG.chosen_appItem.workdir or None,
                workdir_try = OG.chosen_workdir_try or None,
            )
        )
        OutsideServ.init()
    @classmethod
    def get_alive_new_sshot_from_cg(cls) -> list:
        CHK( cls.I_AM_OUTEST, "Only outest can call this, but I_AM_OUTEST is not set")
        ps_sshot = []
        for pid in Path(f'{si.CG_SBX}/cgroup.procs').read_text().splitlines():
            if ( p_full_info := get_pinfo_by_pidpath(f'/proc/{pid}') ):
                ps_sshot.append(p_full_info)
        return ps_sshot
    @classmethod
    def update_procsalive(cls): # 只有 最外层 原进程 调用这个函数
        CHK( cls.I_AM_OUTEST, "Only outest can call this, but I_AM_OUTEST is not set")
        alive_new_sshot = cls.get_alive_new_sshot_from_cg()
        # NOTE 必须 既写本cls内部变量，也更新路径文件内容
        cls.procs_alive = alive_new_sshot # 写cls内部
        cls.write_procs_info_to_file('alive')
    @classmethod
    def aliveproc_and_elproc_equal(cls, plv, pel): #plv="proc alive" | pel="proc from event log"
        if not plv.ns or not plv.ns.pid or not pel.ns or not pel.ns.pid : return False
        if plv.NSpid[-1] == pel.self_see_pid \
        and plv.start_tick == pel.start_tick \
        and plv.ns.pid == pel.ns.pid:
            return True
        else: return False
    @classmethod
    def aliveproc_and_seenproc_equal(cls, plv, psn): # plv="proc alive" | psn="proc seen"
        if not plv.ns or not plv.ns.pid: return False
        if plv.NSpid[-1] == psn.self_see_pid \
        and plv.start_tick == psn.start_tick \
        and plv.ns.pid == psn.pidns :
            return True
        else: return False
    @classmethod
    def conv_to_seenproc(cls, aliveProc, logItem): # 输入的是一对互相符合的aliveProc和logItem条目
        return D(
            NSpid = aliveProc.NSpid,
            pidns_tree = logItem.pidns_tree,
            pidns_depth = logItem.pidns_depth,
            start_tick = logItem.start_tick,
            pidns = logItem.ns.pid,
            self_see_pid = logItem.self_see_pid,
        )
    @classmethod
    def sbx_exit_broadcast(cls):
        CHK( cls.I_AM_OUTEST, "Called sbx_exit_broadcast() without I_AM_OUTEST set", 'warn') # 可能会在初始化之前被调用
        for lyrname in si.expected_alive_layers:
            cls.sendmsg_to_lyr(lyrname, d(action='sbx_exit'), loose=True)
    @classmethod
    def sendmsg_to_lyr(cls, lyrname, msgobj, loose=False):
        CHK( cls.I_AM_OUTEST, "Called sendmsg_to_lyr() without I_AM_OUTEST set", 'warn' if loose else 'raise_exit')
        try:
            cls.oPaSkts[lyrname].send(json.dumps(msgobj).encode())
        except Exception as err:
            if loose: log_warn(f"Sending message to {lyrname} was not successful: {err}")
            else: raise
    @classmethod
    def tell_lyr_runsubp(cls, lyrname, subpItem):
        CHK( cls.I_AM_OUTEST, "Only outest can call this, but I_AM_OUTEST is not set")
        cls.sendmsg_to_lyr(lyrname, d(action='run_subp', subpItem=subpItem) )
    @classmethod
    def symlink_into_sbxdir(cls, dest, file_in_sbxdir): # 创建软链，从外部，链到本沙箱实例目录内的文件
        CHK( cls.I_AM_OUTEST, "Only outest can call this, but I_AM_OUTEST is not set")
        linkto = napath(f'{si.outest_sbxdir}/{file_in_sbxdir}')
        CHK( not Path(linkto).is_dir(), f'For safety, linking to directories is not allowed')
        symlink(linkto, dest)
    @classmethod
    def symlink_from_sbxdir_to_in_proc_rootfs(cls, slk_name, to_proc_name, target_in_proc_rootfs): # 创建软链，从本沙箱实例目录内, 链到本沙箱的进程的 rootfs 里的某文件
        CHK( cls.I_AM_OUTEST, "Only outest can call this, but I_AM_OUTEST is not set")
        pid = get_procs_seen()[to_proc_name].NSpid[0]
        real_linkto = napath(f'/proc/{pid}/root/{target_in_proc_rootfs}')
        CHK( not Path(real_linkto).is_dir(), f'For safety, linking to directories is not allowed')
        symlink(real_linkto, f'{si.outest_sbxdir}/into.{to_proc_name}.{slk_name}.link')
    @classmethod
    def custom_action_when_procname_seen(cls, proc_name):
        CHK( cls.I_AM_OUTEST, "Only outest can call this, but I_AM_OUTEST is not set")
        if proc_name == 'userns_unpri':
            OG.userns_unpri = get_userns_unpri()
        if proc_name in ['xephyr', 'xwayland', 'xvfb']:
            cls.symlink_from_sbxdir_to_in_proc_rootfs('x11socket', proc_name, f'/tmp/.X11-unix/X{si.newXId}')
            cls.symlink_into_sbxdir(f'/tmp/.X11-unix/X{si.newXId}', f'into.{proc_name}.x11socket.link')
            cleanup_symlinks_to_rm.add(f'/tmp/.X11-unix/X{si.newXId}')
        if proc_name == 'weston':
            cls.symlink_from_sbxdir_to_in_proc_rootfs('waylandsocket', proc_name, f'{si.sbx_XDG_R_D}/wayland-{si.newXId}')
            cls.symlink_into_sbxdir(f'{si.host_XDG_R_D}/wayland-{si.newXId}', f'into.{proc_name}.waylandsocket.link')
            cleanup_symlinks_to_rm.add(f'{si.host_XDG_R_D}/wayland-{si.newXId}')
        if proc_name.startswith('shareshell_'):
            shellId = proc_name.removeprefix('shareshell_')
            cls.symlink_from_sbxdir_to_in_proc_rootfs('shellsocket', proc_name, f'/sbxdir/temp/shareshell.{shellId}.socket')
        for bItem in (si.bridges or []):
            cls.check_bridges_condition_and_do(proc_name, bItem)
    @classmethod
    def check_bridges_condition_and_do(cls, proc_name, bItem):
        seefrom = bItem.real_seefrom
        seeto   = bItem.real_seeto
        bridge_name = bItem.bridge_name
        condition = ['userns_unpri',  seefrom, seeto]
        if proc_name in condition:
            if set(condition).issubset(set(dict.keys( get_procs_seen() ))):
                log(f'Creating bridge {bridge_name}')
                seefrom_pid         = get_procs_seen()[seefrom].NSpid[0]
                seeto_pid   = get_procs_seen()[seeto].NSpid[0]
                pidfd_seefrom        = os.pidfd_open(seefrom_pid)
                pidfd_seeto   = os.pidfd_open(seeto_pid)
                ns_seefrom        = get_nstypes(f'/proc/{seefrom_pid}/ns')
                ns_seeto   = get_nstypes(f'/proc/{seeto_pid}/ns')
                PID1, _ = fork( proc_dispname='bridge', loghead=bridge_name, cut_stdin=True,
                               close_fds=True,
                               close_keep_fds=[si.file_fds.layerslog_a, pidfd_seefrom,  pidfd_seeto, OG.userns_unpri.usernsfd],
                               set_fds_CLOEXEC=True )
                if PID1 == 0: # 第一个子进程.因为之前创建layer1时unshare过，这里已经是与layer1同pidns
                    # TODO 判断其他ns种类，如果不同，也要setns过去
                    os.setns(pidfd_seefrom, unshrflg(d(pid=1)))

                    PID2, _ = fork(loghead=f'{loghead}F', cut_stdin=True)
                    if PID2 == 0 : # 第二个子进程（孙进程). 与seefrom同pidns
                        mypid = os.getpid()

                        os.setns(pidfd_seefrom, unshrflg(d(mnt=1))) # 先改一次mnt ns ， 等下还要改


                        for lkItem in (bItem.create_links or []) :
                            path = napath(lkItem)
                            symlink(f'/proc/{mypid}/root/{path.lstrip('/')}', path)

                        start_tick=get_start_tick('/proc/self/stat')
                        ns = get_nstypes(f'/proc/self/ns') # 这还不是最终的，还要改

                        ns.mnt = ns_seeto.mnt
                        os.setns(pidfd_seeto, unshrflg(d(mnt=1))) # 在这之后就不可以获得自己的ns或start_tick信息

                        ns.user = OG.userns_unpri.usernsino
                        wlog('subp_start',
                             ready_proc_name=bridge_name ,
                             self_see_pid=mypid,
                             start_tick=start_tick,
                             ns=ns,
                        )
                        close_3ge_fds(keep_fds=[OG.userns_unpri.usernsfd])
                        os.setns(OG.userns_unpri.usernsfd, unshrflg(d(user=1))) # 在这之后无法setns NOTE 在这之前应该关闭重要fd


                        drop_caps(no_textcheck_after_dropcap=True)
                        execvp('sleep', [f"{si.sandbox_name}_{bridge_name}", 'infinity' ])
                        errmsg = f'Bridge exec unsuccessful {bItem}'
                        # wlog('error', errmsg=errmsg) # fd已关闭，无法wlog('error')
                        raise_exit(errmsg, no_cleanup=True)
                    # 第一个子进程
                    # log('First child process exiting')
                    os._exit(0)
                # 原最外层进程
                # log('最外层完成桥的创建')
                os.close(pidfd_seefrom)
                os.close(pidfd_seeto)

    @classmethod
    def find_alive_proc_matching_logitem(cls, elp):
        for proc in get_procs_alive(): # 在存在进程列表中查找，看有没有这个
            if cls.aliveproc_and_elproc_equal(proc, elp):
                return proc
    @classmethod
    def add_keyval_to_procs_record(cls, procsType, key, val): # dict, 不包括alive
        CHK( cls.I_AM_OUTEST, "Only outest can call this, but I_AM_OUTEST is not set")
        CHK(procsType in ['seen', 'heared', 'wdgsee'], 'Unknown procsType')
        # NOTE 必须 既写本cls内部变量，也更新路径文件内容
        getattr(cls, 'procs_'+procsType) [key] = val
        cls.write_procs_info_to_file(procsType)
    @classmethod
    def put_proc_into_seenlist(cls, proc_name, seenProc, logItem):
        cls.add_keyval_to_procs_record('seen', proc_name, seenProc)
        if logItem in cls.logs_should_match_soon: # 上次已经加入了注意名单，现在可以移出注意名单
            log(f'Removing this log from the unrecognized log list {logItem}')
            cls.logs_should_match_soon.remove(logItem)
        if proc_name in si.expected_alive_procs:
            cls.add_keyval_to_procs_record('wdgsee', proc_name, seenProc)
        cls.custom_action_when_procname_seen(proc_name)
    @classmethod
    def got_a_ready_proc_log(cls, logItem): # 被调用时，说明一个进程有了logItem出现
        proc_name = logItem.ready_proc_name
        cls.add_keyval_to_procs_record('heared', proc_name, logItem)
        # 判断这个进程是否已经在aliveProcs的列表里
        if (aliveProc := cls.find_alive_proc_matching_logitem(logItem) ):
            seenProc = cls.conv_to_seenproc(aliveProc, logItem)
            cls.put_proc_into_seenlist(proc_name, seenProc, logItem)
        else: # 不在aliveProcs列表里：1.可能暂时来不及出现，允许等下个周期再出现 2.若已经不是第1个周期，则判断进程死亡
            if proc_name not in si.expected_alive_procs : # 看门狗不用管这个进程
                return
            if logItem not in cls.logs_should_match_soon: # 可能暂时来不及出现，允许等下个周期再出现
                log(f'Adding this log to the unrecognized log list {logItem}')
                cls.logs_should_match_soon.append(logItem)
            else: # 已经不是第1个周期，则判断进程死亡
                log(f'Received message for {proc_name} start, but never found alive. Assume it died')
                sys.exit()
    @classmethod
    def get_and_parse_new_wlog(cls):
        new_logs = WlogReader.readnew()
        for logItem in (cls.logs_should_match_soon + new_logs):
            logItem = dn(logItem)

            if logItem.event == 'error':
                log(f'Received error message from {logItem.logger}: {logItem.errmsg}')
                sys.exit(1)

            if logItem.ready_proc_name :
                cls.got_a_ready_proc_log(logItem)
    @classmethod
    def write_procs_info_to_file(cls, procsType):
        CHK( cls.I_AM_OUTEST, "Only outest can call this, but I_AM_OUTEST is not set")
        CHK(procsType in ['alive', 'seen', 'heared', 'wdgsee'], 'Unknown procsType')
        write_to_fd_override( getattr(cls, 'fd_wr_'+procsType),
            jsondumps_mycompat(getattr(cls, 'procs_'+procsType) ) )
    @classmethod
    def wdg(cls): # 看看那些已经在 procs_wdgsee 列表中的进程还存活吗
        CHK( cls.I_AM_OUTEST, "Only outest can call this, but I_AM_OUTEST is not set")
        cls.update_procsalive()
        cls.get_and_parse_new_wlog()
        for proc_name,psn in dict.items(get_procs_wdgsee()):
            for plv in get_procs_alive():
                if cls.aliveproc_and_seenproc_equal(plv, psn):
                    break
            else:
                log(f'{proc_name} is no longer alive, watchdog terminating sandbox')
                sys.exit()
        OutsideServ.one_loop_task()


def daemon_outest():
    # TODO 等待5秒，等待主app启动的信号，否则退出
    set_proc_dispname(f'{si.sandbox_name}_TSBX_outest_{si.instance_name}'[:15])
    register_sig_handlers(outest=True)

    WlogReader.init()
    OutestProcsMonitor.i_am_outest()

    t0 = time.monotonic()
    while True:
        OutestProcsMonitor.wdg()

        if time.monotonic() >= t0 + (10 if OG.uc.gui not in ['xpra', 'xpra-weston-xwayland'] else 60):
            A = set(dict.keys(get_procs_heared() ))
            B = set(si.expected_alive_procs) # TODO 区分expected_heared_procs , 应用 noWdg=1选项给subprocs
            if not B.issubset(A):
                warn_exit(f'Did not receive startup messages for {list(B-A)} processes within the timeout, assuming sandbox startup was not completely successful')

        if g.sig_say_exit: OutestProcsMonitor.sbx_exit_broadcast()

        if not exist_childtree(): sys.exit()

        time.sleep(0.2)



lasttick_havechd = 0
lasttick_clipbd = 0
def daemon_pidnsleader():
    global lasttick_havechd , lasttick_clipbd
    CHK( os.getpid() == 1, f"{tlcfg.layer_name} detected its own PID is not 1 (should be 1)")
    PidnsleaderListener.i_am_pidnsleader()
    PERIOD = 0.2
    while True:
        if g.sig_say_exit: sys.exit()

        if (msg_from_outest := PidnsleaderListener.readmsg_from_outest() ):
            if msg_from_outest.action == 'sbx_exit':
                sys.exit()
            elif msg_from_outest.action == 'run_subp':
                layer_run_subp(no_wait=True,  **msg_from_outest.subpItem )

                if tlcfg.is_mainlyr: # 默认认为收到过的第一个run_subp指令就是mainApp
                    PidnsleaderListener.MainApp_Ever_Started = True

        if tlcfg.is_mainlyr and PidnsleaderListener.MainApp_Ever_Started :
            if not si.idleKeepSbxTime:
                if not exist_childtree() : sys.exit()
            else: # si.idleKeepSbxTime > 0:
                if exist_childtree()  :
                    lasttick_havechd = time.monotonic()
                else:
                    tick_diff = time.monotonic() - lasttick_havechd
                    if tick_diff%1 <= PERIOD: log(f'{int(tick_diff)}/{si.idleKeepSbxTime} Main layer idle, will terminate sandbox if idle for long')
                    if time.monotonic() > lasttick_havechd+si.idleKeepSbxTime: sys.exit()

        for taskItem in (tlcfg.daemon_tasks or []):
            if taskItem.task == 'sync_clipbd' and time.monotonic() > lasttick_clipbd + 1.5: # NOTE 间隔要够大，比其超时时间大
                ClipboardSyncer.one_loop_task()
                lasttick_clipbd = time.monotonic()

        time.sleep(PERIOD)

class PidnsleaderListener():
    I_AM_PIDNSLEADER=None
    MainApp_Ever_Started=False # 是否收到过来自最外层的mainApp的启动命令（仅主层使用）
    @classmethod
    def i_am_pidnsleader(cls):
        cls.I_AM_PIDNSLEADER=True
        cls.oChdSkt = socket.socket(fileno=si.oSkt_fds[tlcfg.layer_name].chd)
    @classmethod
    def readmsg_from_outest(cls):
        ready, _, wrong = select.select([cls.oChdSkt], [], [cls.oChdSkt], 0)
        if wrong: raise_exit('Unknown error while trying to read message from outest')
        elif ready: return d(json.loads( cls.oChdSkt.recv(300_000).decode() ) )


def D_cont_dn(obj):
    result = D()
    for key,val in enumerate(obj): result[key] = dn(val)
    return result

def get_procs_alive() -> list:
    if OutestProcsMonitor.I_AM_OUTEST:  return OutestProcsMonitor.procs_alive
    else: return [dn(x) in read_all_from_fd_then_jsonloads(si.file_fds.procs_alive) ]

def get_procs_seen():
    if OutestProcsMonitor.I_AM_OUTEST:  return OutestProcsMonitor.procs_seen
    else: return D_cont_dn(read_all_from_fd_then_jsonloads(si.file_fds.procs_seen) )

def get_procs_heared():
    if OutestProcsMonitor.I_AM_OUTEST:  return OutestProcsMonitor.procs_heared
    else: return D_cont_dn(read_all_from_fd_then_jsonloads(si.file_fds.procs_heared) )

def get_procs_wdgsee():
    if OutestProcsMonitor.I_AM_OUTEST:  return OutestProcsMonitor.procs_wdgsee
    else: return D_cont_dn(read_all_from_fd_then_jsonloads(si.file_fds.procs_wdgsee) )



# TODO def get_pUniqId()
def get_nstypes(nsdir_path):
    return D({nstype:os.stat(f'{nsdir_path}/{nstype}').st_ino for nstype in os.listdir(nsdir_path)})

def get_start_tick(statfile_path): # 返回的是字符串，不是数字
    return Path(statfile_path).read_text().split(') ')[-1].split(' ')[22-1-2]  # stat文件里的第22个字段是进程开始时间（cpu tick）， 去掉前两个字段

def get_NSpid_arr(status_file_path) -> list:
    for line in Path(status_file_path).read_text().splitlines():
        if line.startswith("NSpid:"):
            return [int(x) for x in line.split()[1:]]

def get_pinfo_by_pidpath(pidpath):
    try:
        res = D()
        inode1 = os.stat(pidpath).st_ino
        res.comm = Path(f'{pidpath}/comm').read_text().strip()
        res.NSpid = get_NSpid_arr(f'{pidpath}/status')
        res.start_tick = get_start_tick(f'{pidpath}/stat')
        try:    res.ns = get_nstypes(f'{pidpath}/ns')
        except: res.ns = dn()
        res.cmdvec = Path(f'{pidpath}/cmdline').read_text().strip('\x00').split('\x00')
        inode2 = os.stat(pidpath).st_ino
        if inode1 != inode2: return None
        return res
    except: return None
