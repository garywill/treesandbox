# Deploy Tool of Tree Sandbox

## 为什么需要这个批量部署脚本

实际日常使用 Tree Sandbox 时，一个 **TreeSandbox具体沙箱** 的 **启动脚本** 会以独立的 **单`.py`文件** 存在，此文件包含 <ins><u>userconfig</u></ins> 与 <ins><u>沙箱程序源码</u></ins> 两个部分。

手动操作弄好一个具体沙箱的步骤为：

1. 从本仓库复制 `treesandbox.py` 到 `/yourpath/tsbxrun_mysandbox1.py`
1. 打开编辑 `/yourpath/tsbxrun_mysandbox1.py` ， 根据你具体需要，修改其中 userconfig 部分。

因为我们肯定会搞很多个具体沙箱，因此建议使用**批量部署脚本**，便于修改和更新。这样你只需把你的各个具体沙箱的 userconfig 写在对应的各个 `uc.<name>.py` 文件里即可。

## 如何使用

### 准备文件及运行命令

开始使用 `deploy.py` 前，一般应像：

```
treesandbox/         （TreeSandbox的git仓库）
  ├─ treesandbox.py     （沙箱主代码）
  └─ my-sandboxes/
    ├─ deploy.py        （部署工具脚本）
    ├─ list.toml        （定义你的具体沙箱列表）
    ├─ uc.<name1>.py   （你的具体沙箱1的userconfig）
    └─ uc.<name2>.py   （你的具体沙箱2的userconfig）
```

开始使用部署工具：

```sh
python3 -IBS deploy.py
```

（`-IBS` 意思为不使用第三方python库）

它会查找与 `deploy.py` 同目录的 `list.toml` 和 `uc.<name>.py` 。

如果要将 自定义的具体沙箱 与 Tree Sandbox 的代码仓库目录**分开存放**，可以：

```sh
python3 -IBS deploy.py -s /my_path_for_sandboxes
```

那样的话，这样存放文件：

```
treesandbox/         （TreeSandbox的git仓库）
  ├─ treesandbox.py     （沙箱主代码）
  └─ my-sandboxes/
    └─ deploy.py        （部署工具脚本）
    
/my_path_for_sandboxes/
  ├─ list.toml        （定义你的具体沙箱列表）
  ├─ uc.<name1>.py   （你的具体沙箱1的userconfig）
  └─ uc.<name2>.py   （你的具体沙箱2的userconfig）
```

### 如何写 `list.toml` 

例子：（两个具体沙箱）

```toml
my_sandboxes = [
    {name='myapp1', destdir='/mypath1'}, # destfile = /mypath1/tsbxrun_myapp1.py
    {name='myapp2', destdir='/mypath2'}, # destfile = /mypath2/tsbxrun_myapp2.py
    ...
]
```

### 如何搞 `uc.<name>.py`

一个 `uc.<name>.py` 文件里写你的一个具体沙箱的 userconfig 部分。文件名中的`<name>` 与 `list.toml` 里的一个条目的 `name` 一致。

`uc.<name>.py` 的内容像是这样：

```py
def userconfig(si):
    uc = d() # dict-like object
    
    uc.xxxx = yyyy # Your config
    uc.xxww = zzzz # Your config
    .....
    
    return uc
```

打开 `treesandbox.py` ，从其头部获取 userconfig 模板。

## 关于 Shabang

我们的 `treesandbox.py` 和 `deploy.py` 的第一行都**没有写**像 `#!/usr/bin/...` 这样的 shabang 。那是因为，在你使用你的 python 来调用 `deploy.py` 时，它才把所使用的 python 解释器 的绝对路径 作为 shabang 写进 具体沙箱 的 启动脚本 里。
