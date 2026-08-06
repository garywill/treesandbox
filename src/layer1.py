from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量


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