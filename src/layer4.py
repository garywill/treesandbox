from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量


def gen_layer4(si, uc, dyncfg):
    return d( # 主 用户app 在这里跑
        layer_name='layer4', # 默认模板的 layer_name 不要修改
        is_mainlyr=True,  # 我是主app所在层
        unshare_pid=True, unshare_mnt=True,

        envset_grps = [
            d(PATH=getenv("PATH").rstrip(':')+':/sbxdir/apps' ),
            uc.set_envs if uc.set_envs else {},
        ],

        start_after = [
            d(waittype='socket-listened', path=f'/tmp/.X11-unix/X{si.newXId}') if uc.gui in ['xephyr', 'weston-xwayland','xpra', 'xpra-weston-xwayland'] else None,
            d(waittype='socket-listened', path=f'/tmp/dbus-session.socket') if uc.dbus_session else None,
            # TODO 等待icewm, 如果需要
        ],
        # user_shell=True, # 调试用
        # dev_shell=True,  # 调试用
    )