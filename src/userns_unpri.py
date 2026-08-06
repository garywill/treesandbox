from heads import *


def create_userns_unpri():
    pid, skp = fork(create_socketpair=True, loghead=f'{loghead} userns', proc_dispname='unpri userns', cut_stdin=True,
                    close_fds=True, close_keep_fds=[si.file_fds.layerslog_a] )
    if pid == 0: # 子进程
        if not is_dir_inaccessible('/zrootfs'):
            os.unshare(unshrflg(d(mnt=1)))
            mount('tmpfs', '/zrootfs', 'tmpfs', mntflag_tmpfs, 'mode=000')
            rmt_ro('/zrootfs', mntflag_tmpfs, 'mode=000')

        os.unshare(unshrflg(d(user=True)))
        skp.chd_send(BS.SetMeUidUser)
        skp.chd_recv(1, 2, BS.SetYouUidUserDone)
        skp.close()
        drop_caps()
        wlog('userns_unpri_p', me_proc_info=True,
             ready_proc_name='userns_unpri',
             pidns_depth=tlcfg.pidns_depth, pidns_tree=tlcfg.pidns_tree,
        )
        execvp('sleep', [f"{si.sandbox_name}_userns" ,  'infinity'])
        raise_exit('exec sleep failed') # exec后不应该到这里
    else: # 原进程
        skp.pa_recv(1, 1, BS.SetMeUidUser)

        Path(f'/proc/{pid}/setgroups').write_text('deny\n')
        Path(f'/proc/{pid}/uid_map').write_text(f'{si.uid} 0 1\n')
        Path(f'/proc/{pid}/gid_map').write_text(f'{si.gid} 0 1\n')
        result = D(
            pidns_tree = tlcfg.pidns_tree,
            pidfd = os.pidfd_open(pid),
            usernsfd = os.open(f'/proc/{pid}/ns/user', os.O_RDONLY),
            usernsino = os.stat(f'/proc/{pid}/ns/user').st_ino,
        )
        set_fd_keep_on_exec(result.pidfd, False)
        set_fd_keep_on_exec(result.usernsfd, True)

        skp.pa_send(BS.SetYouUidUserDone)
        return result

def get_userns_unpri(): # userns_unpri 是由layer2建立的，outest/layer1F 可能需要从/proc中获取其userns作为fd
    CHK( OutestProcsMonitor.I_AM_OUTEST or (tlcfg.depth==1 and os.getpid()==1), "Only outest or layer1 can call this")
    p_userns_unpri = get_procs_seen()['userns_unpri']
    if OutestProcsMonitor.I_AM_OUTEST:      pid = p_userns_unpri.NSpid[0]
    elif tlcfg.depth==1 and os.getpid()==1: pid = p_userns_unpri.NSpid[1]
    inode1 = os.stat(f'/proc/{pid}').st_ino
    result = D(
        pidns_tree = p_userns_unpri.pidns_tree,
        pidfd = os.pidfd_open(pid),
        usernsfd = os.open(f'/proc/{pid}/ns/user', os.O_RDONLY),
        usernsino = os.stat(f'/proc/{pid}/ns/user').st_ino,
    )
    inode2 = os.stat(f'/proc/{pid}').st_ino
    CHK(inode1==inode2, 'The inode of the user_unpri process changed during get_userns_unpri()')
    return result

