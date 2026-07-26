#!/usr/bin/env -S python3 -IBS

# Tree Sandbox for Linux
# Licensed under GPL.  https://github.com/garywill/treesandbox
# This project comes with no warranty. Use on your own risk.

import os, sys, shutil, subprocess, pwd, grp, time, pty, ctypes, ctypes.util, atexit, json, copy, tempfile, struct, re, socket, signal, asyncio, datetime , types, select, fcntl, traceback, random , errno, shlex, enum, argparse, hashlib, io, resource, string, platform
from pathlib import Path
from glob import glob
shutil.rmtree = None

# === USER_CONFIG BEGIN === NOTE: Don't change this line ===

# You can use our default userconfig() code as example / template / tutorial.
# Config your sandbox by enabling / modifying / commenting out these options.

# Notice TreeSandbox is in early stage. We try to keep userconfig options stably, but no promise.

def userconfig(si):
    uc = d() # dict-like object

    uc.sandbox_name='TryTreeSandbox' # NOTE You should give a name to your sandbox

    # ---- Reuse Or Not ----
    # uc.reuseful=True   # Reuse running same-name sandbox instance if there is one alive. (Enabling this makes your sandbox single-instance, otherwise multi-instance)
    uc.idleKeepSbxTime = 2 if uc.reuseful else 0 # Keep sandbox alive for a time (second), even if idle (no user app alive)
    # ---- ---- ----

    uc.apps = [
        # The first item is default app, which can omit appname
        d(cmdvec=['bash', '--norc'], appname='bash'), # Recommend to keep this item, so host can get sandbox shell easily if needed
        d(cmdvec=['sleep', 'infinity'], appname='sleep'),
    ]
    # cmdvec is array, elements are shell args ( shell command string splitted )
    # When starting sandbox, you can use cli '--app <appname>'. If not, default app is chosen


    # ---- User Mounts -----

    # Linux basic system dirs (/bin, /lib, ...) are auto mounted.
    # uc.user_mnts are what you want to add.
    uc.user_mnts = [
        # The term "CWD" here is the path where you put this sandbox start script.
        # `si` is dict-like object,  means "sandbox info".
        # 'SDS' means "src and dest have same value".

        # For persistant storage, use 'fakehome' dir as sandbox's HOME dir. Otherwise, tmpfs is used as HOME
        # d(op='bind', src=f'{si.CWD}/fakehome', dest=si.HOME),

        # d(op='robind', src=f'{si.HOME}/.bashrc', SDS=1),
        # d(op='robind', src=f'{si.HOME}/bin', SDS=1),
        # d(op='robind', src=f'{si.HOME}/.local/bin', SDS=1),
        # d(op='robind', src=f'{si.HOME}/.local/lib', SDS=1),
        # d(op='robind', src='/home/linuxbrew', SDS=1),
        # d(op='robind', src=f'{si.HOME}/.npmrc', SDS=1),
        # d(op='robind', src=f'{si.HOME}/.vimrc', SDS=1),
        # d(op='robind', src=f'{si.HOME}/.config/pip/pip.conf', SDS=1),

        # d(many_op='appimage', name='xxxx', src=f'{si.CWD}/xxxx.AppImage'),
        # AppImage mounting example. Will do :
        #   - AppImage mounted at /sbxdir/apps/xxxx/ in sandbox
        #   - Script /sbxdir/apps/run_xxxx is created

    ]





    # --- GUI ----

    # Without uc.gui, no DISPLAY in sandbox
    # When uc.gui has value and is not "realX", a sandbox-managed new DISPLAY is used inside.
    # uc.gui="realX" # Use host's real X11
    # uc.gui="weston-xwayland" # Windowed. Xwayland in Weson
    # uc.gui="xephyr" # Windowed
    # uc.gui='xpra-weston-xwayland' # Seamless. GPU acceleration. Xwayland (in Weston) as internal X server
    # uc.gui='xpra' # Seamless. No GPU acceleration. Xvfb as internal X server

    # uc.newXId='50' # When internel DISPLAY used , the DISPLAY id. String. Otherwise random

    uc.windowed_size = (800, 600) # Take effects when gui uses weston/xephyr

    uc.sync_clipbd_from_sandbox = True # Auto sync clipboard from sandbox to host (take effect if internel DISPLAY used)

    uc.gpus     =      True if uc.gui else False # Sandbox can see /dev/dri and needed GPU's PCI paths in /sys .
    uc.see_userfonts = True if uc.gui else False # Sandbox can see ~/.fonts and so on.

    # --- ---- ----


    # uc.see_real_hw=True # Sandbox see host's real /dev and /sys


    # --- DBus ----

    # User (session) DBUS (things like IME needs DBUS)
    if uc.gui: uc.dbus_session="filter"
    # uc.dbus_session="allow" # Allow all DBUS communication
    # uc.dbus_session="filter" # DBUS communication filtered by xdg-dbus-proxy. Default rule is allowing IME and notifications (you can add more to uc.dbusproxy_extra also)

    # uc.dbusproxy_extra = ['--see=org.gnome.Shell'] # xdg-dbus-proxy (by Flatpak) extra args

    # --- ---- ----

    # Create a path in host as share dir. Dir will be accessable (r/w) by sandbox too.
    # In sandbox, both same path and a '/tmp/share' is to this dir (r/w).
    # This is a prefix. Sandbox name will be added to the dir name.
    uc.sharedir_prefix='/tmp/tsbx-share_'


    # uc.pulseaudio=True,
    # uc.cups=True, # CUPS print

    uc.ask_xdg_open=True # Replace 'xdg-open' by an asking script.
    uc.forbid_browsers=True # Ban system's firefox/chromium/... in sandbox. (Experimental)
    # uc.mask_osrelease=True # Ban /etc/os-release
    # uc.machineid='zero' # Write zeros to /etc/machine-id (in rare cases may break some app). Otherwise keep real.

    uc.set_envs = d( # Env vars seen by main apps in sandbox. Values must be string
        # ENV_VAR_NAME1 = 'ENV_VAR_VAL1',
        # ENV_VAR_NAME2 = 'ENV_VAR_VAL2',
    )

    # --- Network ----

    uc.net_iface='real' # Use host's real net ifaces. Won't unshare net ns
    # uc.net_iface='tuntap-pasta' # Use pasta to create new net ns and manage net iface
    # uc.net_iface='none' # Omitting net_iface means 'none' also

    # uc.dns_custom=['127.0.0.1'] # Custom /etc/resolv.conf . If not custom and net_iface=real, host's real resolv.conf will be used

    uc.pasta_custom_args = [ # NOTE Takes effect when uc.net_iface=tuntap-pasta .
        # NOTE （no '-T' or no '-U' will allow all local ports seen by sandbox）
        '-T', 'none', '-U', 'none', # Forbid to access any port of host localhost

        '--config-net', '--host-lo-to-ns-lo',

        # '--no-map-gw',  # If sandbox ip not configured, its internal ip will be looked same as host. In this case you should consider enabling this --no-map-gw
        '-a', '172.16.1.2', '-n', '30',  '-g', '172.16.1.1', '-a', 'fd00::2',  '-g', 'fd00::1',
        # '--ns-mac-addr', '00:00:00:00:00:04', # No this = random MAC

        # '--debug', '--trace',
    ] if uc.net_iface=='tuntap-pasta' else None

    # NOTE Only when uc.net_iface=tuntap-pasta , set_nftables can be enabled
    # uc.set_nftables = True # Enable this, then nftables rules below will be applied to sandbox
    if uc.set_nftables == True : uc.nftables_rule = '''
        define DYNAMIC_BANIP_V4 = { 224.0.0.0/4 }
        # optional blacklisting 224.0.0.0/4, (multicast)
        # optional blacklisting 127.0.0.0/8,  (loopback)
        define DYNAMIC_BANIP_V6 = { ff00::/8 }
        # optional blacklisting ff00::/8,  (multicast)
        # optional blacklisting ::1, (loopback)
        table inet myfiltertable {
            set banip_v4 { type ipv4_addr; flags interval
                elements = { 0.0.0.0/8, 10.0.0.0/8, 100.64.0.0/10, 169.254.0.0/16, 172.16.0.0/12, 192.168.0.0/16, 255.255.255.255, $DYNAMIC_BANIP_V4  }
            }
            set banip_v6 { type ipv6_addr; flags interval
                elements = { ::/128, ::ffff:0:0/96, ::ffff:0:0:0/96, fc00::/7, fe80::/10, $DYNAMIC_BANIP_V6 }
            }
            chain myoutputchain { type filter hook output priority 0; policy accept;
                ct state established,related accept
                meta l4proto ipv6-icmp ip6 daddr { ff02::1, ff02::2, ff02::1:ff00:0/104 } accept
                meta l4proto { tcp, udp } th dport { 53 } accept
                ip  daddr @banip_v4 reject with icmp   type admin-prohibited
                ip6 daddr @banip_v6 reject with icmpv6 type admin-prohibited
            }
        }
    '''.strip()

    return uc

# === USER_CONFIG END === NOTE: Don't change this line ===

def gen_dynamic_cfg(si, uc): # 这个只在顶层解析一次
    cmds_to_mask = [] # 内部，不传递
    paths_to_mask = [] # 传递
    mnts_dns = []
    mnts_gui = []
    xephyr_extra_args = []
    weston_extra_args = []
    xpra_extra_args = [] ; xpra_server_extra_args = [] ; xpra_client_extra_args = []
    xwayland_extra_args = []
    bridges = []
    #-------------------------

    icewm = True if uc.gui in ['xephyr','weston-xwayland'] else False

    if uc.see_userfonts: mnts_gui += [
        d(op='robind', src=f'{si.HOME}/.fonts', SDS=1)      if os.path.lexists(f'{si.HOME}/.fonts') else None,
        d(op='robind', src=f'{si.HOME}/.fonts.conf', SDS=1) if os.path.lexists(f'{si.HOME}/.fonts.conf') else None,
        d(op='ovl', src=f'{si.HOME}/.cache/fontconfig', SDS=1) if os.path.lexists(f'{si.HOME}/.cache/fontconfig') else None,
    ]

    if uc.gpus: # /sys/module/i915 这类一般不用也可以
        sys_devices_pciX_X = [ padir(p) for p in glob('/sys/devices/*/*/drm') ]
        mnts_gui += [
            d(op='rosame', src='/dev/dri', SDS=1),
            d(op='rosame', src='/sys/class/drm', SDS=1),
            *[ d(op='rosame', src=p, SDS=1) for p in glob('/sys/dev/char/226:*') ],
            *[ d(op='rosame', src=p, SDS=1) for p in sys_devices_pciX_X ],
            *[ d(op='rosame', src=rslvy(f'{p}/driver'), SDS=1) for p in sys_devices_pciX_X ],
        ]
        for link in glob('/sys/bus/pci/devices/*'):
            if rslvy(link) in sys_devices_pciX_X:
                mnts_gui += [ d(op='rosame', src=link, SDS=1) ]


    if uc.gui and uc.gui != 'realX': # 使用GUI但不是真实X, 说明是某种隔离的X,需要新的X编号
        if uc.newXId:
            newXId = uc.newXId
        else:
            while (newXId := str(random.randrange(230, 980)) ) :
                if is_XId_available(newXId): break

    if uc.gui in ['xpra', 'xpra-weston-xwayland']:
        mnts_gui += [
            d(op='tmpfs', dest=f'{si.HOME}/.xpra'),
            d(op='tmpfs', dest=f'{si.HOME}/.config/xpra'),
            # d(op='rofile',  dest=f'{si.HOME}/.fakexinerama', content=''), # 不注释这两个则可以阻止这两个文件有内容，但好像不重要
            # d(op='rofile',  dest=f'{si.HOME}/.{newXId}-fakexinerama', content=''),
            d(op='rofile',dest='/etc/X11/Xwrapper.config', content='allowed_users=anybody') if os.path.lexists('/etc/X11/Xwrapper.config') else None,
        ]

        xpra_extra_args += [
            '--daemon=no',
            # '--bind=unix',
            # '--auth=allow', # '--wss-auth=allow', # '--tcp-auth=allow', # '--ssl-auth=allow', # '--rfb-auth=allow', # '--vsock-auth=allow', # '--ssh-auth=allow', # '--rdp-auth=allow', # '--quic-auth=allow',
            '--start-new-commands=no',
            '--pulseaudio=no',
            '--dbus=no',
            '--dbus-launch=no', # NOTE  禁止dbus为什么无效？
            '--dbus-control=no',
            '--tray=no',
            '--webcam=no',
            '--html=off',
            '--http=off',
            '--systemd-run=no',
            '--exit-with-windows=no',
            '--exit-with-client=no',
            '--mdns=no',
            '--file-transfer=no',
            '--forward-xdg-open=off',
            # --headerbar=auto|no|force
            '--printing=no',
            '--keyboard-sync=no',
            # --keyboard-raw=yes|no
            '--opengl=yes:native', # --opengl=(yes|no|auto)[:backend]
            '-z0', # 无压缩

            '--video=yes',
            '--encoding=rgb',
            '--video-encoders=vaapi',

            #--speaker=on|off|disabled and --microphone=on|off|disabled|on:DEVICE|off:DEVICE
            '--speaker=disabled',
            '--microphone=disabled',
            #--title=VALUE
            #--border=yellow,10.
            '--clipboard-direction=disabled', # 用xpra的好像对ASK_OPEN不灵
            '--challenge-handlers=env' ,
            # --xsettings=auto|yes|no # 您本机的主题、字体渲染等配置传递给沙箱程序
            # '--socket-dir=/tmp/xpra/socket-dir',
            # '--sessions-dir=/tmp/xpra/sessions-dir',
            '--video-scaling=off',
            '--desktop-scaling=off',
            '--use-display=yes'
        ]
        if uc.gui=='xpra-weston-xwayland':
            weston_extra_args += [
                '--backend=headless',
                '--renderer=gl',
                '--width=8000', '--height=4500'
            ]

        # Xorg的参数-ac让不需要XAUTHORITY。 如果不自定义xpra的--xvfb的值的话，无法让Xserver免认证。xpra的--auth可能控制的是xpra的客户端与服务端之间的认证，不是x server与client的认证

    if uc.windowed_size:
        if uc.gui == 'xephyr':
            xephyr_extra_args += ['-screen', f'{uc.windowed_size[0]}x{uc.windowed_size[1]}']
        elif uc.gui == 'weston-xwayland' :
            weston_extra_args += [f'--width={uc.windowed_size[0]}', f'--height={uc.windowed_size[1]}' ]
            xwayland_extra_args += ['-geometry', f'{uc.windowed_size[0]}x{uc.windowed_size[1]}']

    if uc.dbus_session == 'filter':
        dbusproxy_argv = [
            getenv('DBUS_SESSION_BUS_ADDRESS'), '/tmp/dbusproxy.socket', '--filter',
            '--talk=org.freedesktop.Notifications',
            '--talk=org.fcitx.*',
            '--talk=org.freedesktop.IBus.*',
            '--talk=org.freedesktop.portal.IBus',
            '--talk=org.freedesktop.portal.Fcitx',
            *(uc.dbusproxy_extra or [])]
            # '--talk=org.kde.StatusNotifierWatcher', org.kde.StatusNotifierItem # TODO 这两个与系统托盘图标有关， realX时可以考虑允许

    # 处理 /etc/resolv.conf
    CHK( Path('/var/run').is_symlink() and rslvn('/var/run') == '/run', "/var/run is not linked to /run on your host, which is different to most Linux distros. We can't handle this for now")
    RSLVCF_is_link = True if Path('/etc/resolv.conf').is_symlink() else False
    RSLVCF_is_file = is_file('/etc/resolv.conf')
    CHK(RSLVCF_is_link or RSLVCF_is_file, f"/etc/resolv.conf not symlink or file. We can't handle this")
    dns_use_custom = isinstance(uc.dns_custom, list)
    if dns_use_custom: RSLVCF_content = ''.join([f'nameserver {ip}\n' for ip in uc.dns_custom])
    have_iface = uc.net_iface in ['real', 'tuntap-pasta']

    if not have_iface: uc.net_iface = 'none'
    if uc.set_nftables: CHK(uc.net_iface=='tuntap-pasta', 'Only when uc.net_iface=tuntap-pasta, set_nftables can be enabled')

    # link/file | custom/notcustom | ifacereal 共8种情况
    # TODO nscd if use real
    if RSLVCF_is_file : # /etc/resolv.conf是文件，非链接
        if dns_use_custom:
            mnts_dns = [d(op='rofile', content=RSLVCF_content, dest='/etc/resolv.conf')]
            log_warn('Your /etc/resolv.conf is file not symlink. And you configured custom dns for sandbox. If NetworkManager changes network state, your custom dns will lose and become back to the host one')
        else:
            if have_iface: mnts_dns = [] # 原本的/etc/resolv.conf文件保持
            else             : mnts_dns = [d(op='empty-if-exist', dest='/etc/resolv.conf')] # 清空
    else: # /etc/resolv.conf是链接
        RSLVCF_target_dir = padir(rslvn('/etc/resolv.conf'))
        CHK(RSLVCF_target_dir.startswith('/run/'), f"/etc/resolv.conf target is {rslvn('/etc/resolv.conf')}, which not in /run/xxx/ , we can't handle this. (Most distros /etc/resolv.conf -> /var/run/xxxx/ -> /run/xxxxx)")
        if dns_use_custom:
            mnts_dns = [d(op='rofile', content=RSLVCF_content, dest=rslvn('/etc/resolv.conf'))]
        else:
            if have_iface: mnts_dns = [d(op='robind', src=RSLVCF_target_dir, SDS=1)]
            else             : pass # 让/run/xxxxx/resolv.conf继续不存在

    browser_cmds = [
        "firefox", "firefox-esr", "seamonkey", "icecat",
        "librewolf", "waterfox", "palemoon", "basilisk", "floop", "zen-browser",
        "chromium", "chromium-browser",
        "google-chrome", "google-chrome-stable", "ungoogled-chromium",
        "microsoft-edge", "microsoft-edge-stable",
        "vivaldi", "brave-browser", "opera",
        "torbrowser-launcher", "torbrowser",
        "konqueror", "falkon", "epiphany",
        "lynx", "w3m", "links", "elinks", "browsh",
        "dillo", "qutebrowser", "midori", "otter-browser", "xombrero", "luakit", "dooble", "netsurf", "nyxt", "iridium", "surf"
    ]
    if uc.forbid_browsers:
        cmds_to_mask += browser_cmds
    paths_to_mask += [ path for cmd in cmds_to_mask if (path := which_and_resolve_exist(cmd)) is not None ]

    if uc.machineid == 'zero':
        machineid = '00000000000000000000000000000000'

    # bridge seefrom是从哪层可看见这个桥进程 seeto是通过这个桥进程看到哪个层的fs
    if uc.gui in ['weston-xwayland','xpra', 'xpra-weston-xwayland']:
        bItem = d(seefrom='semitruCmpannLyr', seeto='mainLyr')
        bItem.create_links = []
        bItem.create_links += [f'/tmp/.X11-unix/X{newXId}']
        if uc.gui in ['xpra', 'xpra-weston-xwayland']:
            bItem.create_links += [ # NOTE 不能链目录，要防止xpra客户端的socket被放进目录里被server看见
                f'/run/xpra/{si.hostname}-{newXId}',
                f'/run/user/{si.uid}/xpra/{si.hostname}-{newXId}',
                f'/run/user/{si.uid}/xpra/Xauthority-{newXId}',
                f'/run/user/{si.uid}/xpra/{newXId}/socket',
                f'/run/user/{si.uid}/xpra/{newXId}/xauthority',
                f'/run/user/{si.uid}/xpra/{newXId}/config',
                f'/run/user/{si.uid}/xpra/{newXId}/cmdline',
                f'/run/user/{si.uid}/xpra/{newXId}/server.env',
                f'{si.HOME}/.xpra/{si.hostname}-{newXId}',
                f'{si.HOME}/.config/xpra/xpra.conf',
            ]
        bridges.append(bItem)

    dyncfg = d({k: v for k, v in locals().items() if k in [
        'paths_to_mask', 'machineid', 'sharedir_onhost', 'dbusproxy_argv' , 'mnts_dns', 'bridges',
        'newXId', 'mnts_gui', 'xephyr_extra_args', 'weston_extra_args', 'xwayland_extra_args', 'xpra_extra_args', 'xpra_server_extra_args', 'xpra_client_extra_args', 'icewm',
    ]})
    return dyncfg

# layer1 产生。 所有的layer_cfg都在 layer1 下
def gen_layer1(si, uc, dyncfg): # 这个只在顶层解析一次
    # 第1层不跑任何程序，只用于PID隔离，和退出时的清理工作
    return d(
        layer_name='layer1', # 默认模板的 layer_name 不要修改
        unshare_pid=True, # 第1层必须
        unshare_mnt=True, # 第1层尝试有unshare mnt但不newrootfs

        # uid 变 0
        unshare_user=True, uid_map_as_root=True,
        # 准备开始第2层。这第1层的 sublayers 数组应该只有一个元素，即，第2层只有一个容器
        sublayers = [gen_layer2(si, uc, dyncfg)],
    )

def gen_layer2(si, uc, dyncfg):
    return d(
        layer_name='layer2', # 默认模板的 layer_name 不要修改
        unshare_mnt=True,
        newrootfs=True, # 第2层必须 # 有newrootfs则必须有fs
        fs=[ # fs全称 fs_operations_for_new_rootfs 。
            # 第2层是首次 unshare mnt 。先复制一次真实host的rootfs环境
            d(many_op='container-rootfs'),
            d(many_op='basic-dev'),
            d(op='rosame', src='/dev/net/tun', SDS=1) if uc.net_iface=='tuntap-pasta' else None,
            d(many_op='mask-privacy', destbase='/'),
            d(many_op='sbxdir-in-newrootfs', dest='/sbxdir'),

            *dyncfg.mnts_gui,

            d(op='robind', src=f'/tmp/.X11-unix/X{getenv("DISPLAY").lstrip(":")}', SDS=1),
            d(op='robind', src=f'{getenv("XAUTHORITY")}', SDS=1),

            d(op='bind', src=getenv('DBUS_SESSION_BUS_ADDRESS').removeprefix('unix:path='), SDS=1 ),

            d(many_op='dup-rootfs', destbase='/zrootfs'), # 排除/proc。不加ro。
            d(many_op='mask-privacy', destbase='/zrootfs'),
            d(op='empty-if-exist', dest=f'/zrootfs/{si.PTMP}'),
        ],
        envs_unset=[
            "SYSTEMD_EXEC_PID", "MANAGERPID", "SSH_AGENT_PID", "SSH_AUTH_SOCK",  "WINDOWMANAGER", "SHELL_SESSION_ID", "INVOCATION_ID", "GPG_TTY", "XDG_SESSION_ID", "KONSOLE_DBUS_SERVICE", "GPG_AGENT_INFO", "OLDPWD", "WINDOWID", "SESSION_MANAGER", "JOURNAL_STREAM",  "XDG_CACHE_HOME",
            "XDG_SESSION_TYPE", "WAYLAND_DISPLAY", "QT_WAYLAND_RECONNECT", # 这几个是因为现在暂时不支持主机wayland所以放这里先
        ],
        envset_grps=[
            d(NO_AT_BRIDGE='1'),
            d(XDG_RUNTIME_DIR=si.sbx_XDG_R_D),
        ],

        create_userns_unpri=True,

        unshare_net=True if uc.net_iface == 'none' else False,
        pasta_args = uc.pasta_custom_args if uc.net_iface=='tuntap-pasta' else None, # 运行pasta, 并把自身加入其新netns
        nftables_rule = uc.nftables_rule if uc.set_nftables else None,

        sublayers = [
            gen_layer2c(si, uc, dyncfg),
            gen_layer2z(si, uc, dyncfg),
        ],
    )

def gen_layer2c(si, uc, dyncfg):
    # layer2c实际上深度为3, 这层是为了运行可信程序如 xpra client , dbus proxy 等
    return d(
        layer_name='layer2c', unshare_pid=True, unshare_mnt=True,
        unshare_net=True, # 如果有些subp会监听抽象套接字，为了不被其他沙箱偷看，要隔离. 也可以考虑用 unshare -n -r -c 来启动它们
        newrootfs=True,
        fs=[
            d(many_op='dup-rootfs', destbase='/'),
            d(many_op='sbxdir-in-newrootfs', dest='/sbxdir'),
        ],
        is_semitruCmpannLyr=True, # 设layer2c（而非2）为semitruCmpannLyr,因为2c才有unshare_pid
        subprocs=[
            d( subp_name='xephyr', cmdvec=["Xephyr",  f":{si.newXId}", '-nolisten', 'local', "-resizeable",  "-ac", '-title', si.sandbox_name,  *dyncfg.xephyr_extra_args]
            ) if uc.gui=='xephyr' else None,

            d( subp_name='weston', cmdvec=["weston", f"--socket=wayland-{si.newXId}" ,  f"--shell=kiosk", *dyncfg.weston_extra_args]
            ) if uc.gui in ['weston-xwayland', 'xpra-weston-xwayland'] else None,

            d( subp_name='xpraclient', cmdvec=['env', 'XPRA_PASSWORD=abc', 'xpra', *dyncfg.xpra_extra_args, *dyncfg.xpra_client_extra_args,  'attach',f':{si.newXId}'],
                start_after = [
                    d(waittype='socket-listened', path=f'/tmp/.X11-unix/X{si.newXId}') ,
                    d(waittype='socket-listened', path=f'/run/xpra/{si.hostname}-{si.newXId}')
            ] ) if uc.gui in ['xpra', 'xpra-weston-xwayland'] else None,

            d( subp_name='dbusproxy',  cmdvec=['xdg-dbus-proxy', *dyncfg.dbusproxy_argv]
            ) if uc.dbus_session=='filter' else None,
        ],
        daemon_tasks = [
            d(task='sync_clipbd') if uc.gui in ['weston-xwayland', 'xephyr', 'xpra', 'xpra-weston-xwayland'] else None,
        ],
    )

def gen_layer2z(si, uc, dyncfg):
    return d( # layer2z 作为 layer2和3之间，把layer2的/zrootfs变回真/，准备让layer3接
        layer_name='layer2z',  unshare_mnt=True,
        start_after=[
            d(waittype='socket-listened', path='/tmp/dbusproxy.socket') if uc.dbus_session=='filter' else None,
            d(waittype='socket-listened', path=f'/tmp/.X11-unix/X{si.newXId}') if uc.gui=='xephyr' else None,
            d(waittype='socket-listened', path=f'{si.sbx_XDG_R_D}/wayland-{si.newXId}') if uc.gui in ['weston-xwayland', 'xpra-weston-xwayland'] else None,
        ],
        newrootfs=True,
        fs=[
            d(many_op='dup-rootfs', srcbase='/zrootfs'),
            d(many_op='sbxdir-in-newrootfs', dest='/sbxdir'),

            d(op='robind', src=f'/tmp/.X11-unix/X{si.newXId}', dest=f'/sbxdir/temp/X{si.newXId}') if uc.gui=='xephyr' else None,
            d(op='robind', src=f'{si.sbx_XDG_R_D}/wayland-{si.newXId}', dest=f'/sbxdir/temp/wayland-{si.newXId}') if uc.gui in ['weston-xwayland', 'xpra-weston-xwayland'] else None,
            d(op='robind', src='/tmp/dbusproxy.socket', dest='/sbxdir/temp/dbusproxy.socket') if uc.dbus_session=='filter' else None,
        ],
        sublayers=[ gen_layer3(si, uc, dyncfg) ],
    )

def gen_layer3(si, uc, dyncfg):
    return d(
        layer_name='layer3', # 默认模板的 layer_name 不要修改
        unshare_mnt=True,
        unshare_cgroup=True,
        unshare_ipc=True,
        unshare_time=True,
        unshare_uts=True,

        newrootfs=True, # 有newrootfs则必须有fs
        fs=[ # fs全称fs_operations_for_new_rootfs 。
            d(many_op='container-rootfs'),  # 不包括 dev 。不包括 proc
            d(many_op='sbxdir-in-newrootfs', dest='/sbxdir'),
            d(op='empty-if-exist', dest=rslvn(si.startscript_on_host)),

            # ---- 以上是不变条目 ----

            d(many_op='basic-dev') if not uc.see_real_hw else None, # 创建新的容器最小的/dev

            d(op='robind', src=f'/run/user/{si.uid}/pulse/native', SDS=1) if uc.pulseaudio else None,
            d(op='robind', src=rslvy('/var/run/cups/cups.sock'), SDS=1) if uc.cups else None,

            *([
            d(op='robind', src='/dev', SDS=1),
            d(op='tmpfs',dest='/dev/shm'),
            d(op='robind',  src='/sys/class', SDS=1),
            d(op='robind',  src='/sys/bus', SDS=1),
            d(op='robind',  src='/sys/devices', SDS=1),
            ] if uc.see_real_hw else [] ),
            # TODO 1. 改用dyncfg  2. layer2里也加

            *([
            d(op='robind', dest=f'/tmp/.X11-unix/X{getenv("DISPLAY").lstrip(":")}', SDS=1),
            d(op='robind', dest='/tmp/xauthfile', src=f'{getenv("XAUTHORITY")}'),
            ] if uc.gui=='realX' else [] ),

            d(op='robind', src=f'/sbxdir/temp/X{si.newXId}', dest=f'/tmp/.X11-unix/X{si.newXId}') if uc.gui=='xephyr' else None,
            d(op='robind', src=f'/sbxdir/temp/wayland-{si.newXId}',  dest=f'{os.getenv("XDG_RUNTIME_DIR")}/wayland-{si.newXId}', ) if uc.gui in ['weston-xwayland', 'xpra-weston-xwayland'] else None,

            *dyncfg.mnts_gui,

            d(op='rofile', dest=shutil.which("xdg-open"), destmode='555', content=ASK_OPEN ) if uc.ask_xdg_open else None,
            *[d(op='empty-if-exist', dest=path) for path in dyncfg.paths_to_mask],

            d(op='robind', dest='/tmp/dbus-session.socket',  src=getenv('DBUS_SESSION_BUS_ADDRESS').removeprefix('unix:path=')) if uc.dbus_session == 'allow' else None,
            d(op='robind', dest='/tmp/dbus-session.socket', src='/sbxdir/temp/dbusproxy.socket') if uc.dbus_session=='filter' else None,

            d(op='empty-if-exist', dest='/etc/fstab'),
            d(op='empty-if-exist', dest=rslvn('/etc/os-release')) if uc.mask_osrelease else None,
            d(op='rofile', dest='/etc/machine-id', content=dyncfg.machineid) if dyncfg.machineid else None,

            *dyncfg.mnts_dns,

            *([
            d(op='tmpfs',  dest=f'{si.HOME}/.icewm'),
            d(op='rofile', dest=f'{si.HOME}/.icewm/preferences', content=ICEWM_PREF),
            d(op='rofile', dest=f'{si.HOME}/.icewm/prefoverride', content=ICEWM_PREF),
            # d(op='rofile', dest=f'{si.HOME}/.icewm/winoptions', content=ICEWM_WINOPTIONS),# 让app无法决定新窗口位置
            d(op='rofile', dest=f'{si.HOME}/.icewm/menu', content=''),
            d(op='rofile', dest=f'{si.HOME}/.icewm/toolbar', content=''),
            d(op='rofile', dest=f'{si.HOME}/.icewm/programs', content=''),
            ] if dyncfg.icewm else [] ),

            *([
            d(op='bind', src=si.sharedir_onhost, dest='/tmp/share'),
            d(op='bind', src=si.sharedir_onhost, SDS=1),
            ] if si.sharedir_onhost else []),

            # NOTE 用户挂载要放最后
            *(uc.user_mnts if uc.user_mnts else []), # NOTE 用户挂载要放最后
            d(op='final-rmt-ro', dest='/sbxdir/apps', flag=mntflag_apps)
        ],
        envs_unset=[
            "ICEAUTHORITY", "XAUTHORITY", "DISPLAY", "WAYLAND_DISPLAY", "XAUTHLOCALHOSTNAME", "IBUS_ADDRESS", "DBUS_SESSION_BUS_ADDRESS", "DBUS_SYSTEM_BUS_ADDRESS",
            "XDG_SESSION_DESKTOP", "XDG_CURRENT_DESKTOP", "KDE_FULL_SESSION", "KDE_APPLICATIONS_AS_SCOPE", "KDE_SESSION_UID", "KDE_SESSION_VERSION", # TODO 如果用户主机不是KDE是其他, 会有其他变量需要去除
        ],
        envset_grps=[
            d( DISPLAY=getenv("DISPLAY"), XAUTHORITY='/tmp/xauthfile', ) if uc.gui=='realX' else None,
            d(DISPLAY=f':{si.newXId}') if uc.gui in ['xephyr','weston-xwayland','xpra', 'xpra-weston-xwayland'] else None,
            # d(WAYLAND_DISPLAY=f'wayland-{si.newXId}') if uc.gui in ['weston-xwayland', 'xpra-weston-xwayland'] else None, # 先不要 WAYLAND_DISPLAY 这个环境变量，让应用都使用 Xwayland 先
            d(DBUS_SESSION_BUS_ADDRESS='unix:path=/tmp/dbus-session.socket') if uc.dbus_session else None,
        ],
        sublayers=[
            gen_layer4c(si, uc, dyncfg),
            gen_layer4(si, uc, dyncfg),
        ],
    )

def gen_layer4c(si, uc, dyncfg):
    return d(
        layer_name='layer4c', # 默认模板的 layer_name 不要修改
        unshare_pid=True, unshare_mnt=True,
        unshare_net=True, # NOTE 内部xpra所带出来的dbus可能监听抽象套接字。最好unshare_net, 否则因为我们不要求认证，其他沙箱不隔离网络就可能偷看这个, 也可以考虑用unshare -n -r -c 来启动Xorg
        subprocs=[
            *([
            d( subp_name='icewm', cmdvec=['env', 'LC_ALL=en_US.UTF8', 'env', 'LANG=en_US.UTF8', 'env', 'LANGUAGE=en_US.UTF8', 'icewm-session', '--nobg'] , start_after = [ d(waittype='socket-listened', path=f'/tmp/.X11-unix/X{si.newXId}') ] ) ,
            # d( subp_name='icewmtray', cmdvec=["icewmtray"] ,  start_after = [ d(waittype='socket-listened', path=f'/tmp/.X11-unix/X{si.newXId}') ] ) ,
            ] if dyncfg.icewm else [] ) ,

            d( subp_name='xwayland',  cmdvec=['env', f'WAYLAND_DISPLAY=wayland-{si.newXId}', 'Xwayland', f':{si.newXId}', '-nolisten', 'local', *dyncfg.xwayland_extra_args ]
            ) if uc.gui in ['weston-xwayland', 'xpra-weston-xwayland'] else None,

            d( subp_name='xvfb', cmdvec=["Xvfb", "+extension", "GLX", "+extension", "RANDR", "+extension", "RENDER", "+extension", "Composite", "-extension", "DOUBLE-BUFFER", "-nolisten", "tcp", "-nolisten", "local", "-noreset", "-ac",  f":{si.newXId}"] ) if uc.gui=='xpra' else None,

            d( subp_name='xpraserver' ,  cmdvec=['env', 'XPRA_PRIVATE_XAUTH=1', 'env', 'XPRA_PASSWORD=abc', 'xpra', 'start', *dyncfg.xpra_extra_args, *dyncfg.xpra_server_extra_args, f':{si.newXId}'], start_after = [ d(waittype='socket-listened', path=f'/tmp/.X11-unix/X{si.newXId}') ]
            ) if uc.gui in ['xpra', 'xpra-weston-xwayland'] else None,
        ],
    )

def gen_layer4(si, uc, dyncfg):
    return d( # 主 用户app 在这里跑
        layer_name='layer4', # 默认模板的 layer_name 不要修改
        is_mainlyr=True,  # 我是主app所在层
        unshare_pid=True, unshare_mnt=True,

        envset_grps = [
            d(PATH=getenv("PATH").rstrip(':')+':/sbxdir/apps' ),
            uc.set_envs if uc.set_envs else {},
        ],

        start_after = [
            d(waittype='socket-listened', path=f'/tmp/.X11-unix/X{si.newXId}') if uc.gui in ['xephyr', 'weston-xwayland','xpra', 'xpra-weston-xwayland'] else None,
            # TODO 等待icewm, 如果需要
        ],
        # user_shell=True, # 调试用
        # dev_shell=True,  # 调试用
    )

class NameMng:
    random_chars = "abcdefghkmnpqrsuvwxyz"
    @classmethod
    def chk_str_valid_sandbox_name(cls, string):
        CHK( re.match(r'^[a-zA-Z0-9_-]+$', string), f"Sandbox name can only contain letters, numbers, '-', '_' . This name is invalid: {string}" )
        CHK( not '--' in string, f" '--' is not allowed in sandbox name. This name is invalid: {string}")
        CHK( not string.startswith('-') and not string.endswith('-'), f"Sandbox name can not starts or ends with '-'. This name is invalid: {string}")
    @classmethod
    def gen_instance_name_mkdir(cls): # 只在 最外层启动时 并且 确定要创建新实例时 调用
        now = datetime.datetime.now()
        time_str = now.strftime("%m%d-%H%M%S")
        ds = now.microsecond // 100_000

        n = 0
        while True:
            if n>100: raise_exit('Have tried too many times generating instance name')

            random_str = ''.join(random.choices(cls.random_chars, k=3))
            instance_name = f'{si.sandbox_name}--{time_str}-{ds}{random_str}'
            outest_sbxdir = f'{si.PTMP}/{instance_name}'
            CG_SBX = f'{si.CG_TSBXS}/{instance_name}'

            if os.path.lexists(outest_sbxdir) or os.path.lexists(CG_SBX):
                n+=1 ; continue

            try: os.makedirs(outest_sbxdir, exist_ok=False)
            except FileExistsError:
                n+=1 ; continue
            except: raise

            mkdirp(si.CG_TSBXS)

            try: os.makedirs(CG_SBX, exist_ok=False)
            except FileExistsError:
                n+=1 ; continue
            except: raise

            Path(f'{CG_SBX}/cgroup.procs').write_text(str(os.getpid()))

            break
        return instance_name, outest_sbxdir, CG_SBX
    @classmethod
    def is_pattern_instance_name(cls, string):
        return re.match(rf'^{si.sandbox_name}--\d{{4}}-\d{{6}}-\d[{cls.random_chars}]{{3}}$', string)

resv_name_prefix = ['bridge_', 'layer', 'shareshell_', 'mainApp']
resv_words = ['host', 'sbx', 'sbxs', 'tsbx', 'tsbxs', 'tsbxes', 'sandbox', 'sandboxs', 'sandboxes', 'layer', 'layers', 'new', 'py', 'json', 'name', 'dirs', 'log', 'logs', 'socket', 'nc', 'tmpfs', 'tmp', 'temp', 'overlay', 'events', 'lyr_cfg', 'pid', 'userconfig', 'rootfs', 'outest', 'mainLyr', 'semitruCmpannLyr', 'userns_unpri', 'netns_tun', 'bridge', 'shareshell', 'mainApp']
def init_sbxinfo(): # 仅顶层运行，子容器层不运行。返回的数据一路传下各个子层
    # 获得调用py脚本的文件位置信息，一般仅用于顶层得多，子容器内用得少
    scriptfilepath = rslvy(os.path.abspath(__file__))
    scriptdirpath = os.path.dirname(scriptfilepath)  # 获取脚本所在目录
    scriptdirname = os.path.basename(scriptdirpath) # 获取脚本所在目录名
    scriptname = os.path.basename(scriptfilepath)  # 获取脚本文件名（含扩展名）
    scriptnamenoext = os.path.splitext(scriptname)[0]  # 获取脚本文件名（不含扩展名）

    si = d()

    for i in [0,1,2]:
        try: fcntl.fcntl(i, fcntl.F_GETFD)
        except OSError as err:
            if err.errno != errno.EBADF: raise
            else:
                devnull = os.open('/dev/null', os.O_RDWR)
                os.dup2(devnull, i)
                if devnull != i: os.close(devnull)
    fdnull = os.open("/dev/null", os.O_PATH)
    CHK(fdnull>=3, 'fdnull must >=3')
    set_fd_keep_on_exec(fdnull, False)
    si.fdnull = fdnull

    # 从外部(linux host)启动沙箱的原本用户信息
    uid = os.getuid()
    gid = os.getgid()
    username = pwd.getpwuid(uid).pw_name # 获取当前用户名
    groupname = grp.getgrgid(gid).gr_name
    HOME = f'/home/{username}' if uid>0 else '/root'
    hostname = open("/etc/hostname").read().strip()
    outest_pid = os.getpid()
    host_XDG_R_D = getenv("XDG_RUNTIME_DIR")
    sbx_XDG_R_D = f'/run/user/{uid}'
    startscript_on_host = scriptfilepath
    CWD = scriptdirpath
    PTMP = f'/tmp/tsbxs-{uid}'
    hash_bootsbx_py = hash_blake2b(open(scriptfilepath, 'rb').read())

    CHK(uid != 0 and gid != 0, f'Currently our sandbox tool does not support running as root')

    mkdirp(PTMP)      # 创建不同沙箱实例共用的 主临时目录,不清理这个
    os.chmod(PTMP, 0o700)

    si.update( { k: v for k, v in locals().items() if k in
        ['hostname', 'PTMP', 'uid', 'gid', 'username', 'groupname', 'HOME', 'outest_pid',
         'startscript_on_host', 'CWD', 'hash_bootsbx_py', 'host_XDG_R_D', 'sbx_XDG_R_D']
    } )

    uc = userconfig(si) # NOTE

    # 沙箱名。不是子容器层名
    if uc.sandbox_name: NameMng.chk_str_valid_sandbox_name(uc.sandbox_name)
    sandbox_name = uc.sandbox_name or f'{scriptdirname}_{scriptname}' # 沙箱名
    sandbox_name = re.sub(r'[^a-zA-Z0-9_\-]', lambda m: f"_{ord(m.group(0)):x}", sandbox_name)
    CHK( sandbox_name not in resv_words, f"Sandbox name {sandbox_name} conflicts with reserved word {resv_words}")
    CHK( len(sandbox_name) < 500, f'Sandbox name too long: {sandbox_name}')

    apps = uc.apps
    if uc.reuseful: reuseful = uc.reuseful
    if uc.idleKeepSbxTime: idleKeepSbxTime = uc.idleKeepSbxTime

    if (sharedir_prefix := uc.sharedir_prefix):
        CHK( sharedir_prefix.startswith('/tmp/') or sharedir_prefix.startswith('/dev/shm/'), "uc.sharedir_prefix must start with '/tmp/' or '/dev/shm/'")
        sharedir_onhost = f'{sharedir_prefix}{sandbox_name}'
        si.sharedir_onhost = sharedir_onhost
    else:
        sharedir_onhost = None

    sync_clipbd_from_sandbox = True if uc.sync_clipbd_from_sandbox else False


    si.update( { k: v for k, v in locals().items() if k in
        [ 'sandbox_name', 'reuseful', 'idleKeepSbxTime', 'apps', 'sync_clipbd_from_sandbox', ]
    } )


    CG_HOSTUSER = f'/sys/fs/cgroup/user.slice/user-{uid}.slice/user@{uid}.service'
    CG_TSBXS = f'{CG_HOSTUSER}/tsbxs.slice'
    CHK( os.access(CG_HOSTUSER, os.W_OK), f"The directory {CG_HOSTUSER} does not exist or is not writable")

    BND_MAX = int(Path('/proc/sys/kernel/cap_last_cap').read_text())
    pythonbin = sys.executable

    dyncfg = gen_dynamic_cfg(si, uc) # NOTE
    if 'newXId' in dict.keys(dyncfg): newXId = dyncfg.newXId

    si.update( { k: v for k, v in locals().items() if k in
          ['newXId', 'CG_HOSTUSER', 'CG_TSBXS', 'BND_MAX', 'pythonbin', ]
    } )

    layer1_cfg = gen_layer1(si, uc, dyncfg)
    start_lyrs_recursive_jobs(si, layer1_cfg)

    if uc.net_iface == 'tuntap-pasta': si.expected_alive_procs += [ 'netns_tun'] # 'pasta_runner'因为无法获取ns所以不放其中

    bridges = []
    for bItem in (dyncfg.bridges or []):
        def get_real_layername(name_in):
            if name_in.startswith('layer'): return name_in
            else:
                if si.specialLyrs[name_in]: return si.specialLyrs[name_in]
        real_seefrom = get_real_layername(bItem.seefrom)
        real_seeto   = get_real_layername(bItem.seeto)
        if not (real_seefrom and real_seeto):
            log_warn(f'The layer(s) indicated by this bridge item {bItem} not found, ignoring bridge item.')
            continue
        bridge_name = f'bridge_<{real_seefrom.removeprefix('layer')}>_<{real_seeto.removeprefix('layer')}>'
        dcp_bItem = copy.deepcopy(bItem)
        dcp_bItem.update( d(real_seefrom=real_seefrom , real_seeto=real_seeto, bridge_name=bridge_name) )
        bridges.append(dcp_bItem)
        si.expected_alive_procs.append(bridge_name)
    si.bridges = bridges

    OG = d(dyncfg=dyncfg, uc=uc)
    return si, layer1_cfg, OG

def start_lyrs_recursive_jobs(si, layer1_cfg): # 这是给最外层启动时把layer1_cfg作为cfg传入的
    recursive_lyrs_jobs(si, layer1_cfg, None, [])
    recr_rm_empty_lyr(si, layer1_cfg)
    recursive_valid_lyrs(si, layer1_cfg)


def recursive_lyrs_jobs(si, cfg, parent_cfg, used_layer_names): # cfg：要处理的层， parent_cfg : 其父层
    # 计算本层深度
    cfg.depth = parent_cfg.depth + 1 if parent_cfg is not None else 1

    CHK( cfg.layer_name, "Some layer has no layer_name")
    CHK( re.match(r'^[a-zA-Z0-9_-]+$', cfg.layer_name), f"layer_name can only contain letters, numbers, '-', '_' . This name is invalid: {cfg.layer_name}" )
    CHK( cfg.layer_name not in resv_words, f"Layer name {cfg.layer_name} conflicts with reserved word {resv_words}")
    CHK( cfg.layer_name.startswith('layer'), f"Layer name {cfg.layer_name} does not start with 'layer'")
    CHK( cfg.layer_name not in used_layer_names, f"Layer name '{cfg.layer_name}' is duplicated")
    used_layer_names.append(cfg.layer_name)

    CHK( len(cfg.layer_name.encode()) <= 15 , f"Layer name {cfg.layer_name} exceeds 15 bytes")

    # 配置中的数组类型去除None成员
    if cfg.fs:
        cfg.fs = [fsItem for fsItem in cfg.fs if fsItem is not None]
    if cfg.sublayers :
        cfg.sublayers = [sublyr for sublyr in cfg.sublayers if sublyr is not None]
    if cfg.subprocs :
        cfg.subprocs = [cmd for cmd in cfg.subprocs if cmd is not None]
        CHK( cfg.unshare_pid and cfg.unshare_mnt, f"Layer {cfg.layer_name} has subprocs but  unshare_pid + unshare_mnt  not enabled")
        for subpItem in cfg.subprocs:
            if subpItem.start_after:
                subpItem.start_after = [item for item in subpItem.start_after if item is not None]
    if cfg.subprocs and cfg.sublayers:
        raise_exit(f"Layer {cfg.layer_name} has both subprocs and sublayers. Not valid config")
    if cfg.envs_unset:
        cfg.envs_unset = [item for item in cfg.envs_unset if item is not None]
    if cfg.envset_grps:
        cfg.envset_grps = [item for item in cfg.envset_grps if item is not None]
    if cfg.start_after:
        cfg.start_after = [item for item in cfg.start_after if item is not None]
    if cfg.uid_map_as_root :
        CHK( cfg.unshare_user, f"Layer {cfg.layer_name} has uid_map_as_* but unshare_user not enabled")

    if cfg.unshare_pid and not cfg.unshare_mnt:
        raise_exit(f"Layer {cfg.layer_name} has unshare_pid enabled, but unshare_mnt not enabled")
    if (cfg.newrootfs or cfg.fs) and not cfg.unshare_mnt:
        raise_exit(f"Layer {cfg.layer_name} sets newrootfs or fs, but unshare_mnt not enabled")
    if bool(cfg.fs) != bool(cfg.newrootfs):
        raise_exit(f"Layer {cfg.layer_name}: fs and newrootfs must both be present or both absent")
    if cfg.is_mainlyr :
        CHK( cfg.unshare_pid , f'Main layer {cfg.layer_name} requires unshare_pid=True')
    if cfg.is_semitruCmpannLyr :
        CHK( cfg.unshare_pid , f'Semi-trusted companion process layer {cfg.layer_name} requires unshare_pid=True')


    # 检查fs条目
    for fsItem in (cfg.fs or []):
        if fsItem.dest: fsItem.dest = napath(fsItem.dest)
        if fsItem.src: fsItem.src = napath(fsItem.src)
        if fsItem.destbase: fsItem.destbase = napath(fsItem.destbase)

    if len(cfg.sublayers or []) > 0 and cfg.newrootfs:
        if not any( opItem.many_op == 'sbxdir-in-newrootfs' for opItem in cfg.fs):
            raise_exit(f"Layer {cfg.layer_name} sets newrootfs and wants to create sublayers, but its fs has no entry with many_op = 'sbxdir-in-newrootfs' (required in this case)")

    # 对第1层检查
    if cfg.depth == 1:
        CHK( cfg.uid_map_as_root,"First layer should enable uid_map_as_root")
        CHK( cfg.unshare_pid, "First layer should enable unshare_pid")
        CHK( len(cfg.sublayers) == 1, "First layer's sublayers array should but does not contain exactly 1 element")
        CHK( not cfg.newrootfs, "First layer should not enable newrootfs")

    if cfg.depth > 1:
        CHK(not cfg.unshare_user, f"Layer {cfg.layer_name} has unshare_user enabled, but layers after the first layer do not need this. We have userns_unpri")

    # 对第2层检查
    if cfg.depth == 2:
        CHK( cfg.unshare_mnt, "Second layer should enable unshare_mnt")
        CHK( cfg.newrootfs, "Second layer should enable newrootfs")
        CHK( cfg.fs, "Second layer should have fs")
        if not any( opItem.many_op == 'dup-rootfs' for opItem in cfg.fs):
            raise_exit("Second layer's fs has no entry with many_op='dup-rootfs'")
        if not any( opItem.many_op == 'mask-privacy' for opItem in cfg.fs):
            raise_exit("Second layer's fs has no entry with many_op='mask-privacy'")

    if cfg.layer_name == 'layer3': # 对第3层检查
        if cfg.fs and any( opItem.many_op == 'dup-rootfs' for opItem in cfg.fs) :
            raise_exit(f"Layer {cfg.layer_name} should not use many_op='dup-rootfs' in fs, because its parent layer is the last layer allowed to see host files")
        if not (cfg.unshare_mnt and cfg.unshare_cgroup and cfg.unshare_ipc and cfg.unshare_time and cfg.unshare_uts and cfg.newrootfs and cfg.fs) :
            raise_exit(f"Layer {cfg.layer_name} did not enable all of [unshare_mnt, unshare_cgroup, unshare_ipc, unshare_time, unshare_uts, newrootfs, fs] (all required)")
        if not any( opItem.many_op == 'container-rootfs' for opItem in cfg.fs):
            raise_exit(f"Layer {cfg.layer_name}'s fs has no entry with many_op='container-rootfs'")

    if cfg.layer_name in ['layer2c', 'layer4c', 'layer4']:
        CHK( cfg.unshare_pid, f"{cfg.layer_name} did not enable unshare_pid=True (required)")

    if parent_cfg is None:
        pa_tree = []
        pa_pidns_depth = 0
        pa_pidns_tree = []
    else:
        pa_tree = parent_cfg.tree
        pa_pidns_depth = parent_cfg.pidns_depth
        pa_pidns_tree  = parent_cfg.pidns_tree

    cfg.tree = pa_tree + [cfg.layer_name]
    cfg.pidns_depth = pa_pidns_depth + (0  if not cfg.unshare_pid else 1)
    cfg.pidns_tree  = pa_pidns_tree  + ([] if not cfg.unshare_pid else [cfg.layer_name])


    if cfg.user_shell or cfg.dev_shell:
        if cfg.sublayers:
            log_warn(f"{cfg.layer_name} is set to start dev_shell or user_shell, its sublayers will be ignored")
            cfg.sublayers = []
        # if cfg.subprocs and [x for x in cfg.subprocs if x.subp_name == 'mainApp']: # 现在mainApp是由最外层发来的了

    for sublyr_cfg in (cfg.sublayers or []):
        recursive_lyrs_jobs(si, sublyr_cfg, cfg, used_layer_names)


def recursive_valid_lyrs(si, layer1_cfg):
    used_proc_names = []
    si.all_layers = []
    si.specialLyrs = d()
    def _recr(cfg):
        nonlocal used_proc_names
        CHK( cfg.layer_name not in used_proc_names, f"Name {cfg.layer_name} is duplicated")
        si.all_layers.append(cfg.layer_name)
        if cfg.unshare_pid:
            used_proc_names.append(cfg.layer_name)
        if cfg.is_mainlyr:
            CHK(not si.specialLyrs.mainLyr, 'Duplicate mainLyr found')
            si.specialLyrs.mainLyr = cfg.layer_name
        if cfg.is_semitruCmpannLyr:
            CHK(not si.specialLyrs.semitruCmpannLyr, 'Duplicate semitruCmpannLyr found')
            si.specialLyrs.semitruCmpannLyr = cfg.layer_name
        for subpItem in (cfg.subprocs or [] ):
            CHK( subpItem.subp_name, f"Subprocess has no subp_name set : {subpItem}")
            CHK( re.match(r'^[a-zA-Z0-9_-]+$', subpItem.subp_name), f"subp_name can only contain letters, numbers, '-', '_' . This name is invalid: {subpItem.subp_name}" )
            CHK( len(subpItem.subp_name)<=30, f"subp_name too long, exceeds 30 characters: {subpItem}")
            CHK( subpItem.subp_name not in used_proc_names, f"Name {subpItem.subp_name} is duplicated")
            for x in resv_name_prefix:
                CHK( not subpItem.subp_name.startswith(x), f"Subprocess name {subpItem.subp_name} starting with '{x}' is invalid {subpItem}")
            used_proc_names.append(subpItem.subp_name)

        if cfg.user_shell: used_proc_names.append('user_shell')
        if cfg.dev_shell: used_proc_names.append('dev_shell')
        for sublyr_cfg in (cfg.sublayers or [] ):
            _recr(sublyr_cfg)
    _recr(layer1_cfg)
    wdg_target_procs = [x for x in used_proc_names if x != 'mainApp'] # 不看主app, 只看它所属层
    si.expected_alive_procs = wdg_target_procs + ['userns_unpri']
    si.expected_alive_layers = list(set(si.expected_alive_procs) & set(si.all_layers))
    CHK(si.specialLyrs.mainLyr, 'mainLyr not found')

def recr_rm_empty_lyr(si, cfg):
    def _recr(si, cfg):
        # print(cfg.layer_name)
        have_rmed = False

        cnt_cmds_0 = len(cfg.subprocs or [] )
        cnt_sl_0 = len(cfg.sublayers or [] )
        cnt_task_0 = len(cfg.daemon_tasks or [])
        if cfg.subprocs : cfg.subprocs = [cmd for cmd in cfg.subprocs if cmd is not None]
        if cfg.sublayers : cfg.sublayers = [sublyr for sublyr in cfg.sublayers if sublyr and not sublyr.disabled]
        if cfg.daemon_tasks : cfg.daemon_tasks = [task for task in cfg.daemon_tasks if task]
        cnt_cmds_1 = len(cfg.subprocs or [] )
        cnt_sl_1 = len(cfg.sublayers or [] )
        cnt_task_1 = len(cfg.daemon_tasks or [])

        if cnt_cmds_0 != cnt_cmds_1 or cnt_sl_0 != cnt_sl_1 or cnt_task_0 != cnt_task_1:
            have_rmed = True
        for sublyr_cfg in (cfg.sublayers or [] ):
            if _recr(si, sublyr_cfg):
                have_rmed = True
        if not (cfg.sublayers or cfg.subprocs or cfg.daemon_tasks or cfg.user_shell or cfg.dev_shell or cfg.is_mainlyr):
            # print('setting' , cfg.layer_name, 'to disable')
            cfg.disabled = True
            have_rmed = True
        # print(have_rmed)
        return have_rmed
    while _recr(si, cfg): pass


def make_mnt_fill_sbxdir(si, lyrcfg, call_at_begin=None, call_at_buildfs=None, OG=None): # 创建本层的sbxdir, 可能是刚启动时新创建，也可能是准备变根前为变根后的环境内创建（可能复制启动时已有的）
    # sbxdir_path/ :
        # dirmaker.xxx.name
        # dirmaker.name -> dirmaker.xxx.name
        # sbxinfo.json
        # bootsbx.py
        # sbx.xxx.name
        # sbx.name -> sbx.xxx.name
        # events.layers.log
        # lyr_cfg.xxx.json (多) 包括本层和所有递归子层
        # new.xxx.rootfs (多)所有有 newrootfs 的本层和递归子层
        # temp/  挂载为rw tmpfs
        # apps/ 挂为 tmpfs rw
        # overlays.xxx.dirs/ 挂载为tmpfs 可能rw (暂未实现）
    if call_at_begin: # 刚启动脚本
        si.instance_name , si.outest_sbxdir, si.CG_SBX = NameMng.gen_instance_name_mkdir()
        target_sbxdir_path = napath(si.outest_sbxdir)
        old_sbxdir_path = None
    elif call_at_buildfs: # 为本层接下来的新文件系统准备的 （可能 变根=新旧路径不同  ，也可能 不变根=新旧路径同）
        target_sbxdir_path = napath(f'{lyrcfg.newrootfs_path}/{lyrcfg.sbxdir_path1}')
        old_sbxdir_path = napath(lyrcfg.sbxdir_path0)

    if target_sbxdir_path == old_sbxdir_path:
        return
        # 能往下执行，说明是要从空白创建
    # else:
    #     creating_new_sbxdir=True

    def make_file_get_fd(filename, open_flag, filemode):
        fd = os.open(f'{target_sbxdir_path}/{filename}', open_flag, filemode)
        set_fd_keep_on_exec(fd, False)
        return fd
    def create_socket_file_fd(socket_file_name):
        skt = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        skt.setblocking(False)
        skt.bind(f'{target_sbxdir_path}/{socket_file_name}')
        fd = skt.detach() ; set_fd_keep_on_exec(fd, False)
        return fd
    def create_socketpair_fds():
        skt_chd, skt_pa = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        fd_chd = skt_chd.detach() ; set_fd_keep_on_exec(fd_chd, False)
        fd_pa  = skt_pa.detach() ; set_fd_keep_on_exec(fd_pa, False) # 为了不让fd号码乱，pa也保留
        return d(pa=fd_pa, chd=fd_chd)

    # sbxdir 本身目录创建
    mkdirp(target_sbxdir_path)
    new_tmpfs_for_sbxdir = True if call_at_buildfs else False
    if new_tmpfs_for_sbxdir:
        mount('tmpfs', target_sbxdir_path, 'tmpfs', mntflag_newsbxdir, 'mode=700')

    # dirmaker.layerX.name
    if not os.path.lexists(f'{target_sbxdir_path}/dirmaker.layer.name'):
        with open(f'{target_sbxdir_path}/dirmaker.layer.{lyrcfg.layer_name}.name', 'w') as f:
            f.write(lyrcfg.layer_name)
            os.chmod(f.name, 0o444)
        symlink(f'dirmaker.layer.{lyrcfg.layer_name}.name', f'{target_sbxdir_path}/dirmaker.layer.name')


    if call_at_begin:
        # sbx.xxxx.pid
        with open(f'{si.outest_sbxdir}/sbx.{si.outest_pid}.pid', 'w') as f:
            f.write(str(si.outest_pid))
            os.chmod(f.name, 0o444)

        symlink(f'sbx.{si.outest_pid}.pid', f'{si.outest_sbxdir}/sbx.pid')
        symlink(f'/proc/{si.outest_pid}/status', f'{si.outest_sbxdir}/sbx.pid.status')

        # userconfig.json , dyncfg.json
        with open(f'{si.outest_sbxdir}/userconfig.json', 'w') as f:
            f.write(json.dumps(OG.uc, indent=2, ensure_ascii=False))
            os.chmod(f.name, 0o444)
        with open(f'{si.outest_sbxdir}/dyncfg.json', 'w') as f:
            f.write(json.dumps(OG.dyncfg, indent=2, ensure_ascii=False))
            os.chmod(f.name, 0o444)


        # fd (procs, subp 文件)
        si.file_fds = D()
        si.file_fds.update( d(
            # 沙箱内只fd写，最外层用路径来读
            layerslog_a = make_file_get_fd('events.layers.log', os.O_WRONLY|os.O_CREAT|os.O_APPEND, 0o644),

            # RDONLY是因为沙箱内只fd读，仅最外层用路径写
            procs_alive = make_file_get_fd('procs.alive.json', os.O_RDONLY|os.O_CREAT, 0o644),
            procs_seen = make_file_get_fd('procs.seen.json', os.O_RDONLY|os.O_CREAT, 0o644),
            procs_heared = make_file_get_fd('procs.heared.json', os.O_RDONLY|os.O_CREAT, 0o644),
            procs_wdgsee = make_file_get_fd('procs.wdgsee.json', os.O_RDONLY|os.O_CREAT, 0o644),
        ) )

        Path(f'{si.outest_sbxdir}/procs.alive.json').write_text("[]")
        Path(f'{si.outest_sbxdir}/procs.seen.json').write_text("{}")
        Path(f'{si.outest_sbxdir}/procs.heared.json').write_text("{}")
        Path(f'{si.outest_sbxdir}/procs.wdgsee.json').write_text("{}")

        si.subp_log_fds = D()
        for pn in si.expected_alive_procs:
            if not (pn in ['user_shell','dev_shell','mainApp'] or pn.startswith('layer') ):
                si.subp_log_fds[pn] = make_file_get_fd(f'subp.{pn}.log', os.O_WRONLY|os.O_CREAT|os.O_APPEND, 0o644)


        si.oSkt_fds = D()
        for lyr in si.expected_alive_layers:
            si.oSkt_fds [lyr] = create_socketpair_fds()



    # 主机写的剪贴板socket
    if si.newXId:
        if call_at_begin:
            si.fd_clipbdWriterFromHostLsn = create_socket_file_fd('clipbdWriterFromHost.socket')


    # empty
    Path(f'{target_sbxdir_path}/empty').touch()
    os.chmod(f'{target_sbxdir_path}/empty', 0)

    # apps目录
    mkdirp(f'{target_sbxdir_path}/apps')
    if old_sbxdir_path :
        if not Path(f'{old_sbxdir_path}/apps').is_mount():
            # 创建新的空的 tmpfs 给apps
            mount('tmpfs', f'{target_sbxdir_path}/apps', 'tmpfs', mntflag_apps, 'mode=755')
        else:
            # 把上一层的apps bind过来. 不是最后一层就应该要保留rw
            mount(f'{old_sbxdir_path}/apps', f'{target_sbxdir_path}/apps', None, MS.BIND|mntflag_apps, None)

    # temp目录
    mkdirp(f'{target_sbxdir_path}/temp')
    if call_at_buildfs:
        mount('tmpfs', f'{target_sbxdir_path}/temp', 'tmpfs', mntflag_sbxtemp, 'mode=755')


    # sbxinfo.json
    if call_at_begin:
        with open(f'{target_sbxdir_path}/sbxinfo.json', 'w') as f:
            f.write(json.dumps(si, indent=2, ensure_ascii=False))
            os.chmod(f.name, 0o444)
        with open(f'{target_sbxdir_path}/sbx.{si.sandbox_name}.name', 'w') as f:
            f.write(si.sandbox_name)
            os.chmod(f.name, 0o444)
        symlink(f'sbx.{si.sandbox_name}.name', f'{target_sbxdir_path}/sbx.name')


    # 递归 创建和写 (不包括本层)所有子层（递归） 需要的 路径和文件
    def create_lyrs_files_recr(lyr_cfg):
        if call_at_begin:
            with open(f'{target_sbxdir_path}/lyr_cfg.{lyr_cfg.layer_name}.json', 'w') as f:
                f.write(json.dumps(lyr_cfg, indent=2, ensure_ascii=False))
                os.chmod(f.name, 0o444)
        if lyr_cfg.newrootfs:
            mkdirp(f'{target_sbxdir_path}/new.{lyr_cfg.layer_name}.rootfs')
        for sublyr_cfg in (lyr_cfg.sublayers or [] ) :
            create_lyrs_files_recr(sublyr_cfg)

    # 判断是最外层 才把 本层配置（即第1层） 写入,否则只写子层
    arr_recr_create_conf = [lyrcfg] if call_at_begin else (lyrcfg.sublayers or [] )
    for sublyr_cfg in arr_recr_create_conf :
        create_lyrs_files_recr(sublyr_cfg)

    # 重新挂载为ro
    if new_tmpfs_for_sbxdir:
        os.chmod(target_sbxdir_path, 0o555)
        rmt_ro(target_sbxdir_path, mntflag_newsbxdir)


si = None # sbxinfo , sandbox info
tlcfg = None # thislyr_cfg , this layer config
OG = None # outest global dynamic info
LG = None # layer global dynamic info
def main(lyrcfg_in):
    global si, tlcfg, OG

    if not isinstance(lyrcfg_in, dict): is_outest = True # 是顶层
    else: is_outest = False # 是子层

    if is_outest: # 是顶层
        arg_parser = argparse.ArgumentParser( add_help=True, usage="%(prog)s [options] [<user_cli_argv> ...]",
            description="Tree Sandbox script. Do sandbox operations based on userconfig() function and CLI args. Can start new sandbox instance or reuse a running same-name instance."
        )
        arg_parser.add_argument("--nocleanup", action='store_true',
                                help="Do not delete the temporary sandbox info dir after sandbox instance quit")
        arg_parser.add_argument("--reusefg", action='store_true',
                                help="If reusing a running instance, use remote shell, letting new-started app in foreground of current terminal. Otherwise, send the new-app command to running instance then we return. (Only effective if the sandbox has reuseful enabled in config). If starting a new sandbox instance, this option is ignored.")
        # arg_parser.add_argument("--enter", action='store_true',
                                # help="自动找到一个正在运行的同名沙箱实例，获得其shell。若无正在运行的实例，报错退出")
        # arg_parser.add_argument("--enter-instance", metavar="<chosen_instance_name>",
                                # help="找到指定的正在运行的具体实例，获得其shell。可以是非同名沙箱，但沙箱版本需要一致")
        arg_parser.add_argument("--app", metavar="<chosen_appname>", default="default",
                                help="Using a configured appname, specify the command to start in sandbox. Not specifying or using '--app default' has the same effect.")
        arg_parser.add_argument("--workdir", metavar="<path>", default=None,
                                help="Before launch app, cd to this path")
        arg_parser.add_argument("--workdir-try", metavar="<path>", default=None,
                                help="Similar to '--workdir', but will fallback to default workdir path if cd fails")


        (sbx_args, # 上面列出的参数
         user_cli_argv # 未知参数，即之后的参数，传给沙箱内的app
        ) = arg_parser.parse_known_args()

        nocleanup = sbx_args.nocleanup
        reusefg = sbx_args.reusefg
        # enter = sbx_args.enter
        # chosen_instance_name = sbx_args.enter_instance
        chosen_appname = sbx_args.app
        chosen_workdir     = sbx_args.workdir
        chosen_workdir_try = sbx_args.workdir_try

    if is_outest:
        si, layer1_cfg, OG = init_sbxinfo() # 只有从最外层启动才运行这个函数
        tlcfg = layer1_cfg

        # tlcfg.sbxdir_path0 = # 到后面决定了instance_name才设置这个

        if nocleanup: si.nocleanup = True
    else: # 是子层
        tlcfg = lyrcfg_in
        tlcfg.sbxdir_path0 = '/sbxdir' if is_dir('/sbxdir') else si.outest_sbxdir
        # si =  # 不需要再加载si, 因为是fork来的

    if is_outest:
        if reusefg: CHK(si.reuseful, '--reusefg cannot be used because reuseful is not enabled in the sandbox configuration')
        log(f"PID: {si.outest_pid}  Sandbox name: {si.sandbox_name}   Run by: {si.username} {si.groupname}")
        if not chosen_appname or chosen_appname=='default': chosen_appItem = si.apps[0]
        else: chosen_appItem = next((app for app in si.apps if app.get('appname') == chosen_appname), None)
        CHK( chosen_appItem and chosen_appItem.cmdvec, 'Selected app not found, or selected app does not have a valid cmdvec')
        OG.chosen_appItem = chosen_appItem
        OG.chosen_workdir     = chosen_workdir
        OG.chosen_workdir_try = chosen_workdir_try
        OG.user_cli_argv = user_cli_argv
        OG.mainApp_cmdvec = chosen_appItem.cmdvec + user_cli_argv
        log(f'App command to run in sandbox: {OG.mainApp_cmdvec}')

        # 判断应该 新实例 还是 发送app命令到 正在运行的实例
        if si.reuseful:
            question_reuse = maybe_sendto_running_instance(reusefg)
            CHK( question_reuse=='not_reusing', 'Here either the result should be "not_reusing", or the judgment function should have ended the process')
        log('---------------------')
        if si.newXId:
            CHK( is_XId_available(si.newXId), f"The display number {si.newXId=} to be used is occupied")
        log(f"Procs to be polled by watchdog: {si.expected_alive_procs}")
        if si.newXId: log(f'X11/Wayland display number used in sandbox: {si.newXId}')

        reg_cleanup_func(cleanup_outest) # 顶层父进程注册清理函数

        make_mnt_fill_sbxdir(si, layer1_cfg, call_at_begin=True, OG=OG)
        log(f"Create new instance of sandbox. Info dir: {si.outest_sbxdir}")
        log(f"cgroup: {si.CG_SBX}")
        tlcfg.sbxdir_path0 = si.outest_sbxdir

    set_loghead (f'{tlcfg.layer_name}: ' if not is_outest else 'outest: ')
    set_ps1('notready')

    # 创建主机与沙箱之间的临时共享目录
    if is_outest and si.sharedir_onhost:
        log(f'Create temporary shared dir between host and sandbox at {si.sharedir_onhost}')
        mkdirp(si.sharedir_onhost)

    # ----------------------------
    # 预先算好变根后的 sbxdir_path1
    if not tlcfg.newrootfs:
        tlcfg.sbxdir_path1 = tlcfg.sbxdir_path0
    else:
        tlcfg.sbxdir_path1 = next((opItem.dest for opItem in tlcfg.fs if opItem.many_op == 'sbxdir-in-newrootfs'), None)
    # sbxdir_path 说明
    # 本层变根 前 后 的 sbxdir_path ( sbxdir_path0 sbxdir_path1)
    # 变根前 0 = 刚启动本层启动脚本时
    # 变根后 1 = 即将运行下层的启动脚本时
    # 变根不一定发生，由本层配置决定，但也把两个sbxdir_path以 前 后 来称呼
    # ----------------------------

    # 环境变量
    for env_to_unset in (tlcfg.envs_unset or [] ):
        os.environ.pop(env_to_unset, None)
    for envg in (tlcfg.envset_grps or [] ) :
        if len(dict.keys(envg))>0:
            log('Update env variables' , envg)
            os.environ.update(envg)

    wait_for_startAfters(tlcfg.start_after)

    # TODO 用个数组储存 pid time 是fork前做，其他main2做
    unshr_cfg = lyrcfg_to_unshrcfg(tlcfg)
    unshr_cfg.mnt=False # unshare排除mnt（后面再做）
    if tlcfg.depth != 1: unshr_cfg.user=False # 非首层则unshare排除user（后面再做）
    os.unshare(unshrflg(unshr_cfg))

    set_ps1('afterUnshare')

    pid, skp_lyfk = fork(create_socketpair=True, loghead=f'{tlcfg.layer_name} F: ', proc_dispname=tlcfg.layer_name)
    if pid == 0: # 子进程
        if tlcfg.depth == 1:
            set_pdeathsig(signal.SIGTERM) # 最外层的原进程（fork前的进程）退出的话，layer1的fork出来的子进程应该主动退出
        return main2(skp_lyfk)
    else: # 父进程

        # if tlcfg.uid_map_as_user and tlcfg.depth > 1: # 已删除 map_as_user 的功能
        skp_lyfk.close()

        if is_outest:
            OG.layer1_pid = pid
            daemon_outest() # NOTE skp_lyfk 关了后，才进入daemon
        else:
            sys.exit()



def main2(skp_lyfk):
    # 变内部uid=0 (root)
    if tlcfg.uid_map_as_root:
        Path('/proc/self/setgroups').write_text('deny\n')
        Path('/proc/self/uid_map').write_text(f'0 {si.uid} 1\n')
        Path('/proc/self/gid_map').write_text(f'0 {si.gid} 1\n')
        log(f"Internal current uid={os.getuid()} gid={os.getgid()}")

    if tlcfg.unshare_mnt: # 现在才做，保证不影响父进程所看到的 /proc
        os.unshare(unshrflg(d(mnt=True)))


    # 本层文件系统、挂载proc （维持 rw）， 变根
    build_fs(tlcfg)

    # Unshare User (非首层)
    if tlcfg.unshare_user and tlcfg.depth > 1 : # 第1层的若要做在之前就做了
        os.unshare(unshrflg(d(user=True)))

    if tlcfg.create_userns_unpri:
        OG.userns_unpri = create_userns_unpri()
    if tlcfg.pasta_args:
        OG.netns_tun = create_netns_tun( tlcfg.pasta_args )
        os.setns(OG.netns_tun.pidfd, unshrflg(d(net=1)))
    if tlcfg.nftables_rule:
        with tempfile.NamedTemporaryFile( dir=f'{tlcfg.sbxdir_path1}/temp', mode='w', delete=True) as f:
            f.write(tlcfg.nftables_rule)
            f.flush()
            PATH_w_sbin = '/sbin:/usr/sbin:/usr/local/sbin:' +  getenv('PATH', '').strip(':')
            run_a_cmd(['env', f'PATH={PATH_w_sbin}',  'nft', '-f', f.name ])

    # 变内部uid=1000 (user)
    # if tlcfg.uid_map_as_user: # 已删除 map_as_user 功能

    # 关闭临时socket
    skp_lyfk.close()# NOTE 注意， 在创建任何 subp 之前 ， skp_lyfk(临时socket)必须已关闭

    # 非unshare_pid 层 则要等待fork前父进程退出
    if not tlcfg.unshare_pid:
        while os.getppid() not in [0, 1] : time.sleep(0.03)


    #--- 创建 subp -----------------------------------
    # NOTE 注意， 在创建任何 subp 之前 ， skp_lyfk(临时socket)必须已关闭

    inprepare_children = []

    # 以subp启动子层
    for sublyr_cfg in (tlcfg.sublayers or []):
        pid, skp_spfk = layer_run_subp( subp_name=sublyr_cfg.layer_name )
        if pid == 0:
            return sublyr_cfg # 让main2()返回，准备开始下一层
        inprepare_children.append((pid, skp_spfk)) # 原进程才需要pid和skp_spfk

    # 清理函数、信号处理注册 (要在sublayer之后)
    if tlcfg.unshare_pid:
        CHK( os.getpid() == 1, f"{tlcfg.layer_name} detected its own PID is not 1 (should be 1)")
        reg_cleanup_func(cleanup_pidnsleader)
        register_sig_handlers(pidnsleader=True)

    set_ps1('ready')

    # 以subp启动user_shell / dev_shell
    if tlcfg.user_shell or tlcfg.dev_shell:
        if tlcfg.user_shell: set_3ge_fds_cloexec() # 沙箱启动时设置过，保险再来一次
        pid, skp_spfk = layer_run_subp(cmdvec=['/bin/bash'] ,
                        **( d(subp_name='user_shell') if tlcfg.user_shell else {}),
                        **( d(subp_name='dev_shell')  if tlcfg.dev_shell  else {}),
        )
        inprepare_children.append((pid, skp_spfk))

    # 以subp启动普通辅助app
    set_3ge_fds_cloexec() # 沙箱启动时设置过，保险再来一次

    for subpItem in (tlcfg.subprocs or [] ) :
        pid, skp_spfk = layer_run_subp (**subpItem)
        inprepare_children.append((pid, skp_spfk))

    #-------------------------------------------

    # 向最外层发送“本层已boot”，
    wlog('layer_booted', me_proc_info=True,
         ready_proc_name=tlcfg.layer_name,
         pidns_depth=tlcfg.pidns_depth, pidns_tree=tlcfg.pidns_tree,
         **(d(is_mainlyr=True) if tlcfg.is_mainlyr else {}),
         **(d(is_semitruCmpannLyr=True) if tlcfg.is_semitruCmpannLyr else {}),
    )

    if not tlcfg.unshare_pid:
        fds_to_keep = [skp._skt_pa.fileno() for _,skp in inprepare_children]
        close_3ge_fds(keep_fds=fds_to_keep)

    # 放行那些等待住的subp (为了等 重要fd 关闭. pidns层则不怕subp访问/proc/1/fd 因为无法访问 )
    for pid, skp_spfk in inprepare_children:
        skp_spfk.pa_send(BS.YouChdGo)
    for pid, skp_spfk in inprepare_children:
        skp_spfk.pa_send(BS.YouChdGo)
        skp_spfk.close()

    # TODO 让最外层把每一层的pidfd和各类ns保活， 再继续
    if tlcfg.unshare_pid:
        daemon_pidnsleader()
    else: # 如果不是 unshare_pid 的 ,这里将结束退出
        sys.exit()


def layer_run_subp(cmdvec=None, subp_name=None, start_after=None,
                   keep_caps=False, # True 全部 | False 全丢 | 字符串 部分
                   stdin=None, stdout=None, stderr=None,
                   workdir=None, workdir_try=None,
                   no_wait=False,
                   ): # TODO pty或setsid

    mainApp=None; subLayer=None; user_shell=None; dev_shell=None;

    if subp_name.startswith('mainApp'):mainApp=True
    if subp_name.startswith('layer'): subLayer = subp_name
    if subp_name == 'user_shell':     user_shell=True
    if subp_name == 'dev_shell':      dev_shell=True

    if dev_shell:
        keep_caps=True

    if not (workdir or workdir_try):
        if user_shell or dev_shell: workdir = tlcfg.sbxdir_path1
        else: workdir = si.HOME

    if subLayer:
        keep_caps=True

    pid, skp_spfk = fork(create_socketpair=True, loghead=f"{loghead}subp {subp_name}", proc_dispname='sub',
        **(
            d(  close_fds=True,
                close_keep_fds=[
                    OG.userns_unpri.usernsfd,
                    si.file_fds.layerslog_a,
                    *( [si.subp_log_fds[subp_name]] if subp_name in dict.keys(si.subp_log_fds) else [] ),
                ]
        ) if not subLayer and not keep_caps else {} )
    )
    if pid == 0: # 子进程
        skp_spfk.chd_send(BS.IChdBorn)
        skp_spfk.chd_recv(1, 5, BS.YouChdGo)
        skp_spfk.chd_recv(1, 2, BS.YouChdGo)
        skp_spfk.chd_recv(1, 2, b'') # 仅所有持有对端（原进程）的fd的进程都关闭了其fd之后，才会收到 b'' 。若fork时，有漏关的，则不行
        skp_spfk.close()

        wait_for_startAfters(start_after) # NOTE 必须在wlog之前等待

        # NOTE 必须在等待那些等待条件满足之后才发wlog
        wlog('subp_start', me_proc_info=True,
                **( d(cmdvec=cmdvec) if cmdvec else {} ),
                **( d(
                    ready_proc_name=subp_name,
                    pidns_depth=tlcfg.pidns_depth,
                    pidns_tree=tlcfg.pidns_tree,
                    ) if not subLayer else {}
                ),
        )

        if subLayer:    startTip = f'Starting sublayer {subLayer}'
        elif dev_shell: startTip = 'Starting dev_shell'
        elif user_shell:startTip = 'Starting user_shell'
        elif keep_caps: startTip = f'Starting subprocess (with caps) {subp_name}'
        else:           startTip = f'Starting subprocess {subp_name}'
        if cmdvec: log(f'{startTip} : ', cmdvec)

        if workdir_try:
            try: os.chdir(workdir_try)
            except:
                log_warn(f"Could not cd to '{workdir_try}'. Would use fallback workdir if needed")
                if workdir: os.chdir(workdir)
        elif workdir: os.chdir(workdir)

        # === 重定向 stdin/out/err  # NOTE 下面可能无法再 log 或 print
        devnull = os.open('/dev/null', os.O_RDWR)
        if subp_name in dict.keys(si.subp_log_fds):
            os.dup2(devnull, 0) if not stdin else None
            os.dup2(si.subp_log_fds[subp_name], 1) if not stdout else None
            os.dup2(si.subp_log_fds[subp_name], 2) if not stderr else None
        os.dup2(devnull, 0) if stdin  is False else None
        os.dup2(devnull, 1) if stdout is False else None
        os.dup2(devnull, 2) if stderr is False else None
        os.close(devnull)
        # NOTE 无法再 log 或 print NOTE

        set_3ge_fds_cloexec() if not dev_shell else set_3ge_fds_cloexec(action='keepall')

        if not subLayer:
            if not keep_caps:
                close_3ge_fds(keep_fds=[OG.userns_unpri.usernsfd]) # 已经给它们cloexec=True， 这些再关闭一次更保险
                os.setns(OG.userns_unpri.usernsfd, unshrflg(d(user=1)))
                drop_caps()

            execvp(cmdvec[0], cmdvec)
            errmsg = f"exec() starting new program [ {cmdvec[0]} ] failed"
            # wlog('error', errmsg=errmsg) # fd 已关闭，无法wlog
            raise_exit(errmsg, no_cleanup=True)
        else: # 是subLayer
            return 0, None
    else: # 原进程
        skp_spfk.pa_recv(1, 2, BS.IChdBorn)
        if no_wait:
            for _ in range(2): skp_spfk.pa_send(BS.YouChdGo);
            skp_spfk.close() ; skp_spfk = None
        return pid, skp_spfk

    # os.execv('/bin/bash', ['/bin/bash', '--norc'])
    # os.exec*成功后不回来，替换了进程
        # l/v： 可变参 或 数组 来指定参数
        # p : 指定path
        # e : 指定环境变量，不继承父的环境。必须完整路径
    # NOTE 不要调用os.exec*， 用自己的安全的execvp()

def execvp(*args, **kwargs):
    CHK(not os.path.lexists('/boot') and not os.path.lexists('/srv'), 'Before exec, found /boot or /srv. Filesystem might not be protected')
    CHK(is_dir_inaccessible('/zrootfs'), 'Before exec, found /zrootfs accessible. Filesystem not protected' )
    os.execvp(*args, **kwargs)

def is_dir_inaccessible(path):
    return not (os.access(path, os.R_OK) or os.access(path, os.W_OK) or os.access(path, os.X_OK))

def create_netns_tun( pasta_custom_args=[] ):
    os.mkfifo(f'/{tlcfg.sbxdir_path1}/temp/netns_proc_info.fifo')
    pid, skp = fork(create_socketpair=True, loghead=f'{loghead} netns', proc_dispname='pasta runner', cut_stdin=True,
                    close_fds=True, close_keep_fds=[si.file_fds.layerslog_a, OG.userns_unpri.usernsfd] )
    if pid == 0: # 子进程
        if not is_dir_inaccessible('/zrootfs'):
            os.unshare(unshrflg(d(mnt=1)))
            mount('tmpfs', '/zrootfs', 'tmpfs', mntflag_tmpfs, 'mode=000')
            rmt_ro('/zrootfs', mntflag_tmpfs, 'mode=000')
        os.setns(OG.userns_unpri.usernsfd, unshrflg(d(user=1)))
        drop_caps()
        # 尽管运行pasta前，上面已经通过userns回到了uid=1000，并降权，
        # 但pasta又会创建新容器，其子进程自认uid=0, 且自拥有
            # CapPrm: 0000000000201400
            # CapEff: 0000000000201400
            # CapBnd: 000001ffffffffff
        PYCODE = '\n'.join([line.strip() for line in f'''
            import os, json, pathlib, ctypes, ctypes.util, signal
            libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
            PR_SET_PDEATHSIG = 1 ; libc.prctl(PR_SET_PDEATHSIG, signal.SIGKILL)
            output = dict()
            output["self_see_pid"] = os.getpid()
            output["ns"] = dict(net=os.stat('/proc/self/ns/net').st_ino, pid=os.stat('/proc/self/ns/pid').st_ino)
            output["start_tick"] = open('/proc/self/stat').read().split(') ')[-1].split(' ')[22-1-2]
            pathlib.Path('/{tlcfg.sbxdir_path1}/temp/netns_proc_info.fifo').write_text( json.dumps(output) )
            os.execvp('sleep', ["{si.sandbox_name}_pasta", 'infinity'])
        '''.strip().splitlines() ])
        execvp('pasta',  ['pasta', '-f',  '--runas', f'{si.uid}:{si.gid}',
            *pasta_custom_args,
            si.pythonbin, '-IBS', '-c', PYCODE
        ] )
        warn_exit("exec to be pasta failed")
    else: # 原进程
        fd_fifo = os.open(f'/{tlcfg.sbxdir_path1}/temp/netns_proc_info.fifo', os.O_RDONLY|os.O_NONBLOCK)
        ready, _, wrong = select.select([fd_fifo], [], [fd_fifo], 2)
        if wrong: raise_exit('Unknown error while waiting for process info from netns process')
        elif not ready: raise_exit('Timeout while waiting for process info from netns process')
        netns_proc_info = d( json.loads( os.read(fd_fifo, 4096).decode() ) )
        os.close(fd_fifo)
        Path(f'/{tlcfg.sbxdir_path1}/temp/netns_proc_info.fifo').unlink()

        for x in [int(x) for x in os.listdir('/proc') if x.isdigit() ]:
            if os.access(f'/proc/{x}/ns', os.R_OK|os.X_OK) : ns_x = get_nstypes(f'/proc/{x}/ns')
            else: continue
            if ns_x.pid == netns_proc_info.ns.pid \
            and get_NSpid_arr(f'/proc/{x}/status')[-1] == netns_proc_info.self_see_pid \
            and get_start_tick(f'/proc/{x}/stat') == netns_proc_info.start_tick :
                pid_netns = x ;
                ns_netns_proc = ns_x
                break
        else: raise_exit('No matching netns process found')
        pidfd = os.pidfd_open(pid_netns)
        result = D(
            pid = pid_netns,
            pidfd = pidfd,
            netnsfd = os.open(f'/proc/{pid_netns}/ns/net', os.O_RDONLY),
            netnsino = os.stat(f'/proc/{pid_netns}/ns/net').st_ino,
        )
        wlog('netns_tun_p', ready_proc_name='netns_tun',
            self_see_pid=netns_proc_info.self_see_pid,
            start_tick=netns_proc_info.start_tick,
            ns=ns_netns_proc,
        )
        set_fd_keep_on_exec(result.pidfd, False)
        set_fd_keep_on_exec(result.netnsfd, True)

        return result

def create_userns_unpri():
    pid, skp = fork(create_socketpair=True, loghead=f'{loghead} userns', proc_dispname='unpri userns', cut_stdin=True,
                    close_fds=True, close_keep_fds=[si.file_fds.layerslog_a] )
    if pid == 0: # 子进程
        if not is_dir_inaccessible('/zrootfs'):
            os.unshare(unshrflg(d(mnt=1)))
            mount('tmpfs', '/zrootfs', 'tmpfs', mntflag_tmpfs, 'mode=000')
            rmt_ro('/zrootfs', mntflag_tmpfs, 'mode=000')

        os.unshare(unshrflg(d(user=True)))
        skp.chd_send(BS.SetMeUidUser)
        skp.chd_recv(1, 2, BS.SetYouUidUserDone)
        skp.close()
        drop_caps()
        wlog('userns_unpri_p', me_proc_info=True,
             ready_proc_name='userns_unpri',
             pidns_depth=tlcfg.pidns_depth, pidns_tree=tlcfg.pidns_tree,
        )
        execvp('sleep', [f"{si.sandbox_name}_userns" ,  'infinity'])
        raise_exit('exec sleep failed') # exec后不应该到这里
    else: # 原进程
        skp.pa_recv(1, 1, BS.SetMeUidUser)

        Path(f'/proc/{pid}/setgroups').write_text('deny\n')
        Path(f'/proc/{pid}/uid_map').write_text(f'{si.uid} 0 1\n')
        Path(f'/proc/{pid}/gid_map').write_text(f'{si.gid} 0 1\n')
        result = D(
            pidns_tree = tlcfg.pidns_tree,
            pidfd = os.pidfd_open(pid),
            usernsfd = os.open(f'/proc/{pid}/ns/user', os.O_RDONLY),
            usernsino = os.stat(f'/proc/{pid}/ns/user').st_ino,
        )
        set_fd_keep_on_exec(result.pidfd, False)
        set_fd_keep_on_exec(result.usernsfd, True)

        skp.pa_send(BS.SetYouUidUserDone)
        return result
def get_userns_unpri(): # userns_unpri 是由layer2建立的，outest/layer1F 可能需要从/proc中获取其userns作为fd
    CHK( OutestProcsMonitor.I_AM_OUTEST or (tlcfg.depth==1 and os.getpid()==1), "Only outest or layer1 can call this")
    p_userns_unpri = get_procs_seen()['userns_unpri']
    if OutestProcsMonitor.I_AM_OUTEST:      pid = p_userns_unpri.NSpid[0]
    elif tlcfg.depth==1 and os.getpid()==1: pid = p_userns_unpri.NSpid[1]
    inode1 = os.stat(f'/proc/{pid}').st_ino
    result = D(
        pidns_tree = p_userns_unpri.pidns_tree,
        pidfd = os.pidfd_open(pid),
        usernsfd = os.open(f'/proc/{pid}/ns/user', os.O_RDONLY),
        usernsino = os.stat(f'/proc/{pid}/ns/user').st_ino,
    )
    inode2 = os.stat(f'/proc/{pid}').st_ino
    CHK(inode1==inode2, 'The inode of the user_unpri process changed during get_userns_unpri()')
    return result


def wait_for_startAfters(arr_startAfter):
    if not arr_startAfter: return
    for wait_task in arr_startAfter:
        tt = time.monotonic()
        if wait_task.waittype == 'socket-listened':
            while not is_unix_socket_listened(wait_task.path):
                CHK(time.monotonic() <= tt+(6 if OG.uc.gui not in ['xpra', 'xpra-weston-xwayland'] else 40), f'Waited too long, reporting error ( {wait_task} )')
                time.sleep(0.1)



def build_fs(cfg):
    if not cfg.newrootfs_path:
        if cfg.newrootfs: # 如果设置了将要变根，现在先提前确定新根的位置
            cfg.newrootfs_path = f'{cfg.sbxdir_path0}/new.{cfg.layer_name}.rootfs'
        else:
            cfg.newrootfs_path = '/'
    mkdirp(cfg.newrootfs_path)

    if cfg.fs:
        fsOpertns = gen_fsOpertns(cfg)
        remountPlans = commit_fsOpertns(cfg, fsOpertns)
        commit_remounts(remountPlans)

    # 在build_fs完了之后挂载/proc, 与fsOpertns那边的代码解耦
    if cfg.unshare_pid or cfg.newrootfs:
        new_proc_path = napath(cfg.newrootfs_path+'/proc')
        # log(f'Mounting proc to {new_proc_path}')
        mkdirp(new_proc_path)
        mount('proc', new_proc_path, 'proc', mntflag_proc, 'hidepid=1')
        cfg.new_proc_dir_mnted = True
    set_ps1('afterFs')

    # 执行变根 (chroot)
    if cfg.newrootfs:
        mkdirp(f'{cfg.newrootfs_path}/oldroot')
        # log(f'Going to pivot root to {cfg.newrootfs_path}')
        pivot_root(cfg.newrootfs_path, f'{cfg.newrootfs_path}/oldroot')
        os.chdir('/')
        umount('/oldroot', MNT.DETACH)
        os.rmdir('/oldroot') # 必须为空目录才能删除，这也保证已经缷载，未缷载则报错退出
        os.chmod('/', 0o555)
        rmt_ro('/', mntflag_newrootfs)
        # log(f'This layer filesystem ready {os.listdir('/')}')
    del cfg.newrootfs_path
    del cfg.sbxdir_path0


def commit_fsOpertns(cfg, fsOpertns):
    target_fs_path = cfg.newrootfs_path
    # log(f'Going to build (mount/create) this layer filesystem, will use this as root: {target_fs_path}')
    remountPlans = []
    def z(rmtItem):
        remountPlans.append(rmtItem)

    if target_fs_path.startswith(si.PTMP):
        mount(si.PTMP, si.PTMP, None, mntflag_binddir|MS.RDONLY, None)
        rmt_ro(si.PTMP, mntflag_binddir)
        CHK( os.statvfs(si.PTMP).f_flag&MS.RDONLY, "PTMP failed to made ro")
    if not Path(f'{cfg.sbxdir_path0}/temp').is_mount():
        mount('tmpfs', f'{cfg.sbxdir_path0}/temp', 'tmpfs', mntflag_tmpfs, None)

    mkdirp(target_fs_path)
    if napath(target_fs_path) != '/':
        mount("tmpfs", target_fs_path, "tmpfs", mntflag_newrootfs, None)
        mount(None, target_fs_path, None, MS.REC | MS.SLAVE, None)
        # # 用了slave它还是private,不知原因
    os.chdir(target_fs_path)
    CHK( Path(target_fs_path).is_mount() , f"{target_fs_path} is not a mount point")
    mkdirp(f'{target_fs_path}/proc') # proc不在这里做，预留个目录

    for opItem in fsOpertns:
        op = opItem.op
        src = opItem.src
        dest = opItem.dest
        real_dest = napath(f'{target_fs_path}/{dest}')
        if op in ['same', 'rosame', 'bind', 'robind'] : # TODO bindfs 它才可以设置destmode
            CHK( os.path.lexists(src) , f"Source {src} does not exist")
            if op in ['bind', 'robind'] :
                src = rslvy(src)
            RO = True if op in ['rosame', 'robind'] else False
            if Path(src).is_symlink(): # 软链 (一定要把 symlink 放在最先判断)
                symlink(Path(src).readlink(), real_dest)
                # TODO chroot 前后对symlink做一致性检查
            elif is_dir(src): # 文件夹
                mkdirp(real_dest)
                mount(src, real_dest, None, mntflag_binddir, None)
                if RO : rmt_ro(real_dest, mntflag_binddir )
            elif is_file(src) or is_dev(src):
                # 普通文件可以这这样。猜测 字符设备、块设备 也可以当普通文件一样处理
                make_file_exist(real_dest)
                mount(src,  real_dest, None, MS.BIND, None)
                rmt_ro(real_dest, MS.BIND) if RO else None
            elif is_socket(src): # 已知socket不能remount成ro
                make_file_exist(real_dest)
                mount(src,  real_dest, None, MS.BIND|MS.RDONLY, None)
            else: raise_exit(f"Type of source {src} is not yet supported")
        elif op in ['ovl']:
            mkdirp(real_dest)
            work_tmp = tempfile.mkdtemp(dir=f'{cfg.sbxdir_path0}/temp')
            upper_tmp = tempfile.mkdtemp(dir=f'{cfg.sbxdir_path0}/temp')
            mount_overlayfs(lowerdir=src, workdir=work_tmp, upperdir=upper_tmp, target=real_dest)
        elif op in ['tmpfs', 'rotmpfs']:
            RO = True if op == 'rotmpfs' else False
            mkdirp(real_dest)
            flag = opItem.flag or mntflag_tmpfs
            mount('tmpfs', real_dest, 'tmpfs', flag , 'mode=755')
            if RO : z(d(dirpath=real_dest, flag=flag))
        elif op == 'dir':
            mkdirp(real_dest)
        elif op == 'any-exist': #如果已存在，无论是文件/目录/软链都可以，不存在就建个空文件
            if not os.path.lexists(real_dest):
                make_file_exist(real_dest)
        elif op in ['file', 'rofile'] :
            # NOTE 无论何种情况，都不要对目标文件做写入，而是创建个临时文件去“挂载覆盖”。
            # 记得永远不要写入目标文件，防止覆盖用户文件
            RO = True if op == 'rofile' else False
            with tempfile.NamedTemporaryFile( dir=f'{cfg.sbxdir_path0}/temp', mode='w', delete=False) as f:
                f.write(opItem.content)
                mode = None ; optn = None
                if RO :             mode = '444'
                if opItem.destmode : mode = opItem.destmode
                if mode is not None : os.chmod(f.name, int(mode,base=8)) ; optn = f'mode={mode}'
                make_file_exist(real_dest)
                mount(f.name, real_dest, None, MS.BIND|(MS.RDONLY if RO else 0), optn)
                try_pass(lambda: rmt_ro(real_dest, mntflag_binddir, optn) if RO else None )
        elif op == 'symlink':
            symlink(opItem.linkto, real_dest)
            # TODO chroot 前后对symlink做一致性检查
        elif op == 'empty-if-exist' : # TODO landlock 优先
            if not os.path.lexists(real_dest): continue
            optn='mode=0000'
            if Path(real_dest).is_symlink(): # 软链 (一定要把 symlink 放在最先判断)
                raise_exit(f"Path {real_dest} to be emptied is a symlink, handling not yet implemented")
            elif is_dir(real_dest): # 文件夹
                mount('tmpfs', real_dest, 'tmpfs', MS.RDONLY|MS.NODEV|MS.NOEXEC|MS.NOSUID, optn)
            elif is_dev(real_dest): # 设备文件
                mount('/dev/null', real_dest,  None, MS.BIND|MS.RDONLY, optn)
                try_pass(lambda: rmt_ro(real_dest, mntflag_binddir, optn) )
            else: # 普通文件、socket, fifo
                mount(f'{cfg.sbxdir_path0}/empty', real_dest,  None, MS.BIND|MS.RDONLY, optn)
                try_pass(lambda: rmt_ro(real_dest, mntflag_binddir, optn) )
        elif op == 'sbxdir-in-newrootfs':
            CHK(dest == '/sbxdir', "dest for sbxdir-in-newrootfs must be /sbxdir")
            make_mnt_fill_sbxdir(si,  cfg, call_at_buildfs=True)
        elif op == 'devpts':
            mkdirp(real_dest)
            mount('devpts', real_dest, 'devpts', MS.NOEXEC|MS.NOSUID, 'mode=0666,ptmxmode=0666,newinstance')
        elif op in ['appimg-mount', 'sqfs-mount'] :
            mkdirp(real_dest)
            src = rslvy(src)
            offset = get_appimg_sqoffset(src) if op == 'appimg-mount' else 0
            # TODO 先做symlink链接到真实appimage文件路径，再调用 squashfuse命令
            run_a_cmd(['squashfuse', '-o', f'ro,offset={offset}', src, real_dest])
            # 不考虑内核挂载先，因为内核挂载squashfs要loop, 容器内难搞.先用住 fuse
        elif op == 'rmt-ro':
            rmt_ro(real_dest, opItem.flag or 0)
        elif op == 'final-rmt-ro':
            z(d(dirpath=real_dest, flag=opItem.flag or 0))
        else:
            raise_exit(f"Unrecognized fsOp item {opItem}")

    return remountPlans

def gen_fsOpertns(cfg): # 把fs里面的 many_op 都转成 op ,并去重、排序
    fsOpertns = []
    def a(stepobj):
        fsOpertns.append(stepobj)

    for opItem in cfg.fs:
        # 一个 opItem 里， many_op 和 op 只应该出现其中一种
        many_op = opItem.many_op # 预设的多个op的集合
        op = opItem.op # 一个op
        if many_op == 'dup-rootfs': # 把前一个rootfs复制到子层。包含dev
            destbase = opItem.destbase or '/'
            srcbase = opItem.srcbase or '/'
            CHK( destbase in ['/', '/zrootfs'], "dup-rootfs requires destbase to be '/' or '/zrootfs'")
            CHK( srcbase in ['/', '/zrootfs'],  "dup-rootfs requires srcbase to be '/' or '/zrootfs'")
            if destbase != '/':
                a( d( op='rotmpfs', dest=destbase , flag=mntflag_newrootfs) )
            for x in os.listdir(srcbase):
                if x in [ 'proc', 'sbxdir', 'zrootfs', ]: continue
                a( d( op='same', dest=napath(f'{destbase}/{x}') , src=napath(f'{srcbase}/{x}') ) )
            # a( d( op='tmpfs', dest=napath(f'{destbase}/run/tmux') ) ) # 按理说，使用 dup-rootfs 的层本来不应该运行任何程序（因为uid=0)，但可能会用 tmux 当内外通信工具，先预留这个，并且要与host中的 /run/tmux 不同
        elif many_op == 'sbxdir-in-newrootfs':
            dcp_pItem = copy.deepcopy(opItem)
            a( d({'op': dict.pop(dcp_pItem, 'many_op'), **dcp_pItem} ) )
        elif many_op == 'basic-dev':
            # 最小 /dev 集合。把常用设备结点从宿主机 bind 进来；并为 shm 提供 tmpfs
            a( d( op='rotmpfs', dest='/dev' ) )
            basic_devs = [ 'null', 'zero', 'full', 'urandom', 'random',] # 'tty', 'console'
            for dname in basic_devs:
                a( d( op='rosame', dest=f'/dev/{dname}', src=f'/dev/{dname}' ) ) # 不能ro对单个具体设备？
            a( d( op='devpts',  dest='/dev/pts') )
            a( d( op='symlink', dest='/dev/ptmx', linkto='pts/ptmx' ) )
            a( d( op='symlink', dest='/dev/fd',     linkto='/proc/self/fd' ) )
            a( d( op='symlink', dest='/dev/stdin',  linkto='/proc/self/fd/0' ) )
            a( d( op='symlink', dest='/dev/stdout', linkto='/proc/self/fd/1' ) )
            a( d( op='symlink', dest='/dev/stderr', linkto='/proc/self/fd/2' ) )
            a( d( op='symlink', dest='/dev/core',   linkto='/proc/kcore' ) )
            a( d( op='tmpfs', dest='/dev/shm' ) )
        elif many_op == 'container-rootfs':
            # 只读挂载的重要系统路径
            paths_to_rosame = [ '/bin', '/sbin', '/usr', '/lib64', '/lib', '/etc',
                '/var/cache/fontconfig' ]
            if os.path.lexists('/var/lib/ca-certificates'):
                paths_to_rosame.append += ['/var/lib/ca-certificates']
            for p in paths_to_rosame:
                a( d( op='rosame', dest=p, src=p ) )
            # 需要 tmpfs 的可写路径（容器内部用）
            paths_to_tmpfs = [ '/run', '/tmp', '/root', '/mnt',
                '/var', '/var/lib', '/var/lib/empty', '/var/cache',
                f'/run/user/{si.uid}', '/run/user/0', '/run/lock',
                '/run/tmux' , f'{si.HOME}' , f'{si.HOME}/.cache' ,
                f'{si.HOME}/.local/share/RecentDocuments',
                f'{si.HOME}/.local/share/recently-used.xbel',
                f'{si.HOME}/.local/share/Trash', ]
            for p in paths_to_tmpfs:
                a( d( op='tmpfs', dest=p ) )
            a( d( op='symlink', dest='/var/run', linkto='/run' ) )
            a( d( op='symlink', dest='/var/lock', linkto='/run/lock' ) )
            a( d( op='symlink', dest='/var/lib/dbus/machine-id', linkto='/etc/machine-id' ) )
        elif many_op == 'mask-privacy':
            destbase = opItem.destbase
            CHK( destbase in ['/', '/zrootfs'], "mask-privacy requires destbase to be '/' or '/zrootfs'")
            path_maskfile = f'{si.HOME}/.config/treesandbox/paths_never_access.txt'
            maskfile = Path(path_maskfile)
            paths_to_mask = maskfile.read_text().splitlines() if maskfile.exists() else []
            paths_to_mask = [path.strip() for path in paths_to_mask if path.strip()]
            log(f'Need to mask {len(paths_to_mask)} paths, from {path_maskfile}')
            for path in paths_to_mask:
                CHK( path.startswith('/'), "Entry in paths_never_access.txt does not start with '/'")
                path = napath(path)
                if os.path.lexists(path):
                    a( d( op='empty-if-exist', dest=napath(f'{destbase}/{path}' ) ) )
        elif many_op == 'appimage':
            a( d(op='appimg-mount', src=opItem.src, dest=f'/sbxdir/apps/{opItem.name}') )
            start_sh_content = f'''#!/bin/bash
                script=$(readlink -f "$0")
                scriptpath=$(dirname "$script")
                env APPDIR="$scriptpath/{opItem.name}" "$scriptpath"/{opItem.name}/AppRun "$@"
            '''
            a( d(op='rofile', dest=f'/sbxdir/apps/run_{opItem.name}', destmode='555', content=start_sh_content) )
        elif many_op == 'squashfs':
            a( d(op='sqfs-mount', src=opItem.src, dest=f'/sbxdir/apps/{opItem.name}') )
        # 下面是 op 而不是 many_op 。因为它们两个不应同时有，所以用同一if树
        elif op:
            a( opItem )
        else:
            raise_exit(f"Unrecognized fs item {opItem}")

    for i, opItem in enumerate(fsOpertns):
        if opItem.SDS:
            if   opItem.src and not opItem.dest: opItem.dest = opItem.src
            elif opItem.dest and not opItem.src: opItem.src = opItem.dest
            elif not opItem.src and not opItem.dest:        raise_exit(f"{opItem} has neither src nor dest")
            elif napath(opItem.src) != napath(opItem.dest): raise_exit(f"{opItem} has SDS set, but src and dest are inconsistent")
            del opItem.SDS
        dcp_pItem = copy.deepcopy(opItem)
        dcp_pItem = d({'op': dict.pop(dcp_pItem, 'op'), **dcp_pItem})
        fsOpertns[i] = dcp_pItem

    # 查找移除重复的dest
    def find_dup_dest():
        used_dest = set()
        for i in reversed(range(0, len(fsOpertns))):
            opItem = fsOpertns[i]
            if opItem.op in ['rmt-ro', 'final-rmt-ro']: continue
            if opItem.dest in used_dest:
                log(f"debug: due to duplicate dest (={opItem.dest}), removing {opItem}")
                fsOpertns[i] = d(removed=True)
            used_dest.add(opItem.dest)
    # TODO 分为 普通、remount、overlay 几个组来去重
    find_dup_dest()
    fsOpertns = [opItem for opItem in fsOpertns if not opItem.removed]

    # 排序 fsOpertns
    fsOpertns = sorted(fsOpertns, key=lambda opItem: napath(opItem['dest']).split(os.sep) )
    fsOpertns = sorted(fsOpertns, key=lambda x: 0 if (isinstance(x, dict) and x.get('op') == 'sbxdir-in-newrootfs') else 1)

    # [log(opItem) for opItem in fsOpertns] # debug
    return fsOpertns

def commit_remounts(remntPlans):
    for rItem in remntPlans:
        # log('ro-remounting: ' , rItem) # debug
        dirpath = rItem.dirpath
        flag = rItem.flag or 0
        rmt_ro(dirpath, flag)

def rmt_ro(path, flag=0, optn=''):
    flag |= os.statvfs(path).f_flag & (MS.NODEV|MS.NOSUID|MS.NOEXEC)
    mount(None, path, None, MS.REMOUNT|MS.RDONLY|flag, optn)


def maybe_sendto_running_instance(reusefg):
    log('Looking for running instance of same-name sandbox ...')
    MATCH_SI_K = ["hash_bootsbx_py", "hostname", "uid", "gid", "username", "groupname", "PTMP", "pythonbin",  ]
    def is_still_alive(instance_name):
        if is_dir(f'{si.PTMP}/{instance_name}') and not os.path.lexists(f'{si.PTMP}/{instance_name}_exit'):
            return True # is_still_alive() 返回 真

    chosen_instance = None
    sock_estb = None
    for dir_in_PTMP in Path(si.PTMP).iterdir():
        dirname = dir_in_PTMP.name
        # 是否是同名沙箱
        if not NameMng.is_pattern_instance_name(dirname):
            continue
        # 是否无 xxx_exit 退出标记
        if os.path.lexists(f'{si.PTMP}/{dirname}_exit'):
            continue

        tmp_t = time.monotonic()
        while time.monotonic() <= tmp_t+1.5 and is_still_alive(dirname): # 允许那个实例2s的时间建立OutsideServ的socket文件
            if is_socket(f'{si.PTMP}/{dirname}/OServ.socket'):
                break
            time.sleep(0.1)
        else: # 那个实例2s都没有设置socket文件
            log_warn(f"Ignoring a possibly abnormal old instance {dirname}")
            continue

        # 再检查一次 是否无 xxx_exit 退出标记
        if os.path.lexists(f'{si.PTMP}/{dirname}_exit'):
            continue

        tmp_t = time.monotonic()
        sock_estb = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        while time.monotonic() <= tmp_t+1 and is_still_alive(dirname): # 允许那个实例1s的时间开始监听那个它自己已经创建的socket
            try:
                sock_estb.connect(f'{si.PTMP}/{dirname}/OServ.socket')
                break
            except ConnectionRefusedError:
                time.sleep(0.05)
        else:
            log(f"Ignoring a possibly abnormal old instance (OServ.socket unresponsive): {dirname}")
            continue


        chosen_instance = dirname
        break

    if not chosen_instance:
        if sock_estb : sock_estb.close()
        return "not_reusing"

    log(f'Found instance {chosen_instance}, attempting to send app command to it ')
    msgObj = d()
    msgObj.run_in_mainLyr_cmdvec = OG.mainApp_cmdvec
    msgObj.workdir     = OG.chosen_workdir or OG.chosen_appItem.workdir or None
    msgObj.workdir_try = OG.chosen_workdir_try or None
    msgObj.si_should_match = d({k:si[k] for k in MATCH_SI_K})
    if reusefg: msgObj.use_dtach = True

    si.client_pid = si.outest_pid
    si.reuse_instance = chosen_instance
    si.reuse_sbxdir = si.outest_sbxdir
    del si.instance_name ; del si.outest_sbxdir ; del si.CG_SBX; del si.outest_pid

    try:
        sock_estb.send( json.dumps(msgObj).encode() )
    except Exception as err:
        warn_exit(f'Error: Failed to send message to found instance {err}')

    ready, _, wrong = select.select([sock_estb], [], [sock_estb], 3)  # 阻塞检查
    if wrong:
        warn_exit(f'Error while waiting for reply, possibly timeout or unknown error')
    elif not ready:
        warn_exit(f'Did not receive a successful reply from the running instance')
    elif ready:
        try: data = sock_estb.recv(300_000)
        except Exception as err: warn_exit(f'Error receiving data from socket:{err}')
        finally: sock_estb.close()
        if data:
            try: msgObj = d( json.loads( data.decode() ) )
            except Exception as err: warn_exit(f'Cannot parse received message correctly:{err}')
            if msgObj.message: log(f'Additional message in reply: {msgObj.message}')
            if msgObj.reuseSucceeded:
                if not reusefg: log('Successfully sent app command to the instance')
                else: # reusefg==True
                    shareShellSubpName = msgObj.message
                    if not shareShellSubpName.startswith('shareshell_'):
                        warn_exit('Did not receive shareshell_ process name')
                    linkfile = f'{si.PTMP}/{chosen_instance}/into.{shareShellSubpName}.shellsocket.link'
                    t0 = time.monotonic()
                    while time.monotonic() <= t0 + 2:
                        if os.path.exists(linkfile) : break
                    else: warn_exit(f'Timeout waiting for target of link file {linkfile}')
                    print('...\n' * os.get_terminal_size().lines)
                    try: os.execvp('dtach', ['dtach', '-a', os.readlink(linkfile) ] ) # NOTE 不能用Path来解析，可能因为跨root
                    except Exception as err: warn_exit(err)
                sys.exit(0)
            else:
                log_warn(f'Reply of running instance was not success')
                if msgObj.youStartNewInstance:
                    log('Reply of the running instance indicates we should create new instance to run app')
                    return "not_reusing"
                sys.exit(1)
        else: warn_exit(f'Received empty reply')
    else: raise_exit('Unknown error, unexpected logic branch')

class OutsideServ():
    conns = []
    cnt_recvmsg = 0
    @classmethod
    def init(cls):
        cls.skt_OServLsn = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        cls.skt_OServLsn.bind(f'{si.outest_sbxdir}/OServ.socket')
        cls.skt_OServLsn.listen(5)
    @classmethod
    def one_loop_task(cls):
        # 处理已经建立的连接
        for i in reversed(range(0, len(cls.conns))):
            connItem = cls.conns[i]
            ready, _, wrong = select.select([connItem.skt_conn], [], [connItem.skt_conn], 0)  # 非阻塞检查
            if wrong:
                log_warn('An OutsideServ connection encountered an error')
                cls.close_conn(connItem)
                continue
            elif ready:
                try: data = connItem.skt_conn.recv(300_000)
                except Exception as err:
                    log_warn(f'Error reading data received from socket:{err}')
                    cls.close_conn(connItem)

                if data:
                    connItem.last_tick = time.monotonic()
                    # log(f"Received external message: {data!r}")
                    try: cls.onDataRecved(data, connItem )
                    except Exception as err:
                        log_warn(f'Error processing received message:{err}')
                        cls.close_conn(connItem)
                else:
                    # log("External connection closed (recv returned empty)") # 发完消息正常断开
                    cls.close_conn(connItem)
            else: # 无消息
                if connItem.last_tick + 60 < time.monotonic():
                    log_warn("External connection timed out (no messages), closing")
                    cls.close_conn(connItem)


        # 有没有新的外部连接
        ready, _, wrong = select.select([cls.skt_OServLsn], [], [cls.skt_OServLsn], 0)
        if wrong: raise_exit('Unknown error while waiting for new external connections')
        elif ready:
            conn, client_addr = cls.skt_OServLsn.accept()
            cls.cnt_recvmsg += 1
            # log(f'New external connection {cls.cnt_recvmsg}', conn)
            cls.conns.append( d(skt_conn=conn, last_tick=time.monotonic() , index=cls.cnt_recvmsg) )
    @classmethod
    def onDataRecved(cls, data, connItem):
        try: msgObj = d( json.loads( data.decode() ) )
        except Exception as err:
            errmsg = f'Cannot parse received message correctly:{err}'
            log_warn(f'{errmsg}')
            cls.response_close(connItem, message=errmsg)
            return False
        for k,v in dict.items(msgObj.si_should_match or {}):
            if not eq_ignore_order(si[k], v):
                errmsg = f'si[{k}] inconsistent.\nValue in running sandbox: {si[k]}\nValue in message: {v}\n(If you modified the sandbox configuration, you may need to terminate the running sandbox first)'
                log_warn(f'{errmsg}')
                cls.response_close(connItem, message=errmsg)
                return False
        if msgObj.run_in_mainLyr_cmdvec:
            targetLyr = si.specialLyrs.mainLyr
            workdir     = msgObj.workdir or None
            workdir_try = msgObj.workdir_try or None
            if not msgObj.use_dtach:
                cmdvec = msgObj.run_in_mainLyr_cmdvec
                subp_name = f'mainApp_{connItem.index}'
            else : # use_dtach 为真
            # if True:
                # shellId =           f'AASSDD-{targetLyr}'
                randstr = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
                shellId = f'{randstr}-{targetLyr}'
                cmdvec = ['dtach', '-N', f'/sbxdir/temp/shareshell.{shellId}.socket',  *msgObj.run_in_mainLyr_cmdvec ]
                subp_name = f'shareshell_{shellId}'
            OutestProcsMonitor.tell_lyr_runsubp(targetLyr,
                d(
                    cmdvec=cmdvec,
                    workdir     = workdir,
                    workdir_try = workdir_try,
                    subp_name=subp_name,
                    stdin=False
                )
            )
            cls.response_close(connItem, reuseSucceeded=True, message=subp_name)
            return True
    @classmethod
    def response_close(cls, connItem, reuseSucceeded=None, youStartNewInstance=None, message=None):
        responseObj = d()
        if reuseSucceeded:      responseObj.reuseSucceeded = True
        if youStartNewInstance: responseObj.youStartNewInstance = True
        if message:             responseObj.message = message
        try:
            connItem.skt_conn.send( json.dumps(responseObj).encode() )
            return True
        except Exception as err:
            log_warn(f'Failed to reply to external connection {err}')
            return False
        finally:
            cls.close_conn(connItem)

    @classmethod
    def close_conn(cls, connItem):
        connItem.skt_conn.close()
        try: cls.conns.remove(connItem)
        except Exception as err: log_warn(f'Error while closing external connection (might already be closed): {err}')

# 「self_see_pid, start_tick, pidns(inode) = 必备认证3要素」 。仅那些能从主机读出ns目录的可以认证
class OutestProcsMonitor:
    I_AM_OUTEST=None
    @classmethod
    def i_am_outest(cls):
        cls.I_AM_OUTEST=True
        cls.procs_alive = [] # 最外层从主机/proc中读出的。NSpid, start_tick, ns(含各类，但可能无)， cmdvec
        cls.procs_heared = D() # 收到过WLOG且WLOG带ready_proc_name, 但由于可能太快结束，不一定被alive捉到，那样就不进入seen. 格式为WLOG的内容
        cls.procs_seen = D() # WLOG收到信息并与alive对比上后的，NSpid(来自alive), 「self_see_pid, start_tick, pidns(inode) = 必备认证3要素」。可能来自WLOG的pidns_tree, pidns_depth
        cls.procs_wdgsee = D() # 格式同seen, 但只收录需要保活的
        cls.logs_should_match_soon = []
        cls.fd_wr_alive = os.open(f'{si.outest_sbxdir}/procs.alive.json', os.O_WRONLY)
        cls.fd_wr_seen = os.open(f'{si.outest_sbxdir}/procs.seen.json', os.O_WRONLY)
        cls.fd_wr_heared = os.open(f'{si.outest_sbxdir}/procs.heared.json', os.O_WRONLY)
        cls.fd_wr_wdgsee = os.open(f'{si.outest_sbxdir}/procs.wdgsee.json', os.O_WRONLY)

        cls.oPaSkts = d()
        for lyrn, fdpair in dict.items(si.oSkt_fds):
            cls.oPaSkts[lyrn] = socket.socket(fileno=fdpair.pa)

        # 不需等主层启动就发，保证主层收到的第一条信息是这个mainApp的命令
        cls.tell_lyr_runsubp(si.specialLyrs.mainLyr,
            d(
                cmdvec=OG.mainApp_cmdvec,
                subp_name='mainApp',
                workdir     = OG.chosen_workdir     or OG.chosen_appItem.workdir or None,
                workdir_try = OG.chosen_workdir_try or None,
            )
        )
        OutsideServ.init()
    @classmethod
    def get_alive_new_sshot_from_cg(cls) -> list:
        CHK( cls.I_AM_OUTEST, "Only outest can call this, but I_AM_OUTEST is not set")
        ps_sshot = []
        for pid in Path(f'{si.CG_SBX}/cgroup.procs').read_text().splitlines():
            if ( p_full_info := get_pinfo_by_pidpath(f'/proc/{pid}') ):
                ps_sshot.append(p_full_info)
        return ps_sshot
    @classmethod
    def update_procsalive(cls): # 只有 最外层 原进程 调用这个函数
        CHK( cls.I_AM_OUTEST, "Only outest can call this, but I_AM_OUTEST is not set")
        alive_new_sshot = cls.get_alive_new_sshot_from_cg()
        # NOTE 必须 既写本cls内部变量，也更新路径文件内容
        cls.procs_alive = alive_new_sshot # 写cls内部
        cls.write_procs_info_to_file('alive')
    @classmethod
    def aliveproc_and_elproc_equal(cls, plv, pel): #plv="proc alive" | pel="proc from event log"
        if not plv.ns or not plv.ns.pid or not pel.ns or not pel.ns.pid : return False
        if plv.NSpid[-1] == pel.self_see_pid \
        and plv.start_tick == pel.start_tick \
        and plv.ns.pid == pel.ns.pid:
            return True
        else: return False
    @classmethod
    def aliveproc_and_seenproc_equal(cls, plv, psn): # plv="proc alive" | psn="proc seen"
        if not plv.ns or not plv.ns.pid: return False
        if plv.NSpid[-1] == psn.self_see_pid \
        and plv.start_tick == psn.start_tick \
        and plv.ns.pid == psn.pidns :
            return True
        else: return False
    @classmethod
    def conv_to_seenproc(cls, aliveProc, logItem): # 输入的是一对互相符合的aliveProc和logItem条目
        return D(
            NSpid = aliveProc.NSpid,
            pidns_tree = logItem.pidns_tree,
            pidns_depth = logItem.pidns_depth,
            start_tick = logItem.start_tick,
            pidns = logItem.ns.pid,
            self_see_pid = logItem.self_see_pid,
        )
    @classmethod
    def sbx_exit_broadcast(cls):
        CHK( cls.I_AM_OUTEST, "Called sbx_exit_broadcast() without I_AM_OUTEST set", 'warn') # 可能会在初始化之前被调用
        for lyrname in si.expected_alive_layers:
            cls.sendmsg_to_lyr(lyrname, d(action='sbx_exit'), loose=True)
    @classmethod
    def sendmsg_to_lyr(cls, lyrname, msgobj, loose=False):
        CHK( cls.I_AM_OUTEST, "Called sendmsg_to_lyr() without I_AM_OUTEST set", 'warn' if loose else 'raise_exit')
        try:
            cls.oPaSkts[lyrname].send(json.dumps(msgobj).encode())
        except Exception as err:
            if loose: log_warn(f"Sending message to {lyrname} was not successful: {err}")
            else: raise
    @classmethod
    def tell_lyr_runsubp(cls, lyrname, subpItem):
        CHK( cls.I_AM_OUTEST, "Only outest can call this, but I_AM_OUTEST is not set")
        cls.sendmsg_to_lyr(lyrname, d(action='run_subp', subpItem=subpItem) )
    @classmethod
    def symlink_into_sbxdir(cls, dest, file_in_sbxdir): # 创建软链，从外部，链到本沙箱实例目录内的文件
        CHK( cls.I_AM_OUTEST, "Only outest can call this, but I_AM_OUTEST is not set")
        linkto = napath(f'{si.outest_sbxdir}/{file_in_sbxdir}')
        CHK( not Path(linkto).is_dir(), f'For safety, linking to directories is not allowed')
        symlink(linkto, dest)
    @classmethod
    def symlink_from_sbxdir_to_in_proc_rootfs(cls, slk_name, to_proc_name, target_in_proc_rootfs): # 创建软链，从本沙箱实例目录内, 链到本沙箱的进程的 rootfs 里的某文件
        CHK( cls.I_AM_OUTEST, "Only outest can call this, but I_AM_OUTEST is not set")
        pid = get_procs_seen()[to_proc_name].NSpid[0]
        real_linkto = napath(f'/proc/{pid}/root/{target_in_proc_rootfs}')
        CHK( not Path(real_linkto).is_dir(), f'For safety, linking to directories is not allowed')
        symlink(real_linkto, f'{si.outest_sbxdir}/into.{to_proc_name}.{slk_name}.link')
    @classmethod
    def custom_action_when_procname_seen(cls, proc_name):
        CHK( cls.I_AM_OUTEST, "Only outest can call this, but I_AM_OUTEST is not set")
        if proc_name == 'userns_unpri':
            OG.userns_unpri = get_userns_unpri()
        if proc_name in ['xephyr', 'xwayland', 'xvfb']:
            cls.symlink_from_sbxdir_to_in_proc_rootfs('x11socket', proc_name, f'/tmp/.X11-unix/X{si.newXId}')
            cls.symlink_into_sbxdir(f'/tmp/.X11-unix/X{si.newXId}', f'into.{proc_name}.x11socket.link')
            cleanup_symlinks_to_rm.add(f'/tmp/.X11-unix/X{si.newXId}')
        if proc_name == 'weston':
            cls.symlink_from_sbxdir_to_in_proc_rootfs('waylandsocket', proc_name, f'{si.sbx_XDG_R_D}/wayland-{si.newXId}')
            cls.symlink_into_sbxdir(f'{si.host_XDG_R_D}/wayland-{si.newXId}', f'into.{proc_name}.waylandsocket.link')
            cleanup_symlinks_to_rm.add(f'{si.host_XDG_R_D}/wayland-{si.newXId}')
        if proc_name.startswith('shareshell_'):
            shellId = proc_name.removeprefix('shareshell_')
            cls.symlink_from_sbxdir_to_in_proc_rootfs('shellsocket', proc_name, f'/sbxdir/temp/shareshell.{shellId}.socket')
        for bItem in (si.bridges or []):
            cls.check_bridges_condition_and_do(proc_name, bItem)
    @classmethod
    def check_bridges_condition_and_do(cls, proc_name, bItem):
        seefrom = bItem.real_seefrom
        seeto   = bItem.real_seeto
        bridge_name = bItem.bridge_name
        condition = ['userns_unpri',  seefrom, seeto]
        if proc_name in condition:
            if set(condition).issubset(set(dict.keys( get_procs_seen() ))):
                log(f'Creating bridge {bridge_name}')
                seefrom_pid         = get_procs_seen()[seefrom].NSpid[0]
                seeto_pid   = get_procs_seen()[seeto].NSpid[0]
                pidfd_seefrom        = os.pidfd_open(seefrom_pid)
                pidfd_seeto   = os.pidfd_open(seeto_pid)
                ns_seefrom        = get_nstypes(f'/proc/{seefrom_pid}/ns')
                ns_seeto   = get_nstypes(f'/proc/{seeto_pid}/ns')
                PID1, _ = fork( proc_dispname='bridge', loghead=bridge_name, cut_stdin=True,
                               close_fds=True,
                               close_keep_fds=[si.file_fds.layerslog_a, pidfd_seefrom,  pidfd_seeto, OG.userns_unpri.usernsfd],
                               set_fds_CLOEXEC=True )
                if PID1 == 0: # 第一个子进程.因为之前创建layer1时unshare过，这里已经是与layer1同pidns
                    # TODO 判断其他ns种类，如果不同，也要setns过去
                    os.setns(pidfd_seefrom, unshrflg(d(pid=1)))

                    PID2, _ = fork(loghead=f'{loghead}F', cut_stdin=True)
                    if PID2 == 0 : # 第二个子进程（孙进程). 与seefrom同pidns
                        mypid = os.getpid()

                        os.setns(pidfd_seefrom, unshrflg(d(mnt=1))) # 先改一次mnt ns ， 等下还要改


                        for lkItem in (bItem.create_links or []) :
                            path = napath(lkItem)
                            symlink(f'/proc/{mypid}/root/{path.lstrip('/')}', path)

                        start_tick=get_start_tick('/proc/self/stat')
                        ns = get_nstypes(f'/proc/self/ns') # 这还不是最终的，还要改

                        ns.mnt = ns_seeto.mnt
                        os.setns(pidfd_seeto, unshrflg(d(mnt=1))) # 在这之后就不可以获得自己的ns或start_tick信息

                        ns.user = OG.userns_unpri.usernsino
                        wlog('subp_start',
                             ready_proc_name=bridge_name ,
                             self_see_pid=mypid,
                             start_tick=start_tick,
                             ns=ns,
                        )
                        close_3ge_fds(keep_fds=[OG.userns_unpri.usernsfd])
                        os.setns(OG.userns_unpri.usernsfd, unshrflg(d(user=1))) # 在这之后无法setns NOTE 在这之前应该关闭重要fd


                        drop_caps(no_textcheck_after_dropcap=True)
                        execvp('sleep', [f"{si.sandbox_name}_{bridge_name}", 'infinity' ])
                        errmsg = f'Bridge exec unsuccessful {bItem}'
                        # wlog('error', errmsg=errmsg) # fd已关闭，无法wlog('error')
                        raise_exit(errmsg, no_cleanup=True)
                    # 第一个子进程
                    # log('First child process exiting')
                    os._exit(0)
                # 原最外层进程
                # log('最外层完成桥的创建')
                os.close(pidfd_seefrom)
                os.close(pidfd_seeto)

    @classmethod
    def find_alive_proc_matching_logitem(cls, elp):
        for proc in get_procs_alive(): # 在存在进程列表中查找，看有没有这个
            if cls.aliveproc_and_elproc_equal(proc, elp):
                return proc
    @classmethod
    def add_keyval_to_procs_record(cls, procsType, key, val): # dict, 不包括alive
        CHK( cls.I_AM_OUTEST, "Only outest can call this, but I_AM_OUTEST is not set")
        CHK(procsType in ['seen', 'heared', 'wdgsee'], 'Unknown procsType')
        # NOTE 必须 既写本cls内部变量，也更新路径文件内容
        getattr(cls, 'procs_'+procsType) [key] = val
        cls.write_procs_info_to_file(procsType)
    @classmethod
    def put_proc_into_seenlist(cls, proc_name, seenProc, logItem):
        cls.add_keyval_to_procs_record('seen', proc_name, seenProc)
        if logItem in cls.logs_should_match_soon: # 上次已经加入了注意名单，现在可以移出注意名单
            log(f'Removing this log from the unrecognized log list {logItem}')
            cls.logs_should_match_soon.remove(logItem)
        if proc_name in si.expected_alive_procs:
            cls.add_keyval_to_procs_record('wdgsee', proc_name, seenProc)
        cls.custom_action_when_procname_seen(proc_name)
    @classmethod
    def got_a_ready_proc_log(cls, logItem): # 被调用时，说明一个进程有了logItem出现
        proc_name = logItem.ready_proc_name
        cls.add_keyval_to_procs_record('heared', proc_name, logItem)
        # 判断这个进程是否已经在aliveProcs的列表里
        if (aliveProc := cls.find_alive_proc_matching_logitem(logItem) ):
            seenProc = cls.conv_to_seenproc(aliveProc, logItem)
            cls.put_proc_into_seenlist(proc_name, seenProc, logItem)
        else: # 不在aliveProcs列表里：1.可能暂时来不及出现，允许等下个周期再出现 2.若已经不是第1个周期，则判断进程死亡
            if proc_name not in si.expected_alive_procs : # 看门狗不用管这个进程
                return
            if logItem not in cls.logs_should_match_soon: # 可能暂时来不及出现，允许等下个周期再出现
                log(f'Adding this log to the unrecognized log list {logItem}')
                cls.logs_should_match_soon.append(logItem)
            else: # 已经不是第1个周期，则判断进程死亡
                log(f'Received message for {proc_name} start, but never found alive. Assume it died')
                sys.exit()
    @classmethod
    def get_and_parse_new_wlog(cls):
        new_logs = WlogReader.readnew()
        for logItem in (cls.logs_should_match_soon + new_logs):
            logItem = dn(logItem)

            if logItem.event == 'error':
                log(f'Received error message from {logItem.logger}: {logItem.errmsg}')
                sys.exit(1)

            if logItem.ready_proc_name :
                cls.got_a_ready_proc_log(logItem)
    @classmethod
    def write_procs_info_to_file(cls, procsType):
        CHK( cls.I_AM_OUTEST, "Only outest can call this, but I_AM_OUTEST is not set")
        CHK(procsType in ['alive', 'seen', 'heared', 'wdgsee'], 'Unknown procsType')
        write_to_fd_override( getattr(cls, 'fd_wr_'+procsType),
            jsondumps_mycompat(getattr(cls, 'procs_'+procsType) ) )
    @classmethod
    def wdg(cls): # 看看那些已经在 procs_wdgsee 列表中的进程还存活吗
        CHK( cls.I_AM_OUTEST, "Only outest can call this, but I_AM_OUTEST is not set")
        cls.update_procsalive()
        cls.get_and_parse_new_wlog()
        for proc_name,psn in dict.items(get_procs_wdgsee()):
            for plv in get_procs_alive():
                if cls.aliveproc_and_seenproc_equal(plv, psn):
                    break
            else:
                log(f'{proc_name} is no longer alive, watchdog terminating sandbox')
                sys.exit()
        OutsideServ.one_loop_task()


def daemon_outest():
    # TODO 等待5秒，等待主app启动的信号，否则退出
    set_proc_dispname(f'{si.sandbox_name}_TSBX_outest_{si.instance_name}'[:15])
    register_sig_handlers(outest=True)

    WlogReader.init()
    OutestProcsMonitor.i_am_outest()

    t0 = time.monotonic()
    while True:
        OutestProcsMonitor.wdg()

        if time.monotonic() >= t0 + (10 if OG.uc.gui not in ['xpra', 'xpra-weston-xwayland'] else 60):
            A = set(dict.keys(get_procs_heared() ))
            B = set(si.expected_alive_procs) # TODO 区分expected_heared_procs , 应用 noWdg=1选项给subprocs
            if not B.issubset(A):
                warn_exit(f'Did not receive startup messages for {list(B-A)} processes within the timeout, assuming sandbox startup was not completely successful')

        if sig_say_exit: OutestProcsMonitor.sbx_exit_broadcast()

        if not exist_childtree(): sys.exit()

        time.sleep(0.2)



lasttick_havechd = 0
lasttick_clipbd = 0
def daemon_pidnsleader():
    global lasttick_havechd , lasttick_clipbd
    CHK( os.getpid() == 1, f"{tlcfg.layer_name} detected its own PID is not 1 (should be 1)")
    PidnsleaderListener.i_am_pidnsleader()
    PERIOD = 0.2
    while True:
        if sig_say_exit: sys.exit()

        if (msg_from_outest := PidnsleaderListener.readmsg_from_outest() ):
            if msg_from_outest.action == 'sbx_exit':
                sys.exit()
            elif msg_from_outest.action == 'run_subp':
                layer_run_subp(no_wait=True,  **msg_from_outest.subpItem )

                if tlcfg.is_mainlyr: # 默认认为收到过的第一个run_subp指令就是mainApp
                    PidnsleaderListener.MainApp_Ever_Started = True

        if tlcfg.is_mainlyr and PidnsleaderListener.MainApp_Ever_Started :
            if not si.idleKeepSbxTime:
                if not exist_childtree() : sys.exit()
            else: # si.idleKeepSbxTime > 0:
                if exist_childtree()  :
                    lasttick_havechd = time.monotonic()
                else:
                    tick_diff = time.monotonic() - lasttick_havechd
                    if tick_diff%1 <= PERIOD: log(f'{int(tick_diff)}/{si.idleKeepSbxTime} Main layer idle, will terminate sandbox if idle for long')
                    if time.monotonic() > lasttick_havechd+si.idleKeepSbxTime: sys.exit()

        for taskItem in (tlcfg.daemon_tasks or []):
            if taskItem.task == 'sync_clipbd' and time.monotonic() > lasttick_clipbd + 1.5: # NOTE 间隔要够大，比其超时时间大
                ClipboardSyncer.one_loop_task()
                lasttick_clipbd = time.monotonic()

        time.sleep(PERIOD)

class PidnsleaderListener():
    I_AM_PIDNSLEADER=None
    MainApp_Ever_Started=False # 是否收到过来自最外层的mainApp的启动命令（仅主层使用）
    @classmethod
    def i_am_pidnsleader(cls):
        cls.I_AM_PIDNSLEADER=True
        cls.oChdSkt = socket.socket(fileno=si.oSkt_fds[tlcfg.layer_name].chd)
    @classmethod
    def readmsg_from_outest(cls):
        ready, _, wrong = select.select([cls.oChdSkt], [], [cls.oChdSkt], 0)
        if wrong: raise_exit('Unknown error while trying to read message from outest')
        elif ready: return d(json.loads( cls.oChdSkt.recv(300_000).decode() ) )

class ClipboardSyncer():
    inited = False
    socket_fromHostLsn = None
    LAST_CONTENT_F = '/sbxdir/temp/ClipboardLastContent.data'
    @classmethod
    def init(cls):
        log(f'ClipboardSyncer initializing')
        cls.socket_fromHostLsn = socket.socket(fileno=si.fd_clipbdWriterFromHostLsn)
        cls.socket_fromHostLsn.setblocking(False) # 设置为非阻塞
        cls.socket_fromHostLsn.listen(1)
        cls.inited = True
    @classmethod
    def one_loop_task(cls): # NOTE 不同方向的内容传递是靠任务间隔比超时时间大来保证不产生竞争
        if not cls.inited: cls.init()
        if not is_unix_socket_listened(f'/tmp/.X11-unix/X{si.newXId}'): return
        # 从主机来的 tcp socket 是否要往沙箱写剪贴板内容
        ready, _, wrong = select.select([cls.socket_fromHostLsn], [], [cls.socket_fromHostLsn], 0) # 非阻塞
        if wrong: log_warn('Unknown error while listening for host write requests to sandbox clipboard')
        elif ready:
            log(f'New connection from host to write to sandbox clipboard')
            pid , _ = fork(loghead=f'{loghead}HostWriteSbxClipbd', proc_dispname='clipbd write',
                           close_fds=True, cut_stdin=True,
                           close_keep_fds=[cls.socket_fromHostLsn.fileno(), OG.userns_unpri.usernsfd],
                           )
            if pid == 0: # 子进程：处理客户端
                os.setns(OG.userns_unpri.usernsfd, unshrflg(d(user=1)))
                try: cls.handle_client_clipbdFromHostSocket()
                except Exception as err: log_warn(err)
                finally: warn_exit('handle_client_clipbdFromHostSocket should have ended its process but did not') #若到这,说明上面未成功退出
            return

        # 如果上面没有return ， 才执行这里
        if not si.sync_clipbd_from_sandbox:
            return
        pid , _ = fork(loghead=f'{loghead}CheckSbxClipbdNewCont', proc_dispname='clipbd read',
                    close_fds=True, cut_stdin=True,
                    close_keep_fds=[OG.userns_unpri.usernsfd ],
                    )
        if pid == 0 : # 子进程：循环从管道读xsel的输出
            os.setns(OG.userns_unpri.usernsfd, unshrflg(d(user=1)))
            try: cls.sync_from_sandbox_to_host()
            except Exception as err: log_warn(err)
            finally: warn_exit('sync_from_sandbox_to_host should have ended its process but did not')  #若到这,说明上面未成功退出
    @classmethod
    def sync_from_sandbox_to_host(cls): # 只有fork出一个子进程后会调用这个. 这个不返回，只结束自己的进程
        if os.getpid() == 1: log_warn('sync_from_sandbox_to_host() called with pid=1, this should not happen') ; print_stack(); return #由于探测到pid=1, 这里返回，不exit
        def timeout_handler(signum, frame):
            warn_exit(f'Timeout while syncing sandbox clipboard to host, giving up', no_cleanup=True)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, 0.5) # 设置超时

        sandbox_clipbd_data = cls.read_clipboard(si.newXId)
        if not isinstance(sandbox_clipbd_data, bytes):
            os._exit(0) # 读回的不是bytes
        if len(sandbox_clipbd_data) == 0:
            os._exit(0) # 成功读回，但沙箱剪贴板是空的


        if is_file(cls.LAST_CONTENT_F): # 有上次的剪贴板内容
            # log('Previous clipboard content file exists')
            if len(sandbox_clipbd_data) == os.path.getsize(cls.LAST_CONTENT_F) \
            and sandbox_clipbd_data == Path(cls.LAST_CONTENT_F).read_bytes():
                # log('Same as last time, ignoring')
                os._exit(0) # 与上次一样
        # 到这里是的确应该 从沙箱 往主机 写剪贴板
        log(f'Sandbox clipboard content updated, syncing to host {sandbox_clipbd_data[:20]}')
        Path(cls.LAST_CONTENT_F).write_bytes(sandbox_clipbd_data)
        cls.write_clipboard(getenv("DISPLAY").lstrip(':'), sandbox_clipbd_data)
        os._exit(0)
    @classmethod
    def read_clipboard(cls, XId) ->bytes|bool: # 这个只应该在fork出一个子进程后调用。它不os._exit, 只返回False或数据
        if os.getpid() == 1: log_warn('read_clipboard() called with pid=1, this should not happen') ; print_stack(); return False
        try:
            proc = subprocess.Popen(
                ['env', f'DISPLAY=:{XId}', 'xsel', '-b', '--output'], bufsize=0,
                preexec_fn=subprocess_preexec, close_fds=True, restore_signals=True,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
            ba = bytearray()
            while True:
                ready, _, wrong = select.select([proc.stdout], [], [proc.stdout], 99) # 超时由之前的signal设置
                if wrong: log_warn('Unknown error while reading from xsel pipe stdout'); return False
                elif ready:
                    try: data = proc.stdout.read(8192)
                    except Exception as err: try_showerr(lambda: proc.kill() ) ; log_warn(err) ; return False
                    if not data: # 已读完
                        try: proc.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            log_warn('Pipe ended, but timeout while waiting for xsel process to exit'); return False
                        if proc.returncode == 0:
                            break
                        else:
                            log_warn(f'xsel failed with return code {proc.returncode}')
                            return False
                    ba.extend(data)
                    if len(ba) > 1_000_000:
                        try_showerr(lambda: proc.kill() )
                        break
            return bytes(ba)
        except Exception as err:
            log_warn(f'Failed to run xsel - {err}')
            return False
    @classmethod
    def write_clipboard(cls, XId, data) ->bool : # 这个只应该在fork出一个子进程后调用。它不os._exit, 只返回真假
        if os.getpid() == 1: log_warn('write_clipboard() called with pid=1, this should not happen') ; print_stack(); return False
        log(f'Send {len(data)} bytes to clipboard :{XId}')
        try:
            proc = subprocess.Popen(
                ['env', f'DISPLAY=:{XId}', 'xsel', '-b', '--input'],
                preexec_fn=subprocess_preexec, close_fds=True, restore_signals=True,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            stdout, stderr = proc.communicate(input=data, timeout=0.5)
            if proc.returncode != 0:
                # 捕获到错误，打印返回码和输出信息
                log_warn(f'xsel failed with return code {proc.returncode}. stdout: "{stdout.decode()}", stderr: "{stderr.decode()}"')
                return False
            return True
        except Exception as err:
            log_warn(f'Failed to run xsel - {err}')
            return False
    @classmethod
    def handle_client_clipbdFromHostSocket(cls): # 只有fork出一个子进程后会调用这个. 这个不返回，只结束自己的进程
        if os.getpid() == 1: log_warn('handle_client_clipbdFromHostSocket() called with pid=1, this should not happen') ; print_stack(); return #由于探测到pid=1, 这里返回，不exit
        def timeout_handler(signum, frame):
            warn_exit(f'Timeout while receiving data, giving up', no_cleanup=True)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, 0.5) # 设置超时
        client_sock, _ = cls.socket_fromHostLsn.accept()
        data = b''
        try:
            while True:
                chunk = client_sock.recv(4096)
                if not chunk: break
                data += chunk
                if len(data) > 1_000_000: log_warn('Truncating overly long clipboard data'); break # 超过 1MB
        except Exception as err: warn_exit(err)
        finally: client_sock.close()
        if data:
            log(f'Syncing clipboard content from host to sandbox {data[:20]}')
            Path(cls.LAST_CONTENT_F).write_bytes(data)
            os._exit(0 if cls.write_clipboard(si.newXId, data) is True else 1)

def D_cont_dn(obj):
    result = D()
    for key,val in enumerate(obj): result[key] = dn(val)
    return result

def get_procs_alive() -> list:
    if OutestProcsMonitor.I_AM_OUTEST:  return OutestProcsMonitor.procs_alive
    else: return [dn(x) in read_all_from_fd_then_jsonloads(si.file_fds.procs_alive) ]

def get_procs_seen():
    if OutestProcsMonitor.I_AM_OUTEST:  return OutestProcsMonitor.procs_seen
    else: return D_cont_dn(read_all_from_fd_then_jsonloads(si.file_fds.procs_seen) )

def get_procs_heared():
    if OutestProcsMonitor.I_AM_OUTEST:  return OutestProcsMonitor.procs_heared
    else: return D_cont_dn(read_all_from_fd_then_jsonloads(si.file_fds.procs_heared) )

def get_procs_wdgsee():
    if OutestProcsMonitor.I_AM_OUTEST:  return OutestProcsMonitor.procs_wdgsee
    else: return D_cont_dn(read_all_from_fd_then_jsonloads(si.file_fds.procs_wdgsee) )


# TODO 清理环境变量
def fork(cut_stdin=False, create_socketpair=False, loghead=None, proc_dispname=None,
         close_fds=False, close_keep_fds=[] ,
         set_fds_CLOEXEC=False, CLOEXEC_keep_fds=[]
         ):
    sktpair = None
    if create_socketpair:
        sktpair = TmpSocketPair()
        set_fd_keep_on_exec(sktpair._skt_chd.fileno(), False)
        set_fd_keep_on_exec(sktpair._skt_pa .fileno(), False)
    sys.stdout.flush() ; sys.stderr.flush()
    pid = os.fork()
    CHK(pid >= 0, 'fork failed')
    if pid == 0 : # 子进程
        unreg_cleanup_func()
        unregister_sig_handlers()
        if close_fds:
            if create_socketpair: close_keep_fds += [sktpair._skt_chd.fileno() ]
            close_3ge_fds(keep_fds=close_keep_fds)
        if set_fds_CLOEXEC: set_3ge_fds_cloexec(keep_fds=CLOEXEC_keep_fds)
        if cut_stdin:
            devnull = os.open('/dev/null', os.O_RDWR)
            os.dup2(devnull, 0)
            os.close(devnull)
            os.setsid()
            # os.setpgid(0, 0)
        if loghead is not None: set_loghead(loghead)
        if proc_dispname is not None: set_proc_dispname(proc_dispname)
        if create_socketpair: sktpair.i_am_chd()
    else: # 原进程
        if create_socketpair: sktpair.i_am_pa()
    return pid, sktpair

whoCleanupRegister = None
def reg_cleanup_func(cleanup_func):
    global whoCleanupRegister
    if not whoCleanupRegister is None: raise_exit('Cleanup function already registered', no_cleanup=True)
    whoCleanupRegister = (os.getpid(), get_nstypes('/proc/self/ns').pid)
    atexit.register(cleanup_func)
def unreg_cleanup_func():
    global whoCleanupRegister
    atexit._clear()
    whoCleanupRegister = None
def isMeThatRegedCleanup(): # TODO 把stat里的时间也加入要素
    if (os.getpid(), get_nstypes('/proc/self/ns').pid) == whoCleanupRegister : return True
    else: log_warn('I am not the process that registered cleanup function. Cleanup function might not unregistered in time'); return False

cleanup_symlinks_to_rm = set()
def cleanup_outest():
    atexit._clear()
    if not isMeThatRegedCleanup(): return
    if os.getpid() == 1: return
    log(f"About to exit, waiting for all child processes to finish, before cleanup...")
    try_showerr(lambda: Path(f'{si.outest_sbxdir}_exit').touch() ) # 设个正在退出的标记
    try_showerr(lambda: Path(f'{si.outest_sbxdir}/EXITING').touch() )
    try_pass(lambda: OutsideServ.skt_OServLsn.close() )
    # if OG and OG.layer1_pid: try_pass(lambda: os.setpgid(OG.layer1_pid, 0) )
    try_pass(lambda: OutestProcsMonitor.sbx_exit_broadcast())

    cleanup_startat = time.monotonic()
    while time.monotonic() <= cleanup_startat+5:
        time.sleep(0.1)
        if not exist_childtree() : break
    else: log_warn('Child processes did not exit within timeout. Sandbox management process exiting first')

    for slkItem in cleanup_symlinks_to_rm:
        if Path(slkItem).is_symlink() :
            linkto = os.readlink(slkItem)
            if linkto == si.outest_sbxdir or linkto.startswith(f'{si.outest_sbxdir}/'):
                try_showerr(lambda: Path(slkItem).unlink() )

    if si.nocleanup:
        return

    # NOTE 不要对那些可能挂载的目录用递归删除!  # 要删除那种目录的话只能用 rmdir （只删空的目录）
    # 因为有挂载，递归删除可能会误删重要文件。危险！ # 例如:
        # new.*.rootfs/
        # apps/*/
    paths_rm_sub_files = [ #准备删这些目录的一级子文件和目录本身
        *glob(f'{si.outest_sbxdir}/temp'),
        *glob(f'{si.outest_sbxdir}/apps'),
        *glob(f'{si.outest_sbxdir}/new.*.rootfs'),
        *glob(f'{si.outest_sbxdir}'),
    ]
    def safe_call(f):
        try: return f()
        except Exception as err: print_exc(); return []
    for dirpath in paths_rm_sub_files:
        for f in safe_call(lambda: Path(dirpath).iterdir() ):
            if is_file(f) or f.is_symlink() or f.is_socket():
                try_showerr(lambda: f.unlink() )
        try_showerr(lambda: os.rmdir(dirpath) )

    if exist_childtree(): log_warn('cgroup directory for this sandbox instance not cleaned up')
    else:
        try:
            Path(f'{si.CG_TSBXS}/cgroup.procs').write_text(str(os.getpid()))
            os.rmdir(si.CG_SBX)
        except Exception as err:
            log_warn(err)
    try_pass(lambda: os.rmdir(si.sharedir_onhost))

    if not os.path.lexists(si.outest_sbxdir): os.unlink(f'{si.outest_sbxdir}_exit') # 清除正在退出标记

def cleanup_pidnsleader():
    atexit._clear()
    if not isMeThatRegedCleanup(): return
    if os.getpid() != 1 : log_warn("pid != 1. Only the leader process should run this cleanup function"); return
    for u in range(3):
        if not exist_childtree(): break
        os.kill(-1, signal.SIGTERM)
        for i in range(10):
            if (clear := not exist_childtree()): break
            time.sleep(0.1)
        if clear: break
    else:
        os.kill(-1, signal.SIGKILL)


def unregister_sig_handlers():
    for signum in signal.valid_signals():
        if signum not in (signal.SIGKILL, signal.SIGSTOP):
            signal.signal(signum, signal.SIG_DFL)

# NOTE HUP < INT < TERM 退出强烈程度 # TODO SIGHUP 是关闭终端窗口时的信号 ，由用户配置决定外层动作
SIGS_TO_IGN = []
SIGS_TO_PASSBY = [signal.SIGINT, signal.SIGHUP, signal.SIGUSR1, signal.SIGUSR2, signal.SIGTSTP]
SIGS_TO_HANDLE = SIGS_TO_PASSBY + [signal.SIGTERM, signal.SIGCHLD]
def register_sig_handlers(outest=False, pidnsleader=False):
    for sig in SIGS_TO_IGN:     signal.signal(sig, signal.SIG_IGN)
    if pidnsleader:
        for sig in SIGS_TO_HANDLE:  signal.signal(sig, signals_handler_pidnsleader)
    if outest:
        for sig in SIGS_TO_HANDLE:  signal.signal(sig, signals_handler_outest)
def signals_handler_outest(signum, frame):
    _signals_handler(signum, is_outest=True)
def signals_handler_pidnsleader(signum, frame):
    _signals_handler(signum)

sig_say_exit = False
def _signals_handler(signum, is_outest=False):
    # NOTE 不能print 不能sleep 不能sys.exit . 只能 os._exit ， 但不要os._exit, 设置should_exit)
    global sig_say_exit
    if signum in SIGS_TO_PASSBY:
        pass # TODO
    elif signum == signal.SIGTERM:
        sig_say_exit = True
    elif signum == signal.SIGCHLD:
        while True:
            try:
                # -1 表示等待任意子进程 # os.WNOHANG 表示非阻塞：如果没有可回收的子进程，立即返回 (0, 0)
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0: break  # 没有进程退出, 可能是子进程被暂停（STOP）触发的SIGCHLD，我们忽略它，也可能已经处理完了僵尸
            except ChildProcessError:
                if not tlcfg.is_mainlyr or not si.idleKeepSbxTime: sig_say_exit = True ;
                break


def exist_childtree(): # 不需要自己pid=1也可以用
    try:
        pid, status = os.waitpid(-1, os.WNOHANG)
        return True
    except ChildProcessError:
        return False


# os.waitpid(-1, os.WNOHANG) 的结果说明：
#     (child_pid, exit_status)	成功回收一个僵尸进程
#     (0, 0)	无僵尸可回收，但子进程仍存在
#     抛出 ChildProcessError（继承自 OSError	errno = ECHILD（No child processes） 值通常为 10 ）


def lines_add_prefix(text):
    prefix = f'[ {loghead} ]' if loghead else ''
    return ''.join( [prefix + l for l in text.splitlines(True)] )
def print_exc(*args): # 替代原 traceback.print_exc()
    sio = io.StringIO()
    traceback.print_exc(*args, file=sio)
    print( lines_add_prefix(sio.getvalue()) , file=sys.stderr)
def print_stack(*args): # 替代原 traceback.print_stack()
    sio = io.StringIO()
    traceback.print_stack(*args, file=sio)
    print( lines_add_prefix(sio.getvalue()) , file=sys.stderr)

def custom_excepthook(*args):
    tb_str = "".join(traceback.format_exception(*args))
    print( lines_add_prefix(tb_str) , file=sys.stderr)

_print = print
def print(*args, **kwargs):
    try:
        _print(*args, **kwargs)
        sys.stdout.flush() ; sys.stderr.flush()
    except: pass
loghead = ''
def set_loghead(new_loghead):
    global loghead
    loghead = new_loghead.rstrip(': ') + ': '
    sys.excepthook = custom_excepthook
def log(*args, **kwargs):
    new_args = args
    if loghead: new_args = ( loghead,  *args)
    print(*new_args, **kwargs)
def log_warn(*args, **kwargs):
    if 'file' not in kwargs: kwargs['file'] = sys.stderr
    log('WARNING: ',  *args, **kwargs)

def wlog(event, me_proc_info=False, **kw_args) :
    if not (si and si.file_fds and si.file_fds.layerslog_a): return False
    kw_args = d(kw_args)
    if kw_args.errmsg: event = 'error' ; kw_args.errmsg=str(kw_args.errmsg)
    logObj = d(
        logger = loghead or tlcfg.layer_name if tlcfg else '',
        event = event,
        **kw_args
    )
    if me_proc_info:
        logObj.self_see_pid=os.getpid()
        logObj.start_tick=get_start_tick('/proc/self/stat')
        logObj.ns = get_nstypes(f'/proc/self/ns')
    try:
        fcntl.flock(si.file_fds.layerslog_a, fcntl.LOCK_EX)
        os.write(si.file_fds.layerslog_a, ''.join([json.dumps(logObj), '\n\n']).encode())
    except Exception as err:
        print_exc()
    finally:
        fcntl.flock(si.file_fds.layerslog_a, fcntl.LOCK_UN)


class WlogReader():
    wlogf = None
    @classmethod
    def init(cls):
        cls.wlogf = open(f'{si.outest_sbxdir}/events.layers.log', 'r')
    @classmethod
    def _read(cls):
        try:
            fcntl.flock(cls.wlogf.fileno(), fcntl.LOCK_EX)
            return cls.wlogf.read()
        finally:
            fcntl.flock(cls.wlogf.fileno(), fcntl.LOCK_UN)
    @classmethod
    def readnew(cls) -> list:
        new_logs = []
        for line in cls._read().splitlines():
            if not line.strip(): continue
            new_logs.append(json.loads(line))
        return new_logs

def jsondumps_mycompat(obj):
    if isinstance(obj, dict):
        json_str = '\n'.join(['{',
            '\n,\n'.join([f'"{k}" : {json.dumps(v)}' for k,v in dict.items(obj) ]) ,
            '}'])
    elif isinstance(obj, list):
        json_str = '\n'.join(['[', '\n,\n'.join([json.dumps(x) for x in obj]) ,']'])
    else: json_str = json.dumps(obj)
    return json_str


# TODO def get_pUniqId()
def get_nstypes(nsdir_path):
    return D({nstype:os.stat(f'{nsdir_path}/{nstype}').st_ino for nstype in os.listdir(nsdir_path)})

def get_start_tick(statfile_path): # 返回的是字符串，不是数字
    return Path(statfile_path).read_text().split(') ')[-1].split(' ')[22-1-2]  # stat文件里的第22个字段是进程开始时间（cpu tick）， 去掉前两个字段

def get_NSpid_arr(status_file_path) -> list:
    for line in Path(status_file_path).read_text().splitlines():
        if line.startswith("NSpid:"):
            return [int(x) for x in line.split()[1:]]

def get_pinfo_by_pidpath(pidpath):
    try:
        res = D()
        inode1 = os.stat(pidpath).st_ino
        res.comm = Path(f'{pidpath}/comm').read_text().strip()
        res.NSpid = get_NSpid_arr(f'{pidpath}/status')
        res.start_tick = get_start_tick(f'{pidpath}/stat')
        try:    res.ns = get_nstypes(f'{pidpath}/ns')
        except: res.ns = dn()
        res.cmdvec = Path(f'{pidpath}/cmdline').read_text().strip('\x00').split('\x00')
        inode2 = os.stat(pidpath).st_ino
        if inode1 != inode2: return None
        return res
    except: return None

ps1 = ">"
def set_ps1(status):
    global ps1
    ps1 = ''.join( [
        r'''$(LEC=$? ; if [[ $LEC -ne 0 ]]; then echo -n '\[\e[0;91m\]' ; else echo -n '\[\e[0;94m\]' ; fi ; printf "(%3d)" $LEC ; echo -n '\[\e[0m\]' ) \[\e[1;93m\]'''
        ,
        f'{si.sandbox_name} {tlcfg.layer_name} {status}',
        r''' | \w ''',
        r'''$(if [[ "$(id -u)" == "0" ]];then echo -n '#' ; else echo -n '>'; fi )''',
        r'''\[\e[0m\] '''
    ])
    os.environ['PS1'] = ps1


UNSHR_MAP = types.SimpleNamespace( pid='PID', mnt='NS', user='USER', cgroup='CGROUP', ipc='IPC', time='TIME', uts='UTS', net='NET', )
def lyrcfg_to_unshrcfg(lyrcfg):
    unshr_cfg = d({k.removeprefix('unshare_'):v for k,v in dict.items(lyrcfg) if k.startswith('unshare_')})
    for x in dict.keys(unshr_cfg): CHK(x in UNSHR_MAP.__dict__.keys(), f'This unshare flag is unknown: {x}')
    return unshr_cfg
def unshrflg(unshr_cfg):
    unshr_flg = 0
    for k,v in dict.items(unshr_cfg):
        if v: unshr_flg |= os.__dict__['CLONE_NEW' + UNSHR_MAP.__dict__[k]]
    return unshr_flg


class TmpSocketPair:
    def __init__(self):
        self._skt_chd, self._skt_pa = socket.socketpair()
        set_fd_keep_on_exec(self._skt_chd.fileno(), False)
        set_fd_keep_on_exec(self._skt_pa.fileno(), False)
        self.I_AM_PA = False ; self.I_AM_CHD = False
    def i_am_pa(self):
        CHK(not self.I_AM_CHD, "Already set as child's end of pipe")
        self._skt_chd.close() ; self.I_AM_PA = True
    def i_am_chd(self):
        CHK(not self.I_AM_PA, "Already set as parent's end of pipe")
        self._skt_pa.close() ; self.I_AM_CHD = True
    def pa_send(self, data):
        CHK(self.I_AM_PA, "Called not by the parent process of fork")
        if isinstance(data, BS): data = data.value
        self._skt_pa.send(data)
    def chd_send(self, data):
        CHK(self.I_AM_CHD, "Called not by the child process of fork")
        if isinstance(data, BS): data = data.value
        self._skt_chd.send(data)
    def pa_recv(self, byte_cnt, timeout, expect_data=None):
        CHK(select.select([self._skt_pa], [], [], timeout)[0], "Parent process of fork timed out waiting for signal from child")
        if isinstance(expect_data, BS): expect_data = expect_data.value
        data = self._skt_pa.recv(byte_cnt)
        if expect_data is not None: CHK(data == expect_data, f"Parent process of fork received an unexpected signal: got {data!r}, expect {expect_data!r}")
        return data
    def chd_recv(self, byte_cnt, timeout, expect_data=None):
        CHK(select.select([self._skt_chd], [], [], timeout)[0], "Child process of fork timed out waiting for signal from parent")
        if isinstance(expect_data, BS): expect_data = expect_data.value
        data = self._skt_chd.recv(byte_cnt)
        if expect_data is not None: CHK(data == expect_data, f"Child process of fork received an unexpected signal: got {data!r}, expect {expect_data!r}")
        return data
    def close(self):
        if self.I_AM_PA  and self._skt_pa:  self._skt_pa.close() ;  self._skt_pa = None
        if self.I_AM_CHD and self._skt_chd: self._skt_chd.close() ; self._skt_chd = None



class BS(enum.Enum): # fork前后父子进程之间通信用的，以及 最外层和内层之间通信用的单字节信号
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return bytes([count])  # 或者 bytes([count & 0xFF]) 防止溢出
    SetMeUidRoot = enum.auto()
    SetYouUidRootDone = enum.auto()
    SetMeUidUser = enum.auto()
    SetYouUidUserDone = enum.auto()
    IChdBorn = enum.auto()
    YouChdGo = enum.auto()



def set_fd_keep_on_exec(fd:int, keep:bool):
    if keep: new_fdflag = fcntl.fcntl(fd, fcntl.F_GETFD) & (~fcntl.FD_CLOEXEC)
    else:    new_fdflag = fcntl.fcntl(fd, fcntl.F_GETFD) | fcntl.FD_CLOEXEC
    fcntl.fcntl(fd, fcntl.F_SETFD, new_fdflag)


def read_alltext_from_fd(fd:int) -> str:
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        return os.pread(fd, os.fstat(fd).st_size, 0).decode()
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)

def read_all_from_fd_then_jsonloads(fd) -> list|dict :
    return json.loads( read_alltext_from_fd(fd) )

def write_to_fd_override(fd:int, text:str):
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.ftruncate(fd, 0)
        os.pwrite(fd, text.encode(), 0)
    finally:
        fcntl.flock(fd,  fcntl.LOCK_UN)

def get_all_3ge_fds() -> list:
    CHK( os.fstat(si.fdnull).st_ino == os.stat('/dev/null').st_ino, 'si.fdnull st_ino does not match /dev/null')
    CHK( os.fstat(si.fdnull).st_dev == os.stat('/dev/null').st_dev, 'si.fdnull st_dev does not match /dev/null')
    soft_limit, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
    result = []
    for fd in range(3, soft_limit): # 可以包括fdnull自己，因为dup2自己也没问题
        try:
            fcntl.fcntl(fd, fcntl.F_GETFD)
            result.append(fd)
        except OSError as e:
            if e.errno != errno.EBADF: raise
    return result

def set_3ge_fds_cloexec(keep_fds=[] , action='default'):
    if action == 'default': KEEP=False
    elif action == 'keepall' : KEEP=True
    for fd in get_all_3ge_fds() :
        if fd in keep_fds:
            continue
        try: set_fd_keep_on_exec(fd, KEEP)
        except OSError as e:
            # 9 错误 EBADF 错误表示可能已关闭 （Bad file descriptor）
            if e.errno == 9: pass; #  log_warn(f'尝试设置{fd=}为CLOEXEC但发现刚刚已被关闭')
            else: raise


def close_3ge_fds(keep_fds=[] ):
    for fd in get_all_3ge_fds() :
        if fd in keep_fds:
            continue
        # log(f'Closing {fd=}')
        try:
            os.dup2(si.fdnull, fd) # 不用os.close
            set_fd_keep_on_exec(fd, False)
        except OSError as e:
            # 9 错误 EBADF 错误表示可能已关闭 （Bad file descriptor）
            if e.errno == 9: pass; # log_warn(f'尝试关闭{fd=}但发现刚刚已被关闭')
            else: raise




def run_a_cmd(cmdv, print_output=False):
    prc = subprocess.Popen(cmdv,
            preexec_fn=subprocess_preexec, close_fds=True, restore_signals=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            text=True, bufsize=1, universal_newlines=True,
        )
    stdout_data, _ = prc.communicate()
    # prc.wait()
    if print_output: log(stdout_data)
    if prc.returncode != 0: raise_exit(f"Command was not successful (return code {prc.returncode}) {stdout_data}")

def subprocess_preexec():
    unreg_cleanup_func()
    unregister_sig_handlers()
    set_pdeathsig(signal.SIGKILL)

libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)

def set_nonewpriv(doprint=False):
    PR_SET_NO_NEW_PRIVS = 38
    ret = libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
    errno = ctypes.get_errno() if ret != 0 else None
    errstr = os.strerror(errno) if ret != 0 else None
    log('Setting noNewPrivs', (ret, errno, errstr)) if doprint else None
    return (ret, errno, errstr)

def drop_caps(no_textcheck_after_dropcap=False):
    PR_GET_NO_NEW_PRIVS = 39
    PR_CAPBSET_DROP = 24
    PR_CAPBSET_READ = 23
    PR_CAP_AMBIENT = 47
    PR_CAP_AMBIENT_CLEAR_ALL = 4
    CAP_SETPCAP = 8

    class CapHeader(ctypes.Structure):
        _fields_ = [("version", ctypes.c_uint32), ("pid", ctypes.c_int)]
    cap_hdr = CapHeader(version=0x20080522, pid=0)

    class CapData(ctypes.Structure):
        _fields_ = [ ("effective", ctypes.c_uint32 * 2), ("permitted", ctypes.c_uint32 * 2), ("inheritable", ctypes.c_uint32 * 2), ]

    def get_caps_dict():
        status_text = Path("/proc/self/status").read_text()
        cap_fields = {}
        for cap_field in ["CapInh", "CapPrm", "CapEff", "CapBnd",  "CapAmb", "NoNewPrivs" ]:
            pattern = rf"^{cap_field}:\s*(\S+)"
            match = re.search(pattern, status_text, re.MULTILINE)
            cap_fields[cap_field] = match.group(1)
        return cap_fields

    def capset_clear(eff=False, prm=False, inh=False,  doprint=False):
        cap_data = CapData()
        for i in range(2):
            cap_data.effective[i] = 0    if eff else 0xffffffff
            cap_data.permitted[i] = 0    if prm else 0xffffffff
            cap_data.inheritable[i] = 0  if inh else 0xffffffff
        ret = libc.capset(ctypes.byref(cap_hdr), ctypes.byref(cap_data) )
        errno = ctypes.get_errno() if ret != 0 else None
        errstr = os.strerror(errno) if ret != 0 else None
        log(f"Clearing capability sets {eff=} {prm=} {inh=}", (ret, errno, errstr)) if doprint else None
        return (ret, errno, errstr)

    def amb_clear(doprint=False):
        ret = libc.prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL, 0, 0, 0)
        errno = ctypes.get_errno() if ret != 0 else None
        errstr = os.strerror(errno) if ret != 0 else None
        log('Clearing amb', (ret, errno, errstr)) if doprint else None
        return (ret, errno, errstr)

    def bnd_clear(maxid, doprint=False):
        results = []
        for cap_id in range(maxid + 1):
            ret = libc.prctl(PR_CAPBSET_DROP, cap_id, 0, 0, 0)
            errno = ctypes.get_errno() if ret != 0 else None
            errstr = os.strerror(errno) if ret != 0 else None
            results.append((ret, errno, errstr))
        log('Clearing bnd', results) if doprint else None
        return results



    show_clear_result = False
    capset_clear(eff=False , prm=True, inh=True,  doprint=show_clear_result)
    amb_clear(doprint=show_clear_result)
    set_nonewpriv(doprint=show_clear_result)
    bnd_clear(si.BND_MAX,  doprint=show_clear_result)
    capset_clear(eff=True, prm=True, inh=True,  doprint=show_clear_result)

    # ------验证------------

    # libc验证 no_new_privs
    CHK( libc.prctl(PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0) == 1, 'noNewPrivs clear verification failed')
    # libc验证 bounding set
    for cap_id in range(si.BND_MAX +1): # 内核只支持0~40
        CHK( libc.prctl(PR_CAPBSET_READ, cap_id, 0, 0, 0) == 0, f'cap_id {cap_id} capability drop failed')

    if no_textcheck_after_dropcap:
        return

    # 验证 /proc/self/status 中所有能力字段为 0
    caps_dict = get_caps_dict()
    CHK( caps_dict.pop('NoNewPrivs') == '1' , "NoNewPrivs not successfully set as shown in /proc" ) # 用pop不用get
    for k,v in caps_dict.items(): CHK( re.search(rf"^0+$", v), f"Clearing failed for {k} as shown in /proc ")


def pivot_root(new_root, put_old):
    res = libc.pivot_root(ctypes.c_char_p(new_root.encode()), ctypes.c_char_p(put_old.encode()))
    if res != 0:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno))


MS = types.SimpleNamespace(RDONLY=0x01, NOSUID=0x02, NODEV=0x04, NOEXEC=0x08,  REMOUNT=0x20, NOSYMFOLLOW=0x100, BIND=0x1000, MOVE=0x2000, REC=0x4000,  UNBINDABLE=1<<17, PRIVATE=1<<18, SLAVE=1<<19, SHARED=1<<20, )
def mount(source, target, fstype, flags, data): # source可能空, 或为tmpfs或proc， target一定有
    allowed_nonabs = ['tmpfs', 'proc', 'devpts', 'overlay']
    if not ( (source is None) or (source in allowed_nonabs) or (source.startswith('/')) ):
        raise_exit(f"Mount source {source} is not an absolute path, and not in allowed {allowed_nonabs}")
    if isinstance(source, str) and source.startswith('/'):
        source = napath(source)
    target = napath(target)
    if source and source.startswith('/') and rslvy(source) != source:
        raise_exit(f"Mount source path {source} or one of its parent directories is currently a symlink. Handling for this case not yet implemented")
    if rslvy(target) != target:
        raise_exit(f"Mount target path {target} or one of its parent directories is currently a symlink. Handling for this case not yet implemented")
    # log(f"Executing mount {source} --> {target}")
    ret = libc.mount(
        source.encode() if source else None,
        target.encode(),
        fstype.encode() if fstype else None,
        flags,
        data.encode() if data else None
    )
    if ret != 0:
        log(f"Error during mount {source} -> {target} | {fstype=} {flags=} {data=}")
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno), target)

def mount_overlayfs(lowerdir, upperdir, workdir, target, flags=0):
    def pathEscape(p: str) -> str:
        p = napath(p)
        return p.replace("\\", "\\\\") .replace(",", "\\,") .replace(":", "\\:")

    upperdir = pathEscape(upperdir)
    workdir = pathEscape(workdir)

    if isinstance(lowerdir, list): # lowerdir 是数组
        lowerdir = [pathEscape(x) for x in lowerdir]
    else: # lowerdir不是数组
        lowerdir = [pathEscape(lowerdir) ]
    joined_lowerdir = ':'.join(lowerdir)

    mount('overlay', target, 'overlay', flags=flags,
          data=f"lowerdir={joined_lowerdir},upperdir={upperdir},workdir={workdir}"
          )


MNT = types.SimpleNamespace(FORCE=1, DETACH=2, EXPIRE=4, NOFOLLOW=8) # 缷载（umount2)可能用到的常数
def umount(target, flags=0):
    ret = libc.umount2(
        target.encode(),
        flags
    )
    if ret != 0:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno), target)

mntflag_newrootfs = MS.NODEV | MS.NOSUID
mntflag_proc = MS.NODEV|MS.NOSUID|MS.NOEXEC
mntflag_newsbxdir = MS.NODEV|MS.NOSUID
mntflag_apps = MS.NODEV|MS.NOSUID
mntflag_sbxtemp = MS.NOSUID|MS.NODEV
mntflag_binddir = MS.BIND|MS.REC|MS.NOSUID
mntflag_tmpfs = MS.NOSUID|MS.NODEV # 这里设置nodev也会让/dev有nodev,但因为每个具体的设备是bind进去的，所以好像没问题


def set_pdeathsig(sig): # 由layer1的fork出来的子进程调用, 让真实父进程退出后沙箱内能够收到TERM信号
    PR_SET_PDEATHSIG = 1
    libc.prctl(PR_SET_PDEATHSIG, sig)

def set_proc_dispname(dispname):
    PR_SET_NAME = 15
    CHK( len(name_bytes := dispname.encode("utf-8")) <= 15 , f"Process name {dispname} exceeds 15 bytes")
    libc.prctl(PR_SET_NAME, name_bytes, 0, 0, 0)


def get_appimg_sqoffset(appimg_path):
    with open(appimg_path, 'rb') as f: elfHeader = f.read(64)
    (bitness,endianness) = struct.unpack("4x B B 58x", elfHeader);
    (shoff,shentsize,shnum) = struct.unpack(
        (">" if endianness == 2 else "<") +
        ("40x Q 10x H H 2x" if bitness == 2 else "32x L 10x H H 14x"),
        elfHeader
    );
    return (shoff + shentsize * shnum)


def napath(pstr):
    pstr = str(pstr)
    if not str(pstr.startswith('/')): raise_exit(f"Not an absolute path: {pstr}")
    return  ''.join( [ '/' , os.path.normpath(pstr).strip('/') ] )

def which_and_resolve_exist(cmd):
    path = shutil.which(cmd)
    if not path:
        return None
    try:
        return rslvy(path)
    except FileNotFoundError:
        return None

def rslvn(path):
    return str(Path(napath(path)).resolve(strict=False))

def rslvy(path):
    return str(Path(napath(path)).resolve(strict=True))

def getenv(env_var_name, allow_no=False):
    r = os.getenv(env_var_name, None)
    if not allow_no:
        CHK ( r is not None, f'No Environment variable {env_var_name}')
    if r is None: r = ''
    return r

def padir(path):
    if napath(path) == '/': raise_exit(f"{path} is already the root path, cannot get parent directory")
    return str(Path(path).parent)

def is_file(path):
    return not Path(path).is_symlink() and Path(path).is_file()
def is_dir(path):
    return not Path(path).is_symlink() and Path(path).is_dir()
def is_blockdev(path):
    return not Path(path).is_symlink() and Path(path).is_block_device()
def is_chardev(path):
    return not Path(path).is_symlink() and Path(path).is_char_device()
def is_dev(path):
    return is_chardev(path) or is_blockdev(path)
def is_fifo(path):
    return not Path(path).is_symlink() and Path(path).is_fifo()
def is_socket(path):
    return not Path(path).is_symlink() and Path(path).is_socket()
def is_ro(path):
    return os.statvfs(path).f_flag & MS.RDONLY

def is_XId_available(newXId):  # TODO 搞清楚xpra在run里面创建什么与XID有关的文件，也检查它们
    if  not os.path.lexists(f'/tmp/.X11-unix/X{newXId}')  \
    and not os.path.lexists(f'{getenv("XDG_RUNTIME_DIR")}/wayland-{newXId}')  \
    and not re.search(rf':{newXId}(?:\.|$)', getenv('DISPLAY')) \
    and not getenv('WAYLAND_DISPLAY',allow_no=True) == f'wayland-{newXId}' \
    and not re.search(rf'\/tmp/\.X11-unix\/X{newXId}\b', Path('/proc/net/unix').read_text(), re.MULTILINE) :
        return True
    else: return False


def is_unix_socket_listened(sock_path):
    if not os.path.exists(sock_path):
        return False
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(sock_path)
        sock.close()
        return True
    except (FileNotFoundError, ConnectionRefusedError):
        sock.close()
        return False
    finally:
        sock.close()

def mkdirp(dirpath):
    os.makedirs(dirpath, exist_ok=True)

def make_file_exist(path): # 路径不能已有目录
    if is_dir(path): raise_exit(f"{path} is already a directory")
    if not os.path.exists(path):
        mkdirp(Path(path).parent)
        Path(path).touch()

def symlink(linkto, dest):  # linkto：要创建的软链的指向 .  dest: 在哪个位置创建软链。
    if Path(dest).is_symlink() and Path(dest).readlink() == linkto: return
    mkdirp(Path(dest).parent)
    os.symlink(linkto, dest)


class EnhancedFalse:
    def __init__(self, dictObj, keyName):
        self.dictObj = dictObj
        self.keyName = keyName
    def _error(self):
        raise_exit(f"Program tries to stringlize or compare a non-defined member '{self.keyName}' of a dict-like obj: {str(self.dictObj)[:200]} ...")
    def __str__(self):
        self._error()
    def __repr__(self):
        self._error()
    def __bool__(self):
        return False
    def __eq__(self, other):
        return False
    def __ne__(self, other):
        return True
    def __lt__(self, other):
        self._error()
    def __le__(self, other):
        self._error()
    def __gt__(self, other):
        self._error()
    def __ge__(self, other):
        self._error()
    __hash__ = None


class EnhancedDictTempl(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, value in self.items():
            if isinstance(value, dict) and not isinstance(value, type(self)):
                self[key] = type(self)(value)
            elif isinstance(value, list):
                self[key] = self._convert_list(value)
    def _convert_list(self, lst):
        new_list = []
        for item in lst:
            if isinstance(item, dict) and not isinstance(item, type(self)):
                new_list.append(type(self)(item))
            elif isinstance(item, list):
                new_list.append(self._convert_list(item))
            else: new_list.append(item)
        return new_list
    def __setattr__(self, name, value):
        self[name] = value
    def __delattr__(self, name):
        try: del self[name]
        except KeyError: pass
    def __setitem__(self, key, value):
        processed_value = value
        if isinstance(value, dict) and not isinstance(value, type(self)):
            processed_value = type(self)(value)
        elif isinstance(value, list):
             processed_value = self._convert_list(value)
        super().__setitem__(key, processed_value)
class Dict(EnhancedDictTempl):
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        try: return self[name]
        except :
            raise
class DictFALSE(EnhancedDictTempl):
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"): raise AttributeError(name)
        try: return self[name]
        except KeyError:
            return EnhancedFalse(self, name)
    def __getitem__(self, key):
        try: return super().__getitem__(key)
        except KeyError:
            return EnhancedFalse(self, key)
class DictNone(EnhancedDictTempl):
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        try: return self[name]
        except :
            return None
    def __getitem__(self, key):
        try: return super().__getitem__(key)
        except KeyError:
            return None
D = Dict  # Raises an error when trying to access a non-existent key.
d = DictFALSE  # Returns EnhancedFalse when trying to access a non-existent key.
dn = DictNone  # Returns None when trying to access a non-existent key.


def eq_ignore_order(v1, v2):
    if type(v1) != type(v2): return False
    if isinstance(v1, dict): return v1.keys() == v2.keys() and all(eq_ignore_order(v1[k], v2[k]) for k in v1)
    if isinstance(v1, list): return len(v1) == len(v2) and sorted(v1, key=str) == sorted(v2, key=str)
    return v1 == v2


def hash_blake2b(in_str):
    return hashlib.blake2b(in_str).hexdigest()


def try_pass(func):
    try:    return func()
    except: pass

def try_showerr(func):
    try:
        return func()
    except Exception as err:
        print_exc()

def warn_exit(err_msg, no_cleanup=False):
    print(loghead + err_msg, file=sys.stderr)
    if not no_cleanup:
        sys.exit(1)
    else: os._exit(1)
def raise_exit(err_msg, no_cleanup=False):
    print_stack()
    try_pass(lambda: wlog('error', errmsg=err_msg) )
    warn_exit(err_msg, no_cleanup)

def CHK( condition, errmsg='Some check failed', action='raise_exit'):
    if not condition:
        if action == 'raise_exit': raise_exit(errmsg)
        elif action == 'warn': log_warn(f"{errmsg}")

ASK_OPEN='''\
#!/bin/bash
tried_cmd="$0"
input_arguments="$@"
title_text="Some program tried to execute"
message_text="Some program tried to execute a command:\n$tried_cmd\nwith arguments passed as follows:"
echo "$title_text $0 $input_arguments"
if [[ ! -n "$input_arguments" ]]; then exit ; fi
if [[ ! -n "$DISPLAY" ]]; then exit ; fi
if command -v kdialog &> /dev/null; then
    kdialog --title "$title_text" --textinputbox "$message_text" "$input_arguments"
elif command -v zenity &> /dev/null; then # zenity --text-info or --entry
    echo -e "$message_text\n\n$input_arguments" | zenity --text-info --title "$title_text" --editable --filename=/dev/stdin
else
    echo "Neither kdialog nor zenity installed, cannot show dialog"
fi
'''

ICEWM_WINOPTIONS='''
.ignorePositionHint: 1
'''

# NOTE 不要启用icewm的启动器、程序菜单等，因为那样所启动的程序与沙箱的主层不是同一个pidns
ICEWM_PREF='''
TaskBarEnableSystemTray=1
TaskBarShowTray=1
ToolTipIcon=1
ShowSysTray=1
ShowTaskBar=1

ShowStartMenu=0
ShowLogoutMenu=0
ShowSettingsMenu=0
ShowRun=0

TaskBarShowStartMenu=0
TaskBarShowClock=0
TaskBarShowCPUStatus=0
TaskBarShowMEMStatus=0
TaskBarShowMailboxStatus=0
TaskBarShowBatteryStatus=0
TaskBarShowNetStatus=0
TaskBarShowAPMStatus=0

WorkspaceNames="1"
TaskBarShowWorkspaces = 0

TaskBarShowAllWindows=1

EdgeSwitch=0
HorizontalEdgeSwitch=0
VerticalEdgeSwitch=0
ContinuousEdgeSwitch=0

LimitPosition=1
LimitSize=1
'''

if __name__ == "__main__":
    CHK( platform.system() == 'Linux' and tuple(map(int, platform.release().split('.')[:2])) >= (6, 3) , 'Require Linux >= 6.3')
    set_nonewpriv()
    lyrcfg_to_use = 'notready'
    while lyrcfg_to_use:
        tlcfg = None
        LG = d()
        if isinstance(lyrcfg_to_use, dict):
            log(f'Sublayer {lyrcfg_to_use.layer_name}')
            set_proc_dispname(lyrcfg_to_use.layer_name)
        try:
            lyrcfg_to_use = main(lyrcfg_to_use)
        except Exception as err:
            try_pass(lambda: wlog('error', errmsg=err) )
            raise
