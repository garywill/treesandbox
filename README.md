
English | [中文](README_zh.md)

# Tree Sandbox for Linux

You’ve played with Podman, Firejail, Flatpak, Bubblewrap, ...

Tree Sandbox is another rootless Linux sandbox tool.

"Tree-shaped" sandbox: multi-layer nesting and branching, like a “tree” composed of multiple sub-containers.

## Comparison with other sandbox tools

### Compare with Firejail / Flatpak

| Feature | **Tree sandbox** | Firejail | Flatpak |
| --- | --- | --- | --- |
| Filesystem: privacy vs size vs convinience | ◐ Pick needed paths from host fs. Score 2/3 | ✘ Use host fs, masking unneeded paths. Score 1/3 | ◐ Download container image. Score 2/3 |
| Single-instance for same-app sandbox (cmd/args sent to first-started instance) | ● | ● | ● |
| Multi-instance for same-app sandbox (each other isolated & independent) | ● | ● | ✘ |
| Containers nesting | ● "Containers tree" is the way it works. We run "untrusted" and "semi-trusted" procs in different layers of a sandbox | ✘ Refuses to be nested | ✘ |
| No install/build. No system daemon | ● Single-file .py. No host root needed | ✘ Need install and suid | ✘ Need system daemon |
| Works out of the box (for specific app) | ◐ Users need edit some configs first | ● Has some built-in app profiles | ● Flathub |
| No traces in host HOME dir | ● | ● | ✘ |
| Able to open in host when in-sandbox calls xdg-open | ● Can replace xdg-open by asking script. User can copy url/path/args | ✘ | ● Managed by portal |
| Dynamically change accessable file/hardware list | ✘ Pre-configured mount list | ✘ Pre-configured mount list | ● Portal can do dynamically change, but in-sandbox see unpredictable file path |
| unshare net ns with host. Sandbox has Internet. Choosily "merge" host's and sandbox's allowed localhost ports | ● tun/tap + nftables (rootless). Fine-grained control | ◐ | ◐ |

### Compare with Bubblewrap

| Feature | **Tree sandbox** | Bubblewrap |
| --- | --- | --- |
| How sandbox is configured | Edit config file | By CLI args |
| Works out of the box (for a basic-system sandbox) | ● | ✘ Need long args to make basic system |
| Integration of common tools (eg isolated X11 server, DBUS filter proxy etc.), and common socket path mounting options | ● | ✘ |
| Single-instance for same-app sandbox (cmd/args sent to first-started instance) | ● | ✘ |
| Multi-instance for same-app sandbox (each other isolated & independent) | ● | ● |
| Host can get in-sandbox shell easily, via a socket | ● Currently usable under some config case. Will fully support | ✘ Need host root to `nsenter` |

## Features and status

- [x] No root needed; no system daemon; no host caps or suid ; no subuid/subgid needed.

- [x] Image-free containers. Tools like vim/git don’t need to be reinstalled inside.

- GUI in sandbox
  - [x] Optionally expose host X11 to the sandbox.
  - [x] Optional isolated X11 using Weston + Xwayland (GPU usable) ( with icewm).
  - [x] Optional isolated X11 using Xephyr ( with icewm).
  - [x] Optional seamless isolated X11 proxy via Xpra.
  - [ ] Optional expose Wayland to the sandbox.
  - [ ] Optional isolated full desktop running inside a single window.
  - [x] Optional clipboard sync (from sandbox to host; the reverse direction can temporarily be done by IME paste).

- [x] Expose an in-container shell interface to the host, allowing the host to easily get (partially usable. Full support in plan).

- Optionally expose real hardware devices to the sandbox
  - [x] Expose GPU devices to the sandbox.
  - [x] Expose all hardware devices to the sandbox.

- DBus
  - [x] Optional host DBus exposure to the sandbox.
  - [x] Optional DBus communication filtering.

- Sandbox network
  - [x] Optional don't manage network (don't unshare net ns)
  - [x] Optional network control
    - [x] Controllable tun/tap (managed by pasta) network interface
    - [x] Custom nftables rules (rootless) in sandbox.

- [x] Mount AppImage and squashfs internally to access their contents inside the sandbox.

- [x] Optionally expose the PulseAudio interface to the sandbox.

- [x] Optionally expose the CUPS interface to the sandbox.

- For the same-name sandbox: single-app/multi-app; single-instance/multi-instance (app selection at startup, instance management, and cmd/args passing)

  Note: the user-configured `sandbox_name` is used to identify a “same-name sandbox”.
  - [x] One sandbox can configure multiple apps; you can choose the app at startup (e.g., put multiple apps from the <ins><u> same vendor </u></ins> into one sandbox for their easier interaction).
  - [x] Multi-instance mode: starting the sandbox multiple times creates multiple isolated independent instances.
  - [x] Single-instance mode: after starting one sandbox, starting the same sandbox again passes command arguments to the <ins><u>already-running</u></ins> sandbox.

- [x] “Containers tree” internally can do:
  - [x] Per-layer control of whether a type of ns is `unshare`d or not from parent layer.
  - [x] Per-layer environment variable control.
  - [x] Per-layer fine-grained new-rootfs filesystem setup list:
    - [x] bind mounts (rw/ro) for dir/file/socket/chardevice; symlink ; tmpfs . etc.
    - [ ] overlayfs

- [x] Handle uid_map and user ns ; Drop caps;  noNewPrivs ; procfs hidepid=1

- [x] Watchdog.

- [ ] Separate PGID/SID, then implement some signal forwarding.

- [ ] Pass user-specified fd to the app.

- [ ] Quickly list instances and procs from host

## What is “containers tree”

Tree Sandbox is designed so that a sandbox is composed of multiple layered sub-containers connected as a “containers tree”. The “tree” has branches and container nodes. The “connection” between nodes can be any combination of namespaces being “unshared” or “not unshared” .

With this design, “untrusted” procs and “semi-trusted” procs run in different **layers** of a sandbox; User's app and other companion procs run in different **layers**.

Here is an example of what a sandbox container tree might look like:

```verilog
[Linux Host]
    Host X11
    Host DBus services

    [TreeSandbox Sandbox]
     |
     |--[Sub-container: Untrusted zone]
     |   |
     |   |--[Sub-container: User App: Untrusted]
     |   |      The user's app runs here
     |   |
     |   |--[Sub-container: Companion procs (Group 2): Untrusted]
     |          Internal X11 services
     |          Internal DBus services
     |
     |--[Sub-container: Companion procs (Group 1): Semi-trusted]
            Proc that forward between internal and host X11
            DBus proxy and filtering proc
```

With the “containers tree” model, we can **isolate** procs of different "classes" inside the sandbox  <ins><u> without requiring host subuid/subgid </u></ins>.

The way it works allow finely controlling the isolation degree and filesystem visibility for each layer. If you want, you can even play with unlimited nesting.

## To Use

### Quick Trying

```sh
git clone --shallow-since=2026-03-01 https://github.com/garywill/treesandbox
cd treesandbox
python3 -IBS ./treesandbox.py
```

(`-IBS` means we don't need third-party python library)

If you see in-sandbox shell prompt, congratulations! It works!

Now you can take a look at [dependency list](#Dependencies), and consider installing some optional software to unlock more integrated features.

### Get Your Sandbox(es) Ready

Above just checked your computer can run Tree Sandbox. Before actual use, you want to make your startup script(s) of your **specific sandbox(es)** ready.

Currently, need to manually do:

1. Copy `treesandbox.py` in this repo to `/yourpath/tsbxrun_mysandbox1.py`
1. Open and edit `/yourpath/tsbxrun_mysandbox1.py`. **Modify userconfig section according to your specific needs**.

Sandboxes of TreeSandbox will run as standalone single `.py` files, each of them contain both userconfig section and the sandbox program code. So that's current deploy & config steps. (We'll make a auto deploy script, for likely we'll have many specific sandboxes)

## What Difference with Tree Sandbox

Let's see some examples to get to know about Tree Sandbox. A few words cannot cover it all — just a glimpse.

### Example - Two Apps in One Sandbox

Suppose you have two apps, VSCode and MSEdge, which come from **same vendor**, so you want them run in same sandbox **called `ms`**, to enable their better **interaction** (assuming they will interact with each other).

Tree Sandbox supports <ins><u>placing **multiple different apps in same sandbox** and provides **choose-and-launch** method</u></ins>.

Assume that after proper configuration, our host can call MSEdge browser using following command to open GitHub:

```sh
tsbxrun_ms.py --app msedge https://github.com   # 1
```

Now assume we’re going to do coding. Host calls VSCode to edit some files:

```sh
tsbxrun_ms.py --app vscode main.c zlib.h  # 2
```

```sh
tsbxrun_ms.py --app vscode app.js  # 3
```

That’s 3 calls already. Next, assume host calls the **in-sandbox** browser again to open Linux website **in new tab**:

```sh
tsbxrun_ms.py --app msedge https://www.kernel.org   # 4
```

Above has assumed the host has made **multiple calls** to `tsbxrun_ms.py`. To tell subsequent calls to **reuse** the sandbox instance started on the first call, we configure the sandbox as **"reuseful"**.

A userconfig for this example looks like (simplified):

```python
uc.sandbox_name = 'ms' 
uc.reuseful = True
uc.apps = [
    d(cmdvec=['/somepath1/microsoft-edge'], appname='msedge'), 
    d(cmdvec=['/somepath2/code'], appname='vscode'), 
]
```

### Example - Partially "Merge" localhost

Other sandboxes offer similar network feature, while we currently have slight advantage.

Assume programs on host listen on local ports 22, 53, and 8000. You do not want to expose 22 to sandbox, but you want sandbox able to access 53 and 8000, and you want the sandbox to access them directly via `127.0.0.1` to avoid configuring subnet gateway IP.

Assume also a program in sandbox listening on port 1080. You want host able to access sandbox's 1080, directly via `127.0.0.1` too, to avoid configuring subnet client IPs.

Now let’s bring in pasta, which Tree Sandbox has integrated. (pasta isn't well-known I guess. It’s part of Podman’s passt project and can be used as a replacement for slirp4netns.) We configure in Tree Sandbox’s userconfig like this (simplified):

```python
uc.net_iface='tuntap-pasta'
uc.pasta_custom_args = [ 
    '-T', '53,8000', '-U', '53,8000' ,
    '-t', '1080', '-u', '1080', 
#Or '-t', 'auto', '-u', 'auto',  # Dynamic. 'auto' is default, can omit -t/-u
    ...
]
```

That achieves a "partial merge" of localhost between host and sandbox.

Other sandbox tools have similar feature, while we using pasta having **<ins><u>advantages </u></ins>** :

- pasta uses tun/tap, and does not involve host root at all.
- Host **won't** spawn an extra interface like `docker0`.
- Both IP and MAC of sandbox can be configured. Even, <ins><u>IP can be looked same as host's  without conflict</u></ins>. 

Furthermore, since we've been able to manage network interface, we can set custom nftables rules in sandbox (rootlessly). That opens up a lot of possibilities.

### Example - Use AppImage in Sandbox

You may have encountered before: Trying to run a downloaded AppImage file inside a sandbox, it failed because sandbox disables `CAP_SYS_ADMIN`, stopping fuse.

Tree Sandbox can **<ins><u>do the mounting work, so no need to give AppImage fuse permission</u></ins>**. A typical configuration is like:

```python
uc.user_mnts = [ 
  d(many_op='appimage', name='SomeName', src=f'/path/xxxx.AppImage') 
]
```

The squashfs in AppImage will be mounted to an in-sandbox path, and a start script for it will be created:

```
/sbxdir/apps/SomeName/  # squashfs (AppImage) mounted
/sbxdir/apps/run_SomeName  # Start script for it
```

You should also include in your configuration:

```python
uc.apps = [
    d(cmdvec=['/sbxdir/apps/run_SomeName'])
]
```

or, more simply: (because `/sbxdir/apps` automatically added to `PATH`)

```python
    d(cmdvec=['run_SomeName'])
```

### Example - From Host Get Multiple Shells

If you have a sandbox where you frequently need to <ins><u>from host connect to multiple shell sessions inside the sandbox simultaneously</u></ins>, you can configure :

```python
uc.reuseful=True
uc.apps = [
    ...
    d(cmdvec=['bash'], appname='bash'), 
    ...
]
```

("reuseful" explained before)

When to launch this sandbox, or when host to connect to a new inner shell session, <ins><u>host</u></ins> can use command:

```sh
tsbxrun_mysandbox.py --reusefg --app bash
```

`--reusefg` means "reuse in foreground".

## Some Terms

- Linux namespaces (ns) and their types :

  pid ns, mnt ns, net ns ..., which are the basis of container/sandbox.

- The `unshare`d state (and the non-`unshare`d state): 

  the “connection relationship” between a container and its parent .

<ins><u>Above</u></ins> are what you've already knew.

<ins><u>Following</u></ins> are Tree Sandbox's concepts:

- Main layer:

  The layer used to run the "main app" that the user intends to run is called the "main layer".

- Companion Process:

  Processes that are needed for a sandbox to function but are not the user's target app. Such as Xpra, xdg-dbus-proxy, etc. Companion processes run on layers other than the main layer.

- "Untrusted" and "semi-trusted":

  A semi-trusted layer has access to more host sockets than an untrusted layer. For example, a pure X server running inside the sandbox runs on untrusted layer, while the proc used to forward X11 needs to run in semi-trusted layer. The "main layer" is an untrusted layer.

- Instance, “same-name sandbox”, and "reuse" 

  For a regular "non-reuseful" sandbox, each time the sandbox get started, a new running **sandbox instance** is spawned;
  
  For a "reuseful" sandbox, only one same-name sandbox instance can be kept running. During this time if an attempt to call the start script is made , it simply send the request to the already-running same-name sandbox instance.

  You have an app to run isolated in sandbox. When you want sandbox for this <ins><u>same app</u></ins> act as <ins><u>single-instance sandbox</u></ins> ,  "same-name" is the basis for identification (`uc.sandbox_name`). After finding a live same-name sandbox instance, "reuse" takes off. (Similar to Firejail's `--join=name`)

## Dependencies

Required:

- Linux Kernel >= 6.3
    - user namespace
    - cgroup v2
- glibc
- Python >= 3.12
- bash
- sleep

(Although Python script it is, it directly talks to Linux kernel via libc, no third-party Python library.)

Optional:

- dtach (share shell to the host)
- xdg-dbus-proxy (filter DBus communication)
- [pasta (passt)](https://passt.top) (tun/tap networking)
- nftables (network traffic control)
- Xpra (isolated X11, seamless)
- Weston + Xwayland + icewm (isolated X11)
- Xephyr + icewm (isolated X11)
- xsel (clipboard sync)
- squashfuse (mount AppImage/squashfs internally)
- zenity or kdialog (we stop random web popups with interactive prompts)

## User Manual

### Config using dict-like object

`uc` stands for userconfig. It is a dict-like object.

Unsatisfied with Python's built-in dict, we invent `d()`, a JS-style object that allows member access using **dot**. The following example shows its usage:

```python
uc = d()
# uc.gui = 'real' # The user does not use GUI, so this line is commented out
if uc.gui : # No error occurs here, even if the member gui not exist,
    uc.gpus = True
```

With `d()`, we don't need to use the cumbersome Python approach `if 'gui' in uc`.

`si` means "sandbox info". Its also dict-like. `si` contains commonly used consts of a running sandbox:

```python
si.username
si.uid
si.hostname
si.CWD  # Path where you put a sandbox start script
si.HOME # User HOME dir path on host
```

### Where is full user manual?

Open the code and read the userconfig section at top, which is a user-friendly template, with comments which are enough to make it a tutorial.

A full manual hasn’t been written yet. I’m taking a break.

## User Advanced Manual

The User Advanced Manual is different from the User Manual. In 95% of cases you don’t need the Advanced part.

### On host where those live sandboxes info are

Starting an instance of a sandbox named `ms`, info about this instance will be temporarily stored on host at:

```
/tmp/tsbxs-1000/ms-nnnn-nnnn-n/
```

(`ms-nnnn-nnnn-n` is the name of this sandbox instance.  n is number. Assuming your UID is 1000. )

An additional feature: If the sandbox uses isolated internal X11/Wayland, temporary symlink(s) will be created on host at the following location, to allow <ins><u> user to record sandbox screen easily </u></ins> from host: (assume sandbox uses DISPLAY 500)

```
/tmp/.X11-unix/X500  (symlink)   -> /tmp/tsbxs-1000/ms-nnnn-nnnn-n/x11socket  (also a symlink)   -> /proc/<in-sandbox-proc-pid>/root/tmp/.X11-unix/X500
  
$XDG_RUNTIME_DIR/wayland-500  (symlink)   -> /tmp/tsbxs-1000/ms-nnnn-nnnn-n/waylandsocket  (also a symlink)   -> /proc/<in-sandbox-proc-pid>/root/$XDG_RUNTIME_DIR/wayland-500
```

When sandbox exits, temporary symlinks cleaned up.

### Sandbox layering structure of our default template

"Containers tree" design makes it a fully internally nestable sandbox. A default nesting template is provided, which <ins><u>suits 95% uses, so no need to know how it nests</u></ins>.

But, if you want to unlock more possibilities, you need to understand the internals and how the default template define the "layers" of "containers tree". (It's pretty mind-bending)

```
Linux Host
  |
 outest (the process launched by user; it manages this sandbox and stays outside the sandbox)
  |
 layer1 (pid ns unshared; already inside the sandbox)
  |
 layer2 (prepares for building the semi-trusted zone)
   |
   |--layer2c (runs semi-trusted companion programs, such as xdg-dbus-proxy)
   |
 layer2h (intermediary)
    |
  layer3 (untrusted zone: all ns unahred;
    |       can see base system dirs; only paths explicitly configured by user are visible)
    |
    |--layer4 (runs the user app . This is "main layer")
    |--layer4c (runs companion programs that do not need trust, such as a standalone X server)
```

(Both layer2c and layer4c run companion programs. The difference is that layer2c can access the real host X11 and DBus interfaces, while layer4c does not need to access them.)

After the sandbox starts, the user’s app runs in layer4. layer4 is "main layer".

> There’s still a lot not written yet. I’ll take a break first.

> This project is early-stage; We don't promise no internal design changes in the future.

## Disclaimer

1. This project comes with no warranty. Use on your own risk.
1. Ensure your uses are legal and appropriate. Follow the terms of service for any apps you run with this. You're responsible for whatever happens.

## License

Licensed under GPL.
