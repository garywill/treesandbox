# Tree Sandbox for Linux

你一定玩过 Podman、Firejail、Flatpak、Bubblewrap ...

Tree Sandbox 是又一 Linux沙箱工具，可作为它们的补充。

“树形”沙箱，可配置多层嵌套、分枝，像由多个子容器组成的“树”。

## 一些术语

- Linux namespace (ns) 以及 其 几种种类: pid ns, mnt ns, ... 。是容器/沙箱的基础

- `unshare`状态 （以及 未`unshare`状态）。是 容器 与其 父容器 之间的 “连接关系”

以上相信你早就理解。

- “同名沙箱”。这是 Tree Sandbox 的概念。
    你有一个要隔离的App。
    当你想让<ins><u>相同App</u></ins>的沙箱<ins><u>单实例</u></ins>运行 (即，多次发送命令参数到<ins><u>运行中</u></ins>的沙箱，而不要启动沙箱多次) 时，“同名沙箱”是用于判断的依据。

## 与其他沙箱工具对比

### 与 Firejail / Flatpak 对比

### 与 Bubblewrap 对比

## 什么是"容器树"

Tree Sandbox 设计成一个沙箱由多层子容器构成，它们连成一棵“容器树”，“树”可以有多个分枝和容器节点。容器节点之间的“连接”可以是各类互相 “已unshare” 或 “未unshare” 的 namespace（Linux有pid/mnt/net等各类ns）。

“不信任”进程 与 “半信任”进程 可在一个沙箱的不同层运行。用户要运行的 主app 与其他辅助进程在不同的层运行。

可精细控制每层隔离程度、每层可见文件范围。如果你愿意，也可以玩无限嵌套。

以下是一个例子，沙箱容器树可能是像这样的：

```verilog
[Linux Host]
    主机X11
    主机DBUS服务
    
    [TreeSandbox沙箱] 
     |
     |--[子容器 : 不信任空间] 
     |   |
     |   |--[子容器 : 用户App : 不信任] 
     |   |      用户的App在这里跑
     |   |  
     |   |--[子容器 : 辅助进程(组2): 不信任] 
     |          内部的X11服务
     |          内部的DBUS服务
     |          
     |--[子容器 : 辅助进程(组1) : 半信任]
            在内、外部X11之间转发的进程
            DBUS通信代理和过滤进程
```

我们用了“容器树”后，在无需主机 subuid / subgid 的情况下实现沙箱内部的不同“级别”的进程之间的互相隔离。


## 功能列表与完成状态

- [x] 不需root；不需守护进程；不需任何主机的Cap或suid；不需要subuid/subgid

- [x] 无镜像容器。不需要像Docker那样下载系统镜像。用现有真实系统作为基础，内部诸如vim、git等工具无需重复安装

- [x] “树形容器”内部原理实现了:
    - [x] 每层与其上层之间的每种ns的隔离与否(是否unshare)选项控制
    - [x] 每层内部环境变量控制
    - [x] 每层的新rootfs挂载细粒度文件系统建立列表控制
        - [x] bind挂载(rw/ro)目录、文件、套接字、字符设备，symlink，tmpfs 等
        - [ ] overlay
    
- [x] 启动时内部uid变0（提权）；进程uid变回1000(降权）；Drop caps；noNewPrivs

- [x] 可挂载AppImage、squashfs在内部访问其内容

- 沙箱内使用GUI
    - [x] 可选暴露真实X11接口给沙箱
    - [x] 可选使用Weston+Xwayland隔离X11（配icewm）
    - [x] 可选使用Xephyr隔离X11（配icewm）
    - [x] 可选使用Xpra隔离的无缝X11代理
    - [ ] 可选暴露wayland接口给沙箱
    - [ ] 可选在一窗口内运行的隔离的完整桌面环境
    - [x] 可选同步剪贴板（从沙箱到主机。反过来的时候可暂时用IME的粘贴功能替代）
    
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
    说明：以用户设置的`sandbox_name`来识别“同名沙箱”
    - [x] 一个沙箱可设置多个app，启动时可指定app（例如我们可把同一厂商出品的不同app可以放同一沙箱里，便于它们之间交互）
    - [x] 同名沙箱多实例（从主机多次启动沙箱，会运行多个实例，互相隔离、互相独立)
    - [x] 同名沙箱单实例（从主机启动一种沙箱后，再次启动这种沙箱，则传递命令参数至已运行的沙箱）
    
- [x] 容器内部shell接口暴露给主机，主机随时进入（已部分实现）

- [x] 可选暴露pulseaudio接口给沙箱

- [x] 可选暴露CUPS接口给沙箱

- [x] 看门狗

- [ ] PGID、SID分离，然后实现部分信号传递

- [ ] 用户指定的fd传递给app


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
- xdg-dbus-proxy (过滤DBUS通信)
- [pasta](https://passt.top) (网络介面tun/tap)
- nftables (网络流量控制)
- xpra (隔离X11。无缝显示)
- Weston + Xwayland + icewm (隔离X11)
- Xephyr + icewm (隔离X11)
- xsel (同步剪贴板)
- squashfuse (内部AppImage、squashfs挂载)
- zenity 或 kdialog (内部阻止随意的网页等弹窗而改用询问)



## User Manual

正规的手册暂时还没写。我先休息一下。

不过，你可以先打开代码，看头部 `userconfig()` 函数内的注释（或者打开`uc.example.py`看），并结合上面的例子看，也能摸个七七八八。


## User Advanced Manual

User Advanced Manual 与 User Manual 是不同的。95%的情况下不需要看 Advanced。但如果想实现一些默认模板没有提供的功能，那么要了解一下内部实现，了解默认模板是如何给容器树划分“层”的。

### 默认模板的沙箱分层结构

这是“容器树”实现原理个可以自由嵌套的沙箱。已设置有默认的嵌套模板如下：

```
Linux Host 
  |
 outest (用户启动的进程。作为管理本沙箱的进程，工作在沙箱外)
  |
 layer1 (隔离了 pid ns，已在沙箱内)
  |
 layer2 (为 半信任空间 的建立做准备）
   |
   |--layer2c (用于运行 半信任 的辅助程序，如 xdg-dbus-proxy 等）
   |
 layer2h (过度)
    |
  layer3 (不信任空间：隔离所有ns；
    |       可见系统基础目录，其余仅用户挂载进去的路径可见）
    |
    |--layer4 (用于运行用户的App)
    |--layer4c (用于运行 不需要信任 的辅助程序，如 单独的Xserver 等)
```

（layer2c和layer4c都用于运行辅助程序，区别在于layer2c可以访问真实的X11接口、dbus接口，而layer4c则不需要访问这些）


沙箱启动后，用户所要运行的App是在layer4内。

> 还有好多没写，我先休息一下

> 本项目处于早期阶段，不排除以后有修改内部设计的可能性

