from heads import *

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
