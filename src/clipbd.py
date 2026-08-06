from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量


class ClipboardSyncer():
    inited = False
    socket_fromHostLsn = None
    LAST_CONTENT_F = '/sbxdir/temp/ClipboardLastContent.data'
    @classmethod
    def init(cls):
        log(f'ClipboardSyncer initializing')
        cls.socket_fromHostLsn = socket.socket(fileno=si.fd_clipbdWriterFromHostLsn)
        cls.socket_fromHostLsn.setblocking(False) # 设置为非阻塞
        cls.socket_fromHostLsn.listen(1)
        cls.inited = True
    @classmethod
    def one_loop_task(cls): # NOTE 不同方向的内容传递是靠任务间隔比超时时间大来保证不产生竞争
        if not cls.inited: cls.init()
        if not is_unix_socket_listened(f'/tmp/.X11-unix/X{si.newXId}'): return
        # 从主机来的 tcp socket 是否要往沙箱写剪贴板内容
        ready, _, wrong = select.select([cls.socket_fromHostLsn], [], [cls.socket_fromHostLsn], 0) # 非阻塞
        if wrong: log_warn('Unknown error while listening for host write requests to sandbox clipboard')
        elif ready:
            log(f'New connection from host to write to sandbox clipboard')
            pid , _ = fork(loghead=f'{loghead}HostWriteSbxClipbd', proc_dispname='clipbd write',
                           close_fds=True, cut_stdin=True,
                           close_keep_fds=[cls.socket_fromHostLsn.fileno(), OG.userns_unpri.usernsfd],
                           )
            if pid == 0: # 子进程：处理客户端
                os.setns(OG.userns_unpri.usernsfd, unshrflg(d(user=1)))
                try: cls.handle_client_clipbdFromHostSocket()
                except Exception as err: log_warn(err)
                finally: warn_exit('handle_client_clipbdFromHostSocket should have ended its process but did not') #若到这,说明上面未成功退出
            return

        # 如果上面没有return ， 才执行这里
        if not si.sync_clipbd_from_sandbox:
            return
        pid , _ = fork(loghead=f'{loghead}CheckSbxClipbdNewCont', proc_dispname='clipbd read',
                    close_fds=True, cut_stdin=True,
                    close_keep_fds=[OG.userns_unpri.usernsfd ],
                    )
        if pid == 0 : # 子进程：循环从管道读xsel的输出
            os.setns(OG.userns_unpri.usernsfd, unshrflg(d(user=1)))
            try: cls.sync_from_sandbox_to_host()
            except Exception as err: log_warn(err)
            finally: warn_exit('sync_from_sandbox_to_host should have ended its process but did not')  #若到这,说明上面未成功退出
    @classmethod
    def sync_from_sandbox_to_host(cls): # 只有fork出一个子进程后会调用这个. 这个不返回，只结束自己的进程
        if os.getpid() == 1: log_warn('sync_from_sandbox_to_host() called with pid=1, this should not happen') ; print_stack(); return #由于探测到pid=1, 这里返回，不exit
        def timeout_handler(signum, frame):
            warn_exit(f'Timeout while syncing sandbox clipboard to host, giving up', no_cleanup=True)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, 0.5) # 设置超时

        sandbox_clipbd_data = cls.read_clipboard(si.newXId)
        if not isinstance(sandbox_clipbd_data, bytes):
            os._exit(0) # 读回的不是bytes
        if len(sandbox_clipbd_data) == 0:
            os._exit(0) # 成功读回，但沙箱剪贴板是空的


        if is_file(cls.LAST_CONTENT_F): # 有上次的剪贴板内容
            # log('Previous clipboard content file exists')
            if len(sandbox_clipbd_data) == os.path.getsize(cls.LAST_CONTENT_F) \
            and sandbox_clipbd_data == Path(cls.LAST_CONTENT_F).read_bytes():
                # log('Same as last time, ignoring')
                os._exit(0) # 与上次一样
        # 到这里是的确应该 从沙箱 往主机 写剪贴板
        log(f'Sandbox clipboard content updated, syncing to host {sandbox_clipbd_data[:20]}')
        Path(cls.LAST_CONTENT_F).write_bytes(sandbox_clipbd_data)
        cls.write_clipboard(getenv("DISPLAY").lstrip(':'), sandbox_clipbd_data)
        os._exit(0)
    @classmethod
    def read_clipboard(cls, XId) ->bytes|bool: # 这个只应该在fork出一个子进程后调用。它不os._exit, 只返回False或数据
        if os.getpid() == 1: log_warn('read_clipboard() called with pid=1, this should not happen') ; print_stack(); return False
        try:
            proc = subprocess.Popen(
                ['env', f'DISPLAY=:{XId}', 'xsel', '-b', '--output'], bufsize=0,
                preexec_fn=subprocess_preexec, close_fds=True, restore_signals=True,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
            ba = bytearray()
            while True:
                ready, _, wrong = select.select([proc.stdout], [], [proc.stdout], 99) # 超时由之前的signal设置
                if wrong: log_warn('Unknown error while reading from xsel pipe stdout'); return False
                elif ready:
                    try: data = proc.stdout.read(8192)
                    except Exception as err: try_showerr(lambda: proc.kill() ) ; log_warn(err) ; return False
                    if not data: # 已读完
                        try: proc.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            log_warn('Pipe ended, but timeout while waiting for xsel process to exit'); return False
                        if proc.returncode == 0:
                            break
                        else:
                            log_warn(f'xsel failed with return code {proc.returncode}')
                            return False
                    ba.extend(data)
                    if len(ba) > 1_000_000:
                        try_showerr(lambda: proc.kill() )
                        break
            return bytes(ba)
        except Exception as err:
            log_warn(f'Failed to run xsel - {err}')
            return False
    @classmethod
    def write_clipboard(cls, XId, data) ->bool : # 这个只应该在fork出一个子进程后调用。它不os._exit, 只返回真假
        if os.getpid() == 1: log_warn('write_clipboard() called with pid=1, this should not happen') ; print_stack(); return False
        log(f'Send {len(data)} bytes to clipboard :{XId}')
        try:
            proc = subprocess.Popen(
                ['env', f'DISPLAY=:{XId}', 'xsel', '-b', '--input'],
                preexec_fn=subprocess_preexec, close_fds=True, restore_signals=True,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            stdout, stderr = proc.communicate(input=data, timeout=0.5)
            if proc.returncode != 0:
                # 捕获到错误，打印返回码和输出信息
                log_warn(f'xsel failed with return code {proc.returncode}. stdout: "{stdout.decode()}", stderr: "{stderr.decode()}"')
                return False
            return True
        except Exception as err:
            log_warn(f'Failed to run xsel - {err}')
            return False
    @classmethod
    def handle_client_clipbdFromHostSocket(cls): # 只有fork出一个子进程后会调用这个. 这个不返回，只结束自己的进程
        if os.getpid() == 1: log_warn('handle_client_clipbdFromHostSocket() called with pid=1, this should not happen') ; print_stack(); return #由于探测到pid=1, 这里返回，不exit
        def timeout_handler(signum, frame):
            warn_exit(f'Timeout while receiving data, giving up', no_cleanup=True)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, 0.5) # 设置超时
        client_sock, _ = cls.socket_fromHostLsn.accept()
        data = b''
        try:
            while True:
                chunk = client_sock.recv(4096)
                if not chunk: break
                data += chunk
                if len(data) > 1_000_000: log_warn('Truncating overly long clipboard data'); break # 超过 1MB
        except Exception as err: warn_exit(err)
        finally: client_sock.close()
        if data:
            log(f'Syncing clipboard content from host to sandbox {data[:20]}')
            Path(cls.LAST_CONTENT_F).write_bytes(data)
            os._exit(0 if cls.write_clipboard(si.newXId, data) is True else 1)
