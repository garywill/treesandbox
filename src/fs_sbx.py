from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量


def build_fs(cfg):
    if not cfg.newrootfs_path:
        if cfg.newrootfs: # 如果设置了将要变根，现在先提前确定新根的位置
            cfg.newrootfs_path = f'{cfg.sbxdir_path0}/new.{cfg.layer_name}.rootfs'
        else:
            cfg.newrootfs_path = '/'
    mkdirp(cfg.newrootfs_path)

    if cfg.fs:
        fsOpertns = gen_fsOpertns(cfg)
        remountPlans = commit_fsOpertns(cfg, fsOpertns)
        commit_remounts(remountPlans)

    # 在build_fs完了之后挂载/proc, 与fsOpertns那边的代码解耦
    if cfg.unshare_pid or cfg.newrootfs:
        new_proc_path = napath(cfg.newrootfs_path+'/proc')
        # log(f'Mounting proc to {new_proc_path}')
        mkdirp(new_proc_path)
        mount('proc', new_proc_path, 'proc', mntflag_proc, 'hidepid=1')
        cfg.new_proc_dir_mnted = True
    set_ps1('afterFs')

    # 执行变根 (chroot)
    if cfg.newrootfs:
        mkdirp(f'{cfg.newrootfs_path}/oldroot')
        # log(f'Going to pivot root to {cfg.newrootfs_path}')
        pivot_root(cfg.newrootfs_path, f'{cfg.newrootfs_path}/oldroot')
        os.chdir('/')
        umount('/oldroot', MNT.DETACH)
        os.rmdir('/oldroot') # 必须为空目录才能删除，这也保证已经缷载，未缷载则报错退出
        os.chmod('/', 0o555)
        rmt_ro('/', mntflag_newrootfs)
        # log(f'This layer filesystem ready {os.listdir('/')}')
    del cfg.newrootfs_path
    del cfg.sbxdir_path0


def commit_fsOpertns(cfg, fsOpertns):
    target_fs_path = cfg.newrootfs_path
    # log(f'Going to build (mount/create) this layer filesystem, will use this as root: {target_fs_path}')
    remountPlans = []
    def z(rmtItem):
        remountPlans.append(rmtItem)

    if target_fs_path.startswith(si.PTMP):
        mount(si.PTMP, si.PTMP, None, mntflag_binddir|MS.RDONLY, None)
        rmt_ro(si.PTMP, mntflag_binddir)
        CHK( os.statvfs(si.PTMP).f_flag&MS.RDONLY, "PTMP failed to made ro")
    if not Path(f'{cfg.sbxdir_path0}/temp').is_mount():
        mount('tmpfs', f'{cfg.sbxdir_path0}/temp', 'tmpfs', mntflag_tmpfs, None)

    mkdirp(target_fs_path)
    if napath(target_fs_path) != '/':
        mount("tmpfs", target_fs_path, "tmpfs", mntflag_newrootfs, None)
        mount(None, target_fs_path, None, MS.REC | MS.SLAVE, None)
        # # 用了slave它还是private,不知原因
    os.chdir(target_fs_path)
    CHK( Path(target_fs_path).is_mount() , f"{target_fs_path} is not a mount point")
    mkdirp(f'{target_fs_path}/proc') # proc不在这里做，预留个目录

    for opItem in fsOpertns:
        op = opItem.op
        src = opItem.src
        dest = opItem.dest
        real_dest = napath(f'{target_fs_path}/{dest}')
        if op in ['same', 'rosame', 'bind', 'robind'] : # TODO bindfs 它才可以设置destmode
            CHK( os.path.lexists(src) , f"Source {src} does not exist")
            if op in ['bind', 'robind'] :
                src = rslvy(src)
            RO = True if op in ['rosame', 'robind'] else False
            if Path(src).is_symlink(): # 软链 (一定要把 symlink 放在最先判断)
                symlink(Path(src).readlink(), real_dest)
                # TODO chroot 前后对symlink做一致性检查
            elif is_dir(src): # 文件夹
                mkdirp(real_dest)
                mount(src, real_dest, None, mntflag_binddir, None)
                if RO : rmt_ro(real_dest, mntflag_binddir )
            elif is_file(src) or is_dev(src):
                # 普通文件可以这这样。猜测 字符设备、块设备 也可以当普通文件一样处理
                make_file_exist(real_dest)
                mount(src,  real_dest, None, MS.BIND, None)
                rmt_ro(real_dest, MS.BIND) if RO else None
            elif is_socket(src): # 已知socket不能remount成ro
                make_file_exist(real_dest)
                mount(src,  real_dest, None, MS.BIND|MS.RDONLY, None)
            else: raise_exit(f"Type of source {src} is not yet supported")
        elif op in ['ovl']:
            mkdirp(real_dest)
            work_tmp = tempfile.mkdtemp(dir=f'{cfg.sbxdir_path0}/temp')
            upper_tmp = tempfile.mkdtemp(dir=f'{cfg.sbxdir_path0}/temp')
            mount_overlayfs(lowerdir=src, workdir=work_tmp, upperdir=upper_tmp, target=real_dest)
        elif op in ['tmpfs', 'rotmpfs']:
            RO = True if op == 'rotmpfs' else False
            mkdirp(real_dest)
            flag = opItem.flag or mntflag_tmpfs
            mount('tmpfs', real_dest, 'tmpfs', flag , 'mode=755')
            if RO : z(d(dirpath=real_dest, flag=flag))
        elif op == 'dir':
            mkdirp(real_dest)
        elif op == 'any-exist': #如果已存在，无论是文件/目录/软链都可以，不存在就建个空文件
            if not os.path.lexists(real_dest):
                make_file_exist(real_dest)
        elif op in ['file', 'rofile'] :
            # NOTE 无论何种情况，都不要对目标文件做写入，而是创建个临时文件去“挂载覆盖”。
            # 记得永远不要写入目标文件，防止覆盖用户文件
            RO = True if op == 'rofile' else False
            with tempfile.NamedTemporaryFile( dir=f'{cfg.sbxdir_path0}/temp', mode='w', delete=False) as f:
                f.write(opItem.content)
                mode = None ; optn = None
                if RO :             mode = '444'
                if opItem.destmode : mode = opItem.destmode
                if mode is not None : os.chmod(f.name, int(mode,base=8)) ; optn = f'mode={mode}'
                make_file_exist(real_dest)
                mount(f.name, real_dest, None, MS.BIND|(MS.RDONLY if RO else 0), optn)
                try_pass(lambda: rmt_ro(real_dest, mntflag_binddir, optn) if RO else None )
        elif op == 'symlink':
            symlink(opItem.linkto, real_dest)
            # TODO chroot 前后对symlink做一致性检查
        elif op == 'empty-if-exist' : # TODO landlock 优先
            if not os.path.lexists(real_dest): continue
            optn='mode=0000'
            if Path(real_dest).is_symlink(): # 软链 (一定要把 symlink 放在最先判断)
                raise_exit(f"Path {real_dest} to be emptied is a symlink, handling not yet implemented")
            elif is_dir(real_dest): # 文件夹
                mount('tmpfs', real_dest, 'tmpfs', MS.RDONLY|MS.NODEV|MS.NOEXEC|MS.NOSUID, optn)
            elif is_dev(real_dest): # 设备文件
                mount('/dev/null', real_dest,  None, MS.BIND|MS.RDONLY, optn)
                try_pass(lambda: rmt_ro(real_dest, mntflag_binddir, optn) )
            else: # 普通文件、socket, fifo
                mount(f'{cfg.sbxdir_path0}/empty', real_dest,  None, MS.BIND|MS.RDONLY, optn)
                try_pass(lambda: rmt_ro(real_dest, mntflag_binddir, optn) )
        elif op == 'sbxdir-in-newrootfs':
            CHK(dest == '/sbxdir', "dest for sbxdir-in-newrootfs must be /sbxdir")
            make_mnt_fill_sbxdir(si,  cfg, call_at_buildfs=True)
        elif op == 'devpts':
            mkdirp(real_dest)
            mount('devpts', real_dest, 'devpts', MS.NOEXEC|MS.NOSUID, 'mode=0666,ptmxmode=0666,newinstance')
        elif op in ['appimg-mount', 'sqfs-mount'] :
            mkdirp(real_dest)
            src = rslvy(src)
            offset = get_appimg_sqoffset(src) if op == 'appimg-mount' else 0
            # TODO 先做symlink链接到真实appimage文件路径，再调用 squashfuse命令
            run_a_cmd(['squashfuse', '-o', f'ro,offset={offset}', src, real_dest])
            # 不考虑内核挂载先，因为内核挂载squashfs要loop, 容器内难搞.先用住 fuse
        elif op == 'rmt-ro':
            rmt_ro(real_dest, opItem.flag or 0)
        elif op == 'final-rmt-ro':
            z(d(dirpath=real_dest, flag=opItem.flag or 0))
        else:
            raise_exit(f"Unrecognized fsOp item {opItem}")

    return remountPlans

def gen_fsOpertns(cfg): # 把fs里面的 many_op 都转成 op ,并去重、排序
    fsOpertns = []
    def a(stepobj):
        fsOpertns.append(stepobj)

    for opItem in cfg.fs:
        # 一个 opItem 里， many_op 和 op 只应该出现其中一种
        many_op = opItem.many_op # 预设的多个op的集合
        op = opItem.op # 一个op
        if many_op == 'dup-rootfs': # 把前一个rootfs复制到子层。包含dev
            destbase = opItem.destbase or '/'
            srcbase = opItem.srcbase or '/'
            CHK( destbase in ['/', '/zrootfs'], "dup-rootfs requires destbase to be '/' or '/zrootfs'")
            CHK( srcbase in ['/', '/zrootfs'],  "dup-rootfs requires srcbase to be '/' or '/zrootfs'")
            if destbase != '/':
                a( d( op='rotmpfs', dest=destbase , flag=mntflag_newrootfs) )
            for x in os.listdir(srcbase):
                if x in [ 'proc', 'sbxdir', 'zrootfs', ]: continue
                a( d( op='same', dest=napath(f'{destbase}/{x}') , src=napath(f'{srcbase}/{x}') ) )
            # a( d( op='tmpfs', dest=napath(f'{destbase}/run/tmux') ) ) # 按理说，使用 dup-rootfs 的层本来不应该运行任何程序（因为uid=0)，但可能会用 tmux 当内外通信工具，先预留这个，并且要与host中的 /run/tmux 不同
        elif many_op == 'sbxdir-in-newrootfs':
            dcp_pItem = copy.deepcopy(opItem)
            a( d({'op': dict.pop(dcp_pItem, 'many_op'), **dcp_pItem} ) )
        elif many_op == 'basic-dev':
            # 最小 /dev 集合。把常用设备结点从宿主机 bind 进来；并为 shm 提供 tmpfs
            a( d( op='rotmpfs', dest='/dev' ) )
            basic_devs = [ 'null', 'zero', 'full', 'urandom', 'random',] # 'tty', 'console'
            for dname in basic_devs:
                a( d( op='rosame', dest=f'/dev/{dname}', src=f'/dev/{dname}' ) ) # 不能ro对单个具体设备？
            a( d( op='devpts',  dest='/dev/pts') )
            a( d( op='symlink', dest='/dev/ptmx', linkto='pts/ptmx' ) )
            a( d( op='symlink', dest='/dev/fd',     linkto='/proc/self/fd' ) )
            a( d( op='symlink', dest='/dev/stdin',  linkto='/proc/self/fd/0' ) )
            a( d( op='symlink', dest='/dev/stdout', linkto='/proc/self/fd/1' ) )
            a( d( op='symlink', dest='/dev/stderr', linkto='/proc/self/fd/2' ) )
            a( d( op='symlink', dest='/dev/core',   linkto='/proc/kcore' ) )
            a( d( op='tmpfs', dest='/dev/shm' ) )
        elif many_op == 'container-rootfs':
            # 只读挂载的重要系统路径
            paths_to_rosame = [ '/bin', '/sbin', '/usr', '/lib64', '/lib', '/etc',
                '/var/cache/fontconfig' ]
            if os.path.lexists('/var/lib/ca-certificates'):
                paths_to_rosame.append += ['/var/lib/ca-certificates']
            for p in paths_to_rosame:
                a( d( op='rosame', dest=p, src=p ) )
            # 需要 tmpfs 的可写路径（容器内部用）
            paths_to_tmpfs = [ '/run', '/tmp', '/root', '/mnt',
                '/var', '/var/lib', '/var/lib/empty', '/var/cache',
                f'/run/user/{si.uid}', '/run/user/0', '/run/lock',
                '/run/tmux' , f'{si.HOME}' , f'{si.HOME}/.cache' ,
                f'{si.HOME}/.local/share/RecentDocuments',
                f'{si.HOME}/.local/share/recently-used.xbel',
                f'{si.HOME}/.local/share/Trash', ]
            for p in paths_to_tmpfs:
                a( d( op='tmpfs', dest=p ) )
            a( d( op='symlink', dest='/var/run', linkto='/run' ) )
            a( d( op='symlink', dest='/var/lock', linkto='/run/lock' ) )
            a( d( op='symlink', dest='/var/lib/dbus/machine-id', linkto='/etc/machine-id' ) )
        elif many_op == 'mask-privacy':
            destbase = opItem.destbase
            CHK( destbase in ['/', '/zrootfs'], "mask-privacy requires destbase to be '/' or '/zrootfs'")
            path_maskfile = f'{si.HOME}/.config/treesandbox/paths_never_access.txt'
            maskfile = Path(path_maskfile)
            paths_to_mask = maskfile.read_text().splitlines() if maskfile.exists() else []
            paths_to_mask = [path.strip() for path in paths_to_mask if path.strip()]
            log(f'Need to mask {len(paths_to_mask)} paths, from {path_maskfile}')
            for path in paths_to_mask:
                CHK( path.startswith('/'), "Entry in paths_never_access.txt does not start with '/'")
                path = napath(path)
                if os.path.lexists(path):
                    a( d( op='empty-if-exist', dest=napath(f'{destbase}/{path}' ) ) )
        elif many_op == 'appimage':
            a( d(op='appimg-mount', src=opItem.src, dest=f'/sbxdir/apps/{opItem.name}') )
            start_sh_content = f'''#!/bin/bash
                script=$(readlink -f "$0")
                scriptpath=$(dirname "$script")
                env APPDIR="$scriptpath/{opItem.name}" "$scriptpath"/{opItem.name}/AppRun "$@"
            '''
            a( d(op='rofile', dest=f'/sbxdir/apps/run_{opItem.name}', destmode='555', content=start_sh_content) )
        elif many_op == 'squashfs':
            a( d(op='sqfs-mount', src=opItem.src, dest=f'/sbxdir/apps/{opItem.name}') )
        # 下面是 op 而不是 many_op 。因为它们两个不应同时有，所以用同一if树
        elif op:
            a( opItem )
        else:
            raise_exit(f"Unrecognized fs item {opItem}")

    for i, opItem in enumerate(fsOpertns):
        if opItem.SDS:
            if   opItem.src and not opItem.dest: opItem.dest = opItem.src
            elif opItem.dest and not opItem.src: opItem.src = opItem.dest
            elif not opItem.src and not opItem.dest:        raise_exit(f"{opItem} has neither src nor dest")
            elif napath(opItem.src) != napath(opItem.dest): raise_exit(f"{opItem} has SDS set, but src and dest are inconsistent")
            del opItem.SDS
        dcp_pItem = copy.deepcopy(opItem)
        dcp_pItem = d({'op': dict.pop(dcp_pItem, 'op'), **dcp_pItem})
        fsOpertns[i] = dcp_pItem

    # 查找移除重复的dest
    def find_dup_dest():
        used_dest = set()
        for i in reversed(range(0, len(fsOpertns))):
            opItem = fsOpertns[i]
            if opItem.op in ['rmt-ro', 'final-rmt-ro']: continue
            if opItem.dest in used_dest:
                log(f"debug: due to duplicate dest (={opItem.dest}), removing {opItem}")
                fsOpertns[i] = d(removed=True)
            used_dest.add(opItem.dest)
    # TODO 分为 普通、remount、overlay 几个组来去重
    find_dup_dest()
    fsOpertns = [opItem for opItem in fsOpertns if not opItem.removed]

    # 排序 fsOpertns
    fsOpertns = sorted(fsOpertns, key=lambda opItem: napath(opItem['dest']).split(os.sep) )
    fsOpertns = sorted(fsOpertns, key=lambda x: 0 if (isinstance(x, dict) and x.get('op') == 'sbxdir-in-newrootfs') else 1)

    # [log(opItem) for opItem in fsOpertns] # debug
    return fsOpertns

def commit_remounts(remntPlans):
    for rItem in remntPlans:
        # log('ro-remounting: ' , rItem) # debug
        dirpath = rItem.dirpath
        flag = rItem.flag or 0
        rmt_ro(dirpath, flag)

def rmt_ro(path, flag=0, optn=''):
    flag |= os.statvfs(path).f_flag & (MS.NODEV|MS.NOSUID|MS.NOEXEC)
    mount(None, path, None, MS.REMOUNT|MS.RDONLY|flag, optn)




def get_appimg_sqoffset(appimg_path):
    with open(appimg_path, 'rb') as f: elfHeader = f.read(64)
    (bitness,endianness) = struct.unpack("4x B B 58x", elfHeader);
    (shoff,shentsize,shnum) = struct.unpack(
        (">" if endianness == 2 else "<") +
        ("40x Q 10x H H 2x" if bitness == 2 else "32x L 10x H H 14x"),
        elfHeader
    );
    return (shoff + shentsize * shnum)
