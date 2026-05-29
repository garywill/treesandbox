
English | [中文](README_zh.md)

# Deploy Tool of Tree Sandbox

## Why need this batch deploy script

In actual daily use of Tree Sandbox, **startup script** of a **specific TreeSandbox sandbox** will run as standalone **single `.py` file**, containing both <ins><u>userconfig section</u></ins> and the <ins><u>sandbox program code</u></ins>.

To manually make a specific sandbox ready:

1. Copy `treesandbox.py` in this repo to `/yourpath/tsbxrun_mysandbox1.py`
1. Open and edit `/yourpath/tsbxrun_mysandbox1.py`. Modify userconfig section according to your specific needs.

For likely we'll have many specific sandboxes, it's recommended to use **batch deploy script**, which allows conveniently edit and update. In that case, you edit your `uc.<name>.py` files, which are your userconfigs of specific sandboxes.

## How to use

### Prepare files and use command

When about to use `deploy.py`, generally:

```text
treesandbox/         (TreeSandbox git repo)
  ├─ treesandbox.py     (Sandbox program code)
  └─ my-sandboxes/
    ├─ deploy.py        (Deploy tool script)
    ├─ list.toml        (You define your specific sandbox list)
    ├─ uc.<name1>.py   (Your specific sandbox 1's userconfig)
    └─ uc.<name2>.py   (Your specific sandbox 2's userconfig)
```

Begin to use this deploy tool:

```sh
python3 -IBS deploy.py
```

(`-IBS` means we don't need third-party python library)

it will look for `list.toml` and `uc.<name>.py` files in the same dir of `deploy.py`.

If you **separate** your custom sandboxes data **from** TreeSandbox repo, use like this:

```sh
python3 -IBS deploy.py -s /path_to_your_sandboxes_config
```

in that case, files are like:

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
  ├─ tsbxrun_myapp1.py     (Deployed by this tool. Startup script for app1 to run in sandbox)
  └─ app1.AppImage         (You download from Internet)

/pathB/                 (You create this dir for an app)
  ├─ tsbxrun_myapp2.py     (Deployed by this tool. Startup script for app2 to run in sandbox)
  └─ app2/                 (You download from Internet)
    ├─ app2.bin
    ├─ libapp2.so
    └─ ....
```

### How to write `uc.<name>.py`

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

You can get the userconfig **template** from head of `treesandbox.py` file.

## About Shabang

Our `treesandbox.py` and `deploy.py` **do not have** a shabang like `#!/usr/bin/...` in the 1st line. That's because when you use your Python to call `deploy.py`, it then writes the absolute path of the Python interpreter being used as the shabang into the specific sandbox's startup script. (So, keep in mind: neither `treesandbox.py` nor `deploy.py` is meant to be executed. You run them with your `python3` interpreter)
