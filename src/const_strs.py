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



_allfonts = 'sans-serif,serif,monospace,Noto Sans,Noto Serif,Noto Sans Mono,DejaVu Sans,DejaVu Serif,DejaVu Sans Mono,Liberation Sans,Liberation Serif,Liberation Mono,FreeSans,FreeSerif,FreeMono,Arimo,Tinos,Cousine,Roboto,Open Sans,Ubuntu,Cantarell,Lato,Source Sans Pro,Source Serif Pro,Source Code Pro,Fira Sans,Fira Mono,Inter,Hack,WenQuanYi Micro Hei,WenQuanYi Zen Hei,WenQuanYi Micro Hei Mono,WenQuanYi Zen Hei Mono,Noto Sans CJK SC,Noto Serif CJK SC,Noto Sans Mono CJK SC,Source Han Sans SC,Source Han Serif SC,Source Han Mono SC,Microsoft YaHei,SimHei,SimSun,NSimSun,FangSong,KaiTi,Sarasa Gothic SC,Sarasa Mono SC,AR PL UMing CN,AR PL UKai CN,Droid Sans Fallback,Noto Sans CJK TC,Noto Serif CJK TC,Noto Sans Mono CJK TC,Noto Sans CJK HK,Noto Sans CJK JP,Noto Serif CJK JP,Noto Sans Mono CJK JP,Noto Sans CJK KR,Noto Serif CJK KR,Noto Sans Mono CJK KR,Source Han Sans TC,Source Han Serif TC,Source Han Sans HK,Source Han Sans JP,Source Han Sans KR,Microsoft JhengHei,PMingLiU,MingLiU,AR PL UMing TW,AR PL UKai TW,Sarasa Gothic TC,Sarasa Gothic HK,Sarasa Gothic J,Sarasa Gothic K,IPAGothic,IPAMincho,IPAexGothic,IPAexMincho,TakaoGothic,VL Gothic,Meiryo,MS Gothic,Malgun Gothic,NanumGothic,NanumMyeongjo,NanumGothicCoding,UnDotum,UnBatang,Noto Sans Arabic,Noto Naskh Arabic,Noto Sans Hebrew,Noto Serif Hebrew,Noto Sans Thai,Noto Serif Thai,Noto Sans Devanagari,Noto Serif Devanagari,Noto Sans Bengali,Noto Sans Tamil,Noto Sans Telugu,Noto Sans Kannada,Noto Sans Malayalam,Noto Sans Gujarati,Noto Sans Gurmukhi,Noto Sans Oriya,Noto Sans Sinhala,Noto Sans Khmer,Noto Sans Lao,Noto Sans Myanmar,Noto Sans Tibetan,Noto Sans Mongolian,Noto Sans Georgian,Noto Serif Georgian,Noto Sans Armenian,Noto Serif Armenian,Noto Sans Ethiopic,Noto Sans Cherokee,Noto Sans Canadian Aboriginal,Noto Sans Thaana,Noto Sans Syriac,Noto Sans Javanese,Noto Sans Yi,Lohit Devanagari,Lohit Bengali,Lohit Tamil,Lohit Telugu,Lohit Kannada,Lohit Malayalam,Lohit Gujarati,Lohit Punjabi,Lohit Odia,Tibetan Machine Uni,Padauk,Scheherazade,Amiri,Vazirmatn,FreeSans Indic,Unifont,Unifont Upper,Noto Sans Symbols,Noto Sans Symbols2,Noto Sans Math,Noto Music,Noto Sans Runic,Noto Sans Glagolitic,Noto Sans Gothic,Noto Sans Phoenician,Noto Sans Egyptian Hieroglyphs,Noto Sans Cuneiform,STIX Two Math,STIXGeneral,Symbola,Font Awesome 6 Free,Font Awesome 5 Free,FontAwesome,Material Icons,Material Design Icons,Powerline Symbols,Symbols Nerd Font,Symbols Nerd Font Mono,Hack Nerd Font,JetBrainsMono Nerd Font,FiraCode Nerd Font,Wingdings,Webdings,Noto Color Emoji,Noto Emoji,Twitter Color Emoji,Twemoji,EmojiOne Color,JoyPixels,Apple Color Emoji,Segoe UI Emoji,Segoe UI Symbol,OpenMoji Color'

# NOTE 不要启用icewm的启动器、程序菜单等，因为那样所启动的程序与沙箱的主层不是同一个pidns
ICEWM_PREF=f'''
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

PreferFreetypeFonts=1

NormalButtonFontNameXft = "{_allfonts}"
ClockFontNameXft = "{_allfonts}"
MenuFontNameXft = "{_allfonts}"
StatusFontNameXft = "{_allfonts}"
TitleFontNameXft = "{_allfonts}"
ToolTipFontNameXft = "{_allfonts}"
ActiveTaskBarFontNameXft = "{_allfonts}"
NormalTaskBarFontNameXft = "{_allfonts}"
QuickSwitchFontNameXft = "{_allfonts}"
ActiveButtonFontNameXft = "{_allfonts}"
ToolButtonFontNameXft = "{_allfonts}"
NormalWorkspaceFontNameXft = "{_allfonts}"
ActiveWorkspaceFontNameXft = "{_allfonts}"
MinimizedWindowFontNameXft = "{_allfonts}"
ListBoxFontNameXft = "{_allfonts}"
TempFontNameXft = "{_allfonts}"
ApmFontNameXft = "{_allfonts}"
InputFontNameXft = "{_allfonts}"
LabelFontNameXft = "{_allfonts}"

'''
