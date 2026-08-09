# Deploy Tool of Tree Sandbox

## 为什么需要这个批量部署脚本

每当你下载了一个 App 并想要沙箱化运行，就需要弄一个**具体沙箱**，为其编写 userconfig 。

userconfig 里有这些配置：
- 沙箱名（一般以你要运行的app命名）
- 沙箱如何使用 GUI 
- 沙箱网络
- .....

一个 **TreeSandbox具体沙箱** 的 **启动文件** 会以独立的 **单`.pyz`文件** （压缩的.py文件包，可执行）运行。此文件会包含 <ins><u>userconfig</u></ins> 和 <ins><u>沙箱程序源码</u></ins>。

因为我们肯定会搞很多个具体沙箱，因此建议使用这个**批量部署脚本**，便于修改和更新。这样你只需把你的各个具体沙箱的 userconfig 写在对应的各个 `uc.<name>.py` 文件里即可。

部署脚本做的事就是：把 本沙箱工具的程序代码 和 userconfig 一起打包成 .pyz ，然后将其放到硬盘里你想放的位置。

## 如何使用这个部署工具

### 准备文件及运行命令

开始使用 `deploy.py` 前，文件可以像：

```
treesandbox/         （TreeSandbox的git仓库）
  ├─ src/             （沙箱主代码）
  ├─ deploy.py        （这个部署工具脚本）
  └─ my-sandboxes/
    ├─ list.toml       （定义你的具体沙箱列表）
    ├─ uc.<name1>.py   （你的具体沙箱1的userconfig）
    └─ uc.<name2>.py   （你的具体沙箱2的userconfig）
```

运行部署工具：（默认它会查找相对于 `deploy.py` 的 `my-sandboxes/` 下的 用户的 `list.toml` 和 `uc.<name>.py` ）

```sh
python3 -IBS deploy.py # '-IBS' 为不使用第三方python库
```

**但**还有一种**更好**的方式：

**分开存放** 自定义的具体沙箱 与 TreeSandbox的代码仓库：

```
treesandbox/         （TreeSandbox的git仓库）
  ├─ src/             （沙箱主代码）
  └─ deploy.py        （部署工具脚本）
    
/path_to_your_sandboxes_config/
  ├─ list.toml        （定义你的具体沙箱列表）
  ├─ uc.<name1>.py   （你的具体沙箱1的userconfig）
  └─ uc.<name2>.py   （你的具体沙箱2的userconfig）
```

运行

```sh
python3 -IBS deploy.py -s /path_to_your_sandboxes_config
```

### 如何写 `list.toml` 

`list.toml` 简单示例：（两个具体沙箱）

```toml
my_sandboxes = [
    {name='myapp1', destdir='/pathA'}, # destfile = /pathA/tsbxrun_myapp1.pyz
    {name='myapp2', destdir='/pathB'}, # destfile = /pathB/tsbxrun_myapp2.pyz
    ...
]
```

部署完成后，你的App的文件像这样：

```
/pathA/                  (You create this dir for an app)
  ├─ tsbxrun_myapp1.pyz  (Deployed by this tool. Startup file for app1 to run in sandbox)
  └─ app1.AppImage       (You download from Internet)

/pathB/                 (You create this dir for an app)
  ├─ tsbxrun_myapp2.pyz (Deployed by this tool. Startup file for app2 to run in sandbox)
  └─ app2/              (You download from Internet)
    ├─ app2.bin
    ├─ libapp2.so
    └─ ....
```

（支持 为每个具体沙箱 指定 要使用的沙箱程序代码 的 版本，详见 `list.example.toml` ）

### 如何搞 `uc.<name>.py`

一个 `uc.<name>.py` 文件里写你的一个具体沙箱的 userconfig 。文件名中的`<name>` 与 `list.toml` 里的一个条目的 `name` 一致。

`uc.<name>.py` 的内容像是这样：

```py
def userconfig(si):
    uc = d() # dict-like object
    
    uc.xxxx = yyyy # Your config
    uc.xxww = zzzz # Your config
    .....
    
    return uc
```

不需要从零开始写 userconfig 。从我们提供了的**模板**修改。

## 关于 Shabang （指定Python解释器）

虽然我们编写的各个.py脚本在第一行已有 `#!....` 这样的shabang，因此你可以：

```bash
./deploy.py
```

但你也可以指定python解释器来运行：

```bash
/opt/bin/python3 -IBS ./deploy.py
```

`deploy.py` 执行时，它会把所使用的 python 解释器 的绝对路径 写进 目标文件（.pyz） 的头部 shabang。这样用户可以指定 部署好的具体沙箱 所用的 python 解释器。
