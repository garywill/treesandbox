from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量



def main(lyrcfg_in):
    if not isinstance(lyrcfg_in, dict): is_outest = True # 是顶层
    else: is_outest = False # 是子层

    if is_outest: # 是顶层
        arg_parser = argparse.ArgumentParser( add_help=True, usage="%(prog)s [options] [<user_cli_argv> ...]",
            description="Tree Sandbox script. Do sandbox operations based on userconfig() function and CLI args. Can start new sandbox instance or reuse a running same-name instance."
        )
        arg_parser.add_argument("--nocleanup", action='store_true',
                                help="Do not delete the temporary sandbox info dir after sandbox instance quit")
        arg_parser.add_argument("--reusefg", action='store_true',
                                help="If reusing a running instance, use remote shell, letting new-started app in foreground of current terminal. Otherwise, send the new-app command to running instance then we return. (Only effective if the sandbox has reuseful enabled in config). If starting a new sandbox instance, this option is ignored.")
        # arg_parser.add_argument("--enter", action='store_true',
                                # help="自动找到一个正在运行的同名沙箱实例，获得其shell。若无正在运行的实例，报错退出")
        # arg_parser.add_argument("--enter-instance", metavar="<chosen_instance_name>",
                                # help="找到指定的正在运行的具体实例，获得其shell。可以是非同名沙箱，但沙箱版本需要一致")
        arg_parser.add_argument("--app", metavar="<chosen_appname>", default="default",
                                help="Using a configured appname, specify the command to start in sandbox. Not specifying or using '--app default' has the same effect.")
        arg_parser.add_argument("--workdir", metavar="<path>", default=None,
                                help="Before launch app, cd to this path")
        arg_parser.add_argument("--workdir-try", metavar="<path>", default=None,
                                help="Similar to '--workdir', but will fallback to default workdir path if cd fails")


        (sbx_args, # 上面列出的参数
         user_cli_argv # 未知参数，即之后的参数，传给沙箱内的app
        ) = arg_parser.parse_known_args()

        nocleanup = sbx_args.nocleanup
        reusefg = sbx_args.reusefg
        # enter = sbx_args.enter
        # chosen_instance_name = sbx_args.enter_instance
        chosen_appname = sbx_args.app
        chosen_workdir     = sbx_args.workdir
        chosen_workdir_try = sbx_args.workdir_try

    if is_outest:
        layer1_cfg = init_sbxinfo() # 只有从最外层启动才运行这个函数。 也会写 si, OG
        dict.clear(tlcfg) ; dict.update(tlcfg , layer1_cfg)

        # tlcfg.sbxdir_path0 = # 到后面决定了instance_name才设置这个

        if nocleanup: si.nocleanup = True
    else: # 是子层
        dict.clear(tlcfg) ; dict.update(tlcfg , lyrcfg_in)
        tlcfg.sbxdir_path0 = '/sbxdir' if is_dir('/sbxdir') else si.outest_sbxdir
        # si   # 不需要再加载si, 因为是fork来的

    if is_outest:
        if reusefg: CHK(si.reuseful, '--reusefg cannot be used because reuseful is not enabled in the sandbox configuration')
        log(f"PID: {si.outest_pid}  Sandbox name: {si.sandbox_name}   Run by: {si.username} {si.groupname}")
        if not chosen_appname or chosen_appname=='default': chosen_appItem = si.apps[0]
        else: chosen_appItem = next((app for app in si.apps if app.get('appname') == chosen_appname), None)
        CHK( chosen_appItem and chosen_appItem.cmdvec, 'Selected app not found, or selected app does not have a valid cmdvec')
        OG.chosen_appItem = chosen_appItem
        OG.chosen_workdir     = chosen_workdir
        OG.chosen_workdir_try = chosen_workdir_try
        OG.user_cli_argv = user_cli_argv
        OG.mainApp_cmdvec = chosen_appItem.cmdvec + user_cli_argv
        log(f'App command to run in sandbox: {OG.mainApp_cmdvec}')

        # 判断应该 新实例 还是 发送app命令到 正在运行的实例
        if si.reuseful:
            question_reuse = maybe_sendto_running_instance(reusefg)
            CHK( question_reuse=='not_reusing', 'Here either the result should be "not_reusing", or the judgment function should have ended the process')
        log('---------------------')
        if si.newXId:
            CHK( is_XId_available(si.newXId), f"The display number {si.newXId=} to be used is occupied")
        log(f"Procs to be polled by watchdog: {si.expected_alive_procs}")
        if si.newXId: log(f'X11/Wayland display number used in sandbox: {si.newXId}')

        reg_cleanup_func(cleanup_outest) # 顶层父进程注册清理函数

        make_mnt_fill_sbxdir(si, layer1_cfg, call_at_begin=True, OG=OG)
        log(f"Create new instance of sandbox. Info dir: {si.outest_sbxdir}")
        log(f"cgroup: {si.CG_SBX}")
        tlcfg.sbxdir_path0 = si.outest_sbxdir

    set_loghead (f'{tlcfg.layer_name}: ' if not is_outest else 'outest: ')
    set_ps1('notready')

    # 创建主机与沙箱之间的临时共享目录
    if is_outest and si.sharedir_onhost:
        log(f'Create temporary shared dir between host and sandbox at {si.sharedir_onhost}')
        mkdirp(si.sharedir_onhost)

    # ----------------------------
    # 预先算好变根后的 sbxdir_path1
    if not tlcfg.newrootfs:
        tlcfg.sbxdir_path1 = tlcfg.sbxdir_path0
    else:
        tlcfg.sbxdir_path1 = next((opItem.dest for opItem in tlcfg.fs if opItem.many_op == 'sbxdir-in-newrootfs'), None)
    # sbxdir_path 说明
    # 本层变根 前 后 的 sbxdir_path ( sbxdir_path0 sbxdir_path1)
    # 变根前 0 = 刚启动本层启动脚本时
    # 变根后 1 = 即将运行下层的启动脚本时
    # 变根不一定发生，由本层配置决定，但也把两个sbxdir_path以 前 后 来称呼
    # ----------------------------

    # 环境变量
    for env_to_unset in (tlcfg.envs_unset or [] ):
        os.environ.pop(env_to_unset, None)
    for envg in (tlcfg.envset_grps or [] ) :
        if len(dict.keys(envg))>0:
            log('Update env variables' , envg)
            os.environ.update(envg)

    wait_for_startAfters(tlcfg.start_after)

    # TODO 用个数组储存 pid time 是fork前做，其他main2做
    unshr_cfg = lyrcfg_to_unshrcfg(tlcfg)
    unshr_cfg.mnt=False # unshare排除mnt（后面再做）
    if tlcfg.depth != 1: unshr_cfg.user=False # 非首层则unshare排除user（后面再做）
    os.unshare(unshrflg(unshr_cfg))

    set_ps1('afterUnshare')

    pid, skp_lyfk = fork(create_socketpair=True, loghead=f'{tlcfg.layer_name} F: ', proc_dispname=tlcfg.layer_name)
    if pid == 0: # 子进程
        if tlcfg.depth == 1:
            set_pdeathsig(signal.SIGTERM) # 最外层的原进程（fork前的进程）退出的话，layer1的fork出来的子进程应该主动退出
        return main2(skp_lyfk)
    else: # 父进程

        # if tlcfg.uid_map_as_user and tlcfg.depth > 1: # 已删除 map_as_user 的功能
        skp_lyfk.close()

        if is_outest:
            OG.layer1_pid = pid
            daemon_outest() # NOTE skp_lyfk 关了后，才进入daemon
        else:
            sys.exit()



def main2(skp_lyfk):
    # 变内部uid=0 (root)
    if tlcfg.uid_map_as_root:
        Path('/proc/self/setgroups').write_text('deny\n')
        Path('/proc/self/uid_map').write_text(f'0 {si.uid} 1\n')
        Path('/proc/self/gid_map').write_text(f'0 {si.gid} 1\n')
        log(f"Internal current uid={os.getuid()} gid={os.getgid()}")

    if tlcfg.unshare_mnt: # 现在才做，保证不影响父进程所看到的 /proc
        os.unshare(unshrflg(d(mnt=True)))


    # 本层文件系统、挂载proc （维持 rw）， 变根
    build_fs(tlcfg)

    # Unshare User (非首层)
    if tlcfg.unshare_user and tlcfg.depth > 1 : # 第1层的若要做在之前就做了
        os.unshare(unshrflg(d(user=True)))

    if tlcfg.create_userns_unpri:
        OG.userns_unpri = create_userns_unpri()
    if tlcfg.pasta_args:
        OG.netns_tun = create_netns_tun( tlcfg.pasta_args )
        os.setns(OG.netns_tun.pidfd, unshrflg(d(net=1)))
    if tlcfg.nftables_rule:
        with tempfile.NamedTemporaryFile( dir=f'{tlcfg.sbxdir_path1}/temp', mode='w', delete=True) as f:
            f.write(tlcfg.nftables_rule)
            f.flush()
            PATH_w_sbin = '/sbin:/usr/sbin:/usr/local/sbin:' +  getenv('PATH', '').strip(':')
            run_a_cmd(['env', f'PATH={PATH_w_sbin}',  'nft', '-f', f.name ])

    # 变内部uid=1000 (user)
    # if tlcfg.uid_map_as_user: # 已删除 map_as_user 功能

    # 关闭临时socket
    skp_lyfk.close()# NOTE 注意， 在创建任何 subp 之前 ， skp_lyfk(临时socket)必须已关闭

    # 非unshare_pid 层 则要等待fork前父进程退出
    if not tlcfg.unshare_pid:
        while os.getppid() not in [0, 1] : time.sleep(0.03)


    #--- 创建 subp -----------------------------------
    # NOTE 注意， 在创建任何 subp 之前 ， skp_lyfk(临时socket)必须已关闭

    inprepare_children = []

    # 以subp启动子层
    for sublyr_cfg in (tlcfg.sublayers or []):
        pid, skp_spfk = layer_run_subp( subp_name=sublyr_cfg.layer_name )
        if pid == 0:
            return sublyr_cfg # 让main2()返回，准备开始下一层
        inprepare_children.append((pid, skp_spfk)) # 原进程才需要pid和skp_spfk

    # 清理函数、信号处理注册 (要在sublayer之后)
    if tlcfg.unshare_pid:
        CHK( os.getpid() == 1, f"{tlcfg.layer_name} detected its own PID is not 1 (should be 1)")
        reg_cleanup_func(cleanup_pidnsleader)
        register_sig_handlers(pidnsleader=True)

    set_ps1('ready')

    # 以subp启动user_shell / dev_shell
    if tlcfg.user_shell or tlcfg.dev_shell:
        if tlcfg.user_shell: set_3ge_fds_cloexec() # 沙箱启动时设置过，保险再来一次
        pid, skp_spfk = layer_run_subp(cmdvec=['/bin/bash'] ,
                        **( d(subp_name='user_shell') if tlcfg.user_shell else {}),
                        **( d(subp_name='dev_shell')  if tlcfg.dev_shell  else {}),
        )
        inprepare_children.append((pid, skp_spfk))

    # 以subp启动普通辅助app
    set_3ge_fds_cloexec() # 沙箱启动时设置过，保险再来一次

    for subpItem in (tlcfg.subprocs or [] ) :
        pid, skp_spfk = layer_run_subp (**subpItem)
        inprepare_children.append((pid, skp_spfk))

    #-------------------------------------------

    # 向最外层发送“本层已boot”，
    wlog('layer_booted', me_proc_info=True,
         ready_proc_name=tlcfg.layer_name,
         pidns_depth=tlcfg.pidns_depth, pidns_tree=tlcfg.pidns_tree,
         **(d(is_mainlyr=True) if tlcfg.is_mainlyr else {}),
         **(d(is_semitruCmpannLyr=True) if tlcfg.is_semitruCmpannLyr else {}),
    )

    if not tlcfg.unshare_pid:
        fds_to_keep = [skp._skt_pa.fileno() for _,skp in inprepare_children]
        close_3ge_fds(keep_fds=fds_to_keep)

    # 放行那些等待住的subp (为了等 重要fd 关闭. pidns层则不怕subp访问/proc/1/fd 因为无法访问 )
    for pid, skp_spfk in inprepare_children:
        skp_spfk.pa_send(BS.YouChdGo)
    for pid, skp_spfk in inprepare_children:
        skp_spfk.pa_send(BS.YouChdGo)
        skp_spfk.close()

    # TODO 让最外层把每一层的pidfd和各类ns保活， 再继续
    if tlcfg.unshare_pid:
        daemon_pidnsleader()
    else: # 如果不是 unshare_pid 的 ,这里将结束退出
        sys.exit()


def layer_run_subp(cmdvec=None, subp_name=None, start_after=None,
                   keep_caps=False, # True 全部 | False 全丢 | 字符串 部分
                   stdin=None, stdout=None, stderr=None,
                   workdir=None, workdir_try=None,
                   no_wait=False,
                   ): # TODO pty或setsid

    mainApp=None; subLayer=None; user_shell=None; dev_shell=None;

    if subp_name.startswith('mainApp'):mainApp=True
    if subp_name.startswith('layer'): subLayer = subp_name
    if subp_name == 'user_shell':     user_shell=True
    if subp_name == 'dev_shell':      dev_shell=True

    if dev_shell:
        keep_caps=True

    if not (workdir or workdir_try):
        if user_shell or dev_shell: workdir = tlcfg.sbxdir_path1
        else: workdir = si.HOME

    if subLayer:
        keep_caps=True

    pid, skp_spfk = fork(create_socketpair=True, loghead=f"{loghead}subp {subp_name}", proc_dispname='sub',
        **(
            d(  close_fds=True,
                close_keep_fds=[
                    OG.userns_unpri.usernsfd,
                    si.file_fds.layerslog_a,
                    *( [si.subp_log_fds[subp_name]] if subp_name in dict.keys(si.subp_log_fds) else [] ),
                ]
        ) if not subLayer and not keep_caps else {} )
    )
    if pid == 0: # 子进程
        skp_spfk.chd_send(BS.IChdBorn)
        skp_spfk.chd_recv(1, 5, BS.YouChdGo)
        skp_spfk.chd_recv(1, 2, BS.YouChdGo)
        skp_spfk.chd_recv(1, 2, b'') # 仅所有持有对端（原进程）的fd的进程都关闭了其fd之后，才会收到 b'' 。若fork时，有漏关的，则不行
        skp_spfk.close()

        wait_for_startAfters(start_after) # NOTE 必须在wlog之前等待

        # NOTE 必须在等待那些等待条件满足之后才发wlog
        wlog('subp_start', me_proc_info=True,
                **( d(cmdvec=cmdvec) if cmdvec else {} ),
                **( d(
                    ready_proc_name=subp_name,
                    pidns_depth=tlcfg.pidns_depth,
                    pidns_tree=tlcfg.pidns_tree,
                    ) if not subLayer else {}
                ),
        )

        if subLayer:    startTip = f'Starting sublayer {subLayer}'
        elif dev_shell: startTip = 'Starting dev_shell'
        elif user_shell:startTip = 'Starting user_shell'
        elif keep_caps: startTip = f'Starting subprocess (with caps) {subp_name}'
        else:           startTip = f'Starting subprocess {subp_name}'
        if cmdvec: log(f'{startTip} : ', cmdvec)

        if workdir_try:
            try: os.chdir(workdir_try)
            except:
                log_warn(f"Could not cd to '{workdir_try}'. Would use fallback workdir if needed")
                if workdir: os.chdir(workdir)
        elif workdir: os.chdir(workdir)

        # === 重定向 stdin/out/err  # NOTE 下面可能无法再 log 或 print
        devnull = os.open('/dev/null', os.O_RDWR)
        if subp_name in dict.keys(si.subp_log_fds):
            os.dup2(devnull, 0) if not stdin else None
            os.dup2(si.subp_log_fds[subp_name], 1) if not stdout else None
            os.dup2(si.subp_log_fds[subp_name], 2) if not stderr else None
        os.dup2(devnull, 0) if stdin  is False else None
        os.dup2(devnull, 1) if stdout is False else None
        os.dup2(devnull, 2) if stderr is False else None
        os.close(devnull)
        # NOTE 无法再 log 或 print NOTE

        set_3ge_fds_cloexec() if not dev_shell else set_3ge_fds_cloexec(action='keepall')

        if not subLayer:
            if not keep_caps:
                close_3ge_fds(keep_fds=[OG.userns_unpri.usernsfd]) # 已经给它们cloexec=True， 这些再关闭一次更保险
                os.setns(OG.userns_unpri.usernsfd, unshrflg(d(user=1)))
                drop_caps()

            execvp(cmdvec[0], cmdvec)
            errmsg = f"exec() starting new program [ {cmdvec[0]} ] failed"
            # wlog('error', errmsg=errmsg) # fd 已关闭，无法wlog
            raise_exit(errmsg, no_cleanup=True)
        else: # 是subLayer
            return 0, None
    else: # 原进程
        skp_spfk.pa_recv(1, 2, BS.IChdBorn)
        if no_wait:
            for _ in range(2): skp_spfk.pa_send(BS.YouChdGo);
            skp_spfk.close() ; skp_spfk = None
        return pid, skp_spfk

    # os.execv('/bin/bash', ['/bin/bash', '--norc'])
    # os.exec*成功后不回来，替换了进程
        # l/v： 可变参 或 数组 来指定参数
        # p : 指定path
        # e : 指定环境变量，不继承父的环境。必须完整路径
    # NOTE 不要调用os.exec*， 用自己的安全的execvp()



def wait_for_startAfters(arr_startAfter):
    if not arr_startAfter: return
    for wait_task in arr_startAfter:
        tt = time.monotonic()
        if wait_task.waittype == 'socket-listened':
            while not is_unix_socket_listened(wait_task.path):
                CHK(time.monotonic() <= tt+(6 if OG.uc.gui not in ['xpra', 'xpra-weston-xwayland'] else 40), f'Waited too long, reporting error ( {wait_task} )')
                time.sleep(0.1)





ps1 = ">"
def set_ps1(status):
    global ps1
    ps1 = ''.join( [
        r'''$(LEC=$? ; if [[ $LEC -ne 0 ]]; then echo -n '\[\e[0;91m\]' ; else echo -n '\[\e[0;94m\]' ; fi ; printf "(%3d)" $LEC ; echo -n '\[\e[0m\]' ) \[\e[1;93m\]'''
        ,
        f'{si.sandbox_name} {tlcfg.layer_name} {status}',
        r''' | \w ''',
        r'''$(if [[ "$(id -u)" == "0" ]];then echo -n '#' ; else echo -n '>'; fi )''',
        r'''\[\e[0m\] '''
    ])
    os.environ['PS1'] = ps1
