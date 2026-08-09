

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

    uc.gpus = True if uc.gui in ['realX', 'weston-xwayland', 'xpra-weston-xwayland'] else False # Sandbox can see /dev/dri and needed GPU's PCI paths in /sys .
    uc.see_userfonts = True if uc.gui else False # Sandbox can see ~/.fonts and so on.

    # --- ---- ----


    # uc.see_real_hw=True # Sandbox see host's real /dev and /sys


    # --- DBus ----

    # User (session) DBUS (things like IME needs DBUS)
    if uc.gui: uc.dbus_session="filter"
    # uc.dbus_session="allow" # Allow all DBUS communication
    # uc.dbus_session="filter" # DBUS communication filtered by xdg-dbus-proxy. Default rule is allowing IME and notifications (you can add more to uc.dbusproxy_extra also)
    # uc.dbus_session='isolated' # Run a session dbus daemon in sandbox. Totally isolated from host

    # uc.dbusproxy_extra = ['--see=org.gnome.Shell'] # xdg-dbus-proxy (by Flatpak) extra args


    # System DBUS
    # uc.dbus_system='allow'

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
