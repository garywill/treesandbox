# Tree Sandbox

可无限嵌套的Linux沙箱。

一定程度上可作为Firejail、Flatpak、Bubblewrap的替代品。

## 什么是"容器树"

本工具设计成可以层层嵌套创建许多子namespace。你可以配置出想要的容器树。

“不信任”进程 与 “半信任”进程 可在一个沙箱的不同层运行。

可精细控制每层隔离程度、每层可见文件范围。可无限嵌套。

以下是一个例子，沙箱容器树可能是像这样的：

```verilog
[Linux Host]
    [X11] (真实桌面)
    [dbus-daemon --session] (A) (真实dbus用户服务)
    [fcitx5-daemon] (真实输入法)
    
    [TreeSandbox沙箱] 
     |--[子容器:不信任空间] 
     |   |
     |   |--[子容器:用户App:不信任] 
     |   |      [用户的App在这里跑]
     |   |  
     |   |--[子容器:辅助进程(组2):不信任] 
     |          [Xpra X server] (隔离的X11服务端)
     |          [dbus-proxy] (C) (分流转发用户dbus通信到内部(D)和外部(B))
     |          [dbus-daemon --session] (D) (内部的用户dbus服务)
     |          [dbus-daemon --system] (内部的系统级dbus)
     |          [keyring] (内部的Keyring服务)
     |          [icewm] (轻量级WM,一般配合Xephyr)
     |          
     |--[子容器:辅助进程(组1):半信任]
            [Xephyr] (隔离X11服务端+客户端)
            [Xpra client] (无缝隔离X11客户端)
            [dbus-proxy] (B) (dbus通信过滤和转发在A与C之间转发)
        
（以上并非全都用到，会根据选项决定启动哪些）
```

（上例中，有两个子容器用于运行辅助进程，区别在于“半信任”那个可以访问真实的X11接口、dbus接口，而“不信任”那个则无法访问这些。）


## 为什么做这个？它安全性如何？

我暂时把它称为Firejail/Flatpak替代品。Bubblewrap等工具我也用过，它们不让用户控制每一个细节，就连官方工具unshare也是，因此自己做一个完全可控的。主攻其他工具不支持的沙箱多层namespace无限嵌套，和便捷的容器树配置。

在开箱即用性方面，TreeSandbox介于Firejail和Bubblewrap之间。TreeSandbox没有像Firejail那样为每种App适配一种模板，而TreeSandbox有一个内置的、可随用户选项灵活适应的默认模板，可以覆盖95%的情景，因此比Bubblewrap方便。甚至如果高级用户愿意去修改模板，则可达到比Bubblewrap更强的控制力。

这个项目处于早期，可以使用，但要知道，目前无专业团队参与。

## 功能列表与完成状态

- [x] 不需root；不需守护进程；不需任何主机的Cap或suid
- [x] 不留痕，不主动在家目录或硬盘任何位置留下文件。`/tmp`内的临时文件自动清理
- [x] 无镜像容器。不需要像Docker、LXC那样下载系统镜像。用现有真实系统作为基础，内部诸如vim、git等工具无需重复安装
- [x] 可完全自定义的多层嵌套namespace
    - [x] 每层pid ns、mount ns 等 每种namespace的隔离选项控制
    - [x] 每层的新rootfs挂载与细粒度文件系统路径建立方式控制
        - [x] bind挂载(rw/ro)
        - [ ] 文件夹overlay
        - [x] 创建或临时覆盖文件及其内容(rw/ro)；tmpfs目录(rw/ro)
        - [x] symlink
    - [x] 内部环境变量控制
    - [x] 内部uid变0（提权）；某层uid变回1000(降权）；Drop caps；noNewPrivs
- [x] 可挂载AppImage在内部mount ns
- 沙箱内使用GUI
    - [x] 可选暴露真实X11接口给沙箱
    - [x] 可选使用Xephyr隔离X11
    - [ ] 可选使用Xpra隔离的无缝X11代理
    - [ ] 可选暴露wayland接口给沙箱
    - [ ] 可选在一窗口内运行的隔离的完整桌面环境
- [ ] 可选暴露真实物理硬件，或仅显卡渲染所需部分
- DBus
    - [x] 可选暴露真实dbus接口给沙箱
    - [ ] 可选过滤dbus通信
- [ ] 可选的seccomp
- [ ] 可选的网络流量控制
- 实例管理与命令参数传递
    - [x] 同种沙箱多实例（从主机多次启动同种沙箱，会运行多个实例，互相隔离、互相独立)
    - [ ] 同种沙箱单实例（从主机启动一种App的沙箱后，再次启动同种App的沙箱，则传递命令参数至已运行的沙箱。说明：以你设置的`sandbox_name`来区分“同种沙箱”）
- [ ] 容器内部shell接口暴露给主机
- 单文件脚本，随处复制，依使用需求修改头部选项。免安装，精简依赖

## 依赖

必须：

- Linux Kernel >= 6.3 (且支持unprivileged user namespace)
- glibc
- Python >= 3.12
- bash

(虽然是Python脚本，但直接通过libc调用Linux内核功能，不需第三方Python库)

可选：

- squashfuse (内部AppImage挂载)
- Xephyr + icewm (隔离X11)

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
    d(batch_plan='appimage', appname='freecad',  src=f'{si.startdir_on_host}/FreeCAD.AppImage'),
    d(plan='bind', src='/anyhdd2/projects_save/', SDS=1), 
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
```

编辑我们的`.py`文件，配置：

```python
uc.sandbox_name='firefox' # 沙箱名称
user_mnts = [
    d(plan='robind', src=f'{si.startdir_on_host}/firefox', SDS=1), 
    # 也可以去掉上面的`SDS`而改为`dest='/sbxdir/apps/firefox'`。
]
uc.gui="realX" # 使用真实的 X11
uc.dbus_session="allow" # 输入法等通信需要dbus
```

以上尚未挂载持久化的路径以保存浏览器profile目录。若需要，可创建一个`fakehome`目录

```
/anyhdd/ffx/sbxrun_firefox.py
/anyhdd/ffx/fakehome
/anyhdd/ffx/firefox/.... (内含firefox-bin, *.so 等 解压出来的文件)
```

并配置

```python
homedir=f'{si.startdir_on_host}/fakehome',
```

即可持久化保存沙箱内家目录文件。（`/anyhdd/ffx/fakehome`会被挂载到沙箱内的`/home/用户名`）

**例子3：** 沙箱内直接使用自己的vimrc配置

```python
uc.user_mnts = [
    d(plan='robind', src=f'{si.HOME}/.vimrc', SDS=1), 
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
   |--layer2a (降权；用于运行信任的辅助程序，如 xpra client、dbus-proxy ...）
   |
 layer2h (过度)
    |
  layer3 (不信任空间：隔离所有ns；
    |       可见系统基础目录，其余仅用户挂载进去的路径可见）
    |
    |--layer4 (降权；用于运行用户的App)
    |--layer4a (降权；用于运行不信任的辅助程序，如 xpra server ...)
```

（layer2a和layer4a都用于运行辅助程序，区别在于layer2a可以访问真实的X11接口、dbus接口，而layer4a则不需要访问这些）

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
                d( layer_name='layer2a', .... ), 
                d( 
                    layer_name='layer2h', 
                    sublayers = [
                        d( layer_name='layer3', ..... , newrootfs=True, fs=[ ..... ], .....
                            sublayers=[ # 第4层
                                d( layer_name='layer4', .....  , user_shell=True ),
                                d( layer_name='layer4a', ..... ),
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
{'plan': 'robind', 'dest': '/bin', 'src': '/bin'}
{'plan': 'robind', 'dest': '/etc', 'src': '/etc'}
{'plan': 'robind', 'dest': '/lib64', 'src': '/lib64'}
.....

// # 最小的/dev
{'plan': 'rotmpfs', 'dest': '/dev'}
{'plan': 'bind', 'dest': '/dev/console', 'src': '/dev/console'}
{'plan': 'bind', 'dest': '/dev/null', 'src': '/dev/null'}
{'plan': 'bind', 'dest': '/dev/random', 'src': '/dev/random'}
{'plan': 'devpts', 'dest': '/dev/pts'}
{'plan': 'tmpfs', 'dest': '/dev/shm'}
......

// # 创建空的临时目录
{'plan': 'tmpfs', 'dest': '/home/username'}
{'plan': 'tmpfs', 'dest': '/run'}
{'plan': 'tmpfs', 'dest': '/run/user/1000'}
{'plan': 'tmpfs', 'dest': '/tmp'}
......

// # 以下根据用户配置情况而变
{'plan': 'appimg-mount', 'src': '/anyhdd/freecad/FreeCAD.AppImage', 'dest': '/sbxdir/apps/freecad'}
{'plan': 'robind', 'src': '/anyhdd/ffx/firefox', 'dest': '/sbxdir/apps/firefox'}
{'plan': 'robind', 'dest': '/tmp/.X11-unix/X0', 'src': '/tmp/.X11-unix/X0'}
{'plan': 'robind', 'dest': '/tmp/dbus_session_socket', 'src': '/run/user/1000/bus'}

// # 沙箱配置目录
{'batch_plan': 'sbxdir-in-newrootfs', 'dest': '/sbxdir'}
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
