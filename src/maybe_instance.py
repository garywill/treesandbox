from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量



def maybe_sendto_running_instance(reusefg):
    log('Looking for running instance of same-name sandbox ...')
    MATCH_SI_K = ["hash_bootsbx", "hostname", "uid", "gid", "username", "groupname", "PTMP", "pythonbin", "pyz"]
    def is_still_alive(instance_name):
        if is_dir(f'{si.PTMP}/{instance_name}') and not os.path.lexists(f'{si.PTMP}/{instance_name}_exit'):
            return True # is_still_alive() 返回 真

    chosen_instance = None
    sock_estb = None
    for dir_in_PTMP in Path(si.PTMP).iterdir():
        dirname = dir_in_PTMP.name
        # 是否是同名沙箱
        if not NameMng.is_pattern_instance_name(dirname):
            continue
        # 是否无 xxx_exit 退出标记
        if os.path.lexists(f'{si.PTMP}/{dirname}_exit'):
            continue

        tmp_t = time.monotonic()
        while time.monotonic() <= tmp_t+1.5 and is_still_alive(dirname): # 允许那个实例2s的时间建立OutsideServ的socket文件
            if is_socket(f'{si.PTMP}/{dirname}/OServ.socket'):
                break
            time.sleep(0.1)
        else: # 那个实例2s都没有设置socket文件
            log_warn(f"Ignoring a possibly abnormal old instance {dirname}")
            continue

        # 再检查一次 是否无 xxx_exit 退出标记
        if os.path.lexists(f'{si.PTMP}/{dirname}_exit'):
            continue

        tmp_t = time.monotonic()
        sock_estb = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        while time.monotonic() <= tmp_t+1 and is_still_alive(dirname): # 允许那个实例1s的时间开始监听那个它自己已经创建的socket
            try:
                sock_estb.connect(f'{si.PTMP}/{dirname}/OServ.socket')
                break
            except ConnectionRefusedError:
                time.sleep(0.05)
        else:
            log(f"Ignoring a possibly abnormal old instance (OServ.socket unresponsive): {dirname}")
            continue


        chosen_instance = dirname
        break

    if not chosen_instance:
        if sock_estb : sock_estb.close()
        return "not_reusing"

    log(f'Found instance {chosen_instance}, attempting to send app command to it ')
    msgObj = d()
    msgObj.run_in_mainLyr_cmdvec = OG.mainApp_cmdvec
    msgObj.workdir     = OG.chosen_workdir or OG.chosen_appItem.workdir or None
    msgObj.workdir_try = OG.chosen_workdir_try or None
    msgObj.si_should_match = d({k:si[k] for k in MATCH_SI_K})
    if reusefg: msgObj.use_dtach = True

    si.client_pid = si.outest_pid
    si.reuse_instance = chosen_instance
    si.reuse_sbxdir = si.outest_sbxdir
    del si.instance_name ; del si.outest_sbxdir ; del si.CG_SBX; del si.outest_pid

    try:
        sock_estb.send( json.dumps(msgObj).encode() )
    except Exception as err:
        warn_exit(f'Error: Failed to send message to found instance {err}')

    ready, _, wrong = select.select([sock_estb], [], [sock_estb], 3)  # 阻塞检查
    if wrong:
        warn_exit(f'Error while waiting for reply, possibly timeout or unknown error')
    elif not ready:
        warn_exit(f'Did not receive a successful reply from the running instance')
    elif ready:
        try: data = sock_estb.recv(300_000)
        except Exception as err: warn_exit(f'Error receiving data from socket:{err}')
        finally: sock_estb.close()
        if data:
            try: msgObj = d( json.loads( data.decode() ) )
            except Exception as err: warn_exit(f'Cannot parse received message correctly:{err}')
            if msgObj.message: log(f'Additional message in reply: {msgObj.message}')
            if msgObj.reuseSucceeded:
                if not reusefg: log('Successfully sent app command to the instance')
                else: # reusefg==True
                    shareShellSubpName = msgObj.message
                    if not shareShellSubpName.startswith('shareshell_'):
                        warn_exit('Did not receive shareshell_ process name')
                    linkfile = f'{si.PTMP}/{chosen_instance}/into.{shareShellSubpName}.shellsocket.link'
                    t0 = time.monotonic()
                    while time.monotonic() <= t0 + 2:
                        if os.path.exists(linkfile) : break
                    else: warn_exit(f'Timeout waiting for target of link file {linkfile}')
                    print('...\n' * os.get_terminal_size().lines)
                    try: os.execvp('dtach', ['dtach', '-a', os.readlink(linkfile) ] ) # NOTE 不能用Path来解析，可能因为跨root
                    except Exception as err: warn_exit(err)
                sys.exit(0)
            else:
                log_warn(f'Reply of running instance was not success')
                if msgObj.youStartNewInstance:
                    log('Reply of the running instance indicates we should create new instance to run app')
                    return "not_reusing"
                sys.exit(1)
        else: warn_exit(f'Received empty reply')
    else: raise_exit('Unknown error, unexpected logic branch')




class OutsideServ():
    conns = []
    cnt_recvmsg = 0
    @classmethod
    def init(cls):
        cls.skt_OServLsn = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        cls.skt_OServLsn.bind(f'{si.outest_sbxdir}/OServ.socket')
        cls.skt_OServLsn.listen(5)
    @classmethod
    def one_loop_task(cls):
        # 处理已经建立的连接
        for i in reversed(range(0, len(cls.conns))):
            connItem = cls.conns[i]
            ready, _, wrong = select.select([connItem.skt_conn], [], [connItem.skt_conn], 0)  # 非阻塞检查
            if wrong:
                log_warn('An OutsideServ connection encountered an error')
                cls.close_conn(connItem)
                continue
            elif ready:
                try: data = connItem.skt_conn.recv(300_000)
                except Exception as err:
                    log_warn(f'Error reading data received from socket:{err}')
                    cls.close_conn(connItem)

                if data:
                    connItem.last_tick = time.monotonic()
                    # log(f"Received external message: {data!r}")
                    try: cls.onDataRecved(data, connItem )
                    except Exception as err:
                        log_warn(f'Error processing received message:{err}')
                        cls.close_conn(connItem)
                else:
                    # log("External connection closed (recv returned empty)") # 发完消息正常断开
                    cls.close_conn(connItem)
            else: # 无消息
                if connItem.last_tick + 60 < time.monotonic():
                    log_warn("External connection timed out (no messages), closing")
                    cls.close_conn(connItem)


        # 有没有新的外部连接
        ready, _, wrong = select.select([cls.skt_OServLsn], [], [cls.skt_OServLsn], 0)
        if wrong: raise_exit('Unknown error while waiting for new external connections')
        elif ready:
            conn, client_addr = cls.skt_OServLsn.accept()
            cls.cnt_recvmsg += 1
            # log(f'New external connection {cls.cnt_recvmsg}', conn)
            cls.conns.append( d(skt_conn=conn, last_tick=time.monotonic() , index=cls.cnt_recvmsg) )
    @classmethod
    def onDataRecved(cls, data, connItem):
        try: msgObj = d( json.loads( data.decode() ) )
        except Exception as err:
            errmsg = f'Cannot parse received message correctly:{err}'
            log_warn(f'{errmsg}')
            cls.response_close(connItem, message=errmsg)
            return False
        for k,v in dict.items(msgObj.si_should_match or {}):
            if not eq_ignore_order(si[k], v):
                errmsg = f'si[{k}] inconsistent.\nValue in running sandbox: {si[k]}\nValue in message: {v}\n(If you modified the sandbox configuration, you may need to terminate the running sandbox first)'
                log_warn(f'{errmsg}')
                cls.response_close(connItem, message=errmsg)
                return False
        if msgObj.run_in_mainLyr_cmdvec:
            targetLyr = si.specialLyrs.mainLyr
            workdir     = msgObj.workdir or None
            workdir_try = msgObj.workdir_try or None
            if not msgObj.use_dtach:
                cmdvec = msgObj.run_in_mainLyr_cmdvec
                subp_name = f'mainApp_{connItem.index}'
            else : # use_dtach 为真
            # if True:
                # shellId =           f'AASSDD-{targetLyr}'
                randstr = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
                shellId = f'{randstr}-{targetLyr}'
                cmdvec = ['dtach', '-N', f'/sbxdir/temp/shareshell.{shellId}.socket',  *msgObj.run_in_mainLyr_cmdvec ]
                subp_name = f'shareshell_{shellId}'
            OutestProcsMonitor.tell_lyr_runsubp(targetLyr,
                d(
                    cmdvec=cmdvec,
                    workdir     = workdir,
                    workdir_try = workdir_try,
                    subp_name=subp_name,
                    stdin=False
                )
            )
            cls.response_close(connItem, reuseSucceeded=True, message=subp_name)
            return True
    @classmethod
    def response_close(cls, connItem, reuseSucceeded=None, youStartNewInstance=None, message=None):
        responseObj = d()
        if reuseSucceeded:      responseObj.reuseSucceeded = True
        if youStartNewInstance: responseObj.youStartNewInstance = True
        if message:             responseObj.message = message
        try:
            connItem.skt_conn.send( json.dumps(responseObj).encode() )
            return True
        except Exception as err:
            log_warn(f'Failed to reply to external connection {err}')
            return False
        finally:
            cls.close_conn(connItem)

    @classmethod
    def close_conn(cls, connItem):
        connItem.skt_conn.close()
        try: cls.conns.remove(connItem)
        except Exception as err: log_warn(f'Error while closing external connection (might already be closed): {err}')
