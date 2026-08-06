from heads import *

def create_netns_tun( pasta_custom_args=[] ):
    os.mkfifo(f'/{tlcfg.sbxdir_path1}/temp/netns_proc_info.fifo')
    pid, skp = fork(create_socketpair=True, loghead=f'{loghead} netns', proc_dispname='pasta runner', cut_stdin=True,
                    close_fds=True, close_keep_fds=[si.file_fds.layerslog_a, OG.userns_unpri.usernsfd] )
    if pid == 0: # 子进程
        if not is_dir_inaccessible('/zrootfs'):
            os.unshare(unshrflg(d(mnt=1)))
            mount('tmpfs', '/zrootfs', 'tmpfs', mntflag_tmpfs, 'mode=000')
            rmt_ro('/zrootfs', mntflag_tmpfs, 'mode=000')
        os.setns(OG.userns_unpri.usernsfd, unshrflg(d(user=1)))
        drop_caps()
        # 尽管运行pasta前，上面已经通过userns回到了uid=1000，并降权，
        # 但pasta又会创建新容器，其子进程自认uid=0, 且自拥有
            # CapPrm: 0000000000201400
            # CapEff: 0000000000201400
            # CapBnd: 000001ffffffffff
        PYCODE = '\n'.join([line.strip() for line in f'''
            import os, json, pathlib, ctypes, ctypes.util, signal
            libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
            PR_SET_PDEATHSIG = 1 ; libc.prctl(PR_SET_PDEATHSIG, signal.SIGKILL)
            output = dict()
            output["self_see_pid"] = os.getpid()
            output["ns"] = dict(net=os.stat('/proc/self/ns/net').st_ino, pid=os.stat('/proc/self/ns/pid').st_ino)
            output["start_tick"] = open('/proc/self/stat').read().split(') ')[-1].split(' ')[22-1-2]
            pathlib.Path('/{tlcfg.sbxdir_path1}/temp/netns_proc_info.fifo').write_text( json.dumps(output) )
            os.execvp('sleep', ["{si.sandbox_name}_pasta", 'infinity'])
        '''.strip().splitlines() ])
        execvp('pasta',  ['pasta', '-f',  '--runas', f'{si.uid}:{si.gid}',
            *pasta_custom_args,
            si.pythonbin, '-IBS', '-c', PYCODE
        ] )
        warn_exit("exec to be pasta failed")
    else: # 原进程
        fd_fifo = os.open(f'/{tlcfg.sbxdir_path1}/temp/netns_proc_info.fifo', os.O_RDONLY|os.O_NONBLOCK)
        ready, _, wrong = select.select([fd_fifo], [], [fd_fifo], 2)
        if wrong: raise_exit('Unknown error while waiting for process info from netns process')
        elif not ready: raise_exit('Timeout while waiting for process info from netns process')
        netns_proc_info = d( json.loads( os.read(fd_fifo, 4096).decode() ) )
        os.close(fd_fifo)
        Path(f'/{tlcfg.sbxdir_path1}/temp/netns_proc_info.fifo').unlink()

        for x in [int(x) for x in os.listdir('/proc') if x.isdigit() ]:
            if os.access(f'/proc/{x}/ns', os.R_OK|os.X_OK) : ns_x = get_nstypes(f'/proc/{x}/ns')
            else: continue
            if ns_x.pid == netns_proc_info.ns.pid \
            and get_NSpid_arr(f'/proc/{x}/status')[-1] == netns_proc_info.self_see_pid \
            and get_start_tick(f'/proc/{x}/stat') == netns_proc_info.start_tick :
                pid_netns = x ;
                ns_netns_proc = ns_x
                break
        else: raise_exit('No matching netns process found')
        pidfd = os.pidfd_open(pid_netns)
        result = D(
            pid = pid_netns,
            pidfd = pidfd,
            netnsfd = os.open(f'/proc/{pid_netns}/ns/net', os.O_RDONLY),
            netnsino = os.stat(f'/proc/{pid_netns}/ns/net').st_ino,
        )
        wlog('netns_tun_p', ready_proc_name='netns_tun',
            self_see_pid=netns_proc_info.self_see_pid,
            start_tick=netns_proc_info.start_tick,
            ns=ns_netns_proc,
        )
        set_fd_keep_on_exec(result.pidfd, False)
        set_fd_keep_on_exec(result.netnsfd, True)

        return result
