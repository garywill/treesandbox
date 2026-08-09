# Tree Sandbox for Linux

你一定玩过 Podman、Firejail、Flatpak、Bubblewrap ...

Tree Sandbox 是又一免特权的 Linux沙箱工具，可作为它们的补充。

我们独特的安全加强设计：“树形”沙箱，多层容器，像由多个子容器组成的“树”。（见[下文详情](#什么是容器树)）

## 与其他沙箱工具对比

### 与 Firejail / Flatpak 对比

| 功能 | **Tree sandbox** | Firejail | Flatpak |
| --- | --- | --- | --- |
| 文件系统: 隐私vs体积vs便捷 | ◐ 从主机fs中选需要的路径。得分2/3 | ✘ 用主机fs，仅遮盖要保护的路径。得分1/3 | ◐ 下载容器镜像。得分2/3 |
| 同App沙箱单实例 (多次发送命令参数到运行中的沙箱) | ● | ● | ● |
| 同App沙箱多实例 (互相隔离独立) | ● | ● | ✘ |
| 容器嵌套 | ● 工作原理为[多层容器树](#什么是容器树)。“不信任”进程 与 “半信任”进程 在一个沙箱的不同层运行 | ✘ 拒绝嵌套 | ✘ |
| 免安装，免编译，免守护进程 | ● 单文件可运行，完全无需root | ✘ 需要安装并有设置suid | ✘ 需要守护进程 |
| 开箱即用（对于具体App） | ◐ 用户需先设置一些选项 | ● 有一些内置 app profile | ● Flathub |
| 不在真实家目录产生文件 | ● | ● | ✘ |
| 沙箱内部调用xdg-open时在外部打开 | ● 可替换xdg-open为弹出询问，用户复制url/路径/参数 | ✘ | ● 由门户管理 |
| 动态决定沙箱内可访问哪些文件或硬件 | ✘ 固定的事先配置好的挂载表 | ✘ 固定的事先配置好的挂载表 | ● 门户做动态临时挂载/授权，但沙箱内得到的文件路径不确定 |
| 主与机 unshare net ns ，沙箱可以连接互联网，选择性“融合”主机和沙箱的localhost端口 | ● tun/tap + nftables (免root) 细粒度控制 | ◐ | ◐ |

### 与 Bubblewrap 对比

| 功能 | **Tree sandbox** | Bubblewrap |
| --- | --- | --- |
| 沙箱配置方式 | 编辑配置文件 | 写CLI参数 |
| 开箱即用（对于基本系统沙箱） | ● | ✘ 需要较长的参数来搭建基本系统 |
| 常用工具的集成 (如隔离X11/转发、DBUS过滤代理)，和常用socket路径挂载的便捷选项 | ● | ✘ |
| 同App沙箱单实例 (多次发送命令参数到运行中的沙箱) | ● | ✘ |
| 同App沙箱多实例 (互相隔离独立) | ● | ● |
| 容器内部shell接口暴露给主机，主机随时获取 | ● 已实现某些配置下可以，未来更完善 | ✘ 需要主机root做`nsenter` |

## 功能列表与完成状态

- [x] 不需root；不需守护进程；不需主机的Cap或suid；不需要subuid/subgid

- [x] 无镜像容器。内部诸如vim、git等工具无需重复安装

- [x] 内部新 rootfs 文件系统（[容器树](#什么是容器树)的每个层）
    - [x] bind 挂载(rw/ro) 目录、文件、套接字、字符设备，symlink，tmpfs 等
    - [ ] overlayfs

- 沙箱内使用 GUI
  - 沙箱画面显示在主机上
    - [x] 通过 X11 协议 （Wayland 兼容，有 Xwayland）
    - [ ] 通过 Wayland 协议
  - 沙箱内部的显示服务
    - [x] 可选暴露真实 X11 接口给沙箱
    - [x] 可选使用 Weston + Xwayland 隔离 X11（GPU可用）（配icewm）
    - [x] 可选使用 Xephyr 隔离 X11（配icewm）
    - [x] 可选使用 Xpra 隔离的 无缝X11 （Weston+Xwayland） 代理 （GPU可用）
    - [x] 可选使用 Xpra 隔离的 无缝X11 （Xvfb） 代理
    - [ ] 可选暴露 wayland 接口给沙箱
    - [ ] 可选在一窗口内运行的隔离的完整桌面环境
  - 自动同步剪贴板内容
    - [x] 可选 沙箱 -> 主机
    - [ ] 可选 主机 -> 沙箱 （现在暂时用IME的粘贴功能替代）

- [x] 容器内部shell接口暴露给主机，主机随时获取（已部分可用。计划更完善）

- 可选暴露真实物理硬件给沙箱
    - [x] 可选暴露GPU给沙箱
    - [x] 可选暴露所有硬件给沙箱

- DBus
    - [x] 可选暴露真实 DBus 接口给沙箱
    - [x] 可选过滤 DBus 通信

- 沙箱网络
  - [x] 可选的不管理沙箱网络（不 unshare net ns）
  - [x] 可选的网络控制
      - [x] 使用 tun/tap 创建可控网络介面 (pasta管理)
      - [x] 内部 nftbles 规则(免root)自定义

- [x] 沙箱启动时（或被复用时）选择App（从用户为此沙箱配置好的App列表中）
  - [x] 单App沙箱
  - [x] 多App沙箱
  
- [x] 是否<ins><u>复用</u></ins>已启动的沙箱
  - [x] 启动多个实例 （互相隔离、独立）
  - [x] 复用一个实例（同名沙箱） （传递命令参数至<ins><u>运行中</u></ins>的沙箱）

- [x] 可挂载 AppImage、squashfs 在内部访问其内容

- 音频
  - [x] 可选暴露 PulseAudio 接口给沙箱（PipeWire 兼容）
  - [ ] 可选暴露 PipeWire 接口给沙箱

- [x] 可选暴露 CUPS 接口给沙箱

- [x] [树形容器](#什么是容器树)内部原理实现了:
    - [x] 每层与其上层之间的每种 ns 的隔离与否 (是否unshare) 选项控制
    - [x] 每层的新 rootfs 挂载细粒度文件系统建立列表控制
    - [x] 每层内部环境变量控制

- [x] 处理 uid_map 和 user ns ; Drop caps；noNewPrivs ; procfs hidepid=1

- [x] 看门狗

- [ ] PGID、SID分离，然后实现部分信号传递

- [ ] 用户指定的 fd 传递给app

- [ ] 从主机快速列出沙箱和进程

## 什么是"容器树"

Tree Sandbox 设计成一个沙箱由多层子容器构成，它们连成一棵“容器树”，“树”可以有多个分枝和容器节点。容器节点之间的“连接”可以是各类互相 “已unshare” 或 “未unshare” 的 namespace。

这种设计下，“不信任”进程 与 “半信任”进程 可在一个沙箱的不同**层**运行；用户要运行的 主app 与其他 辅助进程 也是在不同的**层**运行。

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

我们用了“容器树”后，在 <ins><u>无需主机 subuid / subgid </u></ins> 的情况下实现沙箱内部的不同“级别”的进程之间的**互相隔离**。

内部实现可精细控制每层隔离程度、每层可见文件范围。如果你愿意，也可以玩无限嵌套。

## 使用

### 快速试用

```sh
git clone --shallow-since=2026-07-01 https://github.com/garywill/treesandbox
cd treesandbox
python3 -IBS src
```

（`-IBS` = 不需要第三方python库）

如果沙箱内的shell提示符出现了，那么恭喜，运行成功！

现在你可以看看 [依赖列表](#依赖) ，考虑是否安装一些额外软件，以解锁更多整合了的功能。然后，你可以修改 `src/userconfig.py` ，然后再次启动沙箱，以尝试不同的设置下的沙箱效果。

### 弄好你的沙箱

以上只是说明你的电脑能跑 Tree Sandbox 了。而实际日常使用时，每当你下载了一个 App 并想要沙箱化运行，就需要弄一个**具体沙箱**，为其编写 userconfig 。

一个 **TreeSandbox具体沙箱** 的 **启动文件** 会以独立的 **单`.pyz`文件** 存在（压缩的.py文件包，可执行），此文件会包含 <ins><u>userconfig</u></ins> 和 <ins><u>沙箱程序源码</u></ins>。

因为我们要使用多种不同App，所以肯定会配置很多个具体沙箱，因此建议使用**批量部署脚本**，便于修改和更新。这样你只需把你的各个具体沙箱的 userconfig 写在对应的各个 `uc.<name>.py` 文件里即可。详见 [`部署工具的说明`](docs/Deploy_my_sandboxes_zh.md) 。

## Tree Sandbox 的一些不同玩法

用些例子演示一下 Tree Sandbox 的一些不同之处。三言两语，不能尽述，略谈一二。

### 例 - 两个App放同一沙箱

假设你有两个App, 叫 VSCode 和 MSEdge , 它们来自**同一厂商**，因此你想要把它们放入一个**叫 `ms`** 的沙箱内运行，以让它们两之间更好地**交互**（假设它们是会互相交互的吧）。

Tree Sandbox 支持<ins><u>将**多个不同App放同一沙箱里**，并提供“**选择-启动**”方式</u></ins>。

假设在经过正确的配置后，主机可以通过以下命令来调用 MSEdge 浏览器，打开 Github：

```sh
tsbxrun_ms.pyz --app msedge https://github.com   # 1
```

假设现在我们要干活写代码了，主机又要调用 VSCode 来编辑一些文件：

```sh
tsbxrun_ms.pyz --app vscode main.c zlib.h  # 2
```

```sh
tsbxrun_ms.pyz --app vscode app.js  # 3
```

已经发生了3次调用了。然后，假设主机又要调用**沙箱里的**浏览器，用**新标签**打开Linux官网:

```sh
tsbxrun_ms.pyz --app msedge https://www.kernel.org   # 4
```

以上已经假设主机进行了**多次调用** `tsbxrun_ms.pyz` 。为了让后面的调用**复用**第一次打开的沙箱，我们需要把沙箱配置成“**复用型**”的。

本例的 userconfig 配置如下（简略）：

```python
uc.sandbox_name = 'ms' 
uc.reuseful = True
uc.apps = [
    d(cmdvec=['/somepath1/microsoft-edge'], appname='msedge'), 
    d(cmdvec=['/somepath2/code'], appname='vscode'), 
]
```

### 例 - localhost的“部分融合”

其他沙箱也有网络方面的类似功能，但我们目前有一点小优势。

假设主机有程序监听本地22、53、8000。不想暴露 22 给沙箱，但 53 和 8000 希望沙箱能访问，而且沙箱 直接通过`127.0.0.1` 访问， 省去 子网网关IP配置 等。

沙箱内也运行程序，它监听端口 1080 。同时又希望主机能访问沙箱的 1080 ，也是 直接通过`127.0.0.1` ，省去 子网客户端IP配置 等。

我们请出 Tree Sandbox 集成的 pasta 。 （pasta 少被人提及，它是Podman的passt项目的一部分，替代slirp4netns 。）我们需要在 Tree Sandbox 的 userconfig 里配置（简略）：

```python
uc.net_iface='tuntap-pasta'
uc.pasta_custom_args = [ 
    '-T', '53,8000', '-U', '53,8000' ,
    '-t', '1080', '-u', '1080', 
#Or '-t', 'auto', '-u', 'auto',  # Dynamic. 'auto' is default, can omit -t/-u
    ...
]
```

这样实现了对主机与沙箱的 localhost 的“部分融合”。

其他沙箱工具也有类似功能，但我们使用 pasta **<ins><u>优势在于</u></ins>**：

- pasta使用的是 tun/tap ，整个过程不涉及主机的root
- 主机**不会**多出一个像`docker0`那样的介面
- 沙箱自身看到的 IP 和 MAC 都可以设置，甚至可让<ins><u>IP与主机的看起来一样，而不冲突</u></ins>

此外，像这样用了自己管理的网络介面，也可设置沙箱内 nftables 规则（免root），玩法就很多了，相信不必多说nftables的强大。

### 例 - 在沙箱里用 AppImage

你可能遇到过，从网上下载 AppImage文件 后，尝试放进某沙箱里跑，因沙箱禁止了 `CAP_SYS_ADMIN` ，fuse无法工作，而跑不起来的情况。

Tree Sandbox 可以<ins><u>**替 AppImage 完成挂载工作，不需要给它 fuse 权限**</u></ins>。用法一般是（配置）：

```python
uc.user_mnts = [ 
  d(many_op='appimage', name='SomeName', src=f'/path/xxxx.AppImage') 
]
```

AppImage 里的 squashfs 会挂载到沙箱内的路径，并创建一个对应的启动脚本：

```
/sbxdir/apps/SomeName/  # squashfs (AppImage) mounted
/sbxdir/apps/run_SomeName  # Start script for it
```

你还应该在配置中加上：

```python
uc.apps = [
    d(cmdvec=['/sbxdir/apps/run_SomeName'])
]
```

或者更简单的： （因为 `/sbxdir/apps` 会被自动加入到 PATH）

```python
    d(cmdvec=['run_SomeName'])
```

### 例 - 主机同时操作多个 shell

若你有某个沙箱，经常要从<ins><u>主机同时连接沙箱内多个 shell 会话</u></ins>，那么可以这样配置：

```python
uc.reuseful=True
uc.apps = [
    ...
    d(cmdvec=['bash'], appname='bash'), 
    ...
]
```

（“reuseful”的含意之前解释过）

要 启动此沙箱 时，或 主机要连接沙箱内新 shell session 时，<ins><u>主机</u></ins>可以用命令：

```sh
tsbxrun_mysandbox.pyz --reusefg --app bash
```

`--reusefg` 意思是 “reuse in foreground”。

## 一些术语

- Linux namespace (ns) 以及 其 几种种类: 

  pid ns, mnt ns, net ns ... 。是容器/沙箱的基础

- `unshare`状态 （以及 未`unshare`状态）:

  是 容器 与其 父容器 之间的 “连接关系”

<ins><u>以上</u></ins>相信你早就理解。

<ins><u>以下</u></ins>是 Tree Sandbox 的概念：

- 主层：

  用于运行 用户要运行的“主app” 的那一层叫 "主层"

- 辅助进程：

  一个沙箱正常运行需要用到的，但又不是用户的目标app的进程，这种进程叫 辅助进程 。 例如 Xpra、xdg-dbus-proxy 等。辅助进程 在 主层以外 的层 运行。

- “不信任” 与 “半信任”：

  “半信任”的层比“不信任”的可以看到更多一些的主机接口。例如沙箱内部的纯粹的 X server 运行在“不信任”层， 而用于转发 X11 通信的，就要运行的“半信任”层。“主层”是不信任的层。

- “具体沙箱”

  为了把各种 App 沙箱化运行，每种 App 需要不同的沙箱配置。配置好的沙箱以 独立的 单个`.pyz`文件 存在和运行。一个配置好的沙箱叫“具体沙箱”。那个`.pyz`文件包含 <ins><u>userconfig</u></ins> 与 <ins><u>沙箱程序源码</u></ins> 两个部分。userconfig 就是沙箱的配置。各个具体沙箱之间，userconfig 不同，沙箱程序源码相同。

- 实例、“同名沙箱” 和 “复用”

    对于 非“复用型” 的普通沙箱，每启动一次沙箱，就产生一个运行中的**沙箱实例**；
    
    而对于 “复用型” 的沙箱，只会有一个 同名沙箱 的 实例 保持运行。期间若尝试再调用启动文件，只会把请求发送给运行中的 同名沙箱 实例。
    
    你有一个要跑在沙箱里隔离的App。当你想让此 <ins><u>相同App</u></ins> 的沙箱 <ins><u>单实例</u></ins> 运行 时，“同名” 是用于判断的依据（`uc.sandbox_name`）。找到 同名沙箱 后，即可“复用”。（类似 Firejail 的 `--join=name` ）

## 依赖

必须：

- Linux Kernel >= 6.3
    - user namespace
    - cgroup v2
- glibc
- Python >= 3.12
- bash
- coreutils

(虽然是Python脚本，但通过libc直接调用Linux内核功能，不需第三方Python库)

可选：

- dtach (共享shell给主机)
- xdg-dbus-proxy (过滤DBUS通信)
- [pasta (passt)](https://passt.top) (网络介面tun/tap) (版本 >= 约 202512xx)
- nftables (网络流量控制)
- Xpra >= 6 (隔离X11。无缝显示)
- Weston + Xwayland (隔离X11)
- Xephyr (隔离X11)
- icewm (窗口化隔离显示时用)
- xsel (同步剪贴板)
- squashfuse (内部AppImage、squashfs挂载)
- zenity 或 kdialog (内部阻止随意的网页等弹窗而改用询问)

## User Manual

### 用 dict-like 对象做配置

`uc`是 userconfig 的意思。是个 dict-like 对象。

对 Python 的内置 dict 不满意，我们造了`d()`，JS风格的对象，可以用**点号**访问成员。以下例子解释用法：

```python
uc = d()
# uc.gui = 'real' # 用户不使用gui，注释掉了这个
if uc.gui : # 在无 gui 这个成员的情况下，这里不报错
    uc.gpus = True
```

有了`d()`，我们不再需要像原本python的麻烦做法那样去判断 `if 'gui' in uc` 。

`si` 意思是 sandbox info ，它也是个 dict-like 。通过它读取一些常量值：

```python
si.username
si.uid
si.hostname
si.CWD  # Path where you put a sandbox start script
si.HOME # User HOME dir path on host
```

### 完整手册在哪？

打开代码，看头部 userconfig 部分。这是一个用户友好的模板，其中的注释已经可以作为教程。

完整的手册暂时还没写。我先休息一下。

## User Advanced Manual

User Advanced Manual 与 User Manual 是不同的。95%的情况下不需要看 Advanced。

### 主机什么位置有运行中的沙箱的信息

若你启动了一个 名为`SomeName` 的 Tree Sandbox 沙箱 的实例，会在主机的这个位置临时储存此实例的信息：

```
/tmp/tsbxs-1000/SomeName-nnnn..../
```

（`SomeName-nnnn....` 是这个沙箱实例的名称。n是时间戳数字。假设你的 uid 是 1000。）

另外有个附加功能：如果沙箱使用的内部的隔离的 X11/Wayland，那么还会在主机的以下位置创建临时symlink，以<ins><u>便于从主机给沙箱录屏</u></ins>： (假设沙箱使用 DISPLAY 500 )

```
/tmp/.X11-unix/X500  (symlink)   -> /tmp/tsbxs-1000/SomeName-nnnn..../x11socket  (also a symlink)   -> /proc/<in-sandbox-proc-pid>/root/tmp/.X11-unix/X500
  
$XDG_RUNTIME_DIR/wayland-500  (symlink)   -> /tmp/tsbxs-1000/SomeName-nnnn..../waylandsocket  (also a symlink)   -> /proc/<in-sandbox-proc-pid>/root/$XDG_RUNTIME_DIR/wayland-500
```

沙箱结束时，会清理临时symlink。

### 沙箱分层结构的默认模板

[容器树](#什么是容器树)的实现决定了这是个内部可嵌套的沙箱。已设置有默认的嵌套模板，<ins><u>满足95%的使用，不需了解它是如何嵌套的</u></ins>。

但，如果你是极客用户，想要发明更多玩法，那么可以了解一下内部实现，了解默认模板是如何给容器树划分“层”的。（挺费脑的哦）

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
    |--layer4 (用于运行用户的App。 这是“主层”)
    |--layer4c (用于运行 不需要信任 的辅助程序，如 单独的Xserver 等)
```

layer2c 和 layer4c 都用于运行辅助程序，区别在于layer2c可以访问真实的X11接口、dbus接口，而layer4c则不需要访问这些

沙箱启动后，用户所要运行的App是在 layer4 内。layer4 是“主层”。 (本项目已可用但处于早期阶段，不排除以后有修改内部设计的可能)

> 还有好多没写，我先休息一下

## 本沙箱工具的局限

1. 主要适配符合主流习惯的、符合 FHS 的 Linux 发行版
1. 目前是用python实现的，每个实例占用内存比编译型容器多 15MB 
1. 树形多层设计带来的开发难度。（还好，已经完成了难的部分）

## 使用即同意声明

1. 本沙箱是个人创建和维护的项目，用于运行App，尽管我们尽全力覆盖安全方面的细节，但不建议用于测试恶意代码。本项目概不担保，用户自担风险。
1. 本工具意在保护系统，不可用于欺骗或破坏App或系统。所用之场、法理之宜，好坏责任，咸归用户。使用即同意。

## License

Licensed under GPL.
