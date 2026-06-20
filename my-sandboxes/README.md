
English | [中文](README_zh.md)

# Deploy Tool of Tree Sandbox

## Why Need This Batch Deploy Script

**Startup script** of a **specific TreeSandbox sandbox** will run as standalone **single `.py` file**, containing both <ins><u>userconfig section</u></ins> and the <ins><u>sandbox program code</u></ins>.

Once you download an app and want to sandbox its execution, you need to create a **specific sandbox** and write a userconfig.

For likely we'll have many specific sandboxes, it's recommended to use this **batch deploy script**, which allows conveniently edit and update. In that case, you edit your `uc.<name>.py` files, which are your userconfigs of specific sandboxes.

## How to Use This Deploy Tool

### Prepare Files and Use Command

When about to use `deploy.py`, files can be like:

```text
treesandbox/         (TreeSandbox git repo)
  ├─ treesandbox.py     (Sandbox program code)
  └─ my-sandboxes/
    ├─ deploy.py        (This deploy tool script)
    |
    ├─ list.toml       (You define your specific sandbox list)
    ├─ uc.<name1>.py   (Your specific sandbox 1's userconfig)
    └─ uc.<name2>.py   (Your specific sandbox 2's userconfig)
```

Run this deploy tool: (by default it looks for user's `list.toml` and `uc.<name>.py` files in the same dir as `deploy.py`)

```sh
python3 -IBS deploy.py # '-IBS' means we don't need third-party python library
```

**However**, a **more** widely **preferred** way:

To **separate** your custom sandboxes data **from** TreeSandbox repo:

```
treesandbox/         (TreeSandbox git repo)
  ├─ treesandbox.py     (Sandbox program code)
  └─ my-sandboxes/
    └─ deploy.py        (Deploy tool script)
    
/path_to_your_sandboxes_config/
  ├─ list.toml        (You define your specific sandbox list)
  ├─ uc.<name1>.py   (Your specific sandbox 1's userconfig)
  └─ uc.<name2>.py   (Your specific sandbox 2's userconfig)
```

Run

```sh
python3 -IBS deploy.py -s /path_to_your_sandboxes_config
```

### Example of `list.toml`

Example of simple `list.toml` for two specific sandboxes:

```toml
my_sandboxes = [
    {name='myapp1', destdir='/pathA'}, # destfile = /pathA/tsbxrun_myapp1.py
    {name='myapp2', destdir='/pathB'}, # destfile = /pathB/tsbxrun_myapp2.py
    ...
]
```

After deploying, your app files are like:

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

(It supports specifying which version of sandbox program code to use for individual specific sandbox. See `list.example.toml` )

### How to Write `uc.<name>.py`

Content of a `uc.<name>.py` file is the userconfig of your specific sandbox. The `<name>` in file name should equal the value of `name` of an item in `list.toml`.

Content of `uc.<name>.py` is like：

```py
def userconfig(si):
    uc = d() # dict-like object
    
    uc.xxxx = yyyy # Your config
    uc.xxww = zzzz # Your config
    .....
    
    return uc
```

Don't write userconfig from scratch. Get userconfig **template** from top of `treesandbox.py` file.

## About Shabang

Our `treesandbox.py` and `deploy.py` **do not have** a shabang like `#!/usr/bin/...` in the 1st line. That's because when you use your Python to call `deploy.py`, it then writes the absolute path of the Python interpreter being used as the shabang into the specific sandbox's startup script. (So, keep in mind: `deploy.py` is not meant to be executed. You run it with your `python3` interpreter)
