from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量


def gen_layer2c(si, uc, dyncfg):
    # layer2c实际上深度为3, 这层是为了运行可信程序如 xpra client , dbus proxy 等
    return d(
        layer_name='layer2c', unshare_pid=True, unshare_mnt=True,
        unshare_net=True, # 如果有些subp会监听抽象套接字，为了不被其他沙箱偷看，要隔离. 也可以考虑用 unshare -n -r -c 来启动它们
        newrootfs=True,
        fs=[
            d(many_op='dup-rootfs', destbase='/'),
            d(many_op='sbxdir-in-newrootfs', dest='/sbxdir'),
        ],
        is_semitruCmpannLyr=True, # 设layer2c（而非2）为semitruCmpannLyr,因为2c才有unshare_pid
        subprocs=[
            d( subp_name='xephyr', cmdvec=["Xephyr",  f":{si.newXId}", '-nolisten', 'local', "-resizeable",  "-ac", '-title', si.sandbox_name,  *dyncfg.xephyr_extra_args]
            ) if uc.gui=='xephyr' else None,

            d( subp_name='weston', cmdvec=["weston", f"--socket=wayland-{si.newXId}" ,  f"--shell=kiosk", *dyncfg.weston_extra_args]
            ) if uc.gui in ['weston-xwayland', 'xpra-weston-xwayland'] else None,

            d( subp_name='xpraclient', cmdvec=['env', 'XPRA_PASSWORD=abc', 'xpra', *dyncfg.xpra_extra_args, *dyncfg.xpra_client_extra_args,  'attach',f':{si.newXId}'],
                start_after = [
                    d(waittype='socket-listened', path=f'/tmp/.X11-unix/X{si.newXId}') ,
                    d(waittype='socket-listened', path=f'/run/xpra/{si.hostname}-{si.newXId}')
            ] ) if uc.gui in ['xpra', 'xpra-weston-xwayland'] else None,

            d( subp_name='dbusproxy',  cmdvec=['xdg-dbus-proxy', *dyncfg.dbusproxy_argv]
            ) if uc.dbus_session=='filter' else None,
        ],
        daemon_tasks = [
            d(task='sync_clipbd') if uc.gui in ['weston-xwayland', 'xephyr', 'xpra', 'xpra-weston-xwayland'] else None,
        ],
    )