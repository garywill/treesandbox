English | [中文](README_zh.md)

# Tree Sandbox

A Linux sandbox tool that allows unlimited nesting. (Comes with a default nesting template designed for regular users.)

Kind of an alternative to Firejail, Flatpak, and Bubblewrap.

> Early-stage project — free to try and read the code. Note: runtime strings and code comments are currently not in English. English comming soon...

## Dependencies

Required:

- Linux Kernel >= 6.3 
    - user namespace
    - cgroup v2
- glibc
- Python >= 3.12
- bash

(Although Python script it is, it directly talks to Linux kernel via libc, without any third-party Python libraries.)

Optional:

- xdg-dbus-proxy
- Weston + Xwayland + icewm (for isolated X11)
- Xephyr + icewm (for isolated X11)
- squashfuse (for mounting AppImage internally)



## What is "container tree"?

This tool focus on a smooth sub-namespaces nesting experience. You can create a tree of layer-on-layer containers as you like.

You can run "untrusted" and "semi-trusted" processes in different layers of one sandbox. 

Every layer's isolation degree is configurable. Every layer's filesystem accessibility range is fine-grained controllable. Arbitrary nestable.

Here's an example, the sandbox container tree might look like:

```verilog
[Linux Host]
    [X11]   Real Desktop
    [dbus-daemon --session]  Real user dbus service

    [Tree Sandbox Sandbox]
      |-[Sub-container : Untrusted zone]
      |   |
      |   |-[Sub-container : Untrusted : User App]
      |   |     [USER-APPS RUN HERE]
      |   | 
      |   |-[Sub-container : Untrusted : Companion Processes (Group 2)]
      |         [Xpra X server]      Isolated X11 Server
      |         [dbus-daemon --session]   Internal user dbus service
      |         [dbus-daemon --system]    Internal system-level dbus
      |         [keyring daemon]          Internal Keyring Service
      |         [icewm]            Lightweight Window Manager, usually paired with Xephyr/Xwayland
      |         
      |-[Sub-container : Semi-trusted zone : Companion Processes (Group 1)]
                [Xephyr]           Isolated X11 Server + Client
                [Weston]           Isolated Wayland Server + Client
                [Xwayland]         Isolated X11 Server 
                [Xpra client]      Seamless Isolated X11 Client
                [dbus-proxy]       Filters and forwards dbus

(Usually not all above will be started. It depends on user options)
```

In above example, two sub-containers are for companion processes. Difference is that the "semi-trusted" one can access host's X11 and DBus socket, while the "untrusted" one can't.

## Why made this? What about its security?

I call it a Firejail/Flatpak alternative. Firejail/Bubblewrap and even official tool `unshare` don't expose some low-level knobs I want. So I built this fully controllable tool. Nesting to arbitrary depth and convinient container tree configuring are our main feature, which other tools don't provide.

Early-stage. It works and you can read the code, but it has not been developed or audited by a security team.

## Features and Implementation Status

- [x] No root needed. No daemon. No host cap/suid needed.
- [x] No junk or traces in home or disk. Temp data in `/tmp` deleted automatically
- [x] Image-free: no container images to download like Docker/LXC. Reuse the host system so tools such as vim/git don’t need to be reinstalled inside
- [x] Fully customizable nested namespaces
    - [x] Per-layer PID/mount/... ns controls
    - [x] Per-layer new rootfs and fine-grained control over filesystem path setup
        - [x] Bind mount (rw/ro)
        - [ ] Directory overlay 
        - [x] Creation or temporary override of files (rw/ro); tmpfs directories (rw/ro)
        - [x] Symlink
    - [x] Environment variable control inside the sandbox
    - [x] UID=0 in layer1, back to uid=1000 in last layer; drop caps; no_new_privs
- [ ] Handle PGID/SID and signals
- [x] Mount AppImage internally
- Use GUI in sandbox:
    - [x] Optional host X11 exposure to sandbox
    - [x] Optional isolated X11 with Weston+Xwayland
    - [x] Optional isolated X11 with Xephyr
    - [ ] Optional Xpra seamless X11 proxy 
    - [ ] Optional host Wayland exposure to sandbox
    - [ ] Optional isolated full desktop in isolated GUI
- Optionally expose real hardwares to sandbox
    - [x] Expose GPU to sandbox
    - [ ] Expose all hardwares to sandbox
- DBus:
    - [x] Optional host DBus exposure to sandbox
    - [x] Optional DBus proxy filtering DBus communication
- [ ] Optional network traffic control 
- Same sandbox: Single-app, multiple-app, single instance, multiple-instance (startup app choosing, instance managing, args passing)
    - [x] Multiple apps for same sandbox (apps by same inc. run in same sandbox)
    - [x] Multi-instances for same sandbox (Multiple startups of same sandbox will have multi-instances running. Each other isolated and independent) 
    - [ ] Single-instance for same sandbox (Multiple startups of same-app sandbox will send args to the first-started running instance. Instruction: Uses `sandbox_name` field you set to distiguish same-app sandbox)
- [ ] In-container shell socket exposed to host 
- [x] Watchdog (when in-sandbox app of companion app exits, sandbox terminated)
- Single-file script. Copy as you like, edit options at file head and run. No install. Minimal dependencies.
    

## Simple usage examples

In following examples, app processes in sandbox can see only ro system dirs, empty home, and some paths/sockets that user explictly allows. 

**Example 1** — Run AppImage in sandbox

Place a copy of Tree Sandbox script next to an AppImage of some app you downloaded. 

```
/anyhdd/freecad/sbxrun_freecad.py
/anyhdd/freecad/FreeCAD.AppImage
/anyhdd2/projects_save/
```

Edit `.py` file and edit `userconfig` part like this:
```python
uc.sandbox_name='freecad'
uc.user_mnts = [
    d(batch_plan='appimage', dirname='freecad', src=f'{si.startdir_on_host}/FreeCAD.AppImage'),
    d(plan='bind', src='/anyhdd2/projects_save/', SDS=1),
]
uc.gui="realX"
```

Tree Sandbox mounts AppImage contents inside the sandbox so AppImage itself doesn’t need to have FUSE caps. This mounts the AppImage under `/sbxdir/apps/freecad/` inside the sandbox. After launching the sandbox, run `/sbxdir/apps/run_freecad` inside it to start the app.

Project files created by the app can be saved under `/anyhdd2/projects_save/` because that host path was bound into the sandbox. The `SDS` flag means “source and destination are the same” so the directory appears with the same path inside and outside the sandbox.

**Example 2** — running a downloaded binary

If you downloaded an app (for example `firefox.tar.xz`) and want to use the app inside the sandbox:

```
/anyhdd/ffx/sbxrun_firefox.py
/anyhdd/ffx/firefox/.... (contains firefox binaries and libraries)
$anyhdd/ffx/fakehome
```

Configure:

```python
uc.sandbox_name='firefox' # sandbox name
uc.user_mnts = [
    d(plan='robind', src=f'{si.startdir_on_host}/firefox', SDS=1), 
    # alternatively, remove SDS and set dest='/sbxdir/apps/firefox'
    d(plan='bind', src=f'{si.startdir_on_host}/fakehome', dest=si.HOME), 
]
uc.gui="realX"
uc.dbus_session="filter" # input methods and other components need dbus
```
**Example 3**— use your existing vimrc inside the sandbox

```python
uc.user_mnts = [
    d(plan='robind', src=f'{si.HOME}/.vimrc', SDS=1), 
]
```
## Sandbox layering model

Tree Sandbox is a multi-layer, nestable sandbox. The script ships with a default nested template:

```
Linux Host 
  |
 layer1 (management layer; PID isolation; start internal privilege)
  |
 layer2 (semi-trusted zone: mount ns isolation; user global privacy paths masked)
   |
   |--layer2c (drop caps; for trusted companion programs, like xpra client / dbus proxy)
   |
 layer2h (intermediary)
    |
  layer3 (untrusted zone: isolates most namespaces; sees system base paths; only data paths explicitly mounted by user are visible)
    |
    |--layer4 (drop caps; where user apps run)
    |--layer4c (drop caps; for untrusted companion programs, such as xpra server)
```

(layer2c and layer4c are both for companion programs. layer2c can access real X11 and real DBus, while layer4c not).

**Normal users do not need to edit the default template — only tweak the user options section.**

When the sandbox is started, user app or an interactive user shell (if requested) will usually run at layer4.

> This project is early-stage and the design may change.

A compact template looks like: (for advanced users) 

```python
layer1 = d( # layer 1
    layer_name='layer1', # do not change the default layer_name
    unshare_pid=True, unshare_user=True, ......
    
    sublayers = [
        d( # layer 2
            layer_name='layer2', # do not change the default layer_name
            unshare_pid=True, unshare_mnt=True, ....
            newrootfs=True, fs=[ ..... ], ....
            
            sublayers = [
                d( layer_name='layer2c', .... ),
                d( 
                    layer_name='layer2h', 
                    sublayers = [
                        d( layer_name='layer3', ..... , newrootfs=True, fs=[ ..... ], .....
                            sublayers=[ # layer 4
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

This is only a rough sketch of the default template. For details open the code.

## Startup sequence

Each layer follows this basic flow:

1. Load the layer configuration
1. Call `unshare()` according to the layer configuration
1. `fork()` — the following steps run in the child
1. Temporary privileges escalation or dropping if configured (Write `/proc/self/uid_map` and related files as required) 
1. Build and mount the layer’s new rootfs (if configured)
1. pivot_root into the new rootfs (if configured)
1. Apply configured environment variable changes (if configured)
1. Drop privileges (if configured)
1. Launch a user shell, start sublayers, or run application(s), depending on configuration

> The project is early-stage and the implementation may evolve.

## Filesystem view inside the sandbox

A typical untrusted app’s visible filesystem inside the sandbox is assembled from plan entries like:

```yml
// # system directories read-only from the host
{'plan': 'robind', 'dest': '/bin', 'src': '/bin'}
{'plan': 'robind', 'dest': '/etc', 'src': '/etc'}
{'plan': 'robind', 'dest': '/lib64', 'src': '/lib64'}
.....

// # minimal /dev
{'plan': 'rotmpfs', 'dest': '/dev'}
{'plan': 'bind', 'dest': '/dev/console', 'src': '/dev/console'}
{'plan': 'bind', 'dest': '/dev/null', 'src': '/dev/null'}
{'plan': 'bind', 'dest': '/dev/random', 'src': '/dev/random'}
{'plan': 'devpts', 'dest': '/dev/pts'}
{'plan': 'tmpfs', 'dest': '/dev/shm'}
......

// # temporary writable directories
{'plan': 'tmpfs', 'dest': '/home/username'}
{'plan': 'tmpfs', 'dest': '/run'}
{'plan': 'tmpfs', 'dest': '/run/user/1000'}
{'plan': 'tmpfs', 'dest': '/tmp'}
......

// # user-configured mounts
{'plan': 'appimg-mount', 'src': '/anyhdd/freecad/FreeCAD.AppImage', 'dest': '/sbxdir/apps/freecad'}
{'plan': 'robind', 'src': '/anyhdd/ffx/firefox', 'dest': '/sbxdir/apps/firefox'}
{'plan': 'robind', 'dest': '/tmp/.X11-unix/X0', 'src': '/tmp/.X11-unix/X0'}
{'plan': 'robind', 'dest': '/tmp/dbus-session.socket', 'src': '/run/user/1000/bus'}

// # sandbox configuration directory
{'batch_plan': 'sbxdir-in-newrootfs', 'dest': '/sbxdir'}
```

(These plan entries are included in the default template so users usually don't have to create them manually.)

The `/sbxdir` directory contains:

- AppImage mountpoints (users may need to know about)
- Configuration and metadata for the current layer and its sublayers
- Files used for communication with layer1 and the host
- Scripts used to start sublayers
- Mountpoints for sublayers’ new rootfs
- …

## How to edit the layer nesting template

TBD