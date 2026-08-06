from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量


def gen_layer4c(si, uc, dyncfg):
    return d(
        layer_name='layer4c', # 默认模板的 layer_name 不要修改
        unshare_pid=True, unshare_mnt=True,
        unshare_net=True, # NOTE 内部xpra所带出来的dbus可能监听抽象套接字。最好unshare_net, 否则因为我们不要求认证，其他沙箱不隔离网络就可能偷看这个, 也可以考虑用unshare -n -r -c 来启动Xorg
        subprocs=[
            *([
            d( subp_name='icewm', cmdvec=['env', 'LC_ALL=en_US.UTF8', 'env', 'LANG=en_US.UTF8', 'env', 'LANGUAGE=en_US.UTF8', 'icewm-session', '--nobg'] ,
              start_after = [
                  d(waittype='socket-listened', path=f'/tmp/.X11-unix/X{si.newXId}'),
                  d(waittype='socket-listened', path=f'/tmp/dbus-session.socket') if uc.dbus_session=='isolated' else None,
                ]
            ) ,
            # d( subp_name='icewmtray', cmdvec=["icewmtray"] ,  start_after = [ d(waittype='socket-listened', path=f'/tmp/.X11-unix/X{si.newXId}') ] ) ,
            ] if dyncfg.icewm else [] ) ,

            d( subp_name='xwayland',  cmdvec=['env', f'WAYLAND_DISPLAY=wayland-{si.newXId}', 'Xwayland', f':{si.newXId}', '-nolisten', 'local', *dyncfg.xwayland_extra_args ]
            ) if uc.gui in ['weston-xwayland', 'xpra-weston-xwayland'] else None,

            d( subp_name='xvfb', cmdvec=["Xvfb", "+extension", "GLX", "+extension", "RANDR", "+extension", "RENDER", "+extension", "Composite", "-extension", "DOUBLE-BUFFER", "-nolisten", "tcp", "-nolisten", "local", "-noreset", "-ac",  f":{si.newXId}"] ) if uc.gui=='xpra' else None,

            d( subp_name='xpraserver' ,  cmdvec=['env', 'XPRA_PRIVATE_XAUTH=1', 'env', 'XPRA_PASSWORD=abc', 'xpra', 'start', *dyncfg.xpra_extra_args, *dyncfg.xpra_server_extra_args, f':{si.newXId}'], start_after = [ d(waittype='socket-listened', path=f'/tmp/.X11-unix/X{si.newXId}') ]
            ) if uc.gui in ['xpra', 'xpra-weston-xwayland'] else None,

            d( subp_name='dbus_daemon_session', cmdvec=['dbus-daemon',  '--session',  '--address=unix:path=/tmp/dbus-session.socket'] ) if uc.dbus_session=='isolated' else None,
        ],
    )