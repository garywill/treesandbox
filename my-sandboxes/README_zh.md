# Deploy Tool of Tree Sandbox

## 为什么需要这个批量部署脚本

一个 **TreeSandbox具体沙箱** 的 **启动脚本** 会以独立的 **单`.py`文件** 运行。此文件包含 <ins><u>userconfig</u></ins> 与 <ins><u>沙箱程序源码</u></ins> 两个部分。

每当你下载了一个 App 并想要沙箱化运行，就需要弄一个**具体沙箱**，为其编写 userconfig 。

因为我们肯定会搞很多个具体沙箱，因此建议使用这个**批量部署脚本**，便于修改和更新。这样你只需把你的各个具体沙箱的 userconfig 写在对应的各个 `uc.<name>.py` 文件里即可。

## 如何使用这个部署工具

### 准备文件及运行命令

开始使用 `deploy.py` 前，文件可以像：

```
treesandbox/         （TreeSandbox的git仓库）
  ├─ treesandbox.py     （沙箱主代码）
  └─ my-sandboxes/
    ├─ deploy.py        （这个部署工具脚本）
    |
    ├─ list.toml       （定义你的具体沙箱列表）
    ├─ uc.<name1>.py   （你的具体沙箱1的userconfig）
    └─ uc.<name2>.py   （你的具体沙箱2的userconfig）
```

运行部署工具：（默认它会查找与 `deploy.py` 同目录的 用户的 `list.toml` 和 `uc.<name>.py` ）

```sh
python3 -IBS deploy.py # '-IBS' 为不使用第三方python库
```

**但**还有一种**更好**的方式：

**分开存放** 自定义的具体沙箱 与 TreeSandbox的代码仓库：

```
treesandbox/         （TreeSandbox的git仓库）
  ├─ treesandbox.py     （沙箱主代码）
  └─ my-sandboxes/
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
    {name='myapp1', destdir='/pathA'}, # destfile = /pathA/tsbxrun_myapp1.py
    {name='myapp2', destdir='/pathB'}, # destfile = /pathB/tsbxrun_myapp2.py
    ...
]
```

部署完成后，你的App的文件像这样：

```
/pathA/                  (You create this dir for an app)
  ├─ tsbxrun_myapp1.py   (Deployed by this tool. Startup script for app1 to run in sandbox)
  └─ app1.AppImage       (You download from Internet)

/pathB/                 (You create this dir for an app)
  ├─ tsbxrun_myapp2.py  (Deployed by this tool. Startup script for app2 to run in sandbox)
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

不需要从零开始写 userconfig 。打开 `treesandbox.py` ，从其头部获取 userconfig **模板**。

## 关于 Shabang

我们的 `treesandbox.py` 和 `deploy.py` 的第一行都**没有写**像 `#!/usr/bin/...` 这样的 shabang 。那是因为，在你使用你的 python 来调用 `deploy.py` 时，它才把所使用的 python 解释器 的绝对路径 作为 shabang 写进 具体沙箱 的 启动脚本 里。（因此，记住了，我们的 `deploy.py` 都不是直接执行的，要用你的 `python3` 来调用）
