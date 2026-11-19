// Panel Fixes: two small repairs to the top bar.
//
// 1. Workspace dots. A dot grows in (scaleIn) or shrinks out
//    (scaleOutAndDestroy) over 500 ms. If an ancestor is taken off the stage
//    and put back while that runs - Dash to Panel moves the Activities button
//    into its own panel when it starts, which at login lands inside that
//    window - Clutter drops the transition and the dot keeps whatever scale it
//    had: a tiny dot, or a dot that never goes away. Each dot's animation is
//    watched and, if it stops without finishing, the dot is set to where the
//    animation was going.
//
// 2. Tray order. AppIndicator puts every new icon at index 1 of the right
//    box. When the extensions are switched on after the apps have started, the
//    autostarted icons sit further right than index 1, so an app opened later
//    lands away from them, next to the net-speed indicator. A new tray icon is
//    put just before the first tray icon already in that box instead, which is
//    index 1 in the normal case and so changes nothing there.

import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const TRAY_PREFIX = 'appindicator-';

export default class PanelFixes extends Extension {
    enable() {
        this._idles = new Set();
        this._patchDots();
        this._patchTray();
    }

    disable() {
        for (const id of this._idles)
            GLib.source_remove(id);
        this._idles = null;
        if (this._dotProto) {
            if (this._dotProto.scaleIn === this._scaleInWrapper)
                this._dotProto.scaleIn = this._origScaleIn;
            if (this._dotProto.scaleOutAndDestroy === this._scaleOutWrapper)
                this._dotProto.scaleOutAndDestroy = this._origScaleOut;
            this._dotProto = null;
        }
        if (this._trayWrapper && Main.panel.addToStatusArea === this._trayWrapper) {
            if (this._origAddWasOwn)
                Main.panel.addToStatusArea = this._origAddToStatusArea;
            else
                delete Main.panel.addToStatusArea;
        }
        this._trayWrapper = null;
        this._origAddToStatusArea = null;
    }

    // --- workspace dots ---------------------------------------------------

    _patchDots() {
        const indicators = Main.panel.statusArea.activities?.get_first_child();
        const sample = indicators?.get_first_child();
        if (indicators?.constructor.name !== 'WorkspaceIndicators' ||
            typeof sample?.scaleIn !== 'function' ||
            typeof sample?.scaleOutAndDestroy !== 'function') {
            console.warn('[panel-fixes] workspace dots not found; dot repair is off');
            return;
        }

        const proto = Object.getPrototypeOf(sample);
        const origScaleIn = proto.scaleIn;
        const origScaleOut = proto.scaleOutAndDestroy;
        const watch = dot => this._watchDot(dot);

        proto.scaleIn = function () {
            markGone(this);
            origScaleIn.call(this);
            watch(this);
        };
        proto.scaleOutAndDestroy = function () {
            markGone(this);
            origScaleOut.call(this);
            watch(this);
        };
        this._dotProto = proto;
        this._scaleInWrapper = proto.scaleIn;
        this._scaleOutWrapper = proto.scaleOutAndDestroy;
        this._origScaleIn = origScaleIn;
        this._origScaleOut = origScaleOut;

        // Repair dots that froze before this extension was enabled.
        for (const dot of findActors(global.stage, a => Object.getPrototypeOf(a) === proto)) {
            markGone(dot);
            this._watchDot(dot);
        }
    }

    _watchDot(dot) {
        if (dot._panelFixesGone)
            return;
        const transition = dot.get_transition('scale-x');
        if (!transition) {
            this._healDot(dot);
            return;
        }
        if (transition._panelFixesWatched)
            return;
        transition._panelFixesWatched = true;
        transition.connect('stopped', (_t, finished) => {
            transition._panelFixesWatched = false;
            if (!finished)
                this._later(() => this._healDot(dot));
        });
    }

    _healDot(dot) {
        if (dot._panelFixesGone || dot.get_transition('scale-x'))
            return;
        if (dot.destroying)
            dot.destroy();
        else if (dot.scale_x !== 1 || dot.scale_y !== 1)
            dot.set({scale_x: 1, scale_y: 1});
    }

    _later(fn) {
        if (!this._idles)
            return;
        const id = GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
            this._idles?.delete(id);
            fn();
            return GLib.SOURCE_REMOVE;
        });
        this._idles.add(id);
    }

    // --- tray order -------------------------------------------------------

    _patchTray() {
        const panel = Main.panel;
        const orig = panel.addToStatusArea;
        this._origAddToStatusArea = orig;
        this._origAddWasOwn = Object.prototype.hasOwnProperty.call(panel, 'addToStatusArea');
        this._trayWrapper = panel.addToStatusArea = function (role, indicator, position, box) {
            if (typeof role === 'string' && role.startsWith(TRAY_PREFIX) &&
                (box ?? 'right') === 'right') {
                const first = firstTrayIndex(this, role);
                if (first >= 0)
                    position = first;
            }
            return orig.call(this, role, indicator, position, box);
        };
    }
}

function markGone(dot) {
    if (dot._panelFixesDestroyId)
        return;
    dot._panelFixesDestroyId = dot.connect('destroy', () => {
        dot._panelFixesGone = true;
    });
}

function firstTrayIndex(panel, role) {
    const trayContainers = new Set();
    for (const [r, item] of Object.entries(panel.statusArea)) {
        if (r !== role && r.startsWith(TRAY_PREFIX) && item?.container)
            trayContainers.add(item.container);
    }
    if (!trayContainers.size)
        return -1;
    return panel._rightBox.get_children().findIndex(c => trayContainers.has(c));
}

function findActors(root, test, out = []) {
    for (const child of root.get_children()) {
        if (test(child))
            out.push(child);
        else
            findActors(child, test, out);
    }
    return out;
}
