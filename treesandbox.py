#!/usr/bin/env -S python3 -I -B

# Tree Sandbox for Linux
# Licensed under GPL
# https://github.com/garywill

import os, sys, shutil, subprocess, pwd, grp, time, pty, ctypes, ctypes.util, atexit, json, copy, tempfile, struct, re, socket, signal, asyncio, datetime , types, select, fcntl, traceback, random , errno, shlex, enum, argparse
from pathlib import Path
from glob import glob

# === HIDE_FOR_SUBLAYERS BEGIN === NOTE: Don't change this line ===
# 普通用户设置这里
def userconfig(si): # 这个只在顶层解析一次
    uc = d()

    uc.sandbox_name='' # 沙箱名称

    # uc.reuseInstance=True # 复用正在运行的同种沙箱实例（即，单实例沙箱，否则为多实例沙箱）

    uc.apps = [
        d(cmdvec=['bash'], appname='bash'), # 第一个是默认app,可不设appname
    ]
    # 命令cmdvec是shell命令以空格分割成的数组
    # 启动沙箱时，可以用'--app <appname>'，也可以不用（选择默认app）

    uc.user_mnts = [
        # AppImage例子，挂载目标为沙箱内的 /sbxdir/apps/xxxx
        # d(batch_plan='appimage', dirname='xxxx', src=f'{si.startdir_on_host}/xxxx.AppImage'),

        # 用当前目录下的 fakehome 目录，作为沙箱内 HOME 的永久储存（否则tmpfs作HOME）
        # d(plan='bind', src=f'{si.startdir_on_host}/fakehome', dest=si.HOME),

        # HOME/bin
        d(plan='robind', src=f'{si.HOME}/bin', SDS=1),

        # HOME/.local/{bin,lib}
        d(plan='robind', src=f'{si.HOME}/.local/bin', SDS=1),
        d(plan='robind', src=f'{si.HOME}/.local/lib', SDS=1),

        # /home/linuxbrew
        # d(plan='robind', src='/home/linuxbrew', SDS=1),

    ]




    # 若不设置gui则内部无任何X11
    uc.gui="realX" # 使用真实的 X11
    # uc.gui="xephyr"
    # uc.gui="weston"

    # uc.newXId='50' # 使用内部隔离X11时，X11的显示编号，字符串。如果不指定，则随机

    uc.icewm = True if uc.gui in ['xephyr','weston'] else False
    uc.windowed_size = (1000, 600)

    uc.gpus     =      True if uc.gui else False
    uc.see_userfonts = True if uc.gui else False

    # uc.see_real_hw=True # 看见真实/dev和/sys



    # 输入法等通信需要dbus
    # uc.dbus_session="allow"
    # uc.dbus_session="filter" # 默认过滤规则:允许输入法和通知。还可以自己在 uc.dbusproxy_extra 中加
    if uc.gui: uc.dbus_session="filter"

    # uc.dbusproxy_extra = ['--see=org.gnome.Shell'] # xdg-dbus-proxy (flatpak) 的额外参数

    uc.net=d(
        iface='real', # 使用真实的网络介面
        # custom_dns=['127.0.0.1'], # 自定义dns (会改/etc/resolv.conf) ，如果不自定义，且iface为real则允许真实的resolv.conf
    )

    uc.sharedir_prefix='/tmp/tsbx-share_' # 在主机的这个位置以这个前缀创建临时共享目录，挂载到沙箱内的 同一路径 和 /tmp/share

    # uc.pulseaudio=True,
    # uc.cups=True, # CUPS打印服务 NOTE 注意 CUPS-PDF 沙箱内的输出位置是否已暴露给主机

    # uc.allow_opt=True # 允许访问真实/opt
    uc.mask_xdg_opens=True # 容器内部不能使用xdg-open, firefox, chromium 等
    # uc.mask_osrelease=True # 不可访问/etc/os-release
    uc.machineid='zero' # 把/etc/machine-id填0

    uc.setenvs = d( # 要给 主app 的环境变量 ，值必须是字符串
        # ENV_VAR_NAME1 = 'ENV_VAR_VAL1',
        # ENV_VAR_NAME2 = 'ENV_VAR_VAL2',
    )

    return uc

# layer1 产生。 所有的layer_cfg都在 layer1 下
def gen_layer1(si, uc, dyncfg): # 这个只在顶层解析一次
    # 第1层不跑任何程序，只用于PID隔离，和退出时的清理工作
    return d(
        layer_name='layer1', # 默认模板的 layer_name 不要修改
        unshare_pid=True, # 第1层必须
        unshare_mnt=True, # 第1层尝试有unshare mnt但不newrootfs

        # uid 变 0
        unshare_user=True, uid_map_as_root=True,
        # 准备开始第2层。这第1层的 sublayers 数组应该只有一个元素，即，第2层只有一个容器
        sublayers = [gen_layer2(si, uc, dyncfg)],
    )

def gen_layer2(si, uc, dyncfg):
    return d(
        layer_name='layer2', # 默认模板的 layer_name 不要修改
        unshare_mnt=True,
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

            d(plan='bind', src=os.getenv('DBUS_SESSION_BUS_ADDRESS').removeprefix('unix:path='), SDS=1 ),

            d(batch_plan='dup-rootfs', destbase='/zrootfs'), # 排除/proc。不加ro。
            d(batch_plan='mask-privacy', destbase='/zrootfs'),
            d(plan='empty-if-exist', dest=f'/zrootfs/{si.PTMP}'),
        ],
        envs_unset=[
            "SYSTEMD_EXEC_PID", "MANAGERPID", "SSH_AGENT_PID", "SSH_AUTH_SOCK",  "WINDOWMANAGER", "SHELL_SESSION_ID", "INVOCATION_ID", "GPG_TTY", "XDG_SESSION_ID", "KONSOLE_DBUS_SERVICE", "GPG_AGENT_INFO", "OLDPWD", "WINDOWID", "SESSION_MANAGER", "JOURNAL_STREAM",  "XDG_CACHE_HOME",
        ],

        sublayers = [
            gen_layer2c(si, uc, dyncfg),
            gen_layer2z(si, uc, dyncfg),
        ],
    )

def gen_layer2c(si, uc, dyncfg):
    # layer2c实际上深度为3, 这层是为了运行可信程序如 xpra client , dbus proxy 等
    return d(
        layer_name='layer2c', unshare_pid=True, unshare_mnt=True,
        # uid 变回 1000
        unshare_user=True, uid_map_as_user=True,

        newrootfs=True,
        fs=[
            d(batch_plan='dup-rootfs', destbase='/'),
            d(batch_plan='sbxdir-in-newrootfs', dest='/sbxdir'),
        ],
        subprocs=[
            d( cmdvec=["Xephyr",  f":{si.newXId}",  "-resizeable",  "-ac",  *dyncfg.xephyr_extra_args] , subp_name='xephyr') if uc.gui=='xephyr' else None,
            d( cmdvec=["weston", f"--socket=wayland-{si.newXId}" ,  f"--shell=kiosk", *dyncfg.weston_extra_args] , subp_name='weston') if uc.gui=='weston' else None,
            d( cmdvec=['xdg-dbus-proxy', *dyncfg.dbusproxy_argv], subp_name='dbusproxy') if uc.dbus_session=='filter' else None,
        ],
    )

def gen_layer2z(si, uc, dyncfg):
    return d( # layer2z 作为 layer2和3之间，把layer2的/zrootfs变回真/，准备让layer3接
        layer_name='layer2z',  unshare_mnt=True,
        start_after=[
            d(waittype='socket-listened', path='/tmp/dbusproxy.socket') if uc.dbus_session=='filter' else None,
            d(waittype='socket-listened', path=f'/tmp/.X11-unix/X{si.newXId}') if uc.gui=='xephyr' else None,
            d(waittype='socket-listened', path=f'{os.getenv("XDG_RUNTIME_DIR")}/wayland-{si.newXId}') if uc.gui=='weston' else None,
        ],
        newrootfs=True,
        fs=[
            d(batch_plan='dup-rootfs', srcbase='/zrootfs'),
            d(batch_plan='sbxdir-in-newrootfs', dest='/sbxdir'),

            d(plan='robind', src=f'/tmp/.X11-unix/X{si.newXId}', dest=f'/sbxdir/temp/X{si.newXId}') if uc.gui=='xephyr' else None,
            d(plan='robind', src=f'{os.getenv("XDG_RUNTIME_DIR")}/wayland-{si.newXId}', dest=f'/sbxdir/temp/wayland-{si.newXId}') if uc.gui=='weston' else None,
            d(plan='robind', src='/tmp/dbusproxy.socket', dest='/sbxdir/temp/dbusproxy.socket') if uc.dbus_session=='filter' else None,
        ],
        sublayers=[ gen_layer3(si, uc, dyncfg) ],
    )

def gen_layer3(si, uc, dyncfg):
    return d(
        layer_name='layer3', # 默认模板的 layer_name 不要修改
        unshare_mnt=True,
        unshare_cgroup=True,
        unshare_ipc=True,
        unshare_time=True,
        unshare_uts=True,

        unshare_net=True if uc.net.iface != 'real' else False,

        newrootfs=True, # 有newrootfs则必须有fs
        fs=[ # fs全称fs_plans_for_new_rootfs 。
            d(batch_plan='container-rootfs'),  # 不包括 dev 。不包括 proc
            d(batch_plan='sbxdir-in-newrootfs', dest='/sbxdir'),
            d(plan='empty-if-exist', dest=rslvn(si.startscript_on_host)),

            # ---- 以上是不变条目 ----

            d(plan='robind', dest='/opt', src='/opt') if uc.allow_opt else None,

            d(batch_plan='basic-dev') if not uc.see_real_hw else None, # 创建新的容器最小的/dev

            d(plan='robind', src=f'/run/user/{si.uid}/pulse/native', SDS=1) if uc.pulseaudio else None,
            d(plan='robind', src=rslvy('/var/run/cups/cups.sock'), SDS=1) if uc.cups else None,

            *([
            d(plan='robind', dest='/dev', src='/dev'),
            d(plan='tmpfs',dest='/dev/shm'),
            d(plan='robind', dest='/sys', src='/sys'),
            ] if uc.see_real_hw else [] ),
            # TODO 1. 改用dyncfg  2. layer2里也加

            *([
            d(plan='robind', dest=f'/tmp/.X11-unix/X{os.getenv("DISPLAY").lstrip(":")}', SDS=1),
            d(plan='robind', dest='/tmp/xauthfile', src=f'{os.getenv("XAUTHORITY")}'),
            ] if uc.gui=='realX' else [] ),

            d(plan='robind', src=f'/sbxdir/temp/X{si.newXId}', dest=f'/tmp/.X11-unix/X{si.newXId}') if uc.gui=='xephyr' else None,
            d(plan='robind', src=f'/sbxdir/temp/wayland-{si.newXId}',  dest=f'{os.getenv("XDG_RUNTIME_DIR")}/wayland-{si.newXId}', ) if uc.gui=='weston' else None,

            *dyncfg.mnts_gui,

            d(plan='rofile', dest=shutil.which("xdg-open"), destmode=0o555, content=ASK_OPEN ) if uc.mask_xdg_opens else None,
            *[d(plan='empty-if-exist', dest=path) for path in dyncfg.paths_to_mask],

            d(plan='robind', dest='/tmp/dbus-session.socket',  src=os.getenv('DBUS_SESSION_BUS_ADDRESS').removeprefix('unix:path=')) if uc.dbus_session == 'allow' else None,
            d(plan='robind', dest='/tmp/dbus-session.socket', src='/sbxdir/temp/dbusproxy.socket') if uc.dbus_session=='filter' else None,

            d(plan='empty-if-exist', dest='/etc/fstab'),
            d(plan='empty-if-exist', dest='/etc/systemd'),
            d(plan='empty-if-exist', dest='/etc/init.d'),
            d(plan='empty-if-exist', dest=rslvn('/etc/os-release')) if uc.mask_osrelease else None,
            d(plan='rofile', dest='/etc/machine-id', content=dyncfg.machineid) if dyncfg.machineid else None,

            *dyncfg.mnts_dns,

            *([
            d(plan='rofile', dest=f'{si.HOME}/.icewm/preferences', content=ICEWM_PREF),
            d(plan='rofile', dest=f'{si.HOME}/.icewm/menu', content=''),
            d(plan='rofile', dest=f'{si.HOME}/.icewm/toolbar', content=''),
            ] if uc.icewm else [] ),

            *([
            d(plan='bind', src=si.sharedir_onhost, dest='/tmp/share'),
            d(plan='bind', src=si.sharedir_onhost, SDS=1),
            ] if si.sharedir_onhost else []),

            # NOTE 用户挂载要放最后
            *uc.user_mnts, # NOTE 用户挂载要放最后
            d(plan='remountro', dest='/sbxdir/apps', flag=mntflag_apps)
        ],
        envs_unset=[
            "ICEAUTHORITY", "XAUTHORITY", "DISPLAY", "WAYLAND_DISPLAY", "XAUTHLOCALHOSTNAME", "IBUS_ADDRESS", "DBUS_SESSION_BUS_ADDRESS", "DBUS_SYSTEM_BUS_ADDRESS",
        ],
        envset_grps=[
            d( DISPLAY=os.getenv("DISPLAY"), XAUTHORITY='/tmp/xauthfile', ) if uc.gui=='realX' else None,
            d(DISPLAY=f':{si.newXId}') if uc.gui in ['xephyr','weston'] else None,
            # d(WAYLAND_DISPLAY=f'wayland-{si.newXId}') if uc.gui=='weston' else None, # 先不要 WAYLAND_DISPLAY 这个环境变量，让应用都使用 Xwayland 先
            d(DBUS_SESSION_BUS_ADDRESS='unix:path=/tmp/dbus-session.socket') if uc.dbus_session else None,
        ],
        sublayers=[
            gen_layer4c(si, uc, dyncfg),
            gen_layer4d(si, uc, dyncfg),
            gen_layer4(si, uc, dyncfg),
        ],
    )

def gen_layer4c(si, uc, dyncfg):
    return d(
        layer_name='layer4c', # 默认模板的 layer_name 不要修改
        unshare_pid=True, unshare_mnt=True,

        # uid 变回 1000
        unshare_user=True, uid_map_as_user=True,

        start_after = [
            d(waittype='socket-listened', path=f'/tmp/.X11-unix/X{si.newXId}') if uc.gui=='weston' else None,
        ],

        subprocs=[
            d( cmdvec=["icewm"] , subp_name='icewm') if uc.icewm else None ,
        ],
    )

def gen_layer4d(si, uc, dyncfg):
    return d(
        layer_name='layer4d', # 默认模板的 layer_name 不要修改
        unshare_pid=True, unshare_mnt=True,

        # uid 变回 1000
        unshare_user=True, uid_map_as_user=True,

        subprocs=[
            d( cmdvec=['env', f'WAYLAND_DISPLAY=wayland-{si.newXId}', 'Xwayland', f':{si.newXId}', *dyncfg.xwayland_extra_args ] , subp_name='xwayland') if uc.gui=='weston' else None,
        ],
    )

def gen_layer4(si, uc, dyncfg):
    return d( # 主 用户app 在这里跑
        layer_name='layer4', # 默认模板的 layer_name 不要修改
        isMainLyr=True,  # 我是主app所在层
        unshare_pid=True, unshare_mnt=True,

        # uid 变回 1000
        unshare_user=True, uid_map_as_user=True,

        envset_grps = [uc.setenvs],

        start_after = [
            d(waittype='socket-listened', path=f'/tmp/.X11-unix/X{si.newXId}') if uc.gui=='weston' else None,
        ],
        # user_shell=True, # 调试用
        # dev_shell=True,  # 调试用
    )

def gen_dynamic_cfg(si, uc): # 这个只在顶层解析一次
    cmds_to_mask = []
    paths_to_mask = []
    mnts_dns = []
    xephyr_extra_args = []
    weston_extra_args = []
    xwayland_extra_args = []

    mnts_gui = [
        *([
        d(plan='robind', src=f'{si.HOME}/.fonts', SDS=1)      if os.path.lexists(f'{si.HOME}/.fonts') else None,
        d(plan='robind', src=f'{si.HOME}/.fonts.conf', SDS=1) if os.path.lexists(f'{si.HOME}/.fonts.conf') else None,
        d(plan='robind', src=f'{si.HOME}/.cache/fontconfig', SDS=1) if os.path.lexists(f'{si.HOME}/.cache/fontconfig') else None,
        ] if uc.see_userfonts else [] ),
        *([
        d(plan='rosame', src='/dev/dri', SDS=1),
        d(plan='rosame', src='/sys/class/drm', SDS=1),
        *[ d(plan='rosame', src=p, SDS=1)        for p in glob('/sys/dev/char/226:*') ],
        *[ d(plan='rosame', src=padir(p), SDS=1) for p in glob('/sys/devices/*/*/drm') ],
        *[ d(plan='rosame',  src=rslvy(f'{padir(p)}/driver'), SDS=1)  for p in glob('/sys/devices/*/*/drm') ],
        ] if uc.gpus else [] ),
    ]

    if uc.gui and uc.gui != 'realX': # 使用GUI但不是真实X, 说明是某种隔离的X,需要新的X编号
        def is_XId_available(newXId):
            if not os.path.lexists(f'/tmp/.X11-unix/X{newXId}')  \
            and not os.path.lexists(f'{os.getenv("XDG_RUNTIME_DIR")}/wayland-{newXId}')  \
            and not re.search(rf':{newXId}(?:\.|$)', os.getenv('DISPLAY')) \
            and not os.getenv('WAYLAND_DISPLAY') == f'wayland-{newXId}' \
            and not re.search(rf'\/tmp/\.X11-unix\/X{newXId}\b', Path('/proc/net/unix').read_text(), re.MULTILINE) :
                return True
            else: return False
        if uc.newXId:
            CHK( is_XId_available(uc.newXId), f"指定的显示编号 {uc.newXId=} 被占用")
            newXId = uc.newXId
        else:
            while (newXId := str(random.randrange(230, 980)) ) :
                if is_XId_available(newXId): break

    if uc.windowed_size:
        if uc.gui == 'xephyr':
            xephyr_extra_args = ['-screen', f'{uc.windowed_size[0]}x{uc.windowed_size[1]}']
        elif uc.gui == 'weston' :
            weston_extra_args = [f'--width={uc.windowed_size[0]}', f'--height={uc.windowed_size[1]}' ]
            xwayland_extra_args = ['-geometry', f'{uc.windowed_size[0]}x{uc.windowed_size[1]}']

    if uc.dbus_session == 'filter':
        dbusproxy_argv = [
            os.getenv('DBUS_SESSION_BUS_ADDRESS'), '/tmp/dbusproxy.socket', '--filter',
            '--talk=org.freedesktop.Notifications',
            '--talk=org.kde.StatusNotifierWatcher',
            '--talk=org.fcitx.*',
            '--talk=org.freedesktop.IBus.*',
            '--talk=org.freedesktop.portal.IBus',
            '--talk=org.freedesktop.portal.Fcitx',
            *(uc.dbusproxy_extra or [])]

    # 处理 /etc/resolv.conf
    CHK( Path('/var/run').is_symlink() and rslvn('/var/run') == '/run', "此Linux上，/var/run不是指向/run, 与现代发行版的习惯不同，暂时无法处理这种情况")
    RSLVCF_is_link = True if Path('/etc/resolv.conf').is_symlink() else False
    RSLVCF_is_file = is_file('/etc/resolv.conf')
    CHK(RSLVCF_is_link or RSLVCF_is_file, f'/etc/resolv.conf非链接非文件，暂时无法处理这种情况')
    dns_use_custom = isinstance(uc.net.custom_dns, list)
    if dns_use_custom: RSLVCF_content = ''.join([f'nameserver {ip}\n' for ip in uc.net.custom_dns])
    iface_use_real = uc.net.iface=='real'

    # link/file | custom/notcustom | ifacereal 共8种情况
    # TODO nscd
    if RSLVCF_is_file : # /etc/resolv.conf是文件，非链接
        if dns_use_custom:
            mnts_dns = [d(plan='rofile', content=RSLVCF_content, dest='/etc/resolv.conf')]
        else:
            if iface_use_real: mnts_dns = [] # 原本的/etc/resolv.conf文件保持
            else             : mnts_dns = [d(plan='empty-if-exist', dest='/etc/resolv.conf')] # 清空
    else: # /etc/resolv.conf是链接
        RSLVCF_target_dir = padir(rslvn('/etc/resolv.conf'))
        CHK(RSLVCF_target_dir.startswith('/run/'), f'/etc/resolv.conf的指向{rslvn('/etc/resolv.conf')}不是在/run/xxx/内，暂时无法处理这种情况（现代发行版一般/etc/resolv.conf -> /var/run/xxxx/ -> /run/xxxxx）')
        if dns_use_custom:
            mnts_dns = [d(plan='rofile', content=RSLVCF_content, dest=rslvn('/etc/resolv.conf'))]
        else:
            if iface_use_real: mnts_dns = [d(plan='robind', src=RSLVCF_target_dir, SDS=1)]
            else             : pass # 让/run/xxxxx/resolv.conf继续不存在

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

    dyncfg = d({k: v for k, v in locals().items()
            if k in ['newXId', 'paths_to_mask', 'machineid', 'mnts_gui', 'xephyr_extra_args', 'weston_extra_args', 'xwayland_extra_args', 'sharedir_onhost',
                     'dbusproxy_argv' , 'mnts_dns']})
    return dyncfg

# === HIDE_FOR_SUBLAYERS END === NOTE: Don't change this line ===

def recr_rm_empty_lyr(si, cfg):
    def _recr(si, cfg):
        # print(cfg.layer_name)
        have_rmed = False

        cnt_cmds_0 = len(cfg.subprocs or [] )
        cnt_sl_0 = len(cfg.sublayers or [] )
        if cfg.subprocs : cfg.subprocs = [cmd for cmd in cfg.subprocs if cmd is not None]
        if cfg.sublayers : cfg.sublayers = [sublyr for sublyr in cfg.sublayers if sublyr and not sublyr.disabled]
        cnt_cmds_1 = len(cfg.subprocs or [] )
        cnt_sl_1 = len(cfg.sublayers or [] )

        if cnt_cmds_0 != cnt_cmds_1 or cnt_sl_0 != cnt_sl_1:
            have_rmed = True
        for sublyr_cfg in (cfg.sublayers or [] ):
            if _recr(si, sublyr_cfg):
                have_rmed = True
        if not (cfg.sublayers or cfg.subprocs or cfg.user_shell or cfg.dev_shell or cfg.isMainLyr):
            # print('设置' , cfg.layer_name, '为disable')
            cfg.disabled = True
            have_rmed = True
        # print(have_rmed)
        return have_rmed
    while _recr(si, cfg): pass

def recursive_valid_lyrs(si, layer1_cfg):
    used_proc_names = []
    si.all_layers = []
    def _recr(cfg):
        nonlocal used_proc_names
        CHK( cfg.layer_name not in used_proc_names, f"名称 {cfg.layer_name} 有重复")
        si.all_layers.append(cfg.layer_name)
        if cfg.unshare_pid:
            used_proc_names.append(cfg.layer_name)
        if cfg.isMainLyr:
            si.mainLyr = cfg.layer_name
        for subpItem in (cfg.subprocs or [] ):
            CHK( subpItem.subp_name, f"子进程未设置 subp_name : {subpItem}")
            CHK( re.match(r'^[a-zA-Z0-9_-]+$', subpItem.subp_name), f"subp_name只能有字母、数字、杠、下划线。此名称不合法： {subpItem.subp_name}" )
            CHK( len(subpItem.subp_name)<=30, f"subp_name 太长，超过30字符: {subpItem}")
            CHK( subpItem.subp_name not in used_proc_names, f"名称 {subpItem.subp_name} 有重复")
            CHK( not subpItem.subp_name.startswith('layer'), f"子进程名称 {subpItem.subp_name} 以'layer'开头不合法 {subpItem}")
            used_proc_names.append(subpItem.subp_name)

        if cfg.user_shell: used_proc_names.append('user_shell')
        if cfg.dev_shell: used_proc_names.append('dev_shell')
        for sublyr_cfg in (cfg.sublayers or [] ):
            _recr(sublyr_cfg)
    _recr(layer1_cfg)
    wdg_target_procs = [x for x in used_proc_names if x != 'mainApp'] # 不看主app, 只看它所属层
    si.expected_alive_procs = wdg_target_procs
    si.expected_alive_layers = list(set(si.expected_alive_procs) & set(si.all_layers))

def recursive_lyrs_jobs(si, cfg, parent_cfg, used_layer_names): # cfg：要处理的层， parent_cfg : 其父层
    # 计算本层深度
    cfg.depth = parent_cfg.depth + 1 if parent_cfg is not None else 1

    CHK( cfg.layer_name, "存在某层没有设置layer_name")
    CHK( re.match(r'^[a-zA-Z0-9_-]+$', cfg.layer_name), f"layer_name只能有字母、数字、杠、下划线。此名称不合法： {cfg.layer_name}" )
    CHK( cfg.layer_name not in resv_words, f"层名{cfg.layer_name}与保留字段{resv_words}重复")
    CHK( cfg.layer_name.startswith('layer'), f"层名{cfg.layer_name}非以'layer'开头")
    CHK( cfg.layer_name not in used_layer_names, f"层名称 '{cfg.layer_name}' 有重复")
    used_layer_names.append(cfg.layer_name)

    CHK( len(cfg.layer_name.encode()) <= 15 , f"层名称 {cfg.layer_name} 大小超过15字节")

    # 配置中的数组类型去除None成员
    if cfg.fs:
        cfg.fs = [fsItem for fsItem in cfg.fs if fsItem is not None]
    if cfg.sublayers :
        cfg.sublayers = [sublyr for sublyr in cfg.sublayers if sublyr is not None]
    if cfg.subprocs :
        cfg.subprocs = [cmd for cmd in cfg.subprocs if cmd is not None]
        CHK( cfg.unshare_pid and cfg.unshare_mnt, f"层{cfg.layer_name}有 subprocs 但没有启用 unshare_pid+unshare_mnt")
        CHK( cfg.uid_map_as_user, f"层{cfg.layer_name}有 subprocs 但没有启用 uid_map_as_user")
    if cfg.subprocs and cfg.sublayers:
        raise_exit("不能同时有 subprocs 和 sublayers")
    if cfg.envs_unset:
        cfg.envs_unset = [item for item in cfg.envs_unset if item is not None]
    if cfg.envset_grps:
        cfg.envset_grps = [item for item in cfg.envset_grps if item is not None]
    if cfg.start_after:
        cfg.start_after = [item for item in cfg.start_after if item is not None]
    if cfg.uid_map_as_root or cfg.uid_map_as_user:
        CHK( cfg.unshare_user, f"层{cfg.layer_name}有 uid_map_as_* 但没有启用 unshare_user")

    if cfg.unshare_pid and not cfg.unshare_mnt:
        raise_exit(f"层{cfg.layer_name}启用了unshare_pid但没有启用unshare_mnt")
    if (cfg.newrootfs or cfg.fs) and not cfg.unshare_mnt:
        raise_exit(f"层{cfg.layer_name}设置了newrootfs或fs但没有启用unshare_mnt")
    if bool(cfg.fs) != bool(cfg.newrootfs):
        raise_exit(f"层{cfg.layer_name}: fs和newrootfs若有则应该两个都有")
    if cfg.isMainLyr :
        CHK( cfg.unshare_pid , f'主层 {cfg.layer_name} 要求启用unshare_pid=True')

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
        CHK( cfg.uid_map_as_root,"第1层未启用 uid_map_as_root (要求启用)")
        CHK( cfg.unshare_pid, "第1层未启用 unshare_pid(要求启用)")
        CHK( len(cfg.sublayers) == 1, "第1层的sublayers数组的元素个数不为1 （要求为1）")
        CHK( not cfg.newrootfs, "第1层不可以启用newrootfs")

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
        if not (cfg.unshare_mnt and cfg.unshare_cgroup and cfg.unshare_ipc and cfg.unshare_time and cfg.unshare_uts and cfg.newrootfs and cfg.fs) :
            raise_exit(f"层{cfg.layer_name}未把 [unshare_mnt, unshare_cgroup, unshare_ipc, unshare_time, unshare_uts, newrootfs, fs] 全启用 （要求全启用）")
        if not any( pItem.batch_plan == 'container-rootfs' for pItem in cfg.fs):
            raise_exit(f"层{cfg.layer_name}的fs中无 batch_plan='container-rootfs' 的条目 （要求有）")

    if cfg.layer_name in ['layer2c', 'layer4c', 'layer4']:
        CHK( cfg.unshare_pid, f"{cfg.layer_name}未启用unshare_pid=True（要求启用）")

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
            log(f"警告： {cfg.layer_name} 设置了启动dev_shell或user_shell, 将忽略其子层", file=sys.stderr)
            cfg.sublayers = []
        if cfg.subprocs and [x for x in cfg.subprocs if x.subp_name == 'mainApp']:
            log(f"警告： {cfg.layer_name} 设置了启动dev_shell或user_shell, 将忽略其mainApp", file=sys.stderr)
            cfg.subprocs = [x for x in cfg.subprocs if x.subp_name != 'mainApp']

    for sublyr_cfg in (cfg.sublayers or []):
        recursive_lyrs_jobs(si, sublyr_cfg, cfg, used_layer_names)


def start_lyrs_recursive_jobs(si, layer1_cfg): # 这是给最外层启动时把layer1_cfg作为cfg传入的
    recursive_lyrs_jobs(si, layer1_cfg, None, [])
    recr_rm_empty_lyr(si, layer1_cfg)
    recursive_valid_lyrs(si, layer1_cfg)


resv_words = ['host', 'sbx', 'sbxs', 'tsbx', 'tsbxs', 'tsbxes', 'sandbox', 'sandboxs', 'sandboxes', 'layer', 'layers', 'new', 'py', 'json', 'name', 'dirs', 'log', 'logs', 'socket', 'nc', 'tmpfs', 'tmp', 'temp', 'overlay', 'events', 'lyr_cfg', 'pid', 'userconfig', 'rootfs']
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


    mkdirp(target_sbxdir_path)
    new_tmpfs_for_sbxdir = True if call_at_buildfs else False
    if new_tmpfs_for_sbxdir:
        mount('tmpfs', target_sbxdir_path, 'tmpfs', mntflag_newsbxdir, 'mode=700')

    if not os.path.lexists(f'{target_sbxdir_path}/dirmaker.layer.name'):
        with open(f'{target_sbxdir_path}/dirmaker.layer.{lyrcfg.layer_name}.name', 'w') as f:
            f.write(lyrcfg.layer_name)
            os.chmod(f.name, 0o444)
        symlink(f'dirmaker.layer.{lyrcfg.layer_name}.name', f'{target_sbxdir_path}/dirmaker.layer.name')


    if call_at_begin:
        with open(f'{si.outest_sbxdir}/sbx.{si.outest_pid}.pid', 'w') as f:
            f.write(str(si.outest_pid))
            os.chmod(f.name, 0o444)

        symlink(f'sbx.{si.outest_pid}.pid', f'{si.outest_sbxdir}/sbx.pid')

        with open(f'{si.outest_sbxdir}/userconfig.json', 'w') as f:
            f.write(json.dumps(OG.uc, indent=2, ensure_ascii=False))
            os.chmod(f.name, 0o444)
        with open(f'{si.outest_sbxdir}/dyncfg.json', 'w') as f:
            f.write(json.dumps(OG.dyncfg, indent=2, ensure_ascii=False))
            os.chmod(f.name, 0o444)



        def make_file_get_fd(filepath, open_flag, filemode):
            fd = os.open(filepath, open_flag, filemode)
            set_fd_keep_on_exec(fd, True)
            return fd

        si.file_fds = d()
        si.file_fds.update( d(
            # 沙箱内只fd写，最外层用路径来读
            layerslog_a = make_file_get_fd(f'{si.outest_sbxdir}/events.layers.log', os.O_WRONLY|os.O_CREAT|os.O_APPEND, 0o644),

            # RDONLY是因为沙箱内只fd读，仅最外层用路径写
            procs_alive = make_file_get_fd(f'{si.outest_sbxdir}/procs.alive.json', os.O_RDONLY|os.O_CREAT, 0o644),
            procs_histseen = make_file_get_fd(f'{si.outest_sbxdir}/procs.histseen.json', os.O_RDONLY|os.O_CREAT, 0o644),
            procs_wdgsee = make_file_get_fd(f'{si.outest_sbxdir}/procs.wdgsee.json', os.O_RDONLY|os.O_CREAT, 0o644),
        ) )

        Path(f'{si.outest_sbxdir}/procs.alive.json').write_text("[]")
        Path(f'{si.outest_sbxdir}/procs.histseen.json').write_text("{}")
        Path(f'{si.outest_sbxdir}/procs.wdgsee.json').write_text("{}")

        si.subp_log_fds = d()
        for pn in si.expected_alive_procs:
            if not (pn in ['user_shell','dev_shell','mainApp'] or pn.startswith('layer') ):
                si.subp_log_fds[pn] = make_file_get_fd(f'{si.outest_sbxdir}/subp.{pn}.log', os.O_WRONLY|os.O_CREAT|os.O_APPEND, 0o644)

        def create_socketpair_fds():
            skt_chd, skt_pa = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            fd_chd = skt_chd.detach() ; set_fd_keep_on_exec(fd_chd, True)
            fd_pa  = skt_pa.detach() ; set_fd_keep_on_exec(fd_pa, True) # 为了不让fd号码乱，pa也保留
            return d(pa=fd_pa, chd=fd_chd)
        si.oSkt_fds = d()
        for lyr in si.expected_alive_layers:
            si.oSkt_fds [lyr] = create_socketpair_fds()





    Path(f'{target_sbxdir_path}/empty').touch()
    os.chmod(f'{target_sbxdir_path}/empty', 0)

    mkdirp(f'{target_sbxdir_path}/apps')
    if old_sbxdir_path :
        if not Path(f'{old_sbxdir_path}/apps').is_mount():
            # 创建新的空的 tmpfs 给apps
            mount('tmpfs', f'{target_sbxdir_path}/apps', 'tmpfs', mntflag_apps, 'mode=755')
        else:
            # 把上一层的apps bind过来. 不是最后一层就应该要保留rw
            mount(f'{old_sbxdir_path}/apps', f'{target_sbxdir_path}/apps', None, MS.BIND|mntflag_apps, None)


    mkdirp(f'{target_sbxdir_path}/temp')
    if call_at_buildfs:
        mount('tmpfs', f'{target_sbxdir_path}/temp', 'tmpfs', mntflag_sbxtemp, 'mode=755')



    if not os.path.exists(f'{target_sbxdir_path}/sbxinfo.json'):
        with open(f'{target_sbxdir_path}/sbxinfo.json', 'w') as f:
            f.write(json.dumps(si, indent=2, ensure_ascii=False))
            os.chmod(f.name, 0o444)
        safe_copy_script(f'{target_sbxdir_path}/bootsbx.py')
        with open(f'{target_sbxdir_path}/sbx.{si.sandbox_name}.name', 'w') as f:
            f.write(si.sandbox_name)
            os.chmod(f.name, 0o444)
        symlink(f'sbx.{si.sandbox_name}.name', f'{target_sbxdir_path}/sbx.name')

    # 创建和写 (不包括本层)所有子层（递归） 需要的 路径和文件
    def create_lyrs_files_recr(lyr_cfg):
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

    if new_tmpfs_for_sbxdir:
        os.chmod(target_sbxdir_path, 0o555)
        mount(None, target_sbxdir_path, None, MS.REMOUNT|MS.RDONLY|mntflag_newsbxdir, None)

   # build_fs 时原有：
            # mount('tmpfs', f'{real_dest}/overlays', 'tmpfs', flag, None)

def init_sbxinfo(): # 仅顶层运行，子容器层不运行。返回的数据一路传下各个子层
    si = d()

    # 从外部(linux host)启动沙箱的原本用户信息
    uid = os.getuid()
    gid = os.getgid()
    username = pwd.getpwuid(uid).pw_name # 获取当前用户名
    groupname = grp.getgrgid(gid).gr_name
    HOME = f'/home/{username}' if uid>0 else '/root'
    outest_pid = os.getpid()
    log(f'PID = {outest_pid}')
    startscript_on_host = scriptfilepath
    startdir_on_host = scriptdirpath
    PTMP = f'/tmp/tsbxs-{uid}'

    mkdirp(PTMP)      # 创建不同沙箱实例共用的 主临时目录,不清理这个
    os.chmod(PTMP, 0o700)

    si.update( { k: v for k, v in locals().items() if k in
        ['PTMP', 'uid', 'gid', 'username', 'groupname', 'HOME', 'outest_pid',
         'startscript_on_host', 'startdir_on_host']
    } )

    uc = userconfig(si) # NOTE

    # 沙箱名。不是子容器层名
    CHK( not uc.sandbox_name or re.match(r'^[a-zA-Z0-9_-]+$', uc.sandbox_name), f"沙箱名只能有字母、数字、杠、下划线。此名称不合法： {uc.sandbox_name}" )
    sandbox_name = uc.sandbox_name or f'{scriptdirname}_{scriptname}' # 沙箱名
    sandbox_name = re.sub(r'[^a-zA-Z0-9_\-]', lambda m: f"_{ord(m.group(0)):x}", sandbox_name)
    CHK( sandbox_name not in resv_words, f"沙箱名{sandbox_name}与保留字段{resv_words}重复")
    CHK( len(sandbox_name) < 500, f'沙箱名太长： {sandbox_name}')

    apps = uc.apps
    if uc.reuseInstance: reuseInstance = uc.reuseInstance

    if (sharedir_prefix := uc.sharedir_prefix):
        CHK( sharedir_prefix.startswith('/tmp/') or sharedir_prefix.startswith('/dev/shm/'), "uc.sharedir_prefix 必须以 /tmp/ 或 /dev/shm/ 开头")
        sharedir_onhost = f'{sharedir_prefix}{sandbox_name}'
        si.sharedir_onhost = sharedir_onhost
    else:
        sharedir_onhost = None


    dyncfg = gen_dynamic_cfg(si, uc) # NOTE

    starttime_str = datetime.datetime.now().strftime("%m%d-%H%M")

    n = 0
    while True:
        instance_name = f'{sandbox_name}_{starttime_str}-{n}'
        if os.path.lexists( (outest_sbxdir := f'{PTMP}/{instance_name}') ) :
            n+=1
        else : break

    if 'newXId' in dict.keys(dyncfg): newXId = dyncfg.newXId

    CG_HOSTUSER = f'/sys/fs/cgroup/user.slice/user-{uid}.slice/user@{uid}.service'
    CG_TSBXS = f'{CG_HOSTUSER}/tsbxs.slice'
    CG_SBX = f'{CG_TSBXS}/{instance_name}'
    CHK( os.access(CG_HOSTUSER, os.W_OK), f"将 {CG_HOSTUSER} 目录 不存在 或 不可写")

    BND_MAX = int(Path('/proc/sys/kernel/cap_last_cap').read_text())
    pythonbin = sys.executable

    si.update( { k: v for k, v in locals().items() if k in
        ['sandbox_name', 'instance_name', 'outest_sbxdir', 'newXId', 'apps',
         'CG_HOSTUSER', 'CG_TSBXS', 'CG_SBX', 'BND_MAX', 'pythonbin']
    } )

    layer1_cfg = gen_layer1(si, uc, dyncfg)
    start_lyrs_recursive_jobs(si, layer1_cfg)




    OG = d(dyncfg=dyncfg, uc=uc)
    return si, layer1_cfg, OG

def set_fd_keep_on_exec(fd:int, keep:bool):
    if keep: new_fdflag = fcntl.fcntl(fd, fcntl.F_GETFD) & (~fcntl.FD_CLOEXEC)
    else:    new_fdflag = fcntl.fcntl(fd, fcntl.F_GETFD) | fcntl.FD_CLOEXEC
    fcntl.fcntl(fd, fcntl.F_SETFD, new_fdflag)


class OutestProcsMonitor:
    I_AM_OUTEST=None
    @classmethod
    def i_am_outest(cls):
        cls.I_AM_OUTEST=True
        cls.procs_alive = []
        cls.procs_wdgsee = d()
        cls.procs_histseen = d()
        cls.logs_should_match_soon = []
        cls.fd_wr_alive = os.open(f'{si.outest_sbxdir}/procs.alive.json', os.O_WRONLY)
        cls.fd_wr_seen = os.open(f'{si.outest_sbxdir}/procs.histseen.json', os.O_WRONLY)
        cls.fd_wr_wdgsee = os.open(f'{si.outest_sbxdir}/procs.wdgsee.json', os.O_WRONLY)

        cls.oPaSkts = d()
        for lyrn, fdpair in dict.items(si.oSkt_fds):
            cls.oPaSkts[lyrn] = socket.socket(fileno=fdpair.pa)
        cls.tell_lyr_runsubp(si.mainLyr, d(cmdvec=OG.mainApp_cmdvec, subp_name='mainApp', workdir=OG.chosen_appItem.workdir or None)) # 不需等主层启动就发，保证主层收到的第一条信息是这个mainApp的命令
    @classmethod
    def get_NSpid_arr(cls, status_file_path) -> list:
        for line in Path(status_file_path).read_text().splitlines():
            if line.startswith("NSpid:"):
                return [int(x) for x in line.split()[1:]]
    @classmethod
    def get_procsalive_arr_from_cg(cls) -> list:
        CHK( cls.I_AM_OUTEST, "只有outest可以调用这个，但 I_AM_OUTEST 未设置")
        result = []
        for pid in Path(f'{si.CG_SBX}/cgroup.procs').read_text().splitlines():
            try:
                inode1 = os.stat(f'/proc/{pid}').st_ino

                comm = Path(f'/proc/{pid}/comm').read_text().strip()
                NSpid = cls.get_NSpid_arr(f'/proc/{pid}/status')
                start_tick = get_start_tick(f'/proc/{pid}/stat')
                ns = get_nstypes(f'/proc/{pid}/ns')
                cmdvec = Path(f'/proc/{pid}/cmdline').read_text().strip('\x00').split('\x00')

                inode2 = os.stat(f'/proc/{pid}').st_ino
                if inode1 != inode2: continue
            except:
                continue
            result.append(D( comm=comm, NSpid=NSpid, start_tick=start_tick,  ns=ns , cmdvec=cmdvec))
        return result
    @classmethod
    def update_procsalive(cls): # 只有 最外层 原进程 调用这个函数
        CHK( cls.I_AM_OUTEST, "只有outest可以调用这个，但 I_AM_OUTEST 未设置")
        procsalive_arr = cls.get_procsalive_arr_from_cg()
        # NOTE 必须 既写本cls内部变量，也更新路径文件内容
        cls.procs_alive = procsalive_arr # 写cls内部
        try: # 写文件
            json_str = '\n'.join(['[', '\n,\n'.join([json.dumps(x) for x in procsalive_arr]) ,']'])
            fcntl.flock(cls.fd_wr_alive, fcntl.LOCK_EX)
            os.ftruncate(cls.fd_wr_alive, 0)
            os.pwrite(cls.fd_wr_alive, json_str.encode(), 0)
        finally:
            fcntl.flock(cls.fd_wr_alive, fcntl.LOCK_UN)
    @classmethod
    def aliveproc_and_elproc_equal(cls, plv, pel): #plv="proc alive" | pel="proc from event log"
        if plv.NSpid[-1] == pel.self_see_pid \
        and plv.start_tick == pel.start_tick \
        and plv.ns.pid == pel.ns.pid:
            return True
        else: return False
    @classmethod
    def aliveproc_and_seenproc_equal(cls, plv, psn): # plv="proc alive" | psn="proc seen"
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
        CHK( cls.I_AM_OUTEST, "警告：在无I_AM_OUTEST的情况下调用了sbx_exit_broadcast()", 'warn') # 可能会在初始化之前被调用
        for lyrname in si.expected_alive_layers:
            cls.sendmsg_to_lyr(lyrname, d(action='sbx_exit'), loose=True)
    @classmethod
    def sendmsg_to_lyr(cls, lyrname, msgobj, loose=False):
        CHK( cls.I_AM_OUTEST, "警告：在无I_AM_OUTEST的情况下调用了sendmsg_to_lyr()", 'warn' if loose else 'raise_exit')
        try:
            cls.oPaSkts[lyrname].send(json.dumps(msgobj).encode())
        except Exception as err:
            if loose: log(f"警告：发送消息给{lyrname}未成功: {err}", file=sys.stderr)
            else: raise
    @classmethod
    def tell_lyr_runsubp(cls, lyrname, subpItem):
        CHK( cls.I_AM_OUTEST, "只有outest可以调用这个，但 I_AM_OUTEST 未设置")
        cls.sendmsg_to_lyr(lyrname, d(action='run_subp', subpItem=subpItem) )
    @classmethod
    def symlink_into_sbxdir(cls, dest, file_in_sbxdir): # 创建软链，从外部，链到本沙箱实例目录内的文件
        CHK( cls.I_AM_OUTEST, "只有outest可以调用这个，但 I_AM_OUTEST 未设置")
        linkto = napath(f'{si.outest_sbxdir}/{file_in_sbxdir}')
        CHK( not Path(linkto).is_dir(), f'为了安全，不允许链接到目录')
        symlink(linkto, dest)
    @classmethod
    def symlink_from_sbxdir_to_in_proc_rootfs(cls, slk_name, to_proc_name, target_in_proc_rootfs): # 创建软链，从本沙箱实例目录内, 链到本沙箱的进程的 rootfs 里的某文件
        CHK( cls.I_AM_OUTEST, "只有outest可以调用这个，但 I_AM_OUTEST 未设置")
        pid = cls.procs_histseen[to_proc_name].NSpid[0]
        real_linkto = napath(f'/proc/{pid}/root/{target_in_proc_rootfs}')
        CHK( not Path(real_linkto).is_dir(), f'为了安全，不允许链接到目录')
        symlink(real_linkto, f'{si.outest_sbxdir}/into.{to_proc_name}.{slk_name}.link')
    @classmethod
    def custom_action_when_procname_seen(cls, proc_name):
        CHK( cls.I_AM_OUTEST, "只有outest可以调用这个，但 I_AM_OUTEST 未设置")
        if proc_name == 'xephyr':
            cls.symlink_from_sbxdir_to_in_proc_rootfs('x11socket', 'xephyr', f'/tmp/.X11-unix/X{si.newXId}') # TODO wayland
            cls.symlink_into_sbxdir(f'/tmp/.X11-unix/X{si.newXId}', f'into.{proc_name}.x11socket.link')
            cleanup_symlinks_to_rm.append(f'/tmp/.X11-unix/X{si.newXId}') # TODO wayland
    @classmethod
    def find_alive_proc_matching_logitem(cls, elp):
        for proc in cls.procs_alive: # 在存在进程列表中查找，看有没有这个
            if cls.aliveproc_and_elproc_equal(proc, elp):
                return proc
    @classmethod
    def put_proc_into_seenlist(cls, proc_name, seenProc, logItem):
        cls.procs_histseen[proc_name] = seenProc
        if logItem in cls.logs_should_match_soon: # 上次已经加入了注意名单，现在可以移出注意名单
            log(f'把这条消息从未识别的消息列表中删除 {logItem}')
            cls.logs_should_match_soon.remove(logItem)
        if proc_name in si.expected_alive_procs:
            cls.procs_wdgsee[proc_name] = seenProc
        cls.custom_action_when_procname_seen(proc_name)
    @classmethod
    def got_a_ready_proc_log(cls, logItem): # 被调用时，说明一个进程有了logItem出现
        proc_name = logItem.ready_proc_name
        # 判断这个进程是否已经在aliveProcs的列表里
        if (aliveProc := cls.find_alive_proc_matching_logitem(logItem) ):
            seenProc = cls.conv_to_seenproc(aliveProc, logItem)
            cls.put_proc_into_seenlist(proc_name, seenProc, logItem)
        else: # 不在aliveProcs列表里：1.可能暂时来不及出现，允许等下个周期再出现 2.若已经不是第1个周期，则判断进程死亡
            if proc_name not in si.expected_alive_procs : # 看门狗不用管这个进程
                return
            if logItem not in cls.logs_should_match_soon: # 可能暂时来不及出现，允许等下个周期再出现
                log(f'把此消息加入未识别的列表 {logItem}')
                cls.logs_should_match_soon.append(logItem)
            else: # 已经不是第1个周期，则判断进程死亡
                log(f'收到过{proc_name}的启动消息，但一直未发现过存活，判断进程已死')
                sys.exit()
    @classmethod
    def get_and_parse_new_wlog(cls):
        new_logs = WlogReader.readnew()
        for logItem in (cls.logs_should_match_soon + new_logs):
            logItem = d(logItem)

            if logItem.event == 'error':
                log(f'收到来自 {logItem.logger} 的错误消息 {logItem.errmsg}')
                sys.exit(1)

            if logItem.ready_proc_name :
                cls.got_a_ready_proc_log(logItem)
        cls.write_procs_seen_to_fd(cls.procs_histseen, cls.fd_wr_seen) #写文件procs.histseen.json
        cls.write_procs_seen_to_fd(cls.procs_wdgsee, cls.fd_wr_wdgsee) # procs.wdgsee.json
    @classmethod
    def write_procs_seen_to_fd(cls, procs_seen_obj, fd):
        CHK( cls.I_AM_OUTEST, "只有outest可以调用这个，但 I_AM_OUTEST 未设置")
        try:
            json_str = '\n'.join(['{',
                '\n,\n'.join([f'"{k}" : {json.dumps(v)}' for k,v in dict.items(procs_seen_obj) ]) ,
                '}'])
            fcntl.flock(fd, fcntl.LOCK_EX)
            os.ftruncate(fd, 0)
            os.pwrite(fd, json_str.encode(), 0)
        finally:
            fcntl.flock(fd,  fcntl.LOCK_UN)
    @classmethod
    def wdg(cls): # 看看那些已经在 procs_wdgsee 列表中的进程还存活吗
        CHK( cls.I_AM_OUTEST, "只有outest可以调用这个，但 I_AM_OUTEST 未设置")
        cls.update_procsalive()
        cls.get_and_parse_new_wlog()
        for proc_name,psn in dict.items(cls.procs_wdgsee):
            for plv in cls.procs_alive:
                if cls.aliveproc_and_seenproc_equal(plv, psn):
                    break
            else:
                log(f'{proc_name} 已不再存活，看门狗结束沙箱')
                sys.exit()


def read_alltext_from_fd(fd:int) -> str:
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        return os.pread(fd, os.fstat(fd).st_size, 0).decode()
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)

def read_all_from_fd_then_jsonloads(fd) -> list|dict :
    return d( json.loads( read_alltext_from_fd(fd) ) )

def get_alive() -> list:
    if OutestProcsMonitor.I_AM_OUTEST:   return OutestProcsMonitor.procs_alive
    else:   return read_all_from_fd_then_jsonloads(si.file_fds.procs_alive)

def get_histseen() -> dict:
    if OutestProcsMonitor.I_AM_OUTEST:  return OutestProcsMonitor.procs_histseen
    else:   return read_all_from_fd_then_jsonloads(si.file_fds.procs_histseen)

def get_wdgsee() -> dict:
    if OutestProcsMonitor.I_AM_OUTEST:  return OutestProcsMonitor.procs_wdgsee
    else:   return read_all_from_fd_then_jsonloads(si.file_fds.procs_wdgsee)


def get_nstypes(nsdir_path):
    return D({nstype:os.stat(f'{nsdir_path}/{nstype}').st_ino for nstype in os.listdir(nsdir_path)})

def get_start_tick(statfile_path): # 返回的是字符串，不是数字
    return Path(statfile_path).read_text().split(') ')[-1].split(' ')[22-1-2]  # stat文件里的第22个字段是进程开始时间（cpu tick）， 去掉前两个字段

def maybe_sendto_running_instance():
    return False

si = None # sbxinfo , sandbox info
tlcfg = None # thislyr_cfg , this layer config
OG = None # outest global info
def main():
    global si, tlcfg, OG

    arg_parser = argparse.ArgumentParser(add_help=False)
    sbx_arg_grp = arg_parser.add_mutually_exclusive_group()
    sbx_arg_grp.add_argument("--app", metavar="<user_cli_appname>")
    sbx_arg_grp.add_argument("--lyrcfg", metavar="<cli_lyrcfg_file>")

    sbx_args, user_cli_argv = arg_parser.parse_known_args()

    user_cli_appname = sbx_args.app
    cli_lyrcfg_file = sbx_args.lyrcfg

    if user_cli_appname or not cli_lyrcfg_file: is_outest = True # 是顶层
    else: is_outest = False # 是子层

    if is_outest: # 是顶层
        si, layer1_cfg, OG = init_sbxinfo() # 只有从最外层启动才运行这个函数
        tlcfg = layer1_cfg

        tlcfg.sbxdir_path0 = si.outest_sbxdir
    else: # 是子层
        tlcfg = d(json.loads(Path(cli_lyrcfg_file).read_text()))
        tlcfg.sbxdir_path0 = padir(cli_lyrcfg_file)
        si = d(json.loads(Path(f'{tlcfg.sbxdir_path0}/sbxinfo.json').read_text()))




    if is_outest:
        log(f"当前PID: {si.outest_pid}  沙箱名：{si.sandbox_name}   启动的用户为：{si.username} {si.groupname}")
        if not user_cli_appname or user_cli_appname=='default': chosen_appItem = si.apps[0]
        else: chosen_appItem = next((app for app in si.apps if app.get('appname') == user_cli_appname), None)
        CHK( chosen_appItem and chosen_appItem.cmdvec, '未找到选择的app, 或选择的app没有正确的cmdvec')
        OG.chosen_appItem = chosen_appItem
        OG.user_cli_argv = user_cli_argv
        OG.mainApp_cmdvec = chosen_appItem.cmdvec + user_cli_argv
        log(f'要在沙箱内运行的app的命令: {OG.mainApp_cmdvec}')

        # 判断应该 新实例 还是 发送app命令到 正在运行的实例
        if si.reuseInstance:
            if maybe_sendto_running_instance():
                sys.exit(0)

        print(f"创建新沙箱，信息目录：{si.outest_sbxdir}")
        print(f"cgroup：{si.CG_SBX}")
        print(f"沙箱看门狗要轮询的进程：{si.expected_alive_procs}")
        if si.newXId: log(f'沙箱使用的X11编号 DISPLAY=:{si.newXId}')

        atexit.register(cleanup_outest) # 顶层父进程注册清理函数

        mkdirp(si.CG_TSBXS)
        mkdirp(si.CG_SBX)
        Path(f'{si.CG_SBX}/cgroup.procs').write_text(str(os.getpid()))

        make_mnt_fill_sbxdir(si, layer1_cfg, call_at_begin=True, OG=OG)


    set_loghead (f'{tlcfg.layer_name}: ' if not is_outest else 'outest: ')
    set_ps1('notready')

    # 创建主机与沙箱之间的临时共享目录
    if is_outest and si.sharedir_onhost:
        log(f'在 {si.sharedir_onhost} 创建主机与沙箱之间的临时共享目录')
        mkdirp(si.sharedir_onhost)

    # ----------------------------
    # 预先算好变根后的 sbxdir_path1
    if not tlcfg.newrootfs:
        tlcfg.sbxdir_path1 = tlcfg.sbxdir_path0
    else:
        tlcfg.sbxdir_path1 = next((pItem.dest for pItem in tlcfg.fs if pItem.batch_plan == 'sbxdir-in-newrootfs'), None)
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
            log('更新环境变量' , envg)
            os.environ.update(envg)

    for wait_task in (tlcfg.start_after or [] ):
        if wait_task.waittype == 'socket-listened':
            while not is_unix_socket_listened(wait_task.path):
                time.sleep(0.1)
                pass

    # log(f"执行unshare")
    # TODO 用个数组储存 pid time 是fork前做，其他main2做
    unshr_cfg = lyrcfg_to_unshrcfg(tlcfg)
    unshr_cfg.mnt=False # unshare排除mnt（后面再做）
    if tlcfg.depth != 1: unshr_cfg.user=False # 非首层则unshare排除user（后面再做）
    os.unshare(unshrflg(unshr_cfg))

    set_ps1('afterUnshare')

    skp_lyfk = TmpSocketPair()
    # log(f"即将fork")
    pid = os.fork()
    if pid == 0: # 子进程
        atexit._clear()
        set_loghead (f'{tlcfg.layer_name} F: ')
        skp_lyfk.i_am_chd()
        if tlcfg.depth == 1:
            set_pdeathsig() # 最外层的原进程（fork前的进程）退出的话，layer1的fork出来的子进程应该主动退出
        main2(skp_lyfk)
        sys.exit()
    else: # 父进程
        skp_lyfk.i_am_pa()

        if tlcfg.uid_map_as_user and tlcfg.depth > 1: # 为了改写子进程uid_map, 此时我看到的proc必须rw
            skp_lyfk.pa_recv(1, 5, BS.SetMeUidUser)
            Path(f'/proc/{pid}/setgroups').write_text('deny\n')
            Path(f'/proc/{pid}/uid_map').write_text(f'{si.uid} 0 1\n')
            Path(f'/proc/{pid}/gid_map').write_text(f'{si.gid} 0 1\n')
            skp_lyfk.pa_send(BS.SetYouUidUserDone)
        skp_lyfk.close()

        if is_outest:
            OG.layer1_pid = pid
            daemon_outest() # NOTE skp_lyfk 关了后，才进入daemon
        else:
            sys.exit()



class TmpSocketPair:
    def __init__(self):
        self._skt_chd, self._skt_pa = socket.socketpair()
        set_fd_keep_on_exec(self._skt_chd.fileno(), False)
        set_fd_keep_on_exec(self._skt_pa.fileno(), False)
        self.I_AM_PA = False ; self.I_AM_CHD = False
    def i_am_pa(self):
        CHK(not self.I_AM_CHD, "已设置为是fork的子进程端")
        self._skt_chd.close() ; self.I_AM_PA = True
    def i_am_chd(self):
        CHK(not self.I_AM_PA, "已设置为是fork的父进程端")
        self._skt_pa.close() ; self.I_AM_CHD = True
    def pa_send(self, data):
        CHK(self.I_AM_PA, "非fork的父进程调用了此函数")
        if isinstance(data, BS): data = data.value
        self._skt_pa.send(data)
    def chd_send(self, data):
        CHK(self.I_AM_CHD, "非fork的子进程调用了此函数")
        if isinstance(data, BS): data = data.value
        self._skt_chd.send(data)
    def pa_recv(self, byte_cnt, timeout, expect_data=None):
        CHK(select.select([self._skt_pa], [], [], timeout)[0], "fork的父进程等待子进程的信号超时了")
        if isinstance(expect_data, BS): expect_data = expect_data.value
        data = self._skt_pa.recv(byte_cnt)
        if expect_data is not None: CHK(data == expect_data, f"fork的父进程收到的信号不符合预期: got {data!r}, expected {expect_data!r}")
        return data
    def chd_recv(self, byte_cnt, timeout, expect_data=None):
        CHK(select.select([self._skt_chd], [], [], timeout)[0], "fork的子进程等待父进程的信号超时了")
        if isinstance(expect_data, BS): expect_data = expect_data.value
        data = self._skt_chd.recv(byte_cnt)
        if expect_data is not None: CHK(data == expect_data, f"fork的子进程收到的信号不符合预期: got {data!r}, expected {expect_data!r}")
        return data
    def close(self):
        if self.I_AM_PA  and self._skt_pa:  self._skt_pa.close() ;  self._skt_pa = None
        if self.I_AM_CHD and self._skt_chd: self._skt_chd.close() ; self._skt_chd = None



class BS(enum.Enum): # fork前后父子进程之间通信用的，以及 最外层和内层之间通信用的单字节信号
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return bytes([count])  # 或者 bytes([count & 0xFF]) 防止溢出
    SetMeUidRoot = enum.auto()
    SetYouUidRootDone = enum.auto()
    SetMeUidUser = enum.auto()
    SetYouUidUserDone = enum.auto()
    IChdBorn = enum.auto()
    YouChdGo = enum.auto()


class WlogReader():
    wlogf = None
    @classmethod
    def init(cls):
        cls.wlogf = open(f'{si.outest_sbxdir}/events.layers.log', 'r')
    @classmethod
    def _read(cls):
        try:
            fcntl.flock(cls.wlogf.fileno(), fcntl.LOCK_EX)
            return cls.wlogf.read()
        finally:
            fcntl.flock(cls.wlogf.fileno(), fcntl.LOCK_UN)
    @classmethod
    def readnew(cls) -> list:
        new_logs = []
        for line in cls._read().splitlines():
            if not line.strip(): continue
            new_logs.append(json.loads(line))
        return new_logs


def daemon_outest():
    # TODO 等待5秒，等待主app启动的信号，否则退出

    register_sig_handlers(outest=True)

    WlogReader.init()
    OutestProcsMonitor.i_am_outest()

    while True:
        OutestProcsMonitor.wdg()

        if sig_say_exit: OutestProcsMonitor.sbx_exit_broadcast()

        if not exist_childtree(): sys.exit()

        time.sleep(0.2)


def daemon_pidnsleader():
    CHK( os.getpid() == 1, f"{tlcfg.layer_name} 检测到的自身PID不为1 （应该为1才正确）")
    PidnsleaderListener.i_am_pidnsleader()
    while True:
        if sig_say_exit: sys.exit()

        if (msg_from_outest := PidnsleaderListener.readmsg_from_outest() ):
            if msg_from_outest.action == 'sbx_exit':
                sys.exit()
            elif msg_from_outest.action == 'run_subp':
                PidnsleaderListener.HAS_SUBP_BY_OUTEST = True
                layer_run_subp(no_wait=True,  **msg_from_outest.subpItem )

        if PidnsleaderListener.HAS_SUBP_BY_OUTEST and not exist_childtree(): sys.exit()

        time.sleep(0.2)

class PidnsleaderListener():
    I_AM_PIDNSLEADER=None
    HAS_SUBP_BY_OUTEST=False
    @classmethod
    def i_am_pidnsleader(cls):
        cls.I_AM_PIDNSLEADER=True
        cls.oChdSkt = socket.socket(fileno=si.oSkt_fds[tlcfg.layer_name].chd)
    @classmethod
    def readmsg_from_outest(cls):
        ready, _, _ = select.select([cls.oChdSkt], [], [], 0)
        if ready: return d(json.loads( cls.oChdSkt.recv(300_000).decode() ) )

def main2(skp_lyfk):
    set_proc_dispname(tlcfg.layer_name)

    # 变内部uid=0 (root)
    if tlcfg.uid_map_as_root:
        Path('/proc/self/setgroups').write_text('deny\n')
        Path('/proc/self/uid_map').write_text(f'0 {si.uid} 1\n')
        Path('/proc/self/gid_map').write_text(f'0 {si.gid} 1\n')
        log(f"内部当前 uid={os.getuid()} gid={os.getgid()}")

    if tlcfg.unshare_mnt: # 现在才做，保证不影响父进程所看到的 /proc
        os.unshare(unshrflg(d(mnt=True)))


    # 本层文件系统、挂载proc （维持 rw）， 变根
    build_fs()
    # 若符合条件， proc 改 ro
    if tlcfg.new_proc_dir_mnted and not tlcfg.sublayers :
        mount(None  , '/proc', None, mntflag_proc|MS.REMOUNT|MS.RDONLY, 'hidepid=1')

    # Unshare User (非首层)
    if tlcfg.unshare_user and tlcfg.depth > 1 : # 第1层的若要做在之前就做了
        os.unshare(unshrflg(d(user=True)))
    # 变内部uid=1000 (user)
    if tlcfg.uid_map_as_user: # NOTE 此时父进程看到的 proc 必须为 rw
        skp_lyfk.chd_send(BS.SetMeUidUser)
        skp_lyfk.chd_recv(1, 2, BS.SetYouUidUserDone)
        log(f"内部当前 uid={os.getuid()} gid={os.getgid()}")

    # 关闭临时socket
    skp_lyfk.close()# NOTE 注意， 在创建任何 subp 之前 ， skp_lyfk(临时socket)必须已关闭

    # 非unshare_pid 层 则要等待fork前父进程退出
    if not tlcfg.unshare_pid:
        while os.getppid() not in [0, 1] : time.sleep(0.03)


    # 清理函数、信号处理注册
    if tlcfg.unshare_pid:
        CHK( os.getpid() == 1, f"{tlcfg.layer_name} 检测到的自身PID不为1 （应该为1才正确）")
        atexit.register(cleanup_pidnsleader)
        register_sig_handlers(pidnsleader=True)

    set_ps1('ready')

    #--- 创建 subp -----------------------------------
    # NOTE 注意， 在创建任何 subp 之前 ， skp_lyfk(临时socket)必须已关闭

    inprepare_children = []

    # 以subp启动子层
    for sublyr_cfg in (tlcfg.sublayers or []):
        pid, skp_spfk = layer_run_subp([
                        si.pythonbin ,
                        # 这个脚本虽然是用于创建子层的，但现在仍是在本层,本层的变根后的状态，
                        # 因此用本层的path1
                        f'{tlcfg.sbxdir_path1}/bootsbx.py',
                        '--lyrcfg', f'{tlcfg.sbxdir_path1}/lyr_cfg.{sublyr_cfg.layer_name}.json',
                    ],
                    subp_name=sublyr_cfg.layer_name
        )
        inprepare_children.append((pid, skp_spfk))

    # 以subp启动user_shell / dev_shell
    if tlcfg.user_shell or tlcfg.dev_shell:
        if tlcfg.user_shell: set_important_fds_cloexec() # NOTE 设置 沙箱级重要fd 为CLOEXEC
        pid, skp_spfk = layer_run_subp( ['/bin/bash'] ,
                        **( d(subp_name='user_shell') if tlcfg.user_shell else {}),
                        **( d(subp_name='dev_shell')  if tlcfg.dev_shell  else {}),
        )
        inprepare_children.append((pid, skp_spfk))

    # 以subp启动普通辅助app
    set_important_fds_cloexec() # NOTE 设置 沙箱级重要fd 为CLOEXEC
    for subpItem in (tlcfg.subprocs or [] ) :
        pid, skp_spfk = layer_run_subp (**subpItem)
        inprepare_children.append((pid, skp_spfk))

    #-------------------------------------------

    # 向最外层发送“本层已boot”，
    wlog('layer_booted', ready_proc_name=tlcfg.layer_name, cmdvec=Path(f'/proc/self/cmdline').read_text().strip('\x00').split('\x00') , pidns_depth=tlcfg.pidns_depth, pidns_tree=tlcfg.pidns_tree, **(d(isMainLyr=True) if tlcfg.isMainLyr else {}) )


    # 关闭重要fd (防止本 中间层 退出前，subp有短暂机会入侵本进程的fd)
    if not tlcfg.unshare_pid:
        close_important_fds()

    # 放行那些等待住的subp (为了等 重要fd 关闭. pidns层则不怕subp访问/proc/1/fd 因为无法访问 )
    for pid, skp_spfk in inprepare_children:
        skp_spfk.pa_send(BS.YouChdGo); skp_spfk.close()

    if tlcfg.unshare_pid:
        daemon_pidnsleader()
    else: # 如果不是 unshare_pid 的 ,这里将结束退出
        sys.exit()

def layer_run_subp(cmdvec=None, subp_name=None,
                   keep_caps=False, # True 全部 | False 全丢 | 字符串 部分
                   stdin=None, stdout=None, stderr=None,
                   workdir=None,
                   no_wait=False,
                   ): # TODO pty或setsid

    mainApp=None; subLayer=None; user_shell=None; dev_shell=None;

    if subp_name.startswith('mainApp'):mainApp=True
    if subp_name.startswith('layer'): subLayer = subp_name
    if subp_name == 'user_shell':     user_shell=True
    if subp_name == 'dev_shell':      dev_shell=True

    if dev_shell:
        keep_caps=True

    if not workdir:
        if user_shell or dev_shell: workdir = tlcfg.sbxdir_path1
        else: workdir = si.HOME

    if subLayer:
        keep_caps=True

    skp_spfk = TmpSocketPair()

    pid = os.fork()
    if pid == 0: # 子进程
        atexit._clear()
        set_loghead(f"{loghead}subp: ")
        skp_spfk.i_am_chd()

        if not keep_caps:
            drop_caps()

        skp_spfk.chd_send(BS.IChdBorn)
        skp_spfk.chd_recv(1, 5, BS.YouChdGo)
        skp_spfk.close()

        wlog('subp_start', cmdvec=cmdvec, **(d(ready_proc_name=subp_name, pidns_depth=tlcfg.pidns_depth, pidns_tree=tlcfg.pidns_tree) if not subLayer else {}) )

        if subLayer:    startTip = f'启动子层 {subLayer}'
        elif dev_shell: startTip = '启动 dev_shell'
        elif user_shell:startTip = '启动 user_shell'
        elif keep_caps: startTip = f'启动子进程（带权限） {subp_name}'
        else:           startTip = f'启动子进程 {subp_name}'
        log(f'{startTip} : ', cmdvec)

        if workdir: os.chdir(workdir)

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

        # === 去掉沙箱级别的fd  # NOTE 下面无法再 wlog
        if not (subLayer or dev_shell):
            close_important_fds()
        # NOTE 无法再 wlog NOTE

        os.execvp(cmdvec[0], cmdvec)
        raise_exit(f"exec()启动新程序 [ {cmdvec[0]} ] 失败", no_cleanup=True)
    else: # 原进程
        skp_spfk.i_am_pa()
        skp_spfk.pa_recv(1, 2, BS.IChdBorn)
        if no_wait:
            skp_spfk.pa_send(BS.YouChdGo); skp_spfk.close() ; skp_spfk = None
        return pid, skp_spfk

    # os.execv('/bin/bash', ['/bin/bash', '--norc'])
    # os.exec*成功后不回来，替换了进程
        # l/v： 可变参 或 数组 来指定参数
        # p : 指定path
        # e : 指定环境变量，不继承父的环境。必须完整路径

def get_important_fds():
    return list(si.file_fds.values()) \
            + list(si.subp_log_fds.values()) \
            + [fd for fd_pair in dict.values(si.oSkt_fds) for fd in dict.values(fd_pair)]

def set_important_fds_cloexec():
    fds_to_cloexec = get_important_fds()
    for fd in os.listdir('/proc/self/fd') :
        if int(fd) in fds_to_cloexec: set_fd_keep_on_exec(int(fd), False)


def close_important_fds():
    fds_to_close = get_important_fds()
    # log(f'要关闭fd： {fds_to_close}')
    for fd in os.listdir('/proc/self/fd') :
        if int(fd) in fds_to_close:
            try:
                os.close(int(fd))
            except OSError as e:
                # 本可忽略 9 错误（ EBADF 错误表示可能已关闭 （Bad file descriptor），但现在不忽略
                if e.errno != 9:  raise_exit(f'{fd=}已经被提前关闭过，与整体设计不符')
                else: raise



def cleanup_pidnsleader():
    if os.getpid() != 1 : log("错误：pid != 1 。应该只有领头进程运行此清理函数"); return
    for u in range(3):
        if not exist_childtree(): break
        os.kill(-1, signal.SIGTERM)
        for i in range(10):
            if (clear := not exist_childtree()): break
            time.sleep(0.1)
        if clear: break
    else:
        os.kill(-1, signal.SIGKILL)


SIGS_TO_IGN = []
# NOTE HUP < INT < TERM 退出强烈程度 # TODO SIGHUP 是关闭终端窗口时的信号 ，由用户配置决定外层动作
SIGS_TO_PASSBY = [signal.SIGINT, signal.SIGHUP, signal.SIGUSR1, signal.SIGUSR2, signal.SIGTSTP]
SIGS_TO_HANDLE = SIGS_TO_PASSBY + [signal.SIGTERM, signal.SIGCHLD]
def register_sig_handlers(outest=False, pidnsleader=False):
    for sig in SIGS_TO_IGN:     signal.signal(sig, signal.SIG_IGN)
    if pidnsleader:
        for sig in SIGS_TO_HANDLE:  signal.signal(sig, signals_handler_pidnsleader)
    if outest:
        for sig in SIGS_TO_HANDLE:  signal.signal(sig, signals_handler_outest)
def signals_handler_outest(signum, frame):
    _signals_handler(signum, is_outest=True)
def signals_handler_pidnsleader(signum, frame):
    _signals_handler(signum)
sig_say_exit = False
def _signals_handler(signum, is_outest=False):
    # NOTE 不能print 不能sleep 不能sys.exit . 只能 os._exit ， 但不要os._exit, 设置should_exit)
    global sig_say_exit
    if signum in SIGS_TO_PASSBY:
        pass # TODO
    elif signum == signal.SIGTERM:
        sig_say_exit = True
    elif signum == signal.SIGCHLD:
        while True:
            try:
                # -1 表示等待任意子进程 # os.WNOHANG 表示非阻塞：如果没有可回收的子进程，立即返回 (0, 0)
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0: break  # 没有进程退出, 可能是子进程被暂停（STOP）触发的SIGCHLD，我们忽略它，也可能已经处理完了僵尸
            except ChildProcessError:
                sig_say_exit = True ; break


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
def set_ps1(status):
    global ps1
    ps1 = ''.join( [
        r'''$(LEC=$? ; if [[ $LEC -ne 0 ]]; then echo -n '\[\e[0;91m\]' ; else echo -n '\[\e[0;94m\]' ; fi ; printf "(%3d)" $LEC ; echo -n '\[\e[0m\]' ) \[\e[1;93m\]'''
        ,
        f'{si.sandbox_name} {tlcfg.layer_name} {status}',
        r''' | \w > \[\e[0m\]'''
    ])
    os.environ['PS1'] = ps1

def wlog(event, me_proc_info=False, **kw_args) :
    if not (si and si.file_fds and si.file_fds.layerslog_a): return False
    kw_args = d(kw_args)
    if kw_args.errmsg: event = 'error' ; kw_args.errmsg=str(kw_args.errmsg)
    logObj = d(
        logger = loghead or tlcfg.layer_name if tlcfg else '',
        event = event,
        **kw_args
    )
    if event in ['layer_booted','subp_start']: me_proc_info = True
    if me_proc_info:
        logObj.self_see_pid=os.getpid()
        logObj.start_tick=get_start_tick('/proc/self/stat')
        logObj.ns = get_nstypes(f'/proc/self/ns')
    try:
        fcntl.flock(si.file_fds.layerslog_a, fcntl.LOCK_EX)
        os.write(si.file_fds.layerslog_a, ''.join([json.dumps(logObj), '\n\n']).encode())
    except Exception as err:
        traceback.print_exc(file=sys.stderr)
    finally:
        fcntl.flock(si.file_fds.layerslog_a, fcntl.LOCK_UN)


def build_fs():
    if tlcfg.newrootfs: # 如果设置了将要变根，现在先提前确定新根的位置
        tlcfg.newrootfs_path = f'{tlcfg.sbxdir_path0}/new.{tlcfg.layer_name}.rootfs'
    else:
        tlcfg.newrootfs_path = '/'
    mkdirp(tlcfg.newrootfs_path)

    if tlcfg.fs:
        fsPlans = gen_fsPlans()
        remountPlans = commit_fsPlans(fsPlans)
        commit_remounts(remountPlans)

    # 在build_fs完了之后挂载/proc, 与fsPlans那边的代码解耦
    new_proc_path = napath(tlcfg.newrootfs_path+'/proc')
    if tlcfg.unshare_pid or tlcfg.newrootfs:
        # log(f'挂载proc到 {new_proc_path}')
        mkdirp(new_proc_path)
        mount('proc', new_proc_path, 'proc', mntflag_proc, 'hidepid=1')
        tlcfg.new_proc_dir_mnted = True
    set_ps1('afterFs')

    # 执行变根 (chroot)
    if tlcfg.newrootfs:
        mkdirp(f'{tlcfg.newrootfs_path}/oldroot')
        # log(f'准备变根到 {tlcfg.newrootfs_path}')
        pivot_root(tlcfg.newrootfs_path, f'{tlcfg.newrootfs_path}/oldroot')
        os.chdir('/')
        umount('/oldroot', MNT.DETACH)
        os.rmdir('/oldroot') # 必须为空目录才能删除，这也保证已经缷载，未缷载则报错退出
        os.chmod('/', 0o555)
        mount(None, '/', None, MS.REMOUNT|MS.RDONLY|mntflag_newrootfs, None)
        # log(f'本层文件系统就绪 {os.listdir('/')}')
    del tlcfg.newrootfs_path
    del tlcfg.sbxdir_path0


def commit_fsPlans(fsPlans):
    target_fs_path = tlcfg.newrootfs_path
    # log(f'准备实际建立(挂载、创建)本层的文件系统，以此作根： {target_fs_path}')
    remountPlans = []
    def z(rmtItem):
        remountPlans.append(rmtItem)

    if target_fs_path.startswith(si.PTMP):
        mount(si.PTMP, si.PTMP, None, MS.BIND|MS.REC|MS.RDONLY, None)
        mount(None, si.PTMP, None, MS.REMOUNT|MS.BIND|MS.REC|MS.RDONLY, None)
        CHK( os.statvfs(si.PTMP).f_flag&MS.RDONLY, "si.PTMP未成功转换为ro")

    mkdirp(target_fs_path)
    if napath(target_fs_path) != '/':
        mount("tmpfs", target_fs_path, "tmpfs", mntflag_newrootfs, None)
        mount(None, target_fs_path, None, MS.REC | MS.SLAVE, None)
        # # 用了slave它还是private,不知原因
    os.chdir(target_fs_path)
    CHK( Path(target_fs_path).is_mount() , f"{target_fs_path} 不是挂载点")
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
            elif is_dir(src): # 文件夹
                mkdirp(real_dest)
                mount(src, real_dest, None, mntflag_binddir, None)
                if RO : z(d(dirpath=real_dest, flag=mntflag_binddir ))
            elif is_file(src) or is_dev(src):
                # 普通文件可以这这样。猜测 字符设备、块设备 也可以当普通文件一样处理
                make_file_exist(real_dest)
                mount(src,  real_dest, None, MS.BIND, None)
                mount(None, real_dest, None, MS.REMOUNT|MS.BIND|MS.RDONLY, None) if RO else None
            elif is_socket(src): # 已知socket不能remount成ro
                make_file_exist(real_dest)
                mount(src,  real_dest, None, MS.BIND|MS.RDONLY, None)
            else:
                raise_exit(f"原路径{src}所属文件类型暂未实现处理方式")
        elif plan in ['tmpfs', 'rotmpfs']:
            RO = True if plan == 'rotmpfs' else False
            mkdirp(real_dest)
            flag = pItem.flag or mntflag_tmpfs
            mount('tmpfs', real_dest, 'tmpfs', flag , 'mode=755')
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
            with tempfile.NamedTemporaryFile( dir=f'{tlcfg.sbxdir_path0}/temp', mode='w', delete=False) as f:
                f.write(pItem.content)
                mode = None ; optn = None
                if RO :             mode = 0o444
                if pItem.destmode : mode = pItem.destmode
                if mode is not None : os.chmod(f.name, mode) ; optn = f'mode={mode:o}'
                make_file_exist(real_dest)
                mount(f.name, real_dest, None, MS.BIND|(MS.RDONLY if RO else 0), optn)
                try_pass(lambda: mount(None,real_dest, None, MS.REMOUNT|MS.BIND|MS.RDONLY, optn) if RO else None )
        elif plan == 'symlink':
            symlink(pItem.linkto, real_dest)
            # TODO chroot 前后对symlink做一致性检查
        elif plan == 'empty-if-exist' : # TODO landlock 优先
            if not os.path.lexists(real_dest): continue
            optn='mode=0000'
            if Path(real_dest).is_symlink(): # 软链 (一定要把 symlink 放在最先判断)
                raise_exit(f"要保证为空的路径{real_dest}所属文件类型为symlink，暂未实现处理方式")
            elif is_dir(real_dest): # 文件夹
                mount('tmpfs', real_dest, 'tmpfs', MS.RDONLY|MS.NODEV|MS.NOEXEC|MS.NOSUID, optn)
            elif is_dev(real_dest): # 设备文件
                mount('/dev/null', real_dest,  None, MS.BIND|MS.RDONLY, optn)
                try_pass(lambda: mount(None, real_dest,  None, MS.REMOUNT|MS.BIND|MS.RDONLY, optn) )
            else: # 普通文件、socket, fifo
                mount(f'{tlcfg.sbxdir_path0}/empty', real_dest,  None, MS.BIND|MS.RDONLY, optn)
                try_pass(lambda: mount(None, real_dest,  None, MS.REMOUNT|MS.BIND|MS.RDONLY, optn) )
        elif plan == 'sbxdir-in-newrootfs':
            CHK(dest == '/sbxdir', "sbxdir-in-newrootfs的dest必须为/sbxdir")
            make_mnt_fill_sbxdir(si,  tlcfg, call_at_buildfs=True)
        elif plan == 'devpts':
            mkdirp(real_dest)
            mount('devpts', real_dest, 'devpts', MS.NOEXEC|MS.NOSUID, 'mode=0666,ptmxmode=0666,newinstance')
        elif plan in ['appimg-mount', 'sqfs-mount'] :
            mkdirp(real_dest)
            src = rslvy(src)
            offset = get_appimg_sqoffset(src) if plan == 'appimg-mount' else 0
            # TODO 先做symlink链接到真实appimage文件路径，再调用 squashfuse命令
            run_a_cmd(['squashfuse', '-o', f'ro,offset={offset}', src, real_dest])
        elif plan == 'remountro':
            z(d(dirpath=real_dest, flag=pItem.flag or 0))
        else:
            raise_exit(f"无法识别的fsPlan条目 {pItem}")

    return remountPlans

def gen_fsPlans(): # 把fs里面的batch_plan都转成plan,并去重、排序
    fsPlans = []
    def a(stepobj):
        fsPlans.append(stepobj)

    for pItem in tlcfg.fs:
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
            basic_devs = [ 'null', 'zero', 'full', 'urandom', 'random',] # 'tty', 'console'
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
                '/run/tmux' , f'{si.HOME}' , f'{si.HOME}/.cache' ,
                f'{si.HOME}/.local/share/RecentDocuments',
                f'{si.HOME}/.local/share/recently-used.xbel',
                f'{si.HOME}/.local/share/Trash', ]
            for p in paths_to_tmpfs:
                a( d( plan='tmpfs', dest=p ) )
            a( d( plan='symlink', dest='/var/run', linkto='/run' ) )
            a( d( plan='symlink', dest='/var/lock', linkto='/run/lock' ) )
        elif batch_plan == 'mask-privacy':
            destbase = pItem.destbase
            CHK( destbase in ['/', '/zrootfs'], "mask-privacy要求destbase必须为'/'或'/zrootfs'")
            path_maskfile = f'{si.HOME}/.config/treesandbox/paths_never_access.txt'
            maskfile = Path(path_maskfile)
            paths_to_mask = maskfile.read_text().splitlines() if maskfile.exists() else []
            paths_to_mask = [path.strip() for path in paths_to_mask if path.strip()]
            log(f'从{path_maskfile}读出{len(paths_to_mask)}个路径要屏蔽')
            for path in paths_to_mask:
                CHK( path.startswith('/'), "paths_never_access.txt中有不是以'/'的条目")
                path = napath(path)
                if os.path.lexists(path):
                    a( d( plan='empty-if-exist', dest=napath(f'{destbase}/{path}' ) ) )
        elif batch_plan == 'appimage':
            a( d(plan='appimg-mount', src=pItem.src, dest=f'/sbxdir/apps/{pItem.dirname}') )
            start_sh_content = f'''#!/bin/bash
                script=$(readlink -f "$0")
                scriptpath=$(dirname "$script")
                env APPDIR="$scriptpath/{pItem.dirname}" "$scriptpath"/{pItem.dirname}/AppRun "$@"
            '''
            a( d(plan='rofile', dest=f'/sbxdir/apps/run_{pItem.dirname}', destmode=0o555, content=start_sh_content) )
        elif batch_plan == 'squashfs':
            a( d(plan='sqfs-mount', src=pItem.src, dest=f'/sbxdir/apps/{pItem.dirname}') )
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
                log(f"debug:因dest重复(={pItem.dest})，移除{pItem}")
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

UNSHR_MAP = types.SimpleNamespace( pid='PID', mnt='NS', user='USER', cgroup='CGROUP', ipc='IPC', time='TIME', uts='UTS', net='NET', )
def lyrcfg_to_unshrcfg(lyrcfg):
    unshr_cfg = d({k.removeprefix('unshare_'):v for k,v in dict.items(lyrcfg) if k.startswith('unshare_')})
    for x in dict.keys(unshr_cfg): CHK(x in UNSHR_MAP.__dict__.keys(), f'此unshare flag 未知：{x}')
    return unshr_cfg
def unshrflg(unshr_cfg):
    unshr_flg = 0
    for k,v in dict.items(unshr_cfg):
        if v: unshr_flg |= os.__dict__['CLONE_NEW' + UNSHR_MAP.__dict__[k]]
    return unshr_flg

def safe_copy_script(copy_target_path):
    old_content = Path(scriptfilepath).read_text()

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


cleanup_symlinks_to_rm = []
def cleanup_outest():
    if os.getpid() == 1: return
    log(f"准备退出，等待所有子进程结束后执行清理...")
    try_showerr(lambda: Path(f'{si.outest_sbxdir}_exit').touch() ) # 设个正在退出的标记
    try_showerr(lambda: Path(f'{si.outest_sbxdir}/EXITING').touch() )
    # if OG and OG.layer1_pid: try_pass(lambda: os.setpgid(OG.layer1_pid, 0) )
    try_pass(lambda: OutestProcsMonitor.sbx_exit_broadcast())

    cleanup_startat = time.monotonic()
    while exist_childtree() and time.monotonic() <= cleanup_startat+5: time.sleep(0.1)

    # NOTE 不要对那些可能挂载的目录用递归删除!  # 要删除那种目录的话只能用 rmdir （只删空的目录）
    # 因为有挂载，递归删除可能会误删重要文件。危险！ # 例如:
        # new.*.rootfs/
        # apps/*/
    paths_rm_sub_files = [ #准备删这些目录的一级子文件和目录本身
        *glob(f'{si.outest_sbxdir}/temp'),
        *glob(f'{si.outest_sbxdir}/apps'),
        *glob(f'{si.outest_sbxdir}/new.*.rootfs'),
        *glob(f'{si.outest_sbxdir}'),
    ]
    def safe_call(f):
        try: return f()
        except Exception as err: traceback.print_exc(file=sys.stderr); return []
    for dirpath in paths_rm_sub_files:
        for f in safe_call(lambda: Path(dirpath).iterdir() ):
            if is_file(f) or f.is_symlink() or f.is_socket():
                try_showerr(lambda: f.unlink() )
        try_showerr(lambda: os.rmdir(dirpath) )

    # try_showerr(lambda: os.rmdir(si.CG_SBX)) # 暂时无法删除
    try_pass(lambda: os.rmdir(si.sharedir_onhost))

    for slkItem in cleanup_symlinks_to_rm:
        if Path(slkItem).is_symlink() :
            linkto = os.readlink(slkItem)
            if linkto == si.outest_sbxdir or linkto.startswith(f'{si.outest_sbxdir}/'):
                try_showerr(lambda: Path(slkItem).unlink() )
    if not os.path.lexists(si.outest_sbxdir): os.unlink(f'{si.outest_sbxdir}_exit') # 清除正在退出标记

#==========================================
#======= libc 工具函数 =========================
libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)

def set_proc_dispname(dispname):
    PR_SET_NAME = 15
    CHK( len(name_bytes := dispname.encode("utf-8")) <= 15 , f"进程名 {dispname} 大小超过15")
    libc.prctl(PR_SET_NAME, name_bytes, 0, 0, 0)

MS = types.SimpleNamespace(RDONLY=0x01, NOSUID=0x02, NODEV=0x04, NOEXEC=0x08,  REMOUNT=0x20, NOSYMFOLLOW=0x100, BIND=0x1000, MOVE=0x2000, REC=0x4000,  UNBINDABLE=1<<17, PRIVATE=1<<18, SLAVE=1<<19, SHARED=1<<20, )
def mount(source, target, fstype, flags, data): # source可能空, 或为tmpfs或proc， target一定有
    allowed_nonabs = ['tmpfs', 'proc', 'devpts']
    if not ( (source is None) or (source in allowed_nonabs) or (source.startswith('/')) ):
        raise_exit(f"mount的来源{source}不是绝对路径，且不在允许的{allowed_nonabs}之内")
    if isinstance(source, str) and source.startswith('/'):
        source = napath(source)
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

    show_clear_result = False
    log('降权前', get_caps_dict()) if show_clear_result else None
    capset_clear(eff=False , prm=True, inh=True,  doprint=show_clear_result)
    log('清除中', get_caps_dict()) if show_clear_result else None
    amb_clear(doprint=show_clear_result)
    log('清除中', get_caps_dict()) if show_clear_result else None
    set_nonewpriv(doprint=show_clear_result)
    log('清除中', get_caps_dict()) if show_clear_result else None
    bnd_clear(si.BND_MAX,  doprint=show_clear_result)
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
    for cap_id in range(si.BND_MAX +1): # 内核只支持0~40
        CHK( libc.prctl(PR_CAPBSET_READ, cap_id, 0, 0, 0) == 0, f'cap_id {cap_id} 降权失败')



def set_pdeathsig(): # 由layer1的fork出来的子进程调用, 让真实父进程退出后沙箱内能够收到TERM信号
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
    if is_dir(path): raise_exit(f"{path}已是文件夹")
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

def run_a_cmd(cmdv, print_output=False):
    prc = subprocess.Popen(cmdv,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, bufsize=1, universal_newlines=True
                         )
    stdout_data, _ = prc.communicate()
    # prc.wait()
    if print_output: log(stdout_data)
    if prc.returncode != 0: raise_exit(f"命令运行未成功（{prc.returncode}） {stdout_data}")

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

def is_file(path):
    return not Path(path).is_symlink() and Path(path).is_file()
def is_dir(path):
    return not Path(path).is_symlink() and Path(path).is_dir()
def is_blockdev(path):
    return not Path(path).is_symlink() and Path(path).is_block_device()
def is_chardev(path):
    return not Path(path).is_symlink() and Path(path).is_char_device()
def is_dev(path):
    return is_chardev(path) or is_blockdev(path)
def is_fifo(path):
    return not Path(path).is_symlink() and Path(path).is_fifo()
def is_socket(path):
    return not Path(path).is_symlink() and Path(path).is_socket()
def is_ro(path):
    return os.statvfs(path).f_flag & MS.RDONLY

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
class DotDict(EnhancedDict):
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return self[name]

d = EnhancedDict
D = DotDict

loghead = ''
def set_loghead(new_loghead):
    global loghead
    loghead = new_loghead
def log(*args, **kwargs):
    new_args = args
    if loghead:
        new_args = ( loghead,  *args)
    print(*new_args, **kwargs)

def try_pass(func):
    try:
        return func()
    except:
        pass

def try_showerr(func):
    try:
        return func()
    except Exception as err:
        traceback.print_exc(file=sys.stderr)


def raise_exit(err_msg, no_cleanup=False):
    traceback.print_stack(file=sys.stderr)
    print(loghead + err_msg, file=sys.stderr)
    wlog('error', errmsg=err_msg)
    if not no_cleanup: sys.exit(1)
    else: os._exit(1)

def CHK( condition, errmsg='某项检查失败', action='raise_exit'):
    if not condition:
        if action == 'raise_exit': raise_exit(errmsg)
        elif action == 'warn': log(f"警告: {errmsg}", file=sys.stderr)

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

ICEWM_PREF='''
ShowStartMenu=0
SystemTray=0

TaskBarShowClock=0
TaskBarShowCPUStatus=0
TaskBarShowMEMStatus=0
TaskBarShowMailboxStatus=0
TaskBarShowBatteryStatus=0
TaskBarShowNetStatus=0
TaskBarShowAPMStatus=0

Workspaces=0
WorkspaceNames="Main"
EnableWorkspaces=0
#ShowWorkspaceSwitcher=0
#ShowWorkspaces=0
'''

def get_appimg_sqoffset(appimg_path):
    with open(appimg_path, 'rb') as f: elfHeader = f.read(64)
    (bitness,endianness) = struct.unpack("4x B B 58x", elfHeader);
    (shoff,shentsize,shnum) = struct.unpack(
        (">" if endianness == 2 else "<") +
        ("40x Q 10x H H 2x" if bitness == 2 else "32x L 10x H H 14x"),
        elfHeader
    );
    return (shoff + shentsize * shnum)

#=====================================================

if __name__ == "__main__":
    # 获得调用py脚本的文件位置信息，一般仅用于顶层得多，子容器内用得少
    scriptfilepath = os.path.abspath(__file__)
    scriptdirpath = os.path.dirname(scriptfilepath)  # 获取脚本所在目录
    scriptdirname = os.path.basename(scriptdirpath) # 获取脚本所在目录名
    scriptname = os.path.basename(scriptfilepath)  # 获取脚本文件名（含扩展名）
    scriptnamenoext = os.path.splitext(scriptname)[0]  # 获取脚本文件名（不含扩展名）
    try:
        main()
    except Exception as err:
        wlog('error', errmsg=err)
        raise
