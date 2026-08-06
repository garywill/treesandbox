from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量


class NameMng:
    random_chars = "abcdefghkmnpqrsuvwxyz"
    @classmethod
    def chk_str_valid_sandbox_name(cls, string):
        CHK( re.match(r'^[a-zA-Z0-9_-]+$', string), f"Sandbox name can only contain letters, numbers, '-', '_' . This name is invalid: {string}" )
        CHK( not '--' in string, f" '--' is not allowed in sandbox name. This name is invalid: {string}")
        CHK( not string.startswith('-') and not string.endswith('-'), f"Sandbox name can not starts or ends with '-'. This name is invalid: {string}")
    @classmethod
    def gen_instance_name_mkdir(cls): # 只在 最外层启动时 并且 确定要创建新实例时 调用
        now = datetime.datetime.now()
        time_str = now.strftime("%m%d-%H%M%S")
        ds = now.microsecond // 100_000

        n = 0
        while True:
            if n>100: raise_exit('Have tried too many times generating instance name')

            random_str = ''.join(random.choices(cls.random_chars, k=3))
            instance_name = f'{si.sandbox_name}--{time_str}-{ds}{random_str}'
            outest_sbxdir = f'{si.PTMP}/{instance_name}'
            CG_SBX = f'{si.CG_TSBXS}/{instance_name}'

            if os.path.lexists(outest_sbxdir) or os.path.lexists(CG_SBX):
                n+=1 ; continue

            try: os.makedirs(outest_sbxdir, exist_ok=False)
            except FileExistsError:
                n+=1 ; continue
            except: raise

            mkdirp(si.CG_TSBXS)

            try: os.makedirs(CG_SBX, exist_ok=False)
            except FileExistsError:
                n+=1 ; continue
            except: raise

            Path(f'{CG_SBX}/cgroup.procs').write_text(str(os.getpid()))

            break
        return instance_name, outest_sbxdir, CG_SBX
    @classmethod
    def is_pattern_instance_name(cls, string):
        return re.match(rf'^{si.sandbox_name}--\d{{4}}-\d{{6}}-\d[{cls.random_chars}]{{3}}$', string)

resv_name_prefix = ['bridge_', 'layer', 'shareshell_', 'mainApp']
resv_words = ['host', 'sbx', 'sbxs', 'tsbx', 'tsbxs', 'tsbxes', 'sandbox', 'sandboxs', 'sandboxes', 'layer', 'layers', 'new', 'py', 'json', 'name', 'dirs', 'log', 'logs', 'socket', 'nc', 'tmpfs', 'tmp', 'temp', 'overlay', 'events', 'lyr_cfg', 'pid', 'userconfig', 'rootfs', 'outest', 'mainLyr', 'semitruCmpannLyr', 'userns_unpri', 'netns_tun', 'bridge', 'shareshell', 'mainApp']
def init_sbxinfo(): # 仅顶层运行，子容器层不运行。返回的数据一路传下各个子层
    # 获得调用py脚本的文件位置信息，一般仅用于顶层得多，子容器内用得少
    scriptfilepath = rslvy(os.path.abspath(__file__))
    scriptdirpath = os.path.dirname(scriptfilepath)  # 获取脚本所在目录
    scriptdirname = os.path.basename(scriptdirpath) # 获取脚本所在目录名
    scriptname = os.path.basename(scriptfilepath)  # 获取脚本文件名（含扩展名）
    scriptnamenoext = os.path.splitext(scriptname)[0]  # 获取脚本文件名（不含扩展名）

    for i in [0,1,2]:
        try: fcntl.fcntl(i, fcntl.F_GETFD)
        except OSError as err:
            if err.errno != errno.EBADF: raise
            else:
                devnull = os.open('/dev/null', os.O_RDWR)
                os.dup2(devnull, i)
                if devnull != i: os.close(devnull)
    fdnull = os.open("/dev/null", os.O_PATH)
    CHK(fdnull>=3, 'fdnull must >=3')
    set_fd_keep_on_exec(fdnull, False)
    si.fdnull = fdnull

    # 从外部(linux host)启动沙箱的原本用户信息
    uid = os.getuid()
    gid = os.getgid()
    username = pwd.getpwuid(uid).pw_name # 获取当前用户名
    groupname = grp.getgrgid(gid).gr_name
    HOME = f'/home/{username}' if uid>0 else '/root'
    hostname = open("/etc/hostname").read().strip()
    outest_pid = os.getpid()
    host_XDG_R_D = getenv("XDG_RUNTIME_DIR")
    sbx_XDG_R_D = f'/run/user/{uid}'
    startscript_on_host = scriptfilepath
    CWD = scriptdirpath
    PTMP = f'/tmp/tsbxs-{uid}'
    hash_bootsbx_py = hash_blake2b(open(scriptfilepath, 'rb').read())

    CHK(uid != 0 and gid != 0, f'Currently our sandbox tool does not support running as root')

    mkdirp(PTMP)      # 创建不同沙箱实例共用的 主临时目录,不清理这个
    os.chmod(PTMP, 0o700)

    si.update( { k: v for k, v in locals().items() if k in
        ['hostname', 'PTMP', 'uid', 'gid', 'username', 'groupname', 'HOME', 'outest_pid',
         'startscript_on_host', 'CWD', 'hash_bootsbx_py', 'host_XDG_R_D', 'sbx_XDG_R_D']
    } )

    uc = userconfig(si) # NOTE

    # 沙箱名。不是子容器层名
    if uc.sandbox_name: NameMng.chk_str_valid_sandbox_name(uc.sandbox_name)
    sandbox_name = uc.sandbox_name or f'{scriptdirname}_{scriptname}' # 沙箱名
    sandbox_name = re.sub(r'[^a-zA-Z0-9_\-]', lambda m: f"_{ord(m.group(0)):x}", sandbox_name)
    CHK( sandbox_name not in resv_words, f"Sandbox name {sandbox_name} conflicts with reserved word {resv_words}")
    CHK( len(sandbox_name) < 500, f'Sandbox name too long: {sandbox_name}')

    apps = uc.apps
    if uc.reuseful: reuseful = uc.reuseful
    if uc.idleKeepSbxTime: idleKeepSbxTime = uc.idleKeepSbxTime

    if (sharedir_prefix := uc.sharedir_prefix):
        CHK( sharedir_prefix.startswith('/tmp/') or sharedir_prefix.startswith('/dev/shm/'), "uc.sharedir_prefix must start with '/tmp/' or '/dev/shm/'")
        sharedir_onhost = f'{sharedir_prefix}{sandbox_name}'
        si.sharedir_onhost = sharedir_onhost
    else:
        sharedir_onhost = None

    sync_clipbd_from_sandbox = True if uc.sync_clipbd_from_sandbox else False


    si.update( { k: v for k, v in locals().items() if k in
        [ 'sandbox_name', 'reuseful', 'idleKeepSbxTime', 'apps', 'sync_clipbd_from_sandbox', ]
    } )


    CG_HOSTUSER = f'/sys/fs/cgroup/user.slice/user-{uid}.slice/user@{uid}.service'
    CG_TSBXS = f'{CG_HOSTUSER}/tsbxs.slice'
    CHK( os.access(CG_HOSTUSER, os.W_OK), f"The directory {CG_HOSTUSER} does not exist or is not writable")

    BND_MAX = int(Path('/proc/sys/kernel/cap_last_cap').read_text())
    pythonbin = sys.executable

    dyncfg = gen_dynamic_cfg(si, uc) # NOTE
    if 'newXId' in dict.keys(dyncfg): newXId = dyncfg.newXId

    si.update( { k: v for k, v in locals().items() if k in
          ['newXId', 'CG_HOSTUSER', 'CG_TSBXS', 'BND_MAX', 'pythonbin', ]
    } )

    layer1_cfg = gen_layer1(si, uc, dyncfg)
    start_lyrs_recursive_jobs(si, layer1_cfg)

    if uc.net_iface == 'tuntap-pasta': si.expected_alive_procs += [ 'netns_tun'] # 'pasta_runner'因为无法获取ns所以不放其中

    bridges = []
    for bItem in (dyncfg.bridges or []):
        def get_real_layername(name_in):
            if name_in.startswith('layer'): return name_in
            else:
                if si.specialLyrs[name_in]: return si.specialLyrs[name_in]
        real_seefrom = get_real_layername(bItem.seefrom)
        real_seeto   = get_real_layername(bItem.seeto)
        if not (real_seefrom and real_seeto):
            log_warn(f'The layer(s) indicated by this bridge item {bItem} not found, ignoring bridge item.')
            continue
        bridge_name = f'bridge_<{real_seefrom.removeprefix('layer')}>_<{real_seeto.removeprefix('layer')}>'
        dcp_bItem = copy.deepcopy(bItem)
        dcp_bItem.update( d(real_seefrom=real_seefrom , real_seeto=real_seeto, bridge_name=bridge_name) )
        bridges.append(dcp_bItem)
        si.expected_alive_procs.append(bridge_name)
    si.bridges = bridges

    OG.dyncfg = dyncfg
    OG.uc = uc
    return layer1_cfg

def start_lyrs_recursive_jobs(si, layer1_cfg): # 这是给最外层启动时把layer1_cfg作为cfg传入的
    recursive_lyrs_jobs(si, layer1_cfg, None, [])
    recr_rm_empty_lyr(si, layer1_cfg)
    recursive_valid_lyrs(si, layer1_cfg)


def recursive_lyrs_jobs(si, cfg, parent_cfg, used_layer_names): # cfg：要处理的层， parent_cfg : 其父层
    # 计算本层深度
    cfg.depth = parent_cfg.depth + 1 if parent_cfg is not None else 1

    CHK( cfg.layer_name, "Some layer has no layer_name")
    CHK( re.match(r'^[a-zA-Z0-9_-]+$', cfg.layer_name), f"layer_name can only contain letters, numbers, '-', '_' . This name is invalid: {cfg.layer_name}" )
    CHK( cfg.layer_name not in resv_words, f"Layer name {cfg.layer_name} conflicts with reserved word {resv_words}")
    CHK( cfg.layer_name.startswith('layer'), f"Layer name {cfg.layer_name} does not start with 'layer'")
    CHK( cfg.layer_name not in used_layer_names, f"Layer name '{cfg.layer_name}' is duplicated")
    used_layer_names.append(cfg.layer_name)

    CHK( len(cfg.layer_name.encode()) <= 15 , f"Layer name {cfg.layer_name} exceeds 15 bytes")

    # 配置中的数组类型去除None成员
    if cfg.fs:
        cfg.fs = [fsItem for fsItem in cfg.fs if fsItem is not None]
    if cfg.sublayers :
        cfg.sublayers = [sublyr for sublyr in cfg.sublayers if sublyr is not None]
    if cfg.subprocs :
        cfg.subprocs = [cmd for cmd in cfg.subprocs if cmd is not None]
        CHK( cfg.unshare_pid and cfg.unshare_mnt, f"Layer {cfg.layer_name} has subprocs but  unshare_pid + unshare_mnt  not enabled")
        for subpItem in cfg.subprocs:
            if subpItem.start_after:
                subpItem.start_after = [item for item in subpItem.start_after if item is not None]
    if cfg.subprocs and cfg.sublayers:
        raise_exit(f"Layer {cfg.layer_name} has both subprocs and sublayers. Not valid config")
    if cfg.envs_unset:
        cfg.envs_unset = [item for item in cfg.envs_unset if item is not None]
    if cfg.envset_grps:
        cfg.envset_grps = [item for item in cfg.envset_grps if item is not None]
    if cfg.start_after:
        cfg.start_after = [item for item in cfg.start_after if item is not None]
    if cfg.uid_map_as_root :
        CHK( cfg.unshare_user, f"Layer {cfg.layer_name} has uid_map_as_* but unshare_user not enabled")

    if cfg.unshare_pid and not cfg.unshare_mnt:
        raise_exit(f"Layer {cfg.layer_name} has unshare_pid enabled, but unshare_mnt not enabled")
    if (cfg.newrootfs or cfg.fs) and not cfg.unshare_mnt:
        raise_exit(f"Layer {cfg.layer_name} sets newrootfs or fs, but unshare_mnt not enabled")
    if bool(cfg.fs) != bool(cfg.newrootfs):
        raise_exit(f"Layer {cfg.layer_name}: fs and newrootfs must both be present or both absent")
    if cfg.is_mainlyr :
        CHK( cfg.unshare_pid , f'Main layer {cfg.layer_name} requires unshare_pid=True')
    if cfg.is_semitruCmpannLyr :
        CHK( cfg.unshare_pid , f'Semi-trusted companion process layer {cfg.layer_name} requires unshare_pid=True')


    # 检查fs条目
    for fsItem in (cfg.fs or []):
        if fsItem.dest: fsItem.dest = napath(fsItem.dest)
        if fsItem.src: fsItem.src = napath(fsItem.src)
        if fsItem.destbase: fsItem.destbase = napath(fsItem.destbase)

    if len(cfg.sublayers or []) > 0 and cfg.newrootfs:
        if not any( opItem.many_op == 'sbxdir-in-newrootfs' for opItem in cfg.fs):
            raise_exit(f"Layer {cfg.layer_name} sets newrootfs and wants to create sublayers, but its fs has no entry with many_op = 'sbxdir-in-newrootfs' (required in this case)")

    # 对第1层检查
    if cfg.depth == 1:
        CHK( cfg.uid_map_as_root,"First layer should enable uid_map_as_root")
        CHK( cfg.unshare_pid, "First layer should enable unshare_pid")
        CHK( len(cfg.sublayers) == 1, "First layer's sublayers array should but does not contain exactly 1 element")
        CHK( not cfg.newrootfs, "First layer should not enable newrootfs")

    if cfg.depth > 1:
        CHK(not cfg.unshare_user, f"Layer {cfg.layer_name} has unshare_user enabled, but layers after the first layer do not need this. We have userns_unpri")

    # 对第2层检查
    if cfg.depth == 2:
        CHK( cfg.unshare_mnt, "Second layer should enable unshare_mnt")
        CHK( cfg.newrootfs, "Second layer should enable newrootfs")
        CHK( cfg.fs, "Second layer should have fs")
        if not any( opItem.many_op == 'dup-rootfs' for opItem in cfg.fs):
            raise_exit("Second layer's fs has no entry with many_op='dup-rootfs'")
        if not any( opItem.many_op == 'mask-privacy' for opItem in cfg.fs):
            raise_exit("Second layer's fs has no entry with many_op='mask-privacy'")

    if cfg.layer_name == 'layer3': # 对第3层检查
        if cfg.fs and any( opItem.many_op == 'dup-rootfs' for opItem in cfg.fs) :
            raise_exit(f"Layer {cfg.layer_name} should not use many_op='dup-rootfs' in fs, because its parent layer is the last layer allowed to see host files")
        if not (cfg.unshare_mnt and cfg.unshare_cgroup and cfg.unshare_ipc and cfg.unshare_time and cfg.unshare_uts and cfg.newrootfs and cfg.fs) :
            raise_exit(f"Layer {cfg.layer_name} did not enable all of [unshare_mnt, unshare_cgroup, unshare_ipc, unshare_time, unshare_uts, newrootfs, fs] (all required)")
        if not any( opItem.many_op == 'container-rootfs' for opItem in cfg.fs):
            raise_exit(f"Layer {cfg.layer_name}'s fs has no entry with many_op='container-rootfs'")

    if cfg.layer_name in ['layer2c', 'layer4c', 'layer4']:
        CHK( cfg.unshare_pid, f"{cfg.layer_name} did not enable unshare_pid=True (required)")

    if parent_cfg is None:
        pa_tree = []
        pa_pidns_depth = 0
        pa_pidns_tree = []
    else:
        pa_tree = parent_cfg.tree
        pa_pidns_depth = parent_cfg.pidns_depth
        pa_pidns_tree  = parent_cfg.pidns_tree

    cfg.tree = pa_tree + [cfg.layer_name]
    cfg.pidns_depth = pa_pidns_depth + (0  if not cfg.unshare_pid else 1)
    cfg.pidns_tree  = pa_pidns_tree  + ([] if not cfg.unshare_pid else [cfg.layer_name])


    if cfg.user_shell or cfg.dev_shell:
        if cfg.sublayers:
            log_warn(f"{cfg.layer_name} is set to start dev_shell or user_shell, its sublayers will be ignored")
            cfg.sublayers = []
        # if cfg.subprocs and [x for x in cfg.subprocs if x.subp_name == 'mainApp']: # 现在mainApp是由最外层发来的了

    for sublyr_cfg in (cfg.sublayers or []):
        recursive_lyrs_jobs(si, sublyr_cfg, cfg, used_layer_names)


def recursive_valid_lyrs(si, layer1_cfg):
    used_proc_names = []
    si.all_layers = []
    si.specialLyrs = d()
    def _recr(cfg):
        nonlocal used_proc_names
        CHK( cfg.layer_name not in used_proc_names, f"Name {cfg.layer_name} is duplicated")
        si.all_layers.append(cfg.layer_name)
        if cfg.unshare_pid:
            used_proc_names.append(cfg.layer_name)
        if cfg.is_mainlyr:
            CHK(not si.specialLyrs.mainLyr, 'Duplicate mainLyr found')
            si.specialLyrs.mainLyr = cfg.layer_name
        if cfg.is_semitruCmpannLyr:
            CHK(not si.specialLyrs.semitruCmpannLyr, 'Duplicate semitruCmpannLyr found')
            si.specialLyrs.semitruCmpannLyr = cfg.layer_name
        for subpItem in (cfg.subprocs or [] ):
            CHK( subpItem.subp_name, f"Subprocess has no subp_name set : {subpItem}")
            CHK( re.match(r'^[a-zA-Z0-9_-]+$', subpItem.subp_name), f"subp_name can only contain letters, numbers, '-', '_' . This name is invalid: {subpItem.subp_name}" )
            CHK( len(subpItem.subp_name)<=30, f"subp_name too long, exceeds 30 characters: {subpItem}")
            CHK( subpItem.subp_name not in used_proc_names, f"Name {subpItem.subp_name} is duplicated")
            for x in resv_name_prefix:
                CHK( not subpItem.subp_name.startswith(x), f"Subprocess name {subpItem.subp_name} starting with '{x}' is invalid {subpItem}")
            used_proc_names.append(subpItem.subp_name)

        if cfg.user_shell: used_proc_names.append('user_shell')
        if cfg.dev_shell: used_proc_names.append('dev_shell')
        for sublyr_cfg in (cfg.sublayers or [] ):
            _recr(sublyr_cfg)
    _recr(layer1_cfg)
    wdg_target_procs = [x for x in used_proc_names if x != 'mainApp'] # 不看主app, 只看它所属层
    si.expected_alive_procs = wdg_target_procs + ['userns_unpri']
    si.expected_alive_layers = list(set(si.expected_alive_procs) & set(si.all_layers))
    CHK(si.specialLyrs.mainLyr, 'mainLyr not found')

def recr_rm_empty_lyr(si, cfg):
    def _recr(si, cfg):
        # print(cfg.layer_name)
        have_rmed = False

        cnt_cmds_0 = len(cfg.subprocs or [] )
        cnt_sl_0 = len(cfg.sublayers or [] )
        cnt_task_0 = len(cfg.daemon_tasks or [])
        if cfg.subprocs : cfg.subprocs = [cmd for cmd in cfg.subprocs if cmd is not None]
        if cfg.sublayers : cfg.sublayers = [sublyr for sublyr in cfg.sublayers if sublyr and not sublyr.disabled]
        if cfg.daemon_tasks : cfg.daemon_tasks = [task for task in cfg.daemon_tasks if task]
        cnt_cmds_1 = len(cfg.subprocs or [] )
        cnt_sl_1 = len(cfg.sublayers or [] )
        cnt_task_1 = len(cfg.daemon_tasks or [])

        if cnt_cmds_0 != cnt_cmds_1 or cnt_sl_0 != cnt_sl_1 or cnt_task_0 != cnt_task_1:
            have_rmed = True
        for sublyr_cfg in (cfg.sublayers or [] ):
            if _recr(si, sublyr_cfg):
                have_rmed = True
        if not (cfg.sublayers or cfg.subprocs or cfg.daemon_tasks or cfg.user_shell or cfg.dev_shell or cfg.is_mainlyr):
            # print('setting' , cfg.layer_name, 'to disable')
            cfg.disabled = True
            have_rmed = True
        # print(have_rmed)
        return have_rmed
    while _recr(si, cfg): pass


def make_mnt_fill_sbxdir(si, lyrcfg, call_at_begin=None, call_at_buildfs=None, OG=None): # 创建本层的sbxdir, 可能是刚启动时新创建，也可能是准备变根前为变根后的环境内创建（可能复制启动时已有的）
    # sbxdir_path/ :
        # dirmaker.xxx.name
        # dirmaker.name -> dirmaker.xxx.name
        # sbxinfo.json
        # bootsbx.py
        # sbx.xxx.name
        # sbx.name -> sbx.xxx.name
        # events.layers.log
        # lyr_cfg.xxx.json (多) 包括本层和所有递归子层
        # new.xxx.rootfs (多)所有有 newrootfs 的本层和递归子层
        # temp/  挂载为rw tmpfs
        # apps/ 挂为 tmpfs rw
        # overlays.xxx.dirs/ 挂载为tmpfs 可能rw (暂未实现）
    if call_at_begin: # 刚启动脚本
        si.instance_name , si.outest_sbxdir, si.CG_SBX = NameMng.gen_instance_name_mkdir()
        target_sbxdir_path = napath(si.outest_sbxdir)
        old_sbxdir_path = None
    elif call_at_buildfs: # 为本层接下来的新文件系统准备的 （可能 变根=新旧路径不同  ，也可能 不变根=新旧路径同）
        target_sbxdir_path = napath(f'{lyrcfg.newrootfs_path}/{lyrcfg.sbxdir_path1}')
        old_sbxdir_path = napath(lyrcfg.sbxdir_path0)

    if target_sbxdir_path == old_sbxdir_path:
        return
        # 能往下执行，说明是要从空白创建
    # else:
    #     creating_new_sbxdir=True

    def make_file_get_fd(filename, open_flag, filemode):
        fd = os.open(f'{target_sbxdir_path}/{filename}', open_flag, filemode)
        set_fd_keep_on_exec(fd, False)
        return fd
    def create_socket_file_fd(socket_file_name):
        skt = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        skt.setblocking(False)
        skt.bind(f'{target_sbxdir_path}/{socket_file_name}')
        fd = skt.detach() ; set_fd_keep_on_exec(fd, False)
        return fd
    def create_socketpair_fds():
        skt_chd, skt_pa = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        fd_chd = skt_chd.detach() ; set_fd_keep_on_exec(fd_chd, False)
        fd_pa  = skt_pa.detach() ; set_fd_keep_on_exec(fd_pa, False) # 为了不让fd号码乱，pa也保留
        return d(pa=fd_pa, chd=fd_chd)

    # sbxdir 本身目录创建
    mkdirp(target_sbxdir_path)
    new_tmpfs_for_sbxdir = True if call_at_buildfs else False
    if new_tmpfs_for_sbxdir:
        mount('tmpfs', target_sbxdir_path, 'tmpfs', mntflag_newsbxdir, 'mode=700')

    # dirmaker.layerX.name
    if not os.path.lexists(f'{target_sbxdir_path}/dirmaker.layer.name'):
        with open(f'{target_sbxdir_path}/dirmaker.layer.{lyrcfg.layer_name}.name', 'w') as f:
            f.write(lyrcfg.layer_name)
            os.chmod(f.name, 0o444)
        symlink(f'dirmaker.layer.{lyrcfg.layer_name}.name', f'{target_sbxdir_path}/dirmaker.layer.name')


    if call_at_begin:
        # sbx.xxxx.pid
        with open(f'{si.outest_sbxdir}/sbx.{si.outest_pid}.pid', 'w') as f:
            f.write(str(si.outest_pid))
            os.chmod(f.name, 0o444)

        symlink(f'sbx.{si.outest_pid}.pid', f'{si.outest_sbxdir}/sbx.pid')
        symlink(f'/proc/{si.outest_pid}/status', f'{si.outest_sbxdir}/sbx.pid.status')

        # userconfig.json , dyncfg.json
        with open(f'{si.outest_sbxdir}/userconfig.json', 'w') as f:
            f.write(json.dumps(OG.uc, indent=2, ensure_ascii=False))
            os.chmod(f.name, 0o444)
        with open(f'{si.outest_sbxdir}/dyncfg.json', 'w') as f:
            f.write(json.dumps(OG.dyncfg, indent=2, ensure_ascii=False))
            os.chmod(f.name, 0o444)


        # fd (procs, subp 文件)
        si.file_fds = D()
        si.file_fds.update( d(
            # 沙箱内只fd写，最外层用路径来读
            layerslog_a = make_file_get_fd('events.layers.log', os.O_WRONLY|os.O_CREAT|os.O_APPEND, 0o644),

            # RDONLY是因为沙箱内只fd读，仅最外层用路径写
            procs_alive = make_file_get_fd('procs.alive.json', os.O_RDONLY|os.O_CREAT, 0o644),
            procs_seen = make_file_get_fd('procs.seen.json', os.O_RDONLY|os.O_CREAT, 0o644),
            procs_heared = make_file_get_fd('procs.heared.json', os.O_RDONLY|os.O_CREAT, 0o644),
            procs_wdgsee = make_file_get_fd('procs.wdgsee.json', os.O_RDONLY|os.O_CREAT, 0o644),
        ) )

        Path(f'{si.outest_sbxdir}/procs.alive.json').write_text("[]")
        Path(f'{si.outest_sbxdir}/procs.seen.json').write_text("{}")
        Path(f'{si.outest_sbxdir}/procs.heared.json').write_text("{}")
        Path(f'{si.outest_sbxdir}/procs.wdgsee.json').write_text("{}")

        si.subp_log_fds = D()
        for pn in si.expected_alive_procs:
            if not (pn in ['user_shell','dev_shell','mainApp'] or pn.startswith('layer') ):
                si.subp_log_fds[pn] = make_file_get_fd(f'subp.{pn}.log', os.O_WRONLY|os.O_CREAT|os.O_APPEND, 0o644)


        si.oSkt_fds = D()
        for lyr in si.expected_alive_layers:
            si.oSkt_fds [lyr] = create_socketpair_fds()



    # 主机写的剪贴板socket
    if si.newXId:
        if call_at_begin:
            si.fd_clipbdWriterFromHostLsn = create_socket_file_fd('clipbdWriterFromHost.socket')


    # empty
    Path(f'{target_sbxdir_path}/empty').touch()
    os.chmod(f'{target_sbxdir_path}/empty', 0)

    # apps目录
    mkdirp(f'{target_sbxdir_path}/apps')
    if old_sbxdir_path :
        if not Path(f'{old_sbxdir_path}/apps').is_mount():
            # 创建新的空的 tmpfs 给apps
            mount('tmpfs', f'{target_sbxdir_path}/apps', 'tmpfs', mntflag_apps, 'mode=755')
        else:
            # 把上一层的apps bind过来. 不是最后一层就应该要保留rw
            mount(f'{old_sbxdir_path}/apps', f'{target_sbxdir_path}/apps', None, MS.BIND|mntflag_apps, None)

    # temp目录
    mkdirp(f'{target_sbxdir_path}/temp')
    if call_at_buildfs:
        mount('tmpfs', f'{target_sbxdir_path}/temp', 'tmpfs', mntflag_sbxtemp, 'mode=755')


    # sbxinfo.json
    if call_at_begin:
        with open(f'{target_sbxdir_path}/sbxinfo.json', 'w') as f:
            f.write(json.dumps(si, indent=2, ensure_ascii=False))
            os.chmod(f.name, 0o444)
        with open(f'{target_sbxdir_path}/sbx.{si.sandbox_name}.name', 'w') as f:
            f.write(si.sandbox_name)
            os.chmod(f.name, 0o444)
        symlink(f'sbx.{si.sandbox_name}.name', f'{target_sbxdir_path}/sbx.name')


    # 递归 创建和写 (不包括本层)所有子层（递归） 需要的 路径和文件
    def create_lyrs_files_recr(lyr_cfg):
        if call_at_begin:
            with open(f'{target_sbxdir_path}/lyr_cfg.{lyr_cfg.layer_name}.json', 'w') as f:
                f.write(json.dumps(lyr_cfg, indent=2, ensure_ascii=False))
                os.chmod(f.name, 0o444)
        if lyr_cfg.newrootfs:
            mkdirp(f'{target_sbxdir_path}/new.{lyr_cfg.layer_name}.rootfs')
        for sublyr_cfg in (lyr_cfg.sublayers or [] ) :
            create_lyrs_files_recr(sublyr_cfg)

    # 判断是最外层 才把 本层配置（即第1层） 写入,否则只写子层
    arr_recr_create_conf = [lyrcfg] if call_at_begin else (lyrcfg.sublayers or [] )
    for sublyr_cfg in arr_recr_create_conf :
        create_lyrs_files_recr(sublyr_cfg)

    # 重新挂载为ro
    if new_tmpfs_for_sbxdir:
        os.chmod(target_sbxdir_path, 0o555)
        rmt_ro(target_sbxdir_path, mntflag_newsbxdir)
