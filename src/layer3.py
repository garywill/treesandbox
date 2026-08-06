from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量


def gen_layer3(si, uc, dyncfg):
    return d(
        layer_name='layer3', # 默认模板的 layer_name 不要修改
        unshare_mnt=True,
        unshare_cgroup=True,
        unshare_ipc=True,
        unshare_time=True,
        unshare_uts=True,

        newrootfs=True, # 有newrootfs则必须有fs
        fs=[ # fs全称fs_operations_for_new_rootfs 。
            d(many_op='container-rootfs'),  # 不包括 dev 。不包括 proc
            d(many_op='sbxdir-in-newrootfs', dest='/sbxdir'),
            d(op='empty-if-exist', dest=rslvn(si.startscript_on_host)),

            # ---- 以上是不变条目 ----

            d(many_op='basic-dev') if not uc.see_real_hw else None, # 创建新的容器最小的/dev

            d(op='robind', src=f'/run/user/{si.uid}/pulse/native', SDS=1) if uc.pulseaudio else None,
            d(op='robind', src=rslvy('/var/run/cups/cups.sock'), SDS=1) if uc.cups else None,

            *([
            d(op='robind', src='/dev', SDS=1),
            d(op='tmpfs',dest='/dev/shm'),
            d(op='robind',  src='/sys/class', SDS=1),
            d(op='robind',  src='/sys/bus', SDS=1),
            d(op='robind',  src='/sys/devices', SDS=1),
            ] if uc.see_real_hw else [] ),
            # TODO 1. 改用dyncfg  2. layer2里也加

            *([
            d(op='robind', dest=f'/tmp/.X11-unix/X{getenv("DISPLAY").lstrip(":")}', SDS=1),
            d(op='robind', dest='/tmp/xauthfile', src=f'{getenv("XAUTHORITY")}'),
            ] if uc.gui=='realX' else [] ),

            d(op='robind', src=f'/sbxdir/temp/X{si.newXId}', dest=f'/tmp/.X11-unix/X{si.newXId}') if uc.gui=='xephyr' else None,
            d(op='robind', src=f'/sbxdir/temp/wayland-{si.newXId}',  dest=f'{os.getenv("XDG_RUNTIME_DIR")}/wayland-{si.newXId}', ) if uc.gui in ['weston-xwayland', 'xpra-weston-xwayland'] else None,

            *dyncfg.mnts_gui,

            d(op='rofile', dest=shutil.which("xdg-open"), destmode='555', content=ASK_OPEN ) if uc.ask_xdg_open else None,
            *[d(op='empty-if-exist', dest=path) for path in dyncfg.paths_to_mask],

            d(op='robind', dest='/tmp/dbus-session.socket',  src=getenv('DBUS_SESSION_BUS_ADDRESS').removeprefix('unix:path=')) if uc.dbus_session == 'allow' else None,
            d(op='robind', dest='/tmp/dbus-session.socket', src='/sbxdir/temp/dbusproxy.socket') if uc.dbus_session=='filter' else None,

            d(op='empty-if-exist', dest='/etc/fstab'),
            d(op='empty-if-exist', dest=rslvn('/etc/os-release')) if uc.mask_osrelease else None,
            d(op='rofile', dest='/etc/machine-id', content=dyncfg.machineid) if dyncfg.machineid else None,

            *dyncfg.mnts_dns,

            *([
            d(op='tmpfs',  dest=f'{si.HOME}/.icewm'),
            d(op='rofile', dest=f'{si.HOME}/.icewm/preferences', content=ICEWM_PREF),
            d(op='rofile', dest=f'{si.HOME}/.icewm/prefoverride', content=ICEWM_PREF),
            # d(op='rofile', dest=f'{si.HOME}/.icewm/winoptions', content=ICEWM_WINOPTIONS),# 让app无法决定新窗口位置
            d(op='rofile', dest=f'{si.HOME}/.icewm/menu', content=''),
            d(op='rofile', dest=f'{si.HOME}/.icewm/toolbar', content=''),
            d(op='rofile', dest=f'{si.HOME}/.icewm/programs', content=''),
            ] if dyncfg.icewm else [] ),

            *([
            d(op='bind', src=si.sharedir_onhost, dest='/tmp/share'),
            d(op='bind', src=si.sharedir_onhost, SDS=1),
            ] if si.sharedir_onhost else []),

            # NOTE 用户挂载要放最后
            *(uc.user_mnts if uc.user_mnts else []), # NOTE 用户挂载要放最后
            d(op='final-rmt-ro', dest='/sbxdir/apps', flag=mntflag_apps)
        ],
        envs_unset=[
            "ICEAUTHORITY", "XAUTHORITY", "DISPLAY", "WAYLAND_DISPLAY", "XAUTHLOCALHOSTNAME", "IBUS_ADDRESS", "DBUS_SESSION_BUS_ADDRESS", "DBUS_SYSTEM_BUS_ADDRESS",
            "XDG_SESSION_DESKTOP", "XDG_CURRENT_DESKTOP", "KDE_FULL_SESSION", "KDE_APPLICATIONS_AS_SCOPE", "KDE_SESSION_UID", "KDE_SESSION_VERSION", # TODO 如果用户主机不是KDE是其他, 会有其他变量需要去除
        ],
        envset_grps=[
            d( DISPLAY=getenv("DISPLAY"), XAUTHORITY='/tmp/xauthfile', ) if uc.gui=='realX' else None,
            d(DISPLAY=f':{si.newXId}') if uc.gui in ['xephyr','weston-xwayland','xpra', 'xpra-weston-xwayland'] else None,
            # d(WAYLAND_DISPLAY=f'wayland-{si.newXId}') if uc.gui in ['weston-xwayland', 'xpra-weston-xwayland'] else None, # 先不要 WAYLAND_DISPLAY 这个环境变量，让应用都使用 Xwayland 先
            d(DBUS_SESSION_BUS_ADDRESS='unix:path=/tmp/dbus-session.socket') if uc.dbus_session else None,
            d(DESKTOP_SESSION='icewm-session', XDG_SESSION_DESKTOP='ICEWM', XDG_CURRENT_DESKTOP='ICEWM' ) if dyncfg.icewm else None,
        ],
        sublayers=[
            gen_layer4c(si, uc, dyncfg),
            gen_layer4(si, uc, dyncfg),
        ],
    )