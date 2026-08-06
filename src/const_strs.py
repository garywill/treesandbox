from heads import *  # 真正要import 的模块 和 自定义常量
import g  # 全局变量


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
