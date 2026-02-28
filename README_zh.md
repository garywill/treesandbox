# Tree Sandbox

又一Linux沙箱。可作为Firejail、Flatpak、Bubblewrap的补充。

“树形”沙箱，可配置多层嵌套、分枝，像由多个子容器组成的“树”。


## 开发目标

以下对比表格是本项目的开发计划。（目前处于早期工作，有些未实现）

## 什么是"容器树"

本工具设计成一个沙箱由多层子容器构成，它们连成一棵“容器树”，“树”可以有多个分枝和容器节点。容器节点之间的“连接”可以是各类互相 已unshare 或 未unshare 的 namespace（Linux有pid/mnt/net等各类ns）。

“不信任”进程 与 “半信任”进程 可在一个沙箱的不同层运行。用户要运行的 主app 与其他辅助进程在不同的层运行。

可精细控制每层隔离程度、每层可见文件范围。可无限嵌套。

以下是一个例子，沙箱容器树可能是像这样的：

```verilog
[Linux Host]
    主机X11
    主机DBUS服务
    
    [TreeSandbox沙箱] 
     |
     |--[子容器:不信任空间] 
     |   |
     |   |--[子容器:用户App:不信任] 
     |   |      用户的App在这里跑
     |   |  
     |   |--[子容器:辅助进程(组2):不信任] 
     |          内部的X11服务
     |          内部的DBUS服务
     |          
     |--[子容器:辅助进程(组1):半信任]
            在内、外部X11之间转发的进程
            DBUS通信代理和过滤进程
```




## 功能列表与完成状态

- [x] 不需root；不需守护进程；不需任何主机的Cap或suid；不需要subuid/subgid
- [x] 不留痕，不在家目录留下文件。`/tmp`等处的临时文件自动清理
- [x] 无镜像容器。不需要像Docker、LXC那样下载系统镜像。用现有真实系统作为基础，内部诸如vim、git等工具无需重复安装
- [x] 可完全自定义的多层嵌套namespace
    - [x] 每层与其上层之间pid ns、mount ns 等 每种namespace的隔离与否(是否unshare)选项控制
    - [x] 每层的新rootfs挂载细粒度文件系统建立列表控制
        - [x] bind挂载(rw/ro)目录、文件、套接字、字符设备，symlink，tmpfs 等
        - [ ] overlay
    - [x] 每层内部环境变量控制
- [x] 启动时内部uid变0（提权）；进程uid变回1000(降权）；Drop caps；noNewPrivs
- [ ] PGID、SID分离，并正确传递信号
- [x] 可挂载AppImage、squashfs在内部mount ns
- 沙箱内使用GUI
    - [x] 可选暴露真实X11接口给沙箱
    - [x] 可选使用Weston+Xwayland隔离X11（配icewm）
    - [x] 可选使用Xephyr隔离X11（配icewm）
    - [x] 可选使用Xpra隔离的无缝X11代理
    - [ ] 可选暴露wayland接口给沙箱
    - [ ] 可选在一窗口内运行的隔离的完整桌面环境
    - [x] 可选同步剪贴板（从沙箱到主机。反过来可暂时用IME的粘贴功能替代）
- 可选暴露真实物理硬件给沙箱
    - [x] 暴露GPU给沙箱
    - [x] 暴露所有硬件给沙箱
- DBus
    - [x] 可选暴露真实dbus接口给沙箱
    - [x] 可选过滤dbus通信
- [x] 可选的网络控制
    - [x] 主机与沙箱之间双向、单向端口范围暴露、访问控制（tun，由pasta管理。可通过 localhost:端口号 互访）
    - [x] 内部nftbles规则自定义
- 同名沙箱的：单App、多App；单实例、多实例（启动App选择、实例管理、命令参数传递）
    说明：以用户设置的`sandbox_name`来识别“同名沙箱”）
    - [x] 同名沙箱可设置多个app，启动时可指定app（例如我们可把同一厂商出品的不同app可以放同一沙箱里，便于它们之间交互）
    - [x] 同名沙箱多实例（从主机多次启动同名沙箱，会运行多个实例，互相隔离、互相独立)
    - [x] 同名沙箱单实例（从主机启动一种App的沙箱后，再次启动同名App的沙箱，则传递命令参数至已运行的沙箱。
- [x] 容器内部shell接口暴露给主机，主机随时进入
- [x] 可选暴露pulseaudio接口给沙箱
- [x] 可选暴露CUPS接口给沙箱
- [x] 看门狗（若沙箱内app或辅助app退出，则结束沙箱）
- 单文件脚本，随处复制，依使用需求修改头部选项。免安装，精简依赖


## 依赖

必须：

- Linux Kernel >= 6.3 
    - user namespace
    - cgroup v2
- glibc
- Python >= 3.12
- bash

(虽然是Python脚本，但通过libc直接调用Linux内核功能，不需第三方Python库)

可选：

- dtach (共享shell给主机)
- xdg-dbus-proxy
- pasta (tun网络介面)
- nftables (网络流量控制)
- xpra (隔离X11。无缝显示)
- Weston + Xwayland + icewm (隔离X11)
- Xephyr + icewm (隔离X11)
- xsel (同步剪贴板)
- squashfuse (内部AppImage、squashfs挂载)
- zenity 或 kdialog (内部阻止随意的网页等弹窗而改用询问)


## 简单用例 

以下几个简单例子中，沙箱内app进程都只能看到只读的系统基础目录、空白的家目录，和用户明确指定了可见的路径或接口。

**例子1：** 沙箱内运行下载的AppImage文件

从网络下载任意app的`.AppImage`文件。

复制一份TreeSandbox的`.py`脚本，与下载的AppImage放在一起:

```
/anyhdd/freecad/sbxrun_freecad.py
/anyhdd/freecad/FreeCAD.AppImage
/anyhdd2/projects_save/
```

编辑我们的`.py`文件，配置`userconfig`部分：

```python
uc.sandbox_name='freecad' # 沙箱名称
uc.user_mnts = [
    d(many_op='appimage', dirname='freecad',  src=f'{si.CWD}/FreeCAD.AppImage'),
    d(op='bind', src='/anyhdd2/projects_save/', SDS=1), 
]
uc.gui="realX" # 使用真实的 X11
```

TreeSandbox实现了在内部预先挂载AppImage，不需要把fuse挂载权限给AppImage。会把AppImage里的内容挂载到沙箱内的`/sbxdir/apps/freecad/`下。 启动沙箱后，在内运行`/sbxdir/apps/run_freecad`即启动我们的app。

沙箱内app所创建的工程可以保存在`/anyhdd2/projects_save/`下（用了`SDS`挂载工程目录，沙箱内外皆以同一路径访问此目录，`SDS`是"src and dest are same"的缩写）

**例子2：** 沙箱内运行下载的二进制程序

例如下载`firefox.tar.xz`, 解压，像上例一样把解压出来的文件和复制的一份TreeSandbox的`.py`脚本放一起:

```
/anyhdd/ffx/sbxrun_firefox.py
/anyhdd/ffx/firefox/.... (内含firefox-bin, *.so 等 解压出来的文件)
/anyhdd/ffx/fakehome
```

编辑我们的`.py`文件，配置：

```python
uc.sandbox_name='firefox' # 沙箱名称
user_mnts = [
    d(op='robind', src=f'{si.CWD}/firefox', SDS=1), 
    # 也可以去掉上面的`SDS`而改为`dest='/sbxdir/apps/firefox'`。
    d(op='bind', src=f'{si.CWD}/fakehome', dest=si.HOME), 
]
uc.gui="realX" # 使用真实的 X11
uc.dbus_session="filter" # 输入法等通信需要dbus
```


**例子3：** 沙箱内直接使用自己的vimrc配置

```python
uc.user_mnts = [
    d(op='robind', src=f'{si.HOME}/.vimrc', SDS=1), 
]
```

## 沙箱分层结构

这是个可以自由嵌套的沙箱。脚本内已经设置有默认的嵌套模板：

```
Linux Host 
  |
 layer1 (用于统一管理；隔离pid ns；内部提权)
  |
 layer2 (半信任空间：隔离mount ns；屏蔽用户设置的全局屏蔽路径）
   |
   |--layer2c (降权；用于运行信任的辅助程序，如 xpra client、dbus-proxy ...）
   |
 layer2h (过度)
    |
  layer3 (不信任空间：隔离所有ns；
    |       可见系统基础目录，其余仅用户挂载进去的路径可见）
    |
    |--layer4 (降权；用于运行用户的App)
    |--layer4c (降权；用于运行不信任的辅助程序，如 xpra server ...)
```

（layer2c和layer4c都用于运行辅助程序，区别在于layer2c可以访问真实的X11接口、dbus接口，而layer4c则不需要访问这些）

**以上这个默认的嵌套模板普通用户不需要修改，只需要修改用户选项部分**即可。

沙箱成功启动后，用户获得的 user shell （如果要） ，或所运行的App，是在layer4内。

> 本项目处于早期阶段，不排除以后有修改设计的可能性

模板设置方式类似如下：（进阶用户了解）

```python
layer1 = d( # 第1层
    layer_name='layer1', # 默认模板的 layer_name 不要修改
    unshare_pid=True, unshare_user=True, ......
    
    sublayers = [
        d( # 第2层
            layer_name='layer2', # 默认模板的 layer_name 不要修改
            unshare_pid=True, unshare_mnt=True, ....
            newrootfs=True, fs=[ ..... ], ....
            
            sublayers = [
                d( layer_name='layer2c', .... ), 
                d( 
                    layer_name='layer2h', 
                    sublayers = [
                        d( layer_name='layer3', ..... , newrootfs=True, fs=[ ..... ], .....
                            sublayers=[ # 第4层
                                d( layer_name='layer4', .....  , user_shell=True ),
                                d( layer_name='layer4c', ..... ),
                            ],
                        ),
                    ] 
                )
            ],
        )
    ],
)
```
以上只是非常粗略地展示一下默认模板，想要了解的请打开代码查看。

## 启动流程

每层容器启动及配置流程：

1. 读取本层配置
1. 根据配置进行unshare（开始ns隔离）
1. fork。以下步骤都在子进程中执行
1. 根据配置进行`/proc/self/uid_map`等写入（内部提权、降权）
1. 根据配置建立及挂载本层的新rootfs
1. 根据配置进行pivot_root
1. 根据配置修改环境变量
1. 根据配置降权
1. 根据配置启动 user shell ，或启动下一层子容器，或启动某app

> 本项目处于早期阶段，不排除以后有修改设计的可能性

## 沙箱内文件系统

一般来说，沙箱内所运行的“不信任app”所看到的文件系统类似如下：

```yml
// # 真实的系统目录
{'op': 'robind', 'dest': '/bin', 'src': '/bin'}
{'op': 'robind', 'dest': '/etc', 'src': '/etc'}
{'op': 'robind', 'dest': '/lib64', 'src': '/lib64'}
.....

// # 最小的/dev
{'op': 'rotmpfs', 'dest': '/dev'}
{'op': 'bind', 'dest': '/dev/console', 'src': '/dev/console'}
{'op': 'bind', 'dest': '/dev/null', 'src': '/dev/null'}
{'op': 'bind', 'dest': '/dev/random', 'src': '/dev/random'}
{'op': 'devpts', 'dest': '/dev/pts'}
{'op': 'tmpfs', 'dest': '/dev/shm'}
......

// # 创建空的临时目录
{'op': 'tmpfs', 'dest': '/home/username'}
{'op': 'tmpfs', 'dest': '/run'}
{'op': 'tmpfs', 'dest': '/run/user/1000'}
{'op': 'tmpfs', 'dest': '/tmp'}
......

// # 以下根据用户配置情况而变
{'op': 'appimg-mount', 'src': '/anyhdd/freecad/FreeCAD.AppImage', 'dest': '/sbxdir/apps/freecad'}
{'op': 'robind', 'src': '/anyhdd/ffx/firefox', 'dest': '/sbxdir/apps/firefox'}
{'op': 'robind', 'dest': '/tmp/.X11-unix/X0', 'src': '/tmp/.X11-unix/X0'}
{'op': 'robind', 'dest': '/tmp/dbus-session.socket', 'src': '/run/user/1000/bus'}

// # 沙箱配置目录
{'many_op': 'sbxdir-in-newrootfs', 'dest': '/sbxdir'}
```

（以上所列文件系统已经写进模板里，不需要用户去创建）

`/sbxdir`是TreeSandbox沙箱所需要的目录，它包含：

- AppImage挂载点（与普通用户有关，以下其余普通用户可以不了解）
- 本层及本层的子层的配置信息
- 本层与layer1及与主机通信所需要的文件
- 启动子层所用的脚本
- 子层的新rootfs挂载点
- ...

## 如何编辑多层嵌套模板

TBD
