from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量


def gen_layer2(si, uc, dyncfg):
    return d(
        layer_name='layer2', # 默认模板的 layer_name 不要修改
        unshare_mnt=True,
        newrootfs=True, # 第2层必须 # 有newrootfs则必须有fs
        fs=[ # fs全称 fs_operations_for_new_rootfs 。
            # 第2层是首次 unshare mnt 。先复制一次真实host的rootfs环境
            d(many_op='container-rootfs'),
            d(many_op='basic-dev'),
            d(op='rosame', src='/dev/net/tun', SDS=1) if uc.net_iface=='tuntap-pasta' else None,
            d(many_op='mask-privacy', destbase='/'),
            d(many_op='sbxdir-in-newrootfs', dest='/sbxdir'),

            *dyncfg.mnts_gui,

            d(op='robind', src=f'/tmp/.X11-unix/X{getenv("DISPLAY").lstrip(":")}', SDS=1),
            d(op='robind', src=f'{getenv("XAUTHORITY")}', SDS=1),

            d(op='bind', src=getenv('DBUS_SESSION_BUS_ADDRESS').removeprefix('unix:path='), SDS=1 ),

            d(many_op='dup-rootfs', destbase='/zrootfs'), # 排除/proc。不加ro。
            d(many_op='mask-privacy', destbase='/zrootfs'),
            d(op='empty-if-exist', dest=f'/zrootfs/{si.PTMP}'),
        ],
        envs_unset=[
            "SYSTEMD_EXEC_PID", "MANAGERPID", "SSH_AGENT_PID", "SSH_AUTH_SOCK",  "WINDOWMANAGER", "SHELL_SESSION_ID", "INVOCATION_ID", "GPG_TTY", "XDG_SESSION_ID", "KONSOLE_DBUS_SERVICE", "GPG_AGENT_INFO", "OLDPWD", "WINDOWID", "SESSION_MANAGER", "JOURNAL_STREAM",  "XDG_CACHE_HOME",
            "XDG_SESSION_TYPE", "WAYLAND_DISPLAY", "QT_WAYLAND_RECONNECT", # 这几个是因为现在暂时不支持主机wayland所以放这里先
        ],
        envset_grps=[
            d(NO_AT_BRIDGE='1'),
            d(XDG_RUNTIME_DIR=si.sbx_XDG_R_D),
        ],

        create_userns_unpri=True,

        unshare_net=True if uc.net_iface == 'none' else False,
        pasta_args = uc.pasta_custom_args if uc.net_iface=='tuntap-pasta' else None, # 运行pasta, 并把自身加入其新netns
        nftables_rule = uc.nftables_rule if uc.set_nftables else None,

        sublayers = [
            gen_layer2c(si, uc, dyncfg),
            gen_layer2z(si, uc, dyncfg),
        ],
    )