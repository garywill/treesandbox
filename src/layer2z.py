from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量



def gen_layer2z(si, uc, dyncfg):
    return d( # layer2z 作为 layer2和3之间，把layer2的/zrootfs变回真/，准备让layer3接
        layer_name='layer2z',  unshare_mnt=True,
        start_after=[
            d(waittype='socket-listened', path='/tmp/dbusproxy.socket') if uc.dbus_session=='filter' else None,
            d(waittype='socket-listened', path=f'/tmp/.X11-unix/X{si.newXId}') if uc.gui=='xephyr' else None,
            d(waittype='socket-listened', path=f'{si.sbx_XDG_R_D}/wayland-{si.newXId}') if uc.gui in ['weston-xwayland', 'xpra-weston-xwayland'] else None,
        ],
        newrootfs=True,
        fs=[
            d(many_op='dup-rootfs', srcbase='/zrootfs'),
            d(many_op='sbxdir-in-newrootfs', dest='/sbxdir'),

            d(op='robind', src=f'/tmp/.X11-unix/X{si.newXId}', dest=f'/sbxdir/temp/X{si.newXId}') if uc.gui=='xephyr' else None,
            d(op='robind', src=f'{si.sbx_XDG_R_D}/wayland-{si.newXId}', dest=f'/sbxdir/temp/wayland-{si.newXId}') if uc.gui in ['weston-xwayland', 'xpra-weston-xwayland'] else None,
            d(op='robind', src='/tmp/dbusproxy.socket', dest='/sbxdir/temp/dbusproxy.socket') if uc.dbus_session=='filter' else None,
        ],
        sublayers=[ gen_layer3(si, uc, dyncfg) ],
    )