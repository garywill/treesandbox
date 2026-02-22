#!/usr/bin/python3

# Box-in-Box Linux (BBL) Sandbox
# Licensed under GPL
# https://github.com/garywill/bblsandbox

import os, sys, shutil, subprocess, pwd, grp, time, pty, ctypes, ctypes.util, atexit, json, copy, tempfile, struct, re, socket, signal, asyncio, glob , datetime , types, select
from pathlib import Path

# === HIDE_FOR_SUBLAYERS BEGIN === NOTE: Don't change this line ===
# 普通用户设置这里
def userconfig(si): # 这个只在顶层解析一次
    uc = d()
    uc.sandbox_name='' # 沙箱名称

    # 若不设置 homedir ，则会用 tmpfs 当 $HOME
    # uc.homedir=f'{si.startdir_on_host}/fakehome'

    # 若不设置gui则内部无任何X11
    uc.gui="realX" # 使用真实的 X11
    # uc.gui="xephyr"
    # uc.gui="xpra" # 暂未实现
    # uc.gui="isolatedX"; de_start_cmd="plasmashell"  # 暂未实现

    uc.gpus     =      True if uc.gui else False
    uc.see_userfonts = True if uc.gui else False

    # uc.see_real_hw=True # 看见真实/dev和/sys

    uc.user_mnts = [
        # d(mttype='appimage', appname='xxxx', src=f'{si.startdir_on_host}/xxxx.AppImage'),
        # d(mttype='robind', src=f'{si.startdir_on_host}', SDS=1),
    ]

    # 输入法等通信需要dbus
    uc.dbus_session="allow"
    # uc.dbus_session="filter" # (暂未实现)

    uc.net=d(
        iface='real', # 使用真实的网络介面
        dns='real', #真实的/etc/resolv.conf所指向的目录
        # dns=['127.0.0.1'], # 自定义dns
    )

    uc.allow_opt=True # 允许访问真实/opt
    uc.mask_xdg_opens=True # 容器内部不能使用xdg-open, firefox, chromium 等
    # uc.mask_osrelease=True # 不可访问/etc/os-release
    uc.machineid='zero' # 把/etc/machine-id填0

    return uc

# layer1 产生
def gen_container_cfgs(si, uc, dyncfg): # 这个只在顶层解析一次
    layer1 = d( # 第1层不跑任何程序，只用于PID隔离，和退出时的清理工作
        layer_name='layer1', # 默认模板的 layer_name 不要修改
        unshare_pid=True, # 第1层必须
        unshare_mnt=True, # 第1层尝试有unshare mnt但不newrootfs

        unshare_chdir=True, # chdir()不影响其他

        # uid 变 0
        unshare_user=True, setgroups_deny=True, uid_map=f'0 {si.uid} 1\n', gid_map=f'0 {si.gid} 1\n',
        # 准备开始第2层。这第1层的 sublayers 数组应该只有一个元素，即，第2层只有一个容器
        sublayers = [
            d( # 第2层。 只适合跑 信任的 和要以信任身份显示在X11的： xpra client , dbus proxy . squashfs挂载
                layer_name='layer2', # 默认模板的 layer_name 不要修改
                unshare_mnt=True,
                unshare_chdir=True, # chdir()不影响其他
                newrootfs=True, # 第2层必须 # 有newrootfs则必须有fs
                fs=[ # fs全称fs_plans_for_new_rootfs 。
                    # 第2层是首次 unshare mnt 。先复制一次真实host的rootfs环境
                    d(batch_plan='container-rootfs'),
                    d(batch_plan='basic-dev'),
                    d(batch_plan='mask-privacy', destbase='/'),
                    d(batch_plan='sbxdir-in-newrootfs', dest='/sbxdir'),

                    *dyncfg.mnts_gui,

                    d(plan='robind', src=f'/tmp/.X11-unix/X{os.getenv("DISPLAY").lstrip(":")}', SDS=1),
                    d(plan='robind', src=f'{os.getenv("XAUTHORITY")}', SDS=1),

                    d(plan='bind', src=os.getenv('DBUS_SESSION_BUS_ADDRESS').lstrip('unix:path='), SDS=1 ),

                    d(batch_plan='dup-rootfs', destbase='/zrootfs'), # 排除/proc。不加ro。
                    d(batch_plan='mask-privacy', destbase='/zrootfs'),
                    d(plan='empty-if-exist', dest=f'/zrootfs/{PTMP}'),
                ],
                envs_unset=[
                    "SYSTEMD_EXEC_PID", "MANAGERPID", "SSH_AGENT_PID", "SSH_AUTH_SOCK",  "WINDOWMANAGER", "SHELL_SESSION_ID", "INVOCATION_ID", "GPG_TTY", "XDG_SESSION_ID", "KONSOLE_DBUS_SERVICE", "GPG_AGENT_INFO", "OLDPWD", "WINDOWID", "SESSION_MANAGER", "JOURNAL_STREAM",  "XDG_CACHE_HOME",
                ],

                sublayers = [
                    d( # layer2a实际上深度为3, 这层是为了运行可信程序如 xpra client , dbus proxy 等
                        layer_name='layer2a', unshare_pid=True, unshare_mnt=True,
                        unshare_chdir=True, # chdir()不影响其他

                        # uid 变回 1000
                        unshare_user=True, setgroups_deny=True, uid_map=f'{si.uid} 0 1\n', gid_map=f'{si.gid} 0 1\n',

                        newrootfs=True,
                        fs=[
                            d(batch_plan='dup-rootfs', destbase='/'),
                            d(batch_plan='sbxdir-in-newrootfs', dest='/sbxdir'),
                        ],
                        dropcap_then_cmds=[
                            d(
                                cmdlist=["Xephyr",  ":10",  "-resizeable",  "-ac"] ,
                            ) if uc.gui=='xephyr' else None,
                        ],
                    ),
                    gen_layer2h(si, uc, dyncfg)
                ],
            )
        ],
    )
    return layer1

def gen_layer2h(si, uc, dyncfg):
    layer2h = d( # layer2h 作为 layer2和3之间，把layer2的/zrootfs变回真/，准备让layer3接
        layer_name='layer2h',  unshare_mnt=True, unshare_chdir=True,
        start_after=[
            d(waittype='socket-listened', path='/tmp/.X11-unix/X10') if uc.gui=='xephyr' else None,
        ],
        newrootfs=True,
        fs=[
            d(batch_plan='dup-rootfs', srcbase='/zrootfs'),
            d(batch_plan='sbxdir-in-newrootfs', dest='/sbxdir'),

            d(plan='robind', src='/tmp/.X11-unix/X10', dest='/sbxdir/temp/X10') if uc.gui=='xephyr' else None,
        ],
        sublayers=[ gen_layer3(si, uc, dyncfg) ],
    )
    return layer2h

def gen_layer3(si, uc, dyncfg):
    layer3 = d(
        layer_name='layer3', # 默认模板的 layer_name 不要修改
        unshare_mnt=True,
        unshare_chdir=True, # chdir()不影响其他
        unshare_fd=True,
        unshare_cg=True,
        unshare_ipc=True,
        unshare_time=True,
        unshare_uts=True,

        unshare_net=True if uc.net.iface != 'real' else False,

        newrootfs=True, # 有newrootfs则必须有fs
        fs=[ # fs全称fs_plans_for_new_rootfs 。
            d(batch_plan='container-rootfs'),  # 不包括 dev 。不包括 proc
            d(batch_plan='sbxdir-in-newrootfs', dest='/sbxdir'),
            d(plan='empty-if-exist', dest=si.startscript_on_host),
            *dyncfg.fs_user_mounts,
            # ---- 以上是不变条目 ----

            d(plan='robind', dest='/opt', src='/opt') if uc.allow_opt else None,

            d(batch_plan='basic-dev') if not uc.see_real_hw else None, # 创建新的容器最小的/dev

            *([
            d(plan='robind', dest='/dev', src='/dev'),
            d(plan='tmpfs',dest='/dev/shm'),
            d(plan='robind', dest='/sys', src='/sys'),
            ] if uc.see_real_hw else [] ),
            # TODO 1. 改用dyncfg  2. layer2里也加

            d(plan='bind', dest=f'{si.HOME}', src=uc.homedir) if uc.homedir else None, # 若这条不成立，container-roofs那条会产生一个tmpfs的家目录

            *([
            d(plan='robind', dest=f'/tmp/.X11-unix/X{os.getenv("DISPLAY").lstrip(":")}', SDS=1),
            d(plan='robind', dest='/tmp/xauthfile', src=f'{os.getenv("XAUTHORITY")}'),
            ] if uc.gui=='realX' else [] ),

            d(plan='robind', src='/sbxdir/temp/X10', dest='/tmp/.X11-unix/X10') if uc.gui=='xephyr' else None,

            *dyncfg.mnts_gui,

            d(plan='rofile', dest=shutil.which("xdg-open"), destmode=0o555, content=ASK_OPEN ) if uc.mask_xdg_opens else None,
            *[d(plan='empty-if-exist', dest=path) for path in dyncfg.paths_to_mask],

            d(plan='bind', dest='/tmp/dbus_session_socket',  src=os.getenv('DBUS_SESSION_BUS_ADDRESS').lstrip('unix:path=')) if uc.dbus_session == 'allow' else None,

            d(plan='empty-if-exist', dest='/etc/fstab'),
            d(plan='empty-if-exist', dest='/etc/systemd'),
            d(plan='empty-if-exist', dest='/etc/init.d'),
            d(plan='empty-if-exist', dest=rslvn('/etc/os-release')) if uc.mask_osrelease else None,
            d(plan='rofile', dest='/etc/machine-id', content=dyncfg.machineid) if dyncfg.machineid else None,

            *([
            d(plan='robind', dest=padir(rslvn('/etc/resolv.conf')), SDS=1) if Path('/etc/resolv.conf').is_symlink() else None,
            # nscd ...
            ] if uc.net.dns == 'real' else [] ),
            d(plan='rofile', dest=rslvn('/etc/resolv.conf'), content=''.join([f'nameserver {ip}\n' for ip in uc.net.dns]) ) if isinstance(uc.net.dns, list) else None,

        ],
        envs_unset=[
            "ICEAUTHORITY", "XAUTHORITY", "DISPLAY", "XAUTHLOCALHOSTNAME", "IBUS_ADDRESS", "DBUS_SESSION_BUS_ADDRESS", "DBUS_SYSTEM_BUS_ADDRESS",
        ],
        envset_grps=[
            d( DISPLAY=os.getenv("DISPLAY"), XAUTHORITY='/tmp/xauthfile', ) if uc.gui=='realX' else None,
            d(DBUS_SESSION_BUS_ADDRESS='unix:path=/tmp/dbus_session_socket') if uc.dbus_session else None,
            d(DISPLAY=':10') if uc.gui=='xephyr' else None,
        ],
        sublayers=[
            d(
                layer_name='layer4a', # 默认模板的 layer_name 不要修改
                unshare_pid=True, unshare_mnt=True,
                unshare_chdir=True, # chdir()不影响其他

                # uid 变回 1000
                unshare_user=True, setgroups_deny=True, uid_map=f'{si.uid} 0 1\n', gid_map=f'{si.gid} 0 1\n',
            ),
            d( # 主 用户app 在这里跑
                layer_name='layer4', # 默认模板的 layer_name 不要修改
                unshare_pid=True, unshare_mnt=True,
                unshare_chdir=True, # chdir()不影响其他

                # uid 变回 1000
                unshare_user=True, setgroups_deny=True, uid_map=f'{si.uid} 0 1\n', gid_map=f'{si.gid} 0 1\n',

                user_shell=True,
            ),
        ],
    )
    return layer3

def gen_dynamic_cfg(si, uc): # 这个只在顶层解析一次
    fs_user_mounts = []

    cmds_to_mask = []
    paths_to_mask = []

    mnts_gui = [
        *([
        d(plan='robind', src=f'{si.HOME}/.fonts', SDS=1),
        d(plan='robind', src=f'{si.HOME}/.fonts.conf', SDS=1),
        d(plan='robind', src=f'{si.HOME}/.cache/fontconfig', SDS=1),
        ] if uc.see_userfonts else [] ),
        *([
        d(plan='rosame', src='/dev/dri', SDS=1),
        d(plan='rosame', src='/sys/class/drm', SDS=1),
        *[ d(plan='rosame', src=p, SDS=1)        for p in glob.glob('/sys/dev/char/226:*') ],
        *[ d(plan='rosame', src=padir(p), SDS=1) for p in glob.glob('/sys/devices/*/*/drm') ],
        *[ d(plan='rosame',  src=rslvy(f'{padir(p)}/driver'), SDS=1)  for p in glob.glob('/sys/devices/*/*/drm') ],
        ] if uc.gpus else [] ),
    ]

    for um in (uc.user_mnts or [] ):
        if um.mttype == 'appimage':
            fs_user_mounts += [d(plan='appimg-mount', src=um.src, dest=f'/sbxdir/apps/{um.appname}')]
            start_sh_content = f'''#!/bin/bash
                script=$(readlink -f "$0")
                scriptpath=$(dirname "$script")
                env APPDIR="$scriptpath/{um.appname}" "$scriptpath"/{um.appname}/AppRun "$@"
            '''
            fs_user_mounts += [d(plan='rofile', dest=f'/sbxdir/apps/run_{um.appname}', destmode=0o555, content=start_sh_content)]
        elif um.mttype in ['bind', 'robind', 'same', 'rosame']:
            planItem = copy.deepcopy(um)
            del planItem.mttype
            planItem.plan = um.mttype
            fs_user_mounts += [planItem]


    if uc.mask_xdg_opens:
        cmds_to_mask += [
            "firefox", "firefox-esr", "seamonkey", "icecat",
            "librewolf", "waterfox", "palemoon", "basilisk", "floop", "zen-browser",
            "chromium", "chromium-browser",
            "google-chrome", "google-chrome-stable", "ungoogled-chromium",
            "microsoft-edge", "microsoft-edge-stable",
            "vivaldi", "brave-browser", "opera",
            "torbrowser-launcher", "torbrowser",
            "konqueror", "falkon", "epiphany",
            "lynx", "w3m", "links", "elinks", "browsh",
            "dillo", "qutebrowser", "midori", "otter-browser", "xombrero", "luakit", "dooble", "netsurf", "nyxt", "iridium", "surf"
        ]
    paths_to_mask += [ path for cmd in cmds_to_mask if (path := which_and_resolve_exist(cmd)) is not None ]

    if uc.machineid == 'zero':
        machineid = '00000000000000000000000000000000'

    fs_user_mounts += [d(plan='remountro', dest='/sbxdir/apps', flag=mntflag_apps)]

    dyncfg = d({k: v for k, v in locals().items()
            if k in ['fs_user_mounts', 'paths_to_mask', 'machineid', 'mnts_gui']})
    return dyncfg

# === HIDE_FOR_SUBLAYERS END === NOTE: Don't change this line ===



used_layer_names = []
def recursive_lyrs_jobs(si, cfg, parent_cfg): # cfg：要处理的层， parent_cfg : 其父层
    # 计算本层深度
    cfg.depth = parent_cfg.depth + 1 if parent_cfg is not None else 1

    CHK( cfg.layer_name, "存在某层没有设置layer_name")
    CHK( re.match(r'^[a-zA-Z0-9_-]+$', cfg.layer_name), f"layer_name只能有字母、数字、杠、下划线。此名称不合法： {cfg.layer_name}" )
    CHK( cfg.layer_name not in resv_words, f"层名{cfg.layer_name}与保留字段{resv_words}重复")

    CHK( cfg.layer_name not in used_layer_names, f"层名称 '{cfg.layer_name}' 有重复")
    used_layer_names.append(cfg.layer_name)

    # 配置中的数组类型去除None成员
    if cfg.fs:
        cfg.fs = [fsItem for fsItem in cfg.fs if fsItem is not None]
    if cfg.sublayers :
        cfg.sublayers = [sublyr for sublyr in cfg.sublayers if sublyr and not sublyr.disabled]
    if cfg.dropcap_then_cmds :
        cfg.dropcap_then_cmds = [cmd for cmd in cfg.dropcap_then_cmds if cmd is not None]
    if cfg.envs_unset:
        cfg.envs_unset = [item for item in cfg.envs_unset if item is not None]
    if cfg.envset_grps:
        cfg.envset_grps = [item for item in cfg.envset_grps if item is not None]
    if cfg.start_after:
        cfg.start_after = [item for item in cfg.start_after if item is not None]

    if cfg.unshare_pid and not cfg.unshare_mnt:
        raise_exit(f"层{cfg.layer_name}启用了unshare_pid但没有启用unshare_mnt")
    if (cfg.newrootfs or cfg.fs) and not cfg.unshare_mnt:
        raise_exit(f"层{cfg.layer_name}设置了newrootfs或fs但没有启用unshare_mnt")
    if bool(cfg.fs) != bool(cfg.newrootfs):
        raise_exit(f"层{cfg.layer_name}: fs和newrootfs若有则应该两个都有")

    # 检查fs条目
    for fsItem in (cfg.fs or []):
        if fsItem.dest: fsItem.dest = napath(fsItem.dest)
        if fsItem.src: fsItem.src = napath(fsItem.src)
        if fsItem.destbase: fsItem.destbase = napath(fsItem.destbase)

    if len(cfg.sublayers or []) > 0 and cfg.newrootfs:
        if not any( pItem.batch_plan == 'sbxdir-in-newrootfs' for pItem in cfg.fs):
            raise_exit(f"层{cfg.layer_name}设置了变根，且要创建子容器，但其fs中无 batch_plan = 'sbxdir-in-newrootfs' 的条目 （此情况下要求有）")

    # 对第1层检查
    if cfg.depth == 1:
        CHK( cfg.unshare_pid, "第1层未启用 unshare_pid(要求启用)")
        CHK( len(cfg.sublayers) == 1, "第1层的sublayers数组的元素个数不为1 （要求为1）")

    # 对第2层检查
    if cfg.depth == 2:
        CHK( cfg.unshare_mnt, "第2层未启用 unshare_mnt （要求启用）")
        CHK( cfg.newrootfs, "第2层未启用 newrootfs （要求启用）")
        CHK( cfg.fs, "第2层未设置 fs （要求设置）")
        if not any( pItem.batch_plan == 'dup-rootfs' for pItem in cfg.fs):
            raise_exit("第2层的fs中无 batch_plan='dup-rootfs' 的条目 （要求有）")
        if not any( pItem.batch_plan == 'mask-privacy' for pItem in cfg.fs):
            raise_exit("第2层的fs中无 batch_plan='mask-privacy' 的条目 （要求有）")

    if cfg.layer_name == 'layer3': # 对第3层检查
        if cfg.fs and any( pItem.batch_plan == 'dup-rootfs' for pItem in cfg.fs) :
            raise_exit(f"层{cfg.layer_name}不应该在fs中使用 batch_plan='dup-rootfs'，因为上一层是最后一层允许看到主机文件的层")
        if not (cfg.unshare_mnt and cfg.unshare_chdir and cfg.unshare_fd and cfg.unshare_cg and cfg.unshare_ipc and cfg.unshare_time and cfg.unshare_uts and cfg.newrootfs and cfg.fs) :
            raise_exit(f"层{cfg.layer_name}未把 [unshare_mnt, unshare_chdir, unshare_fd, unshare_cg, unshare_ipc, unshare_time, unshare_uts, newrootfs, fs] 全启用 （要求全启用）")
        if not any( pItem.batch_plan == 'container-rootfs' for pItem in cfg.fs):
            raise_exit(f"层{cfg.layer_name}的fs中无 batch_plan='container-rootfs' 的条目 （要求有）")

    if cfg.layer_name in ['layer2a', 'layer4a', 'layer4']:
        CHK( cfg.unshare_pid, f"{cfg.layer_name}未启用unshare_pid=True（要求启用）")

    for sublyr_cfg in (cfg.sublayers or []):
        recursive_lyrs_jobs(si, sublyr_cfg, cfg)


resv_words = ['sbx', 'sbxs', 'sandbox', 'sandboxs', 'sandboxes', 'layer', 'layers', 'new', 'py', 'json', 'name', 'dirs', 'log', 'logs', 'socket', 'nc', 'tmpfs', 'tmp', 'temp', 'overlay', 'events', 'lyr_cfg', 'pid', 'userconfig', 'rootfs']
def make_mnt_fill_sbxdir(si, thislyr_cfg, call_at_begin=None, call_at_buildfs=None): # 创建本层的sbxdir, 可能是刚启动时新创建，也可能是准备变根前为变根后的环境内创建（可能复制启动时已有的）
    # sbxdir_path/ :
        # cfg/ :
            # si.json
            # bootsbx.py
            # sbx.xxx.name
            # sbx.name -> sbx.xxx.name
            # lyr_cfg.xxx.json (多) 包括本层和所有递归子层
            # events.layers.log (暂未实现） (需要build_fs处理 一路通挂载)
            # tmux.xxx.socket (暂未实现) (需要build_fs处理 一路通挂载)
        # new.xxx.rootfs (多)所有有 newrootfs 的本层和递归子层
        # temp  挂载为rw tmpfs
        # overlays 挂载为tmpfs 可能rw (暂未实现）
        # apps/ 挂为 tmpfs rw
    if call_at_begin: # 刚启动脚本
        target_sbxdir_path = napath(thislyr_cfg.sbxdir_path0)
        old_sbxdir_path = None
    elif call_at_buildfs: # 为本层接下来的新文件系统准备的 （可能 变根=新旧路径不同  ，也可能 不变根=新旧路径同）
        target_sbxdir_path = napath(f'{thislyr_cfg.newrootfs_path}/{thislyr_cfg.sbxdir_path1}')
        old_sbxdir_path = napath(thislyr_cfg.sbxdir_path0)

    if target_sbxdir_path == old_sbxdir_path:
        return
        # 能往下执行，说明是要从空白创建
    # else:
    #     creating_new_sbxdir=True


    mkdirp(target_sbxdir_path)
    new_tmpfs_for_sbxdir = True if call_at_buildfs else False
    if new_tmpfs_for_sbxdir:
        mount('tmpfs', target_sbxdir_path, 'tmpfs', mntflag_newsbxdir, None)

    Path(f'{target_sbxdir_path}/empty').touch()
    os.chmod(f'{target_sbxdir_path}/empty', 0)

    mkdirp(f'{target_sbxdir_path}/apps')
    if old_sbxdir_path :
        if not Path(f'{old_sbxdir_path}/apps').is_mount():
            # 创建新的空的 tmpfs 给apps
            mount('tmpfs', f'{target_sbxdir_path}/apps', 'tmpfs', mntflag_apps, None)
        else:
            # 把上一层的apps bind过来. 不是最后一层就应该要保留rw
            mount(f'{old_sbxdir_path}/apps', f'{target_sbxdir_path}/apps', None, MS.BIND|mntflag_apps, None)


    mkdirp(f'{target_sbxdir_path}/temp')
    if call_at_buildfs:
        mount('tmpfs', f'{target_sbxdir_path}/temp', 'tmpfs', mntflag_sbxtemp, None)



    mkdirp(f'{target_sbxdir_path}/cfg')
    if not os.path.exists(f'{target_sbxdir_path}/cfg/si.json'):
        with open(f'{target_sbxdir_path}/cfg/si.json', 'w') as f:
            f.write(json.dumps(si, indent=2, ensure_ascii=False))
            os.chmod(f.name, 0o444)
        safe_copy_script(f'{target_sbxdir_path}/cfg/bootsbx.py')
        with open(f'{target_sbxdir_path}/cfg/sbx.{si.sandbox_name}.name', 'w') as f:
            f.write(si.sandbox_name)
            os.chmod(f.name, 0o444)
        os.symlink(f'sbx.{si.sandbox_name}.name', f'{target_sbxdir_path}/cfg/sbx.name')

    # 创建和写 (不包括本层)所有子层（递归） 需要的 路径和文件
    def create_lyrs_files_recr(lyr_cfg):
        with open(f'{target_sbxdir_path}/cfg/lyr_cfg.{lyr_cfg.layer_name}.json', 'w') as f:
            f.write(json.dumps(lyr_cfg, indent=2, ensure_ascii=False))
            os.chmod(f.name, 0o444)
        if lyr_cfg.newrootfs:
            mkdirp(f'{target_sbxdir_path}/new.{lyr_cfg.layer_name}.rootfs')
        for sublyr_cfg in (lyr_cfg.sublayers or [] ) :
            create_lyrs_files_recr(sublyr_cfg)
    for sublyr_cfg in (thislyr_cfg.sublayers or [] ) :
        create_lyrs_files_recr(sublyr_cfg)

    # 判断是最外层 才把 本层配置（即第1层） 和 userconfig 写入
    if call_at_begin and thislyr_cfg.depth==1:
        with open(f'{target_sbxdir_path}/cfg/lyr_cfg.{thislyr_cfg.layer_name}.json', 'w') as f:
            f.write(json.dumps(thislyr_cfg, indent=2, ensure_ascii=False) )
            os.chmod(f.name, 0o444)


    if new_tmpfs_for_sbxdir:
        os.chmod(target_sbxdir_path, 0o555)
        mount(None, target_sbxdir_path, None, MS.REMOUNT|MS.RDONLY|mntflag_newsbxdir, None)

   # build_fs 时原有：
            # mount('tmpfs', f'{real_dest}/overlays', 'tmpfs', flag, None)

def init_sbxinfo(): # 仅顶层运行，子容器层不运行。返回的数据一路传下各个子层
    mkdirp(PTMP)      # 创建不同沙箱实例共用的 主临时目录

    sbxinfo = d()

    # 从外部(linux host)启动沙箱的原本用户信息
    uid = os.getuid()
    gid = os.getgid()
    username = pwd.getpwuid(uid).pw_name # 获取当前用户名
    groupname = grp.getgrgid(gid).gr_name
    HOME = f'/home/{username}' # 当前用户的家目录路径
    print(f"启动沙箱的用户为：{username} {groupname}")
    outest_pid = os.getpid()

    sbxinfo.uid = uid
    sbxinfo.gid = gid
    sbxinfo.username = username
    sbxinfo.groupname = groupname
    sbxinfo.HOME = HOME
    sbxinfo.outest_pid = outest_pid
    sbxinfo.startscript_on_host = scriptfilepath
    sbxinfo.startdir_on_host = scriptdirpath

    uc = userconfig(sbxinfo) # 用户配置别名

    # 沙箱名。不是子容器层名
    CHK( not uc.sandbox_name or re.match(r'^[a-zA-Z0-9_-]+$', uc.sandbox_name), f"容器名只能有字母、数字、杠、下划线。此名称不合法： {uc.sandbox_name}" )
    sandbox_name = uc.sandbox_name or f'{scriptdirname}_{scriptname}' # 沙箱名
    sandbox_name = re.sub(r'[^a-zA-Z0-9_\-]', lambda m: f"_{ord(m.group(0)):x}", sandbox_name)
    CHK( sandbox_name not in resv_words, f"沙箱名{sandbox_name}与保留字段{resv_words}重复")
    print(f"沙箱名：{sandbox_name}")

    starttime_str = datetime.datetime.now().strftime("%m%d-%H%M")

    n = 0
    while os.path.lexists( (outest_sbxdir := f'{PTMP}/{sandbox_name}_{starttime_str}-{n}') ):
        n+=1

    mkdirp(outest_sbxdir)    # 创建本次运行的临时目录, 包含'outest_newroot'和'cfg' 两个
    print(f"沙箱工作目录：{outest_sbxdir}")
    mkdirp(f'{outest_sbxdir}/cfg')    # 创建config目录，此目录内千万不要做挂载
    os.chdir(outest_sbxdir)
    print(f'沙箱启动PID: {outest_pid}')

    with open(f'{outest_sbxdir}/cfg/userconfig.json', 'w') as f:
        f.write(json.dumps(uc, indent=2, ensure_ascii=False))
        os.chmod(f.name, 0o444)
    with open(f'{outest_sbxdir}/cfg/sbx.{outest_pid}.pid', 'w') as f:
        f.write(str(outest_pid))
        os.chmod(f.name, 0o444)
    os.symlink(f'sbx.{outest_pid}.pid', f'{outest_sbxdir}/cfg/sbx.pid')

    sbxinfo.pythonbin = sys.executable
    sbxinfo.sandbox_name = sandbox_name
    sbxinfo.outest_sbxdir = outest_sbxdir

    dyncfg = gen_dynamic_cfg(sbxinfo, uc)
    layer1_cfg = gen_container_cfgs(sbxinfo, uc, dyncfg)
    recursive_lyrs_jobs(sbxinfo, layer1_cfg, None)

    # 还要加将给app的cli参数
    return sbxinfo, layer1_cfg

def main():
    # sys.argv[0] 是这个.py文件, sys.argv[1] 是cli传给此脚本的第1个参数
    if not len(sys.argv)>=2 or sys.argv[1] != '--lyrcfg' :
        # 是顶层
        is_outest = True # 是顶层
    else: # 是子层
        is_outest = False # 是子层
        lyrcfg_file = sys.argv[2]


    if is_outest: # 是顶层
        si, layer1_cfg = init_sbxinfo() # 只有从最外层启动才运行这个函数
        thislyr_cfg = layer1_cfg

        thislyr_cfg.sbxdir_path0 = si.outest_sbxdir

    else: # 是子层
        thislyr_cfg = d(json.loads(open(lyrcfg_file).read()))
        thislyr_cfg.sbxdir_path0 = str(Path(lyrcfg_file).parent.parent)
        si = d(json.loads(open(f'{thislyr_cfg.sbxdir_path0}/cfg/si.json').read()))

    set_loghead (f'{thislyr_cfg.layer_name}: ')

    # 预先算好变根后的 sbxdir_path1
    if not thislyr_cfg.newrootfs:
        thislyr_cfg.sbxdir_path1 = thislyr_cfg.sbxdir_path0
    else:
        thislyr_cfg.sbxdir_path1 = next((pItem.dest for pItem in thislyr_cfg.fs if pItem.batch_plan == 'sbxdir-in-newrootfs'), None)
    # sbxdir_path 说明
    # 本层变根 前 后 的 sbxdir_path ( sbxdir_path0 sbxdir_path1)
    # 变根前 0 = 刚启动本层启动脚本时
    # 变根后 1 = 即将运行下层的启动脚本时
    # 变根不一定发生，由本层配置决定，但也把两个sbxdir_path以 前 后 来称呼

    for env_to_unset in (thislyr_cfg.envs_unset or [] ):
        os.environ.pop(env_to_unset, None)
    for envg in (thislyr_cfg.envset_grps or [] ) :
        log(envg)
        os.environ.update(envg)

    for wait_task in (thislyr_cfg.start_after or [] ):
        if wait_task.waittype == 'socket-listened':
            while not is_unix_socket_listened(wait_task.path):
                time.sleep(0.1)
                pass

    if is_outest:
        make_mnt_fill_sbxdir(si, thislyr_cfg, call_at_begin=True)

    set_ps1(si, thislyr_cfg, 'beforeUnshare')

    # log(f"执行unshare")
    unshare_flag = gen_unshareflag_by_lyrcfg(thislyr_cfg)
    os.unshare(unshare_flag)

    set_ps1(si, thislyr_cfg, 'afterUnshare')

    # log(f"即将fork")
    pid = os.fork()
    if pid == 0: # 子进程
        # 最外层的原进程（fork前的进程）退出的话，layer1的fork出来的子进程应该主动退出
        if is_outest:
            set_pdeathsig()

        main2(si, thislyr_cfg)
        # log(f"fork后的子进程即将退出")
        sys.exit()
    else: # 父进程
        if not is_outest:
            sys.exit()

        atexit.register(lambda: cleanup_outest(si) ) # 顶层父进程注册清理函数

        set_ps1(si, thislyr_cfg, 'PaAfterFork')

        _, status = os.waitpid(pid, 0)
        if os.WIFEXITED(status):
            exit_code = os.WEXITSTATUS(status)
            log(f"沙箱内部首层领头进程已退出( {exit_code} )")
        elif os.WIFSIGNALED(status):
            signal_num = os.WTERMSIG(status)
            log(f"沙箱内部首层领头进程被信号 {signal_num} 终止")


def main2(si, thislyr_cfg):
    # 写uid_map 等 。一般来说配合 unshare_user
    if thislyr_cfg.setgroups_deny: Path('/proc/self/setgroups').write_text('deny\n')
    if thislyr_cfg.uid_map: Path('/proc/self/uid_map').write_text(thislyr_cfg.uid_map)
    if thislyr_cfg.gid_map: Path('/proc/self/gid_map').write_text(thislyr_cfg.gid_map)

    set_ps1(si, thislyr_cfg, 'forkedBeforeFs')
    log(f"内部当前 uid={os.getuid()} gid={os.getgid()}")

    # 如果设置了将要变根，现在先提前确定新根的位置
    if thislyr_cfg.newrootfs:
        thislyr_cfg.newrootfs_path = f'{thislyr_cfg.sbxdir_path0}/new.{thislyr_cfg.layer_name}.rootfs'
    else:
        thislyr_cfg.newrootfs_path = '/'
    mkdirp(thislyr_cfg.newrootfs_path)

    if thislyr_cfg.fs:
        build_thislyr_fs(si, thislyr_cfg) # 无论本层是否设置了变根，都调用这个函数

    # 在build_fs完了之后挂载/proc, 与fsPlans那边的代码解耦
    new_proc_path = napath(thislyr_cfg.newrootfs_path+'/proc')
    if thislyr_cfg.unshare_pid or thislyr_cfg.newrootfs:
        # log(f'挂载proc到 {new_proc_path}')
        mkdirp(new_proc_path)
        mount('proc', new_proc_path, 'proc', mntflag_proc, None)
    # 如果非最后一层，不要让 proc 变 ro ，也不要让 proc 内有其他挂载， 否则下一层出错
    if not thislyr_cfg.sublayers and os.getpid() != 1:
        makesure_proc_safe( new_proc_path , allow_newmntns=False ) # safe = proc ro + 1/fd屏蔽
    if not thislyr_cfg.sublayers : # 隐含条件 pid==1  # 仅让 proc ro ， 不要屏蔽1/fd
        make_proc_ro( new_proc_path , allow_newmntns=False )
    set_ps1(si, thislyr_cfg, 'afterFs')

    # 执行变根 (chroot)
    if thislyr_cfg.newrootfs:
        mkdirp(f'{thislyr_cfg.newrootfs_path}/oldroot')
        # log(f'准备变根到 {thislyr_cfg.newrootfs_path}')
        pivot_root(thislyr_cfg.newrootfs_path, f'{thislyr_cfg.newrootfs_path}/oldroot')
        os.chdir('/')
        umount('/oldroot', MNT.DETACH)
        os.rmdir('/oldroot') # 必须为空目录才能删除，这也保证已经缷载，未缷载则报错退出
        os.chmod('/', 0o555)
        mount(None, '/', None, MS.REMOUNT|MS.RDONLY|mntflag_newrootfs, None)
        # log(f'本层文件系统就绪 {os.listdir('/')}')
    del thislyr_cfg.newrootfs_path
    del thislyr_cfg.sbxdir_path0
    del new_proc_path


    if thislyr_cfg.sbxdir_path1:
        os.chdir(thislyr_cfg.sbxdir_path1)

    set_ps1(si, thislyr_cfg, 'afterChroot')

    # 如果unshare_pid,则我是init进程(pid=1)
    #   处理各种SIGNAL
    if thislyr_cfg.unshare_pid:
        CHK( os.getpid() == 1, f"{thislyr_cfg.layer_name} 检测到的自身PID不为1 （应该为1才正确）")
        atexit.register(cleanup_pidnsleader)
        for sig in EXIT_SIGNALS + [signal.SIGCHLD]:
            signal.signal(sig, signals_handler)

    set_ps1(si, thislyr_cfg, 'afterRegSigs')

    direct_child_pids = [] # 记录下直接创建的子进程，但可能用不上

    if thislyr_cfg.user_shell:
        if thislyr_cfg.sublayers or thislyr_cfg.dropcap_then_cmds:
            log("警告：因为启用了user_shell, 其余要启动的命令或子容器都会被忽略", file=sys.stderr)
        layer_run_subp ( thislyr_cfg, ['/bin/bash', '--norc' ] , blocking=True)
        sys.exit()

    for cmdItem in (thislyr_cfg.dropcap_then_cmds or [] ) :
        pid = layer_run_subp ( thislyr_cfg, cmdItem.cmdlist ,
                stdin =cmdItem.stdin , stdout=cmdItem.stdout, stderr=cmdItem.stderr,
                child_no_caps=True,
            )
        direct_child_pids.append(pid)

    sublayers = thislyr_cfg.sublayers or []
    # log(f"本层将生成 {len(sublayers)} 个子层")
    for sublyr_cfg in (sublayers or []):
        log(f"将运行子层 {sublyr_cfg.layer_name} 的启动脚本")
        pid = layer_run_subp(thislyr_cfg, [
                si.pythonbin ,
                # 这个脚本虽然是用于创建子层的，但现在仍是在本层,本层的变根后的状态，
                # 因此用本层的path1
                f'{thislyr_cfg.sbxdir_path1}/cfg/bootsbx.py',
                '--lyrcfg', f'{thislyr_cfg.sbxdir_path1}/cfg/lyr_cfg.{sublyr_cfg.layer_name}.json',
            ],
            stdin=True, stdout=True, stderr=True,
            child_no_caps = False,
        )
        direct_child_pids.append(pid)


    # 如果unshare_pid,则我是init进程(pid=1)
    #   如果有子进程，则等待，否则就退出
    if thislyr_cfg.unshare_pid:
        CHK( os.getpid() == 1, f"{thislyr_cfg.layer_name} 检测到的自身PID不为1 （应该为1才正确）")
        # TODO 改用poll
        async def loop():
            while True:
                if not exist_childtree():
                    log("子进程树已空，退出")
                    sys.exit()
                if should_exit:
                    log(f"因信号 {signal.Signals(should_exit_signum).name} (={should_exit_signum}) ，即将退出")
                    sys.exit()
                await asyncio.sleep(0.3)
        asyncio.run(loop())
    # 如果不是 unshare_pid 的 ,这里直接结束退出

safe_mntns_fd = None
def layer_run_subp(thislyr_cfg, cmdvec, child_no_caps=True, stdin=True, stdout=True, stderr=True, blocking=False):
    global safe_mntns_fd
    # 使用 socketpair 替代两个 pipe
    child_sock, parent_sock = socket.socketpair()

    pid = os.fork()
    if pid == 0: # 子进程
        set_loghead(f"{loghead}subp: ")
        parent_sock.close() # 关闭不需要的 socket 端
        if child_no_caps:
            if safe_mntns_fd is None :
                makesure_proc_safe('/proc', allow_newmntns=True)
            else:
                log('加入已有的安全mnt ns为新进程的运行做准备')
                os.setns(safe_mntns_fd, os.CLONE_NEWNS)

            drop_caps()
        child_sock.send(b'x') # 给父进程发送信号
        CHK( select.select([child_sock], [], [], 1.0) [0] , "子进程 等待 原进程 的回信，超时了") # 等待接收回信
        child_sock.recv(1) ; child_sock.close()

        # 关闭3以上的fd
        if child_no_caps: # 本来应该是判断 keepfds==False, 但用child_no_caps替代先了
            for fd in os.listdir('/proc/self/fd') :
                if int(fd) >=3 :
                    try:
                        os.close(int(fd))
                    except OSError as e:
                        if e.errno != 9: raise # 9 EBADF 错误表示可能已关闭 （Bad file descriptor），可忽略9错误

        log('准备启动（不降权）:' if not child_no_caps else '准备降权启动:' , cmdvec)

        # 去掉 stdin/out/err 中不需要的 （下面无法再log或print）
        devnull = os.open('/dev/null', os.O_RDWR)
        if not stdin:  os.dup2(devnull, 0)
        if not stdout: os.dup2(devnull, 1)
        if not stderr: os.dup2(devnull, 2)
        os.close(devnull)

        os.execvp(cmdvec[0], cmdvec)
        os._exit(123) # 正常不会到这里 , 不能用sys.exit, 否则会执行原进程的清理
    else: # 原进程
        child_sock.close() # 关闭不需要的 socket 端
        CHK( select.select([parent_sock], [], [], 2.0) [0] , "原进程 等待 子进程，超时了")
        parent_sock.recv(1) # 读取子进程的信号 (虽然值不重要，但为了同步)
        if safe_mntns_fd is None: safe_mntns_fd = os.open(f'/proc/{pid}/ns/mnt', os.O_RDONLY)
        parent_sock.send(b'x') ; parent_sock.close() # 回信给子进程

        if not blocking: # 非阻塞
            return pid
        else: # 阻塞
            _, status = os.waitpid(pid, 0)
            return status

    # os.execv('/bin/bash', ['/bin/bash', '--norc'])
    # os.exec*成功后不回来，替换了进程
        # l/v： 可变参 或 数组 来指定参数
        # p : 指定path
        # e : 指定环境变量，不继承父的环境。必须完整路径


def makesure_proc_safe(proc_path, allow_newmntns):
    # 删除了tmpfs覆盖/proc/1/fd 的代码，因为好像它自动会屏蔽
    make_proc_ro(proc_path, allow_newmntns=allow_newmntns)

def make_proc_ro(proc_path, allow_newmntns):
    if not os.statvfs(proc_path).f_flag&MS.RDONLY :
        if allow_newmntns :
            log('创建并进入新的安全mnt ns以为新进程的运行做准备')
            os.unshare(os.CLONE_NEWNS) # CLONE_NEWNS =unshare_mnt
        mount(None, proc_path, None, MS.REMOUNT|MS.RDONLY|mntflag_proc, None)

def cleanup_pidnsleader():
    if os.getpid() == 1:
        for i in range(10):
            if not exist_childtree():
                break
            os.kill(-1, signal.SIGTERM)
            time.sleep(0.1)


# NOTE HUP < INT < TERM 退出强烈程度 # TODO SIGHUP 不一定要退出，由用户配置决定是否
EXIT_SIGNALS = [ signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGUSR1, signal.SIGUSR2, ]
should_exit = False
should_exit_signum = None
def signals_handler(signum, frame):
    # NOTE 不能print 不能sleep 不能sys.exit 只能 os._exit
    global should_exit, should_exit_signum
    if signum in EXIT_SIGNALS:
        should_exit = True ; should_exit_signum = signum
    elif signum == signal.SIGCHLD:
        while True:
            try:
                # -1 表示等待任意子进程 # os.WNOHANG 表示非阻塞：如果没有可回收的子进程，立即返回 (0, 0)
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    break  # 没有进程退出, 可能是子进程被暂停（STOP）触发的SIGCHLD，我们忽略它，也可能已经处理完了僵尸
            except ChildProcessError:
                should_exit = True ; should_exit_signum = signal.SIGCHLD
                os._exit(0)
                break


def exist_childtree():
    try:
        pid, status = os.waitpid(-1, os.WNOHANG)
        return True
    except ChildProcessError:
        return False

# os.waitpid(-1, os.WNOHANG) 的结果说明：
#     (child_pid, exit_status)	成功回收一个僵尸进程
#     (0, 0)	无僵尸可回收，但子进程仍存在
#     抛出 ChildProcessError（继承自 OSError	errno = ECHILD（No child processes） 值通常为 10 ）

# def exist_other_procs():
#     for entry in os.listdir('/proc'):
#         if entry.isdigit() and int(entry) != os.getpid():
#             return True
#     return False




ps1 = ">"
def set_ps1(si, thislyr_cfg, status):
    global ps1
    ps1 = ''.join( [
        r'''$(LEC=$? ; if [[ $LEC -ne 0 ]]; then echo -n '\[\e[0;91m\]' ; else echo -n '\[\e[0;94m\]' ; fi ; printf "(%3d)" $LEC ; echo -n '\[\e[0m\]' ) \[\e[1;93m\]'''
        ,
        f'{si.sandbox_name} {thislyr_cfg.layer_name} {status}',
        r''' | \w > \[\e[0m\]'''
    ])
    os.environ['PS1'] = ps1

def build_thislyr_fs(si, thislyr_cfg):
    # 无论本层是否设置了变根，都调用这个函数
    # 操作目标的基 可能是 '/' （不变根的话） ,  也可能是新根路径 （变根的话）
    fsPlans = gen_fsPlans_by_lyrcfg(si, thislyr_cfg)
    remountPlans = commit_thislyr_fsPlans(si, thislyr_cfg, fsPlans)
    commit_remounts(remountPlans)


def commit_thislyr_fsPlans(si, thislyr_cfg, fsPlans): # 这个函数是本层为本层调用的
    target_fs_path = thislyr_cfg.newrootfs_path
    # log(f'准备实际建立(挂载、创建)本层的文件系统，以此作根： {target_fs_path}')
    remountPlans = []
    def z(rmtItem):
        remountPlans.append(rmtItem)

    mkdirp(target_fs_path)
    if napath(target_fs_path) != '/':
        mount("tmpfs", target_fs_path, "tmpfs", mntflag_newrootfs, None)
        mount(None, target_fs_path, None, MS.REC | MS.SLAVE, None)
        # # 用了slave它还是private,不知原因
    mkdirp(f'{target_fs_path}/proc') # proc不在这里做，预留个目录

    for pItem in fsPlans:
        plan = pItem.plan
        src = pItem.src
        dest = pItem.dest
        real_dest = napath(f'{target_fs_path}/{dest}')
        if plan in ['same', 'rosame', 'bind', 'robind'] :
            CHK( os.path.lexists(src) , f"来源{src}不存在")
            if plan in ['bind', 'robind'] :
                src = rslvy(src)
            RO = True if plan in ['rosame', 'robind'] else False
            if Path(src).is_symlink(): # 软链 (一定要把 symlink 放在最先判断)
                symlink(Path(src).readlink(), real_dest)
                # TODO chroot 前后对symlink做一致性检查
            elif Path(src).is_dir(): # 文件夹
                mkdirp(real_dest)
                mount(src, real_dest, None, mntflag_binddir, None)
                if RO : z(d(dirpath=real_dest, flag=mntflag_binddir ))
            elif (Path(src).is_file() \
                or Path(src).is_char_device() \
                or Path(src).is_block_device() ) :
                # 普通文件可以这这样。猜测 字符设备、块设备 也可以当普通文件一样处理
                make_file_exist(real_dest)
                mount(src,  real_dest, None, MS.BIND, None)
                mount(None, real_dest, None, MS.REMOUNT|MS.BIND|MS.RDONLY, None) if RO else None
            elif Path(src).is_socket(): # 已知socket不能remount成ro
                make_file_exist(real_dest)
                mount(src,  real_dest, None, MS.BIND|MS.RDONLY, None)
            else:
                raise_exit(f"原路径{src}所属文件类型暂未实现处理方式")
        elif plan in ['tmpfs', 'rotmpfs']:
            RO = True if plan == 'rotmpfs' else False
            mkdirp(real_dest)
            flag = pItem.flag or mntflag_tmpfs
            mount('tmpfs', real_dest, 'tmpfs', flag , None)
            if RO : z(d(dirpath=real_dest, flag=flag))
        elif plan == 'dir':
            mkdirp(real_dest)
        elif plan == 'any-exist': #如果已存在，无论是文件/目录/软链都可以，不存在就建个空文件
            if not os.path.lexists(real_dest):
                make_file_exist(real_dest)
        elif plan in ['file', 'rofile'] :
            # NOTE 无论何种情况，都不要对目标文件做写入，而是创建个临时文件去“挂载覆盖”。
            # 记得永远不要写入目标文件，防止覆盖用户文件
            RO = True if plan == 'rofile' else False
            with tempfile.NamedTemporaryFile( dir=f'{thislyr_cfg.sbxdir_path0}/temp', mode='w', delete=False) as f:
                f.write(pItem.content)
                os.chmod(f.name, 0o444) if RO else None
                os.chmod(f.name, pItem.destmode) if pItem.destmode else None
                make_file_exist(real_dest)
                mount(f.name, real_dest, None, MS.BIND, None)
                mount(None,   real_dest, None, MS.REMOUNT|MS.BIND|MS.RDONLY, None) if RO else None
        elif plan == 'symlink':
            symlink(pItem.linkto, real_dest)
            # TODO chroot 前后对symlink做一致性检查
        elif plan == 'empty-if-exist' : # TODO landlock 优先
            if not os.path.lexists(real_dest): continue
            optn='mode=0000'
            if Path(real_dest).is_symlink(): # 软链 (一定要把 symlink 放在最先判断)
                raise_exit(f"要保证为空的路径{real_dest}所属文件类型为symlink，暂未实现处理方式")
            elif Path(real_dest).is_dir(): # 文件夹
                mount('tmpfs', real_dest, 'tmpfs', MS.RDONLY|MS.NODEV|MS.NOEXEC|MS.NOSUID, optn)
            elif Path(real_dest).is_char_device() or Path(real_dest).is_block_device(): # 设备文件
                mount('/dev/null', real_dest,  None, MS.BIND|MS.RDONLY, optn)
                mount(None, real_dest,  None, MS.REMOUNT|MS.BIND|MS.RDONLY, optn)
            else: # 普通文件、socket, fifo
                mount(f'{thislyr_cfg.sbxdir_path0}/empty', real_dest,  None, MS.BIND|MS.RDONLY, optn)
                mount(None, real_dest,  None, MS.REMOUNT|MS.BIND|MS.RDONLY, optn)
        elif plan == 'sbxdir-in-newrootfs':
            CHK(dest == '/sbxdir', "sbxdir-in-newrootfs的dest必须为/sbxdir")
            make_mnt_fill_sbxdir(si, thislyr_cfg, call_at_buildfs=True)
        elif plan == 'devpts':
            mkdirp(real_dest)
            mount('devpts', real_dest, 'devpts', MS.NOEXEC|MS.NOSUID, 'mode=0666,ptmxmode=0666,newinstance')
        elif plan == 'appimg-mount':
            mkdirp(real_dest)
            src = rslvy(src)
            offset = get_appimg_sqoffset(src)
            # TODO 先做symlink链接到真实appimage文件路径，再调用 squashfuse命令
            run_a_cmd(['squashfuse', '-o', f'ro,offset={offset}', src, real_dest])
        elif plan == 'remountro':
            z(d(dirpath=real_dest, flag=pItem.flag or 0))
        else:
            raise_exit(f"无法识别的fsPlan条目 {pItem}")

    return remountPlans

def gen_fsPlans_by_lyrcfg(si, lyr_cfg): # 把fs里面的batch_plan都转成plan,并去重、排序
    fsPlans = []
    def a(stepobj):
        fsPlans.append(stepobj)

    for pItem in lyr_cfg.fs:
        # 一个 pItem 里， batch_plan 和 plan 只应该出现其中一种
        batch_plan = pItem.batch_plan # 预设的多个plan的集合
        plan = pItem.plan # 一个plan
        if batch_plan == 'dup-rootfs': # 把前一个rootfs复制到子层。包含dev
            destbase = pItem.destbase or '/'
            srcbase = pItem.srcbase or '/'
            CHK( destbase in ['/', '/zrootfs'], "dup-rootfs要求destbase必须为'/'或'/zrootfs'")
            CHK( srcbase in ['/', '/zrootfs'],  "dup-rootfs要求srcbase 必须为'/'或'/zrootfs'")
            if destbase != '/':
                a( d( plan='rotmpfs', dest=destbase , flag=mntflag_newrootfs) )
            for x in os.listdir(srcbase):
                if x in [ 'proc', 'sbxdir', 'zrootfs', ]: continue
                a( d( plan='same', dest=napath(f'{destbase}/{x}') , src=napath(f'{srcbase}/{x}') ) )
            a( d( plan='tmpfs', dest=napath(f'{destbase}/run/tmux') ) ) # 按理说，使用 dup-rootfs 的层本来不应该运行任何程序（因为uid=0)，但可能会用 tmux 当内外通信工具，先预留这个，并且要与host中的 /run/tmux 不同
        elif batch_plan == 'sbxdir-in-newrootfs':
            a( d({'plan': dict.pop(pItem, 'batch_plan'), **pItem} ) )
        elif batch_plan == 'basic-dev':
            # 最小 /dev 集合。把常用设备结点从宿主机 bind 进来；并为 shm 提供 tmpfs
            a( d( plan='rotmpfs', dest='/dev' ) )
            basic_devs = [ 'null', 'zero', 'full', 'urandom', 'random', 'tty', 'console', ]
            for dname in basic_devs:
                a( d( plan='same', dest=f'/dev/{dname}', src=f'/dev/{dname}' ) ) # 不能ro对单个具体设备？
            a( d( plan='devpts',  dest='/dev/pts') )
            a( d( plan='symlink', dest='/dev/ptmx', linkto='pts/ptmx' ) )
            a( d( plan='symlink', dest='/dev/fd',     linkto='/proc/self/fd' ) )
            a( d( plan='symlink', dest='/dev/stdin',  linkto='/proc/self/fd/0' ) )
            a( d( plan='symlink', dest='/dev/stdout', linkto='/proc/self/fd/1' ) )
            a( d( plan='symlink', dest='/dev/stderr', linkto='/proc/self/fd/2' ) )
            a( d( plan='symlink', dest='/dev/core',   linkto='/proc/kcore' ) )
            a( d( plan='tmpfs', dest='/dev/shm' ) )
        elif batch_plan == 'container-rootfs':
            # 只读挂载的重要系统路径
            paths_to_rosame = [ '/bin', '/sbin', '/usr', '/lib64', '/lib', '/etc',
                '/var/lib/ca-certificates', '/var/lib/dbus', '/var/cache/fontconfig' , ]
            for p in paths_to_rosame:
                a( d( plan='rosame', dest=p, src=p ) )
            # 需要 tmpfs 的可写路径（容器内部用）
            paths_to_tmpfs = [ '/run', '/tmp', '/root', '/mnt',
                '/var', '/var/lib', '/var/cache', f'/run/user/{si.uid}', '/run/user/0', '/run/lock',
                '/run/tmux' , f'{si.HOME}' , f'{si.HOME}/.cache' ]
            for p in paths_to_tmpfs:
                a( d( plan='tmpfs', dest=p ) )
            a( d( plan='symlink', dest='/var/run', linkto='/run' ) )
            a( d( plan='symlink', dest='/var/lock', linkto='/run/lock' ) )
        elif batch_plan == 'mask-privacy':
            destbase = pItem.destbase
            CHK( destbase in ['/', '/zrootfs'], "mask-privacy要求destbase必须为'/'或'/zrootfs'")
            path_maskfile = f'{si.HOME}/.config/bblsandbox/paths_never_access.txt'
            maskfile = Path(path_maskfile)
            paths_to_mask = maskfile.read_text().splitlines() if maskfile.exists() else []
            paths_to_mask = [path.strip() for path in paths_to_mask if path.strip()]
            log(f'从{path_maskfile}读出{len(paths_to_mask)}个路径要屏蔽')
            for path in paths_to_mask:
                CHK( path.startswith('/'), "paths_never_access.txt中有不是以'/'的条目")
                path = napath(path)
                if os.path.lexists(path):
                    a( d( plan='empty-if-exist', dest=napath(f'{destbase}/{path}' ) ) )

        # 下面是 plan 而不是 batch_plan 。因为它们两个不应同时有，所以用同一if树
        elif plan:
            a( pItem )
        else:
            raise_exit(f"无法识别的fs条目 {pItem}")

    for pItem in fsPlans:
        if pItem.SDS:
            if   pItem.src and not pItem.dest: pItem.dest = pItem.src
            elif pItem.dest and not pItem.src: pItem.src = pItem.dest
            elif not pItem.src and not pItem.dest:        raise_exit(f"{pItem} 既无 src 也无 dest")
            elif napath(pItem.src) != napath(pItem.dest): raise_exit(f"{pItem}设置了SDS，但src与dest不一致")
            del pItem.SDS
    fsPlans = [d({'plan': dict.pop(pItem, 'plan'), **pItem}) for pItem in fsPlans]

    # 查找移除重复的dest
    def find_dup_dest():
        used_dest = set()
        for i in reversed(range(0, len(fsPlans))):
            pItem = fsPlans[i]
            if pItem.dest in used_dest:
                log(f"因dest重复(={pItem.dest})，移除{pItem}")
                fsPlans[i] = d(removed=True)
            used_dest.add(pItem.dest)
    # TODO 分为 普通、remount、overlay 几个组来去重
    find_dup_dest()
    fsPlans = [pItem for pItem in fsPlans if not pItem.removed]

    # 排序 fsPlans
    fsPlans = sorted(fsPlans, key=lambda pItem: napath(pItem['dest']).split(os.sep) )
    fsPlans = sorted(fsPlans, key=lambda x: 0 if (isinstance(x, dict) and x.get('plan') == 'sbxdir-in-newrootfs') else 1)

    # [log(pItem) for pItem in fsPlans] # debug
    return fsPlans

def commit_remounts(remntPlans):
    for rItem in remntPlans:
        # log('ro-remounting: ' , rItem) # debug
        dirpath = rItem.dirpath
        flag = rItem.flag or 0
        flag |= os.statvfs(dirpath).f_flag & (MS.NODEV|MS.NOSUID|MS.NOEXEC)
        mount(None, dirpath, None, MS.REMOUNT|MS.RDONLY|flag, None)


def gen_unshareflag_by_lyrcfg(ly_cfg):
    unshare_flag = 0
    unshare_flag |= os.CLONE_NEWPID if ly_cfg.unshare_pid else 0
    unshare_flag |= os.CLONE_NEWNS if ly_cfg.unshare_mnt else 0
    unshare_flag |= os.CLONE_NEWUSER if ly_cfg.unshare_user else 0
    unshare_flag |= os.CLONE_FS if ly_cfg.unshare_chdir else 0
    unshare_flag |= os.CLONE_FILES if ly_cfg.unshare_fd else 0
    unshare_flag |= os.CLONE_NEWCGROUP if ly_cfg.unshare_cg else 0
    unshare_flag |= os.CLONE_NEWIPC if ly_cfg.unshare_ipc else 0
    unshare_flag |= os.CLONE_NEWTIME if ly_cfg.unshare_time else 0
    unshare_flag |= os.CLONE_NEWUTS if ly_cfg.unshare_uts else 0
    unshare_flag |= os.CLONE_NEWNET if ly_cfg.unshare_net else 0
    return unshare_flag

def safe_copy_script(copy_target_path):
    old_content = open(scriptfilepath).read()

    lines_arr = old_content.splitlines()

    start_marker = "# === HIDE_FOR_SUBLAYERS BEGIN ==="
    end_marker =   "# === HIDE_FOR_SUBLAYERS END ==="
    removed_mark = "# === HIDDEN_PART ==="

    start_index = None
    end_index = None

    for i, line in enumerate(lines_arr):
        if line.startswith(removed_mark):
            make_file_exist(copy_target_path)
            os.chmod(copy_target_path, 0o444)
            mount(scriptfilepath, copy_target_path, None, MS.BIND|MS.RDONLY, None)
            mount(None, copy_target_path, None, MS.REMOUNT|MS.BIND|MS.RDONLY, None)
            return
        if line.startswith(start_marker):
            start_index = i
        elif line.startswith(end_marker):
            end_index = i
        if start_index is not None and end_index is not None:
            break
    if start_index is None: raise_exit(f"找不到 userconfig 的开始标记 '{start_marker}'")
    if end_index is None: raise_exit(f"找不到 userconfig 的结束标记 '{end_marker}'")
    if not (start_index < end_index): raise_exit("userconfig 的开始和结束标记顺序不正确")

    # 将范围内的所有行（包括开始和结束标记行）设置为空字符串
    lines_arr[start_index] = removed_mark
    lines_arr[start_index + 1 : end_index + 1] = [""] * (end_index - start_index)
    script_content_safe = '\n'.join(lines_arr)
    Path(copy_target_path).write_text(script_content_safe)
    os.chmod(copy_target_path, 0o444)



def cleanup_outest(si):
    print(f"{scriptname} 正在执行清理...")
    # NOTE 不要对那些可能挂载的目录用递归删除!  # 要删除那种目录的话只能用 rmdir （只删空的目录）
    # 因为有挂载，递归删除可能会误删重要文件。危险！ # 例如:
        # new.*.rootfs/
        # apps/*/
    paths_rm_sub_files = [ #准备删这些目录的一级子文件和目录本身
        f'{si.outest_sbxdir}/cfg',
        f'{si.outest_sbxdir}/temp',
        f'{si.outest_sbxdir}/apps',
        *glob.glob(f'{si.outest_sbxdir}/new.*.rootfs'),
        f'{si.outest_sbxdir}',
    ]
    for dirpath in paths_rm_sub_files:
        for f in Path(dirpath).iterdir():
            if f.is_file() :
                try:
                    f.unlink()
                except:
                    pass
        try:
            os.rmdir(dirpath)
        except:
            pass

#==========================================
#======= libc 工具函数 =========================
libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)

MS = types.SimpleNamespace(RDONLY=0x01, NOSUID=0x02, NODEV=0x04, NOEXEC=0x08,  REMOUNT=0x20, NOSYMFOLLOW=0x100, BIND=0x1000, MOVE=0x2000, REC=0x4000,  UNBINDABLE=1<<17, PRIVATE=1<<18, SLAVE=1<<19, SHARED=1<<20, )
def mount(source, target, fstype, flags, data): # source可能空, 或为tmpfs或proc， target一定有
    allowed_nonabs = ['tmpfs', 'proc', 'devpts']
    if not ( (source is None) or (source in allowed_nonabs) or (source.startswith('/')) ):
        raise_exit(f"mount的来源{source}不是绝对路径，且不在允许的{allowed_nonabs}之内")
    if isinstance(source, str):
        source = napath(source) if source.startswith('/') else source
    target = napath(target)
    if source and source.startswith('/') and rslvy(source) != source:
        raise_exit(f"挂载来源路径{source}或其某级父路径当前是个symlink。暂未实现对这种情况的处理方式")
    if rslvy(target) != target:
        raise_exit(f"挂载目标路径{target}或其某级父路径当前是个symlink。暂未实现对这种情况的处理方式")
    # log(f"执行挂载 {source} --> {target}")
    ret = libc.mount(
        source.encode() if source else None,
        target.encode(),
        fstype.encode() if fstype else None,
        flags,
        data.encode() if data else None
    )
    if ret != 0:
        log(f"挂载时发生错误 {source} -> {target} | {fstype=} {flags=} {data=}")
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno), target)

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

def pivot_root(new_root, put_old):
    res = libc.pivot_root(ctypes.c_char_p(new_root.encode()), ctypes.c_char_p(put_old.encode()))
    if res != 0:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno))

def drop_caps():
    PR_SET_NO_NEW_PRIVS = 38
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
        log(f"清除能力集 {eff=} {prm=} {inh=}", (ret, errno, errstr)) if doprint else None
        return (ret, errno, errstr)

    def amb_clear(doprint=False):
        ret = libc.prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL, 0, 0, 0)
        errno = ctypes.get_errno() if ret != 0 else None
        errstr = os.strerror(errno) if ret != 0 else None
        log('清除amb', (ret, errno, errstr)) if doprint else None
        return (ret, errno, errstr)

    def bnd_clear(maxid, doprint=False):
        results = []
        for cap_id in range(maxid + 1):
            ret = libc.prctl(PR_CAPBSET_DROP, cap_id, 0, 0, 0)
            errno = ctypes.get_errno() if ret != 0 else None
            errstr = os.strerror(errno) if ret != 0 else None
            results.append((ret, errno, errstr))
        log('清除bnd', results) if doprint else None
        return results

    def set_nonewpriv(doprint=False):
        ret = libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
        errno = ctypes.get_errno() if ret != 0 else None
        errstr = os.strerror(errno) if ret != 0 else None
        log('设置noNewPriv', (ret, errno, errstr)) if doprint else None
        return (ret, errno, errstr)

    BND_MAX = int(Path('/proc/sys/kernel/cap_last_cap').read_text())

    show_clear_result = False
    log('降权前', get_caps_dict()) if show_clear_result else None
    capset_clear(eff=False , prm=True, inh=True,  doprint=show_clear_result)
    log('清除中', get_caps_dict()) if show_clear_result else None
    amb_clear(doprint=show_clear_result)
    log('清除中', get_caps_dict()) if show_clear_result else None
    set_nonewpriv(doprint=show_clear_result)
    log('清除中', get_caps_dict()) if show_clear_result else None
    bnd_clear(BND_MAX,  doprint=show_clear_result)
    log('清除中', get_caps_dict()) if show_clear_result else None
    capset_clear(eff=True, prm=True, inh=True,  doprint=show_clear_result)
    log('降权后', get_caps_dict()) if show_clear_result else None

    # ------验证------------

    # 验证 /proc/self/status 中所有能力字段为 0
    caps_dict = get_caps_dict()
    CHK( caps_dict.pop('NoNewPrivs') == '1' , "在/proc里显示NoNewPrivs未成功设置" )
    for k,v in caps_dict.items(): CHK( re.search(rf"^0+$", v), f"在/proc里显示未清除 {k} ")

    # libc验证 no_new_privs
    CHK( libc.prctl(PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0) == 1, 'noNewPrivs清除验证失败')
    # libc验证 bounding set
    for cap_id in range(BND_MAX +1): # 内核只支持0~40
        CHK( libc.prctl(PR_CAPBSET_READ, cap_id, 0, 0, 0) == 0, f'cap_id {cap_id} 降权失败')



def set_pdeathsig(): # 由layer1的fork出来的子进程调用
    PR_SET_PDEATHSIG = 1
    libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM)

#============================

def mkdirp(dirpath):
    os.makedirs(dirpath, exist_ok=True)

def napath(pstr):
    pstr = str(pstr)
    if not str(pstr.startswith('/')): raise_exit(f"不是绝对路径： {pstr}")
    return  ''.join( [ '/' , os.path.normpath(pstr).strip('/') ] )

def make_file_exist(path): # 路径不能已有目录
    if Path(path).is_dir(): raise_exit(f"{path}已是文件夹")
    if not os.path.exists(path):
        mkdirp(Path(path).parent)
        Path(path).touch()

def symlink(linkto, dest):  # linkto：要创建的软链的指向 .  dest: 在哪个位置创建软链。
    if Path(dest).is_symlink() and Path(dest).readlink() == linkto: return
    mkdirp(Path(dest).parent)
    os.symlink(linkto, dest)

def which_and_resolve_exist(cmd):
    path = shutil.which(cmd)
    if not path:
        return None
    try:
        return rslvy(path)
    except FileNotFoundError:
        return None

def rslvn(path):
    return str(Path(napath(path)).resolve(strict=False))

def rslvy(path):
    return str(Path(napath(path)).resolve(strict=True))

def padir(path):
    if napath(path) == '/': raise_exit(f"{path}已是根路径，无法再取得上级目录")
    return str(Path(path).parent)

def run_a_cmd(cmdv):
    prc = subprocess.Popen(cmdv,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, bufsize=1, universal_newlines=True
                         )
    prc.wait()
    if prc.returncode != 0: raise_exit(f"命令运行未成功（{prc.returncode}）")

def is_unix_socket_listened(sock_path):
    if not os.path.exists(sock_path):
        return False
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(sock_path)
        sock.close()
        return True
    except (FileNotFoundError, ConnectionRefusedError):
        sock.close()
        return False
    finally:
        sock.close()

class FileContent:
    def __init__(self, data):
        if isinstance(data, (list, dict)):
            self._content = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            self._content = str(data)
        self._size_bytes = len(self._content.encode('utf-8'))
    def __str__(self):
        return f"<FileContent size={self._size_bytes}>"
    def __repr__(self):
        return self.__str__()


class EnhancedFalse:
    def __str__(self):
        raise Exception(loghead + "脚本试图字符串化一个不存在的成员")
    def __repr__(self):
        raise Exception(loghead + "脚本试图字符串化一个不存在的成员")
    def __bool__(self):
        return False

FALSE = EnhancedFalse()


class EnhancedDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, value in self.items():
            if isinstance(value, dict) and not isinstance(value, EnhancedDict):
                self[key] = EnhancedDict(value)
            elif isinstance(value, list):
                self[key] = self._convert_list(value)
    def _convert_list(self, lst):
        new_list = []
        for item in lst:
            if isinstance(item, dict) and not isinstance(item, EnhancedDict):
                new_list.append(EnhancedDict(item))
            elif isinstance(item, list):
                new_list.append(self._convert_list(item))
            else:
                new_list.append(item)
        return new_list
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        try:
            return self[name]
        except KeyError:
            # 如果键不存在，则返回 我们自定义的
            return FALSE
    def __setattr__(self, name, value):
        self[name] = value
    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            pass
    def __setitem__(self, key, value):
        processed_value = value
        if isinstance(value, dict) and not isinstance(value, EnhancedDict):
            processed_value = EnhancedDict(value)
        elif isinstance(value, list):
             processed_value = self._convert_list(value)
        super().__setitem__(key, processed_value)
d = EnhancedDict

loghead = ''
def set_loghead(new_loghead):
    global loghead
    loghead = new_loghead
def log(*args, **kwargs):
    new_args = args
    if loghead:
        new_args = ( loghead,  *args)
    print(*new_args, **kwargs)

def raise_exit(err_msg):
    raise Exception( loghead + err_msg)
    sys.exit(1)

def CHK( condition, errmsg='某项检查失败'):
    if not condition:
        raise_exit(errmsg)

ASK_OPEN='''\
#!/bin/bash

PARAS="$@"

TEXT="是否复制以下内容？"
if [[ "$PARAS" ]] ; then
    TEXT="$TEXT\n$PARAS"
fi

kdialog --yesnocancel "$TEXT"
DIALOG_R=$?

if [[ $DIALOG_R -eq 0 ]]; then
    echo "$PARAS" | xclip -i /dev/stdin  -selection clipboard
fi

EXITCODE=$DIALOG_R
[[ $DIALOG_R -eq 2 ]] && EXITCODE=0
exit $EXITCODE
'''

def get_appimg_sqoffset(appimg_path):
    elfHeader = open(appimg_path, 'rb').read(64)
    (bitness,endianness) = struct.unpack("4x B B 58x", elfHeader);
    (shoff,shentsize,shnum) = struct.unpack(
        (">" if endianness == 2 else "<") +
        ("40x Q 10x H H 2x" if bitness == 2 else "32x L 10x H H 14x"),
        elfHeader
    );
    return (shoff + shentsize * shnum)

#=====================================================
# 常量
PTMP = '/tmp/sbxs' # 不同沙箱实例共用的 主临时目录

if __name__ == "__main__":
    # 获得调用py脚本的文件位置信息，一般仅用于顶层得多，子容器内用得少
    scriptfilepath = os.path.abspath(__file__)
    scriptdirpath = os.path.dirname(scriptfilepath)  # 获取脚本所在目录
    scriptdirname = os.path.basename(scriptdirpath) # 获取脚本所在目录名
    scriptname = os.path.basename(scriptfilepath)  # 获取脚本文件名（含扩展名）
    scriptnamenoext = os.path.splitext(scriptname)[0]  # 获取脚本文件名（不含扩展名）

    main()
