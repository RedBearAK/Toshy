/*
KWin Script Application Switcher
(C) 2022 Natalie Clarius <natalie_clarius@yahoo.de>
GNU General Public License v3.0
*/

///////////////////////
// initialization
///////////////////////

// const debugMode = readConfig("debugMode", true);
const debugMode = readConfig("debugMode", false);

function debug(...args) {
    if (debugMode) { console.debug("applicationswitcher:", ...args); }
}
debug("initializing");

// Detect KDE version
const isKDE6 = typeof workspace.windowList === 'function';

function isAppOnCurrentDesktopKDE6(window) {
    return window &&
    (window.desktops && window.desktops.includes(workspace.currentDesktop)) ||
    (window.desktops && window.desktops.length === 0);
}

function isAppOnCurrentDesktopKDE5(window) {
    return window &&
    (window.x11DesktopIds && window.x11DesktopIds.includes(workspace.currentDesktop)) ||
    (window.x11DesktopIds && window.x11DesktopIds.length === 0);
}

let activeWindow;
let windowList;
let connectWindowActivated;
let setActiveWindow;
let isAppOnCurrentDesktop;

// Set up aliases to abstract away the API differences between KDE 5 and KDE 6
if (isKDE6) {
    activeWindow                = () => workspace.activeWindow;
    windowList                  = () => workspace.windowList();
    connectWindowActivated      = (handler) => workspace.windowActivated.connect(handler);
    setActiveWindow             = (window) => { workspace.activeWindow = window; };
    isAppOnCurrentDesktop       = isAppOnCurrentDesktopKDE6
} else {
    activeWindow                = () => workspace.activeClient;
    windowList                  = () => workspace.clientList();
    connectWindowActivated      = (handler) => workspace.clientActivated.connect(handler);
    setActiveWindow             = (window) => { workspace.activeClient = window; };
    isAppOnCurrentDesktop       = isAppOnCurrentDesktopKDE5
}

///////////////////////
// special applications to ignore
///////////////////////

const ignoredApps = ["plasmashell", "org.kde.plasmashell", // desktop shell
                     "krunner", "org.kde.krunner", // KRunner
                     "kwin_wayland", // lock screen
                     "org.kde.ksmserver-logout-greeter", // logout screen
                     "ksplashqml" // login splash screen
                    ];


///////////////////////
// get application a window belongs to
///////////////////////

// "dolphin"
function getApp(current) {
    if (!current || typeof current.resourceClass !== 'string') return "";
    return String(current.resourceClass);
}


///////////////////////
// keep track of active application (to check whether app has been switched)
///////////////////////

// "dolphin"
var prevActiveApp = ""

// set previously active application for initially active window
setPrevActiveApp(activeWindow())

// set previously active application for recently activated window
function setPrevActiveApp(current) {
    if (!current) return;
    prevActiveApp = getApp(current);
}

// get previously active application
function getPrevActiveApp() {
    return prevActiveApp;
}


///////////////////////
// keep track of windows belonging to same application in order of activation
///////////////////////

// {"dolphin": [oldest window, ..., most recent window], "konsole": ...}
var appGroups = {};

// compute app groups for initially present windows
windowList().forEach(window => updateAppGroups(window));

// update app groups with given window
function updateAppGroups(current) {
    if (!current) return;
    let app = getApp(current);
    if (!appGroups[app]) appGroups[app] = [];
    appGroups[app] = appGroups[app].filter(window => window && 
        window != current);
    appGroups[app].push(current);
    debug("updating app group", appGroups[app].map(window =>
        window && window.caption ? window.caption : "undefined window"
    ));
}

function isAppOnCurrentActivity(window) {
    return (window.activities && window.activities.includes(workspace.currentActivity)) ||
            (window.activities && window.activities.length === 0);
}

function getFilterConditions(window) {
    return window && !window.minimized && 
            isAppOnCurrentDesktop(window) && isAppOnCurrentActivity(window);
}

// return other visible windows of same application as given window
function getAppGroup(current) {
    if (!current) return;

    unfilteredAppGroup = appGroups[getApp(current)];
    debug("unfiltered app group", unfilteredAppGroup.map(window =>
        window && window.caption ? window.caption : "undefined window"));

    // let appGroup = appGroups[getApp(current)].filter(getFilterConditions);
    let appGroup = unfilteredAppGroup.filter(getFilterConditions);

    debug("filtered app group", appGroup.map(window =>
        window && window.caption ? window.caption : "undefined window"
    ));
    return appGroup;
}


///////////////////////
// main
///////////////////////

// when client is activated, auto-raise other windows of the same application
function onWindowActivated(active) {
    if (!active) return;
    debug("---------");
    debug("activated", active.caption);
    debug("app", getApp(active));
    // abort if application is ignored
    if (ignoredApps.includes(getApp(active))) {
        debug("ignored");
        return;
    }
    updateAppGroups(active);

    // if application was switched
    debug("previous app", getPrevActiveApp());
    if (getApp(active) != getPrevActiveApp()) {
        debug("app switched");
        setPrevActiveApp(active);
        // auto-raise other windows of same application
        for (let window of getAppGroup(active)) {
            if (window) {
                debug("auto-raising", window.caption);
                setActiveWindow(window);
            }
        }
    }
}

connectWindowActivated(onWindowActivated);
