from enum import IntEnum, EnumMeta

# fmt: off


class KeyMeta(EnumMeta):
    """
    fix numerics being a special case and allows them to be accessed via
    Key["1"] just like any other normal key
    """
    def __getitem__(self, key):
        s = super()
        if key in "0123456789":
            return s.__getitem__(f"KEY_{key}")
        else:
            return s.__getitem__(key)


# https://github.com/torvalds/linux/blob/master/include/uapi/linux/input-event-codes.h
class Key(IntEnum, metaclass=KeyMeta):
    """ representation of a single keyboard key"""
    RESERVED                    = 0
    ESC                         = 1
    KEY_1                       = 2
    KEY_2                       = 3
    KEY_3                       = 4
    KEY_4                       = 5
    KEY_5                       = 6
    KEY_6                       = 7
    KEY_7                       = 8
    KEY_8                       = 9
    KEY_9                       = 10
    KEY_0                       = 11
    MINUS                       = 12
    EQUAL                       = 13
    BACKSPACE                   = 14
    TAB                         = 15
    Q                           = 16
    W                           = 17
    E                           = 18
    R                           = 19
    T                           = 20
    Y                           = 21
    U                           = 22
    I                           = 23  # noqa: E741
    O                           = 24  # noqa: E741
    P                           = 25
    LEFT_BRACE                  = 26
    RIGHT_BRACE                 = 27
    ENTER                       = 28
    LEFT_CTRL                   = 29
    A                           = 30
    S                           = 31
    D                           = 32
    F                           = 33
    G                           = 34
    H                           = 35
    J                           = 36
    K                           = 37
    L                           = 38
    SEMICOLON                   = 39
    APOSTROPHE                  = 40
    GRAVE                       = 41
    LEFT_SHIFT                  = 42
    BACKSLASH                   = 43
    Z                           = 44
    X                           = 45
    C                           = 46
    V                           = 47
    B                           = 48
    N                           = 49
    M                           = 50
    COMMA                       = 51
    DOT                         = 52
    SLASH                       = 53
    RIGHT_SHIFT                 = 54
    KPASTERISK                  = 55
    LEFT_ALT                    = 56
    SPACE                       = 57
    CAPSLOCK                    = 58
    F1                          = 59
    F2                          = 60
    F3                          = 61
    F4                          = 62
    F5                          = 63
    F6                          = 64
    F7                          = 65
    F8                          = 66
    F9                          = 67
    F10                         = 68
    NUMLOCK                     = 69
    SCROLLLOCK                  = 70
    KP7                         = 71
    KP8                         = 72
    KP9                         = 73
    KPMINUS                     = 74
    KP4                         = 75
    KP5                         = 76
    KP6                         = 77
    KPPLUS                      = 78
    KP1                         = 79
    KP2                         = 80
    KP3                         = 81
    KP0                         = 82
    KPDOT                       = 83

    ZENKAKUHANKAKU              = 85
    KEY_102ND                   = 86
    F11                         = 87
    F12                         = 88
    RO                          = 89
    KATAKANA                    = 90
    HIRAGANA                    = 91
    HENKAN                      = 92
    KATAKANAHIRAGANA            = 93
    MUHENKAN                    = 94
    KPJPCOMMA                   = 95
    KPENTER                     = 96
    RIGHT_CTRL                  = 97
    KPSLASH                     = 98
    SYSRQ                       = 99
    RIGHT_ALT                   = 100
    LINEFEED                    = 101
    HOME                        = 102
    UP                          = 103
    PAGE_UP                     = 104
    LEFT                        = 105
    RIGHT                       = 106
    END                         = 107
    DOWN                        = 108
    PAGE_DOWN                   = 109
    INSERT                      = 110
    DELETE                      = 111
    MACRO                       = 112
    MUTE                        = 113
    VOLUMEDOWN                  = 114
    VOLUMEUP                    = 115
    POWER                       = 116
    KPEQUAL                     = 117
    KPPLUSMINUS                 = 118
    PAUSE                       = 119
    SCALE                       = 120

    KPCOMMA                     = 121
    HANGEUL                     = 122
    HANGUEL                     = HANGEUL
    HANJA                       = 123
    YEN                         = 124
    LEFT_META                   = 125
    RIGHT_META                  = 126
    COMPOSE                     = 127

    STOP                        = 128
    AGAIN                       = 129
    PROPS                       = 130
    UNDO                        = 131
    FRONT                       = 132
    COPY                        = 133
    OPEN                        = 134
    PASTE                       = 135
    FIND                        = 136
    CUT                         = 137
    HELP                        = 138
    MENU                        = 139
    CALC                        = 140
    SETUP                       = 141
    SLEEP                       = 142
    WAKEUP                      = 143
    FILE                        = 144
    SENDFILE                    = 145
    DELETEFILE                  = 146
    XFER                        = 147
    PROG1                       = 148
    PROG2                       = 149
    WWW                         = 150
    MSDOS                       = 151
    COFFEE                      = 152
    SCREENLOCK                  = COFFEE
    DIRECTION                   = 153
    CYCLEWINDOWS                = 154
    MAIL                        = 155
    BOOKMARKS                   = 156
    COMPUTER                    = 157
    BACK                        = 158
    FORWARD                     = 159
    CLOSECD                     = 160
    EJECTCD                     = 161
    EJECTCLOSECD                = 162
    NEXTSONG                    = 163
    PLAYPAUSE                   = 164
    PREVIOUSSONG                = 165
    STOPCD                      = 166
    RECORD                      = 167
    REWIND                      = 168
    PHONE                       = 169
    ISO                         = 170
    CONFIG                      = 171
    HOMEPAGE                    = 172
    REFRESH                     = 173
    EXIT                        = 174
    MOVE                        = 175
    EDIT                        = 176
    SCROLLUP                    = 177
    SCROLLDOWN                  = 178
    KPLEFTPAREN                 = 179
    KPRIGHTPAREN                = 180
    NEW                         = 181
    REDO                        = 182

    F13                         = 183
    F14                         = 184
    F15                         = 185
    F16                         = 186
    F17                         = 187
    F18                         = 188
    F19                         = 189
    F20                         = 190
    F21                         = 191
    F22                         = 192
    F23                         = 193
    F24                         = 194

    PLAYCD                      = 200
    PAUSECD                     = 201
    PROG3                       = 202
    PROG4                       = 203
    DASHBOARD                   = 204
    SUSPEND                     = 205
    CLOSE                       = 206
    PLAY                        = 207
    FASTFORWARD                 = 208
    BASSBOOST                   = 209
    PRINT                       = 210
    HP                          = 211
    CAMERA                      = 212
    SOUND                       = 213
    QUESTION                    = 214
    EMAIL                       = 215
    CHAT                        = 216
    SEARCH                      = 217
    CONNECT                     = 218
    FINANCE                     = 219
    SPORT                       = 220
    SHOP                        = 221
    ALTERASE                    = 222
    CANCEL                      = 223
    BRIGHTNESSDOWN              = 224
    BRIGHTNESSUP                = 225
    MEDIA                       = 226

    SWITCHVIDEOMODE             = 227
    KBDILLUMTOGGLE              = 228
    KBDILLUMDOWN                = 229
    KBDILLUMUP                  = 230

    SEND                        = 231
    REPLY                       = 232
    FORWARDMAIL                 = 233
    SAVE                        = 234
    DOCUMENTS                   = 235

    BATTERY                     = 236

    BLUETOOTH                   = 237
    WLAN                        = 238
    UWB                         = 239

    UNKNOWN                     = 240

    VIDEO_NEXT                  = 241
    VIDEO_PREV                  = 242
    BRIGHTNESS_CYCLE            = 243
    BRIGHTNESS_AUTO             = 244
    BRIGHTNESS_ZERO             = BRIGHTNESS_AUTO
    DISPLAY_OFF                 = 245

    WWAN                        = 246
    WIMAX                       = WWAN
    RFKILL                      = 247

    MICMUTE                     = 248

    BTN_MISC                    = 0x100
    BTN_0                       = 0x100
    BTN_1                       = 0x101
    BTN_2                       = 0x102
    BTN_3                       = 0x103
    BTN_4                       = 0x104
    BTN_5                       = 0x105
    BTN_6                       = 0x106
    BTN_7                       = 0x107
    BTN_8                       = 0x108
    BTN_9                       = 0x109

    BTN_MOUSE                   = 0x110
    BTN_LEFT                    = 0x110
    BTN_RIGHT                   = 0x111
    BTN_MIDDLE                  = 0x112
    BTN_SIDE                    = 0x113
    BTN_EXTRA                   = 0x114
    BTN_FORWARD                 = 0x115
    BTN_BACK                    = 0x116
    BTN_TASK                    = 0x117

    BTN_JOYSTICK                = 0x120
    BTN_TRIGGER                 = 0x120
    BTN_THUMB                   = 0x121
    BTN_THUMB2                  = 0x122
    BTN_TOP                     = 0x123
    BTN_TOP2                    = 0x124
    BTN_PINKIE                  = 0x125
    BTN_BASE                    = 0x126
    BTN_BASE2                   = 0x127
    BTN_BASE3                   = 0x128
    BTN_BASE4                   = 0x129
    BTN_BASE5                   = 0x12a
    BTN_BASE6                   = 0x12b
    BTN_DEAD                    = 0x12f

    BTN_GAMEPAD                 = 0x130
    BTN_SOUTH                   = 0x130
    BTN_A                       = BTN_SOUTH
    BTN_EAST                    = 0x131
    BTN_B                       = BTN_EAST
    BTN_C                       = 0x132
    BTN_NORTH                   = 0x133
    BTN_X                       = BTN_NORTH
    BTN_WEST                    = 0x134
    BTN_Y                       = BTN_WEST
    BTN_Z                       = 0x135
    BTN_TL                      = 0x136
    BTN_TR                      = 0x137
    BTN_TL2                     = 0x138
    BTN_TR2                     = 0x139
    BTN_SELECT                  = 0x13a
    BTN_START                   = 0x13b
    BTN_MODE                    = 0x13c
    BTN_THUMBL                  = 0x13d
    BTN_THUMBR                  = 0x13e

    BTN_DIGI                    = 0x140
    BTN_TOOL_PEN                = 0x140
    BTN_TOOL_RUBBER             = 0x141
    BTN_TOOL_BRUSH              = 0x142
    BTN_TOOL_PENCIL             = 0x143
    BTN_TOOL_AIRBRUSH           = 0x144
    BTN_TOOL_FINGER             = 0x145
    BTN_TOOL_MOUSE              = 0x146
    BTN_TOOL_LENS               = 0x147
    BTN_TOOL_QUINTTAP           = 0x148  # Five fingers on trackpad
    BTN_STYLUS3                 = 0x149
    BTN_TOUCH                   = 0x14a
    BTN_STYLUS                  = 0x14b
    BTN_STYLUS2                 = 0x14c
    BTN_TOOL_DOUBLETAP          = 0x14d
    BTN_TOOL_TRIPLETAP          = 0x14e
    BTN_TOOL_QUADTAP            = 0x14f  # Four fingers on trackpad

    BTN_WHEEL                   = 0x150
    BTN_GEAR_DOWN               = 0x150
    BTN_GEAR_UP                 = 0x151

    KEY_OK                      = 0x160
    KEY_SELECT                  = 0x161
    KEY_GOTO                    = 0x162
    KEY_CLEAR                   = 0x163
    KEY_POWER2                  = 0x164
    KEY_OPTION                  = 0x165
    KEY_INFO                    = 0x166  # AL OEM Features/Tips/Tutorial
    KEY_TIME                    = 0x167
    KEY_VENDOR                  = 0x168
    KEY_ARCHIVE                 = 0x169
    KEY_PROGRAM                 = 0x16a  # Media Select Program Guide
    KEY_CHANNEL                 = 0x16b
    KEY_FAVORITES               = 0x16c
    KEY_EPG                     = 0x16d
    KEY_PVR                     = 0x16e  # Media Select Home
    KEY_MHP                     = 0x16f
    KEY_LANGUAGE                = 0x170
    KEY_TITLE                   = 0x171
    KEY_SUBTITLE                = 0x172
    KEY_ANGLE                   = 0x173
    KEY_ZOOM                    = 0x174
    KEY_MODE                    = 0x175
    KEY_KEYBOARD                = 0x176
    KEY_SCREEN                  = 0x177
    KEY_PC                      = 0x178  # Media Select Computer
    KEY_TV                      = 0x179  # Media Select TV
    KEY_TV2                     = 0x17a  # Media Select Cable
    KEY_VCR                     = 0x17b  # Media Select VCR
    KEY_VCR2                    = 0x17c  # VCR Plus
    KEY_SAT                     = 0x17d  # Media Select Satellite
    KEY_SAT2                    = 0x17e
    KEY_CD                      = 0x17f  # Media Select CD
    KEY_TAPE                    = 0x180  # Media Select Tape
    KEY_RADIO                   = 0x181
    KEY_TUNER                   = 0x182  # Media Select Tuner
    KEY_PLAYER                  = 0x183
    KEY_TEXT                    = 0x184
    KEY_DVD                     = 0x185  # Media Select DVD
    KEY_AUX                     = 0x186
    KEY_MP3                     = 0x187
    KEY_AUDIO                   = 0x188  # AL Audio Browser
    KEY_VIDEO                   = 0x189  # AL Movie Browser
    KEY_DIRECTORY               = 0x18a
    KEY_LIST                    = 0x18b
    KEY_MEMO                    = 0x18c  # Media Select Messages
    KEY_CALENDAR                = 0x18d
    KEY_RED                     = 0x18e
    KEY_GREEN                   = 0x18f
    KEY_YELLOW                  = 0x190
    KEY_BLUE                    = 0x191
    KEY_CHANNELUP               = 0x192  # Channel Increment
    KEY_CHANNELDOWN             = 0x193  # Channel Decrement
    KEY_FIRST                   = 0x194
    KEY_LAST                    = 0x195  # Recall Last
    KEY_AB                      = 0x196
    KEY_NEXT                    = 0x197
    KEY_RESTART                 = 0x198
    KEY_SLOW                    = 0x199
    KEY_SHUFFLE                 = 0x19a
    KEY_BREAK                   = 0x19b
    KEY_PREVIOUS                = 0x19c
    KEY_DIGITS                  = 0x19d
    KEY_TEEN                    = 0x19e
    KEY_TWEN                    = 0x19f
    KEY_VIDEOPHONE              = 0x1a0  # Media Select Video Phone
    KEY_GAMES                   = 0x1a1  # Media Select Games
    KEY_ZOOMIN                  = 0x1a2  # AC Zoom In
    KEY_ZOOMOUT                 = 0x1a3  # AC Zoom Out
    KEY_ZOOMRESET               = 0x1a4  # AC Zoom
    KEY_WORDPROCESSOR           = 0x1a5  # AL Word Processor
    KEY_EDITOR                  = 0x1a6  # AL Text Editor
    KEY_SPREADSHEET             = 0x1a7  # AL Spreadsheet
    KEY_GRAPHICSEDITOR          = 0x1a8  # AL Graphics Editor
    KEY_PRESENTATION            = 0x1a9  # AL Presentation App
    KEY_DATABASE                = 0x1aa  # AL Database App
    KEY_NEWS                    = 0x1ab  # AL Newsreader
    KEY_VOICEMAIL               = 0x1ac  # AL Voicemail
    KEY_ADDRESSBOOK             = 0x1ad  # AL Contacts/Address Book
    KEY_MESSENGER               = 0x1ae  # AL Instant Messaging
    KEY_DISPLAYTOGGLE           = 0x1af  # Turn display (LCD) on and off
    KEY_BRIGHTNESS_TOGGLE       = KEY_DISPLAYTOGGLE
    KEY_SPELLCHECK              = 0x1b0   # AL Spell Check
    KEY_LOGOFF                  = 0x1b1   # AL Logoff

    KEY_DOLLAR                  = 0x1b2
    KEY_EURO                    = 0x1b3

    KEY_FRAMEBACK               = 0x1b4  # Consumer - transport controls
    KEY_FRAMEFORWARD            = 0x1b5
    KEY_CONTEXT_MENU            = 0x1b6  # GenDesc - system context menu
    KEY_MEDIA_REPEAT            = 0x1b7  # Consumer - transport control
    KEY_10CHANNELSUP            = 0x1b8  # 10 channels up (10+)
    KEY_10CHANNELSDOWN          = 0x1b9  # 10 channels down (10-)
    KEY_IMAGES                  = 0x1ba  # AL Image Browser

    KEY_DEL_EOL                 = 0x1c0
    KEY_DEL_EOS                 = 0x1c1
    KEY_INS_LINE                = 0x1c2
    KEY_DEL_LINE                = 0x1c3

    KEY_FN                      = 0x1d0
    KEY_FN_ESC                  = 0x1d1
    KEY_FN_F1                   = 0x1d2
    KEY_FN_F2                   = 0x1d3
    KEY_FN_F3                   = 0x1d4
    KEY_FN_F4                   = 0x1d5
    KEY_FN_F5                   = 0x1d6
    KEY_FN_F6                   = 0x1d7
    KEY_FN_F7                   = 0x1d8
    KEY_FN_F8                   = 0x1d9
    KEY_FN_F9                   = 0x1da
    KEY_FN_F10                  = 0x1db
    KEY_FN_F11                  = 0x1dc
    KEY_FN_F12                  = 0x1dd
    KEY_FN_1                    = 0x1de
    KEY_FN_2                    = 0x1df
    KEY_FN_D                    = 0x1e0
    KEY_FN_E                    = 0x1e1
    KEY_FN_F                    = 0x1e2
    KEY_FN_S                    = 0x1e3
    KEY_FN_B                    = 0x1e4

    KEY_BRL_DOT1                = 0x1f1
    KEY_BRL_DOT2                = 0x1f2
    KEY_BRL_DOT3                = 0x1f3
    KEY_BRL_DOT4                = 0x1f4
    KEY_BRL_DOT5                = 0x1f5
    KEY_BRL_DOT6                = 0x1f6
    KEY_BRL_DOT7                = 0x1f7
    KEY_BRL_DOT8                = 0x1f8
    KEY_BRL_DOT9                = 0x1f9
    KEY_BRL_DOT10               = 0x1fa

    KEY_NUMERIC_0               = 0x200  # used by phones, remote controls,
    KEY_NUMERIC_1               = 0x201  # and other keypads
    KEY_NUMERIC_2               = 0x202
    KEY_NUMERIC_3               = 0x203
    KEY_NUMERIC_4               = 0x204
    KEY_NUMERIC_5               = 0x205
    KEY_NUMERIC_6               = 0x206
    KEY_NUMERIC_7               = 0x207
    KEY_NUMERIC_8               = 0x208
    KEY_NUMERIC_9               = 0x209
    KEY_NUMERIC_STAR            = 0x20a
    KEY_NUMERIC_POUND           = 0x20b
    KEY_NUMERIC_A               = 0x20c  # Phone key A - HUT Telephony = 0xb9
    KEY_NUMERIC_B               = 0x20d
    KEY_NUMERIC_C               = 0x20e
    KEY_NUMERIC_D               = 0x20f

    KEY_CAMERA_FOCUS            = 0x210
    KEY_WPS_BUTTON              = 0x211  # WiFi Protected Setup key

    KEY_TOUCHPAD_TOGGLE         = 0x212  # Request switch touchpad on or off
    KEY_TOUCHPAD_ON             = 0x213
    KEY_TOUCHPAD_OFF            = 0x214

    KEY_CAMERA_ZOOMIN           = 0x215
    KEY_CAMERA_ZOOMOUT          = 0x216
    KEY_CAMERA_UP               = 0x217
    KEY_CAMERA_DOWN             = 0x218
    KEY_CAMERA_LEFT             = 0x219
    KEY_CAMERA_RIGHT            = 0x21a

    KEY_ATTENDANT_ON            = 0x21b
    KEY_ATTENDANT_OFF           = 0x21c
    KEY_ATTENDANT_TOGGLE        = 0x21d  # Attendant call on or off
    KEY_LIGHTS_TOGGLE           = 0x21e  # Reading light on or off

    BTN_DPAD_UP                 = 0x220
    BTN_DPAD_DOWN               = 0x221
    BTN_DPAD_LEFT               = 0x222
    BTN_DPAD_RIGHT              = 0x223

    KEY_ALS_TOGGLE              = 0x230  # Ambient light sensor

    KEY_BUTTONCONFIG            = 0x240  # AL Button Configuration
    KEY_TASKMANAGER             = 0x241  # AL Task/Project Manager
    KEY_JOURNAL                 = 0x242  # AL Log/Journal/Timecard
    KEY_CONTROLPANEL            = 0x243  # AL Control Panel
    KEY_APPSELECT               = 0x244  # AL Select Task/Application
    KEY_SCREENSAVER             = 0x245  # AL Screen Saver
    KEY_VOICECOMMAND            = 0x246  # Listening Voice Command
    KEY_ASSISTANT               = 0x247  # AL Context-aware desktop assistant

    KEY_BRIGHTNESS_MIN          = 0x250  # Set Brightness to Minimum
    KEY_BRIGHTNESS_MAX          = 0x251  # Set Brightness to Maximum

    KEY_KBDINPUTASSIST_PREV     = 0x260
    KEY_KBDINPUTASSIST_NEXT     = 0x261
    KEY_KBDINPUTASSIST_PREVGROUP= 0x262
    KEY_KBDINPUTASSIST_NEXTGROUP= 0x263
    KEY_KBDINPUTASSIST_ACCEPT   = 0x264
    KEY_KBDINPUTASSIST_CANCEL   = 0x265

    KEY_RIGHT_UP                = 0x266
    KEY_RIGHT_DOWN              = 0x267
    KEY_LEFT_UP                 = 0x268
    KEY_LEFT_DOWN               = 0x269

    KEY_ROOT_MENU               = 0x26a
    KEY_MEDIA_TOP_MENU          = 0x26b
    KEY_NUMERIC_11              = 0x26c
    KEY_NUMERIC_12              = 0x26d

    KEY_AUDIO_DESC              = 0x26e
    KEY_3D_MODE                 = 0x26f
    KEY_NEXT_FAVORITE           = 0x270
    KEY_STOP_RECORD             = 0x271
    KEY_PAUSE_RECORD            = 0x272
    KEY_VOD                     = 0x273  # Video on Demand
    KEY_UNMUTE                  = 0x274
    KEY_FASTREVERSE             = 0x275
    KEY_SLOWREVERSE             = 0x276

    KEY_DATA                    = 0x277
    KEY_ONSCREEN_KEYBOARD       = 0x278

    # ── Privacy / screenshot keys (kernel 5.x+) ─────────────────────────
    KEY_PRIVACY_SCREEN_TOGGLE   = 0x279
    KEY_SELECTIVE_SCREENSHOT    = 0x27a

    # ── Gaming macro keys (kernel 5.4+, 0x290-0x2ad) ────────────────────
    KEY_MACRO1                  = 0x290
    KEY_MACRO2                  = 0x291
    KEY_MACRO3                  = 0x292
    KEY_MACRO4                  = 0x293
    KEY_MACRO5                  = 0x294
    KEY_MACRO6                  = 0x295
    KEY_MACRO7                  = 0x296
    KEY_MACRO8                  = 0x297
    KEY_MACRO9                  = 0x298
    KEY_MACRO10                 = 0x299
    KEY_MACRO11                 = 0x29a
    KEY_MACRO12                 = 0x29b
    KEY_MACRO13                 = 0x29c
    KEY_MACRO14                 = 0x29d
    KEY_MACRO15                 = 0x29e
    KEY_MACRO16                 = 0x29f
    KEY_MACRO17                 = 0x2a0
    KEY_MACRO18                 = 0x2a1
    KEY_MACRO19                 = 0x2a2
    KEY_MACRO20                 = 0x2a3
    KEY_MACRO21                 = 0x2a4
    KEY_MACRO22                 = 0x2a5
    KEY_MACRO23                 = 0x2a6
    KEY_MACRO24                 = 0x2a7
    KEY_MACRO25                 = 0x2a8
    KEY_MACRO26                 = 0x2a9
    KEY_MACRO27                 = 0x2aa
    KEY_MACRO28                 = 0x2ab
    KEY_MACRO29                 = 0x2ac
    KEY_MACRO30                 = 0x2ad

    # ── Macro recording / preset controls (kernel 5.4+) ─────────────────
    KEY_MACRO_RECORD_START      = 0x2b0
    KEY_MACRO_RECORD_STOP       = 0x2b1
    KEY_MACRO_PRESET_CYCLE      = 0x2b2
    KEY_MACRO_PRESET1           = 0x2b3
    KEY_MACRO_PRESET2           = 0x2b4
    KEY_MACRO_PRESET3           = 0x2b5

    BTN_TRIGGER_HAPPY           = 0x2c0
    BTN_TRIGGER_HAPPY1          = 0x2c0
    BTN_TRIGGER_HAPPY2          = 0x2c1
    BTN_TRIGGER_HAPPY3          = 0x2c2
    BTN_TRIGGER_HAPPY4          = 0x2c3
    BTN_TRIGGER_HAPPY5          = 0x2c4
    BTN_TRIGGER_HAPPY6          = 0x2c5
    BTN_TRIGGER_HAPPY7          = 0x2c6
    BTN_TRIGGER_HAPPY8          = 0x2c7
    BTN_TRIGGER_HAPPY9          = 0x2c8
    BTN_TRIGGER_HAPPY10         = 0x2c9
    BTN_TRIGGER_HAPPY11         = 0x2ca
    BTN_TRIGGER_HAPPY12         = 0x2cb
    BTN_TRIGGER_HAPPY13         = 0x2cc
    BTN_TRIGGER_HAPPY14         = 0x2cd
    BTN_TRIGGER_HAPPY15         = 0x2ce
    BTN_TRIGGER_HAPPY16         = 0x2cf
    BTN_TRIGGER_HAPPY17         = 0x2d0
    BTN_TRIGGER_HAPPY18         = 0x2d1
    BTN_TRIGGER_HAPPY19         = 0x2d2
    BTN_TRIGGER_HAPPY20         = 0x2d3
    BTN_TRIGGER_HAPPY21         = 0x2d4
    BTN_TRIGGER_HAPPY22         = 0x2d5
    BTN_TRIGGER_HAPPY23         = 0x2d6
    BTN_TRIGGER_HAPPY24         = 0x2d7
    BTN_TRIGGER_HAPPY25         = 0x2d8
    BTN_TRIGGER_HAPPY26         = 0x2d9
    BTN_TRIGGER_HAPPY27         = 0x2da
    BTN_TRIGGER_HAPPY28         = 0x2db
    BTN_TRIGGER_HAPPY29         = 0x2dc
    BTN_TRIGGER_HAPPY30         = 0x2dd
    BTN_TRIGGER_HAPPY31         = 0x2de
    BTN_TRIGGER_HAPPY32         = 0x2df
    BTN_TRIGGER_HAPPY33         = 0x2e0
    BTN_TRIGGER_HAPPY34         = 0x2e1
    BTN_TRIGGER_HAPPY35         = 0x2e2
    BTN_TRIGGER_HAPPY36         = 0x2e3
    BTN_TRIGGER_HAPPY37         = 0x2e4
    BTN_TRIGGER_HAPPY38         = 0x2e5
    BTN_TRIGGER_HAPPY39         = 0x2e6
    BTN_TRIGGER_HAPPY40         = 0x2e7

    # ---------------------------------------------------------------------------
    # Virtual carrier keycodes for keymapper-internal fake modifiers.
    #
    # These exist ONLY inside the keymapper -- activating remaps in keymaps,
    # negating a troublesome modifier under specific conditions, etc. They are
    # never meant to carry a real character or modifier out to the system. They are
    # deliberately placed ABOVE 255 for one structural reason:
    #
    #   XKB's keycode space is hard-capped at 255 (evdev 247, after the +8 XKB
    #   offset). Any evdev code above 247 is OUTSIDE the range XKB processes, so it
    #   can never be named, bound to a keysym, or turned into a modifier by ANY
    #   layout -- standard or custom, now or in the future. These fakes are
    #   therefore invisible to the XKB keysym path by construction, not by
    #   circumstance.
    #
    # Why NOT the kernel-undefined 195-199 gap (the obvious-looking spot, and where
    # these used to live): those codes ARE within XKB's range, and the default 'pc'
    # symbols include -- present in virtually every layout -- already binds them:
    #
    #     evdev 195  <LVL5>  ISO_Level5_Shift -> SetMods(LevelFive)
    #     evdev 196  <ALT>   -> Alt   (Mod1)
    #     evdev 197  <META>  Meta_L   (Mod1)
    #     evdev 198  <SUPR>  Super_L  (Mod4)
    #     evdev 199  <HYPR>  Hyper_L  (Mod4)
    #
    # A fake sitting on one of those only stays harmless as long as (a) the
    # keymapper consumes the event before the compositor's XKB sees it, AND (b) the
    # active layout happens to have no content on that modifier's level. Both are
    # circumstantial. On a US layout nothing uses level 5, so a leaked 195 is
    # invisible -- but on an 8-level layout a leaked 195 would suddenly shift to
    # level 5, and a leaked 198 would register as Super (popping launcher menus).
    # So anything below 256 CAN collide with pre-defined XKB behavior; the >255
    # range CANNOT. The "Avoiding ..." note on each line below records which XKB
    # slot that code maps to, so this window is not mistaken for free gap later.
    #
    # Placement: 755-759 sit in the trailing gap below KEY_MAX (767) in
    # input-event-codes.h, clear of all KEY_ and BTN_ definitions, with 760-766
    # left as margin against a future "park it at the very end" kernel addition.
    #
    # Two honest caveats:
    #   - ">255" ghosts these from XKB / keysym translation specifically, NOT from
    #     the input stack as a whole. A raw-evdev reader (this keymapper, evtest, a
    #     game reading /dev/input directly) still sees them as plain event codes;
    #     they just have no symbolic name and no XKB meaning.
    #   - The uinput output device must DECLARE these codes in its EV_KEY capability
    #     bitmap at setup, or the kernel will silently drop writes of them.
    # ---------------------------------------------------------------------------

    # Virtual carrier keys for keymapper-internal fake modifiers (all > 255 so XKB
    # can never see or react to them). See the block above for the full rationale.
    V_L5_SH = 755    # Avoiding 195 (XKB <LVL5>)
    V_FAKEY = 756    # Avoiding 196 (XKB <ALT>)
    V_PLAID = 757    # Avoiding 197 (XKB <META>)
    V_CRAZY = 758    # Avoiding 198 (XKB <SUPR>)
    V_HYPER = 759    # Avoiding 199 (XKB <HYPR>)

    # We avoid low common keys in module aliases so they don't get huge.
    KEY_MIN_INTERESTING         = MUTE
    KEY_MAX                     = 0x2ff
    KEY_CNT                     = (KEY_MAX + 1)

    REL_X                       = 0x00
    REL_Y                       = 0x01
    REL_Z                       = 0x02
    REL_RX                      = 0x03
    REL_RY                      = 0x04
    REL_RZ                      = 0x05
    REL_HWHEEL                  = 0x06
    REL_DIAL                    = 0x07
    REL_WHEEL                   = 0x08
    REL_MISC                    = 0x09
    REL_MAX                     = 0x0f
    REL_CNT                     = (REL_MAX + 1)

    ABS_X                       = 0x00
    ABS_Y                       = 0x01
    ABS_Z                       = 0x02
    ABS_RX                      = 0x03
    ABS_RY                      = 0x04
    ABS_RZ                      = 0x05
    ABS_THROTTLE                = 0x06
    ABS_RUDDER                  = 0x07
    ABS_WHEEL                   = 0x08
    ABS_GAS                     = 0x09
    ABS_BRAKE                   = 0x0a
    ABS_HAT0X                   = 0x10
    ABS_HAT0Y                   = 0x11
    ABS_HAT1X                   = 0x12
    ABS_HAT1Y                   = 0x13
    ABS_HAT2X                   = 0x14
    ABS_HAT2Y                   = 0x15
    ABS_HAT3X                   = 0x16
    ABS_HAT3Y                   = 0x17
    ABS_PRESSURE                = 0x18
    ABS_DISTANCE                = 0x19
    ABS_TILT_X                  = 0x1a
    ABS_TILT_Y                  = 0x1b
    ABS_TOOL_WIDTH              = 0x1c

    ABS_VOLUME                  = 0x20
    ABS_MISC                    = 0x28

    ABS_MT_SLOT                 = 0x2f  # MT slot being modified
    ABS_MT_TOUCH_MAJOR          = 0x30  # Major axis of touching ellipse
    ABS_MT_TOUCH_MINOR          = 0x31  # Minor axis (omit if circular)
    ABS_MT_WIDTH_MAJOR          = 0x32  # Major axis of approaching ellipse
    ABS_MT_WIDTH_MINOR          = 0x33  # Minor axis (omit if circular)
    ABS_MT_ORIENTATION          = 0x34  # Ellipse orientation
    ABS_MT_POSITION_X           = 0x35  # Center X touch position
    ABS_MT_POSITION_Y           = 0x36  # Center Y touch position
    ABS_MT_TOOL_TYPE            = 0x37  # Type of touching device
    ABS_MT_BLOB_ID              = 0x38  # Group a set of packets as a blob
    ABS_MT_TRACKING_ID          = 0x39  # Unique ID of initiated contact
    ABS_MT_PRESSURE             = 0x3a  # Pressure on contact area
    ABS_MT_DISTANCE             = 0x3b  # Contact hover distance
    ABS_MT_TOOL_X               = 0x3c  # Center X tool position
    ABS_MT_TOOL_Y               = 0x3d  # Center Y tool position

    ABS_MAX                     = 0x3f
    ABS_CNT                     = (ABS_MAX + 1)

    SW_LID                      = 0x00  # set = lid shut
    SW_TABLET_MODE              = 0x01  # set = tablet mode
    SW_HEADPHONE_INSERT         = 0x02  # set = inserted
    SW_RFKILL_ALL               = 0x03  # rfkill master switch
    SW_RADIO                    = SW_RFKILL_ALL  # deprecated
    SW_MICROPHONE_INSERT        = 0x04  # set = inserted
    SW_DOCK                     = 0x05  # set = plugged into dock
    SW_LINEOUT_INSERT           = 0x06  # set = inserted
    SW_JACK_PHYSICAL_INSERT     = 0x07  # set = mechanical switch set
    SW_VIDEOOUT_INSERT          = 0x08  # set = inserted
    SW_CAMERA_LENS_COVER        = 0x09  # set = lens covered
    SW_KEYPAD_SLIDE             = 0x0a  # set = keypad slide out
    SW_FRONT_PROXIMITY          = 0x0b  # set = front proximity sensor active
    SW_ROTATE_LOCK              = 0x0c  # set = rotate locked/disabled
    SW_LINEIN_INSERT            = 0x0d  # set = inserted
    SW_MUTE_DEVICE              = 0x0e  # set = device disabled
    SW_PEN_INSERTED             = 0x0f  # set = pen inserted
    SW_MAX                      = 0x0f
    SW_CNT                      = (SW_MAX + 1)

    MSC_SERIAL                  = 0x00
    MSC_PULSELED                = 0x01
    MSC_GESTURE                 = 0x02
    MSC_RAW                     = 0x03
    MSC_SCAN                    = 0x04
    MSC_TIMESTAMP               = 0x05
    MSC_MAX                     = 0x07
    MSC_CNT                     = (MSC_MAX + 1)

    LED_NUML                    = 0x00
    LED_CAPSL                   = 0x01
    LED_SCROLLL                 = 0x02
    LED_COMPOSE                 = 0x03
    LED_KANA                    = 0x04
    LED_SLEEP                   = 0x05
    LED_SUSPEND                 = 0x06
    LED_MUTE                    = 0x07
    LED_MISC                    = 0x08
    LED_MAIL                    = 0x09
    LED_CHARGING                = 0x0a
    LED_MAX                     = 0x0f
    LED_CNT                     = (LED_MAX + 1)

    REP_DELAY                   = 0x00
    REP_PERIOD                  = 0x01
    REP_MAX                     = 0x01
    REP_CNT                     = (REP_MAX + 1)

    SND_CLICK                   = 0x00
    SND_BELL                    = 0x01
    SND_TONE                    = 0x02
    SND_MAX                     = 0x07
    SND_CNT                     = (SND_MAX + 1)

    def __str__(self):
        return self.name


ASCII_TO_KEY = {
    ";": Key.SEMICOLON,
    "'": Key.APOSTROPHE,
    "=": Key.EQUAL,
    "-": Key.MINUS,
    "`": Key.GRAVE,
    "[": Key.LEFT_BRACE,
    "]": Key.RIGHT_BRACE,
    ",": Key.COMMA,
    ".": Key.DOT,
    "/": Key.SLASH,
    " ": Key.SPACE,
    "\\": Key.BACKSLASH
}
