import Clutter from 'gi://Clutter';
import Cogl from 'gi://Cogl';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Graphene from 'gi://Graphene';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';
import System from 'system';
import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {WindowPreview} from 'resource:///org/gnome/shell/ui/windowPreview.js';
import {WorkspaceBackground} from 'resource:///org/gnome/shell/ui/workspace.js';
import {WorkspaceThumbnail} from 'resource:///org/gnome/shell/ui/workspaceThumbnail.js';

const EFFECT_NAME = 'light-rounded-corners';
const DESKTOP_RADIUS = 24;
const PREVIEW_RADIUS = DESKTOP_RADIUS;
// Match the inner curve of the 8px indicator with its 3px border.
const THUMBNAIL_RADIUS = 5;
const GRIP_PADDING = 4;
const GRIP_INSET = 6;

// The shadow is GNOME's own default, libadwaita 1.9 `window.csd`:
//   focused   0 0 14px 5px rgb(0 0 0/15%), 0 0 5px 2px rgb(0 0 0/10%), 0 0 0 1px rgb(0 0 0/5%)
//   backdrop  0 0 14px 5px transparent,    0 0 10px 5px rgb(0 0 0/8%), 0 0 0 1px rgb(0 0 0/5%)
// Each entry is [alpha, spread, sigma] with sigma = blur / 2, as in CSS.
const SHADOW_FOCUSED = [[0.15, 5, 7], [0.10, 2, 2.5]];
const SHADOW_BACKDROP = [[0, 5, 7], [0.08, 5, 5]];
const SHADOW_RING = 0.05;
// The focused profile is below 1/512 beyond 24px.
const SHADOW_EXTENT = 24;
const FOCUS_TRANSITION_MS = 200;
// Clutter frees an offscreen effect's framebuffer, and GNOME's window
// snapshots, only when their JS wrapper is finalized. Collect once this much
// has been dropped, at a quiet moment, instead of whenever SpiderMonkey's own
// heap growth happens to trigger it (hours later, gigabytes later).
const GARBAGE_GC_BYTES = 128 * 1024 * 1024;
const GARBAGE_GC_DELAY_MS = 1500;

const MODE_PASS = 0;
const MODE_CLIP = 1;
const MODE_SHADOW = 2;

const DECLARATIONS = `
    uniform vec2 rcSize;
    uniform vec4 rcBounds;
    uniform float rcRadius;
    uniform float rcMode;
    uniform vec4 rcShadow1;
    uniform vec4 rcShadow2;

    float rcPhi(float x) {
        // Standard normal CDF; absolute error below 1.5e-4.
        x = clamp(x, -8.0, 8.0);
        return 1.0 / (1.0 + exp(-x * (1.5976 + 0.070566 * x * x)));
    }
`;
// Everything outside the rounded frame, including the client's own shadow,
// is replaced. The shadow is part of this window's paint, so it scales, fades
// and moves with every open/close/minimize animation and every clone.
const FRAGMENT = `
    if (rcMode > 0.5) {
        vec2 p = cogl_tex_coord0_in.xy * rcSize;
        vec2 halfSize = 0.5 * (rcBounds.zw - rcBounds.xy);
        vec2 q = abs(p - 0.5 * (rcBounds.xy + rcBounds.zw)) - halfSize + vec2(rcRadius);
        float dist = length(max(q, vec2(0.0))) + min(max(q.x, q.y), 0.0) - rcRadius;
        float coverage = clamp(0.5 - dist, 0.0, 1.0);
        cogl_color_out *= coverage;
        if (rcMode > 1.5 && coverage < 1.0) {
            float d = max(dist, 0.0);
            float a1 = rcShadow1.x * rcPhi((rcShadow1.y - d) * rcShadow1.z);
            float a2 = rcShadow2.x * rcPhi((rcShadow2.y - d) * rcShadow2.z);
            float ring = rcShadow1.w * clamp(rcShadow2.w + 0.5 - d, 0.0, 1.0);
            float shadow = 1.0 - (1.0 - a1) * (1.0 - a2) * (1.0 - ring);
            cogl_color_out += vec4(0.0, 0.0, 0.0,
                shadow * cogl_color_in.a * (1.0 - cogl_color_out.a));
        }
    }
`;

// The ClutterOffscreenEffect framebuffer box, in the actor's own coordinates,
// for its paint volume. Mirrors Clutter 50's _clutter_actor_box_enlarge_for_effects().
function fboBox(x1, y1, x2, y2) {
    const width = Math.floor(x2 - x1 + 0.5);
    const height = Math.floor(y2 - y1 + 0.5);
    const right = Math.ceil(x2 + 0.75);
    const bottom = Math.ceil(y2 + 0.75);
    return [right - width - 3, bottom - height - 3, width + 3, height + 3];
}

// Mutter does not export MetaSurfaceActor to GI; compare GTypes instead.
const SURFACE_ACTOR = GObject.type_from_name('MetaSurfaceActor');

function x11Surface(actor) {
    // An X11 window draws through its surface actor. Other extensions add
    // children of their own (Blur My Shell's application blur does), so the
    // first child is not necessarily the surface.
    if (!SURFACE_ACTOR)
        return actor.get_first_child();
    return actor.get_children().find(child =>
        GObject.type_is_a(child.constructor.$gtype, SURFACE_ACTOR)) ?? null;
}

function shadowProfile(focus) {
    const mix = (a, b) => a + (b - a) * focus;
    return SHADOW_BACKDROP.map((backdrop, i) =>
        backdrop.map((value, j) => mix(value, SHADOW_FOCUSED[i][j])));
}

const CornerGrip = GObject.registerClass({GTypeName: 'LocalRoundedCornerGripV7'},
class CornerGrip extends Clutter.Actor {
    _init(window, corner) {
        const cursors = [Clutter.CursorType.NW_RESIZE, Clutter.CursorType.NE_RESIZE,
            Clutter.CursorType.SW_RESIZE, Clutter.CursorType.SE_RESIZE];
        super._init({name: `light-rounded-grip-${corner}`, reactive: true,
            cursor_type: cursors[corner]});
        this.corner = corner;
        this.radius = DESKTOP_RADIUS;
        this.connect('button-press-event', (_, event) => {
            if (event.get_button() !== 1)
                return Clutter.EVENT_PROPAGATE;
            const ops = [Meta.GrabOp.RESIZING_NW, Meta.GrabOp.RESIZING_NE,
                Meta.GrabOp.RESIZING_SW, Meta.GrabOp.RESIZING_SE];
            const [x, y] = event.get_coords();
            const sprite = global.stage.context.get_backend().get_sprite(global.stage, event);
            window.activate(event.get_time());
            return window.begin_grab_op(ops[corner], sprite, event.get_time(),
                new Graphene.Point({x, y})) ? Clutter.EVENT_STOP : Clutter.EVENT_PROPAGATE;
        });
    }

    vfunc_pick(context) {
        // Pick only a narrow curved band, not the entire square corner. The
        // close button and client content inside the arc keep their own input.
        if (!this.should_pick(context))
            return;
        const r = this.radius;
        if (this._pickRadius !== r) {
            this._pickRadius = r;
            this._pickBoxes = [];
            const span = r + GRIP_PADDING;
            const right = (this.corner % 2) === 1;
            const bottom = this.corner >= 2;
            for (let y = 0; y < span; y++) {
                let start = -1;
                let end = 0;
                for (let x = 0; x < span; x++) {
                    const distance = Math.hypot(x + 0.5 - span, y + 0.5 - span);
                    if (distance >= r - GRIP_INSET && distance <= r + GRIP_PADDING) {
                        if (start < 0)
                            start = x;
                        end = x + 1;
                    }
                }
                if (start >= 0) {
                    this._pickBoxes.push(new Clutter.ActorBox({
                        x1: right ? span - end : start,
                        x2: right ? span - start : end,
                        y1: bottom ? span - y - 1 : y,
                        y2: bottom ? span - y : y + 1,
                    }));
                }
            }
        }
        for (const box of this._pickBoxes)
            this.pick_box(context, box);
    }
});

const CornerEffect = GObject.registerClass({GTypeName: 'LocalLightCornerEffectV7'},
class CornerEffect extends Shell.GLSLEffect {
    _init() {
        super._init();
        this._locations = ['rcSize', 'rcBounds', 'rcRadius', 'rcMode', 'rcShadow1', 'rcShadow2']
            .map(name => this.get_uniform_location(name));
        this._values = [];
        // Window effects: geometry in the actor's own logical coordinates.
        this.geometry = null;
        this.focus = 1;
        this.paintPreview = null;
        // Thumbnails and close fades: a visible radius for the whole actor.
        this.textureRadius = undefined;
    }

    vfunc_build_pipeline() {
        this.add_glsl_snippet(Cogl.SnippetHook.FRAGMENT, DECLARATIONS, FRAGMENT, false);
    }

    _set(index, values) {
        const old = this._values[index];
        if (old?.length === values.length) {
            let same = true;
            for (let i = 0; same && i < values.length; i++)
                same = old[i] === values[i];
            if (same)
                return;
        }
        this._values[index] = values;
        this.set_uniform_float(this._locations[index], values.length, values);
    }

    _pass() {
        this._key = null;
        this._set(3, [MODE_PASS]);
    }

    vfunc_paint_target(node, context) {
        // Read the framebuffer size, never the texture itself: a JS wrapper
        // keeps every framebuffer Clutter replaces (each resize step, each
        // Overview entry) alive until the next garbage collection. Revision 6
        // held gigabytes of them that way.
        const [ok, width, height] = this.get_target_size();
        if (ok && width > 0 && height > 0)
            this._update(width, height);
        else
            this._pass();
        super.vfunc_paint_target(node, context);
    }

    _update(textureWidth, textureHeight) {
        const actor = this.get_actor();
        let frame, visibleWidth = 0, mode;
        if (this.textureRadius !== undefined) {
            const allocation = actor.get_allocation_box();
            frame = [0, 0, allocation.get_width(), allocation.get_height()];
            [visibleWidth] = actor.get_transformed_size();
            mode = MODE_CLIP;
        } else if (this.geometry) {
            frame = this.geometry.frame;
            if (this.paintPreview?.get_stage()) {
                [visibleWidth] = this.paintPreview.get_transformed_size();
                mode = this.geometry.previewMode;
            } else {
                // A maximized window is rounded only inside its Overview
                // preview; clones elsewhere show it as it is on the desktop.
                mode = this.geometry.desktopMode;
            }
            if (mode === MODE_PASS) {
                this._pass();
                return;
            }
            // Most desktop paints repeat the previous one exactly.
            const key = this._key;
            if (key && key.geometry === this.geometry && key.width === textureWidth &&
                key.height === textureHeight && key.visibleWidth === visibleWidth &&
                key.mode === mode && key.focus === this.focus)
                return;
            this._key = {geometry: this.geometry, width: textureWidth, height: textureHeight,
                visibleWidth, mode, focus: this.focus};
            // A buffer in transition has not caught up with the frame yet:
            // show it intact rather than clip it with the new geometry.
            const allocation = actor.get_allocation_box();
            if (Math.abs(allocation.get_width() - this.geometry.width) > 0.5 ||
                Math.abs(allocation.get_height() - this.geometry.height) > 0.5) {
                this._pass();
                return;
            }
        } else {
            this._pass();
            return;
        }

        // The framebuffer covers the paint volume Clutter computed for this
        // paint. Read it: fractional scales pad it by a fraction of a pixel.
        const volume = actor.get_paint_volume();
        if (!volume) {
            this._pass();
            return;
        }
        const origin = volume.get_origin();
        const [x, y, width, height] = fboBox(origin.x, origin.y,
            origin.x + volume.get_width(), origin.y + volume.get_height());
        // Texels per logical pixel.
        const scale = textureWidth / width;
        if (!Number.isInteger(scale) || scale < 1 || textureHeight !== height * scale) {
            this._pass();
            return;
        }
        const bounds = [(frame[0] - x) * scale, (frame[1] - y) * scale,
            (frame[2] - x) * scale, (frame[3] - y) * scale];
        const frameWidth = frame[2] - frame[0];
        let radius = (this.textureRadius ?? DESKTOP_RADIUS) * scale;
        if (visibleWidth > 0)
            radius *= frameWidth / visibleWidth;
        radius = Math.min(radius, (bounds[2] - bounds[0]) / 2, (bounds[3] - bounds[1]) / 2);

        this._set(0, [textureWidth, textureHeight]);
        this._set(1, bounds);
        this._set(2, [radius]);
        this._set(3, [mode]);
        if (mode === MODE_SHADOW) {
            const [[a1, s1, g1], [a2, s2, g2]] = shadowProfile(this.focus);
            this._set(4, [a1, s1 * scale, 1 / (g1 * scale), SHADOW_RING]);
            this._set(5, [a2, s2 * scale, 1 / (g2 * scale), scale]);
        }
    }
});

const PreviewContextEffect = GObject.registerClass({GTypeName: 'LocalRoundedPreviewContextV7'},
class PreviewContextEffect extends Clutter.Effect {
    _init(source, previewActor) {
        super._init();
        this.source = source;
        this.previewActor = previewActor;
    }

    vfunc_paint(_node, context, _flags) {
        // This is not an offscreen effect: reuse the source's cached content
        // and only select the right radius for this particular preview paint.
        // Sticky windows and multiple monitors can clone the same source.
        const effect = this.source.effect;
        const previous = effect?.paintPreview;
        if (effect)
            effect.paintPreview = this.previewActor;
        try {
            this.get_actor().continue_paint(context);
        } finally {
            if (effect)
                effect.paintPreview = previous;
        }
    }
});

export default class RoundedCornersLight extends Extension {
    enable() {
        this._windows = new Map();
        this._previews = new Map();
        this._thumbnails = new Map();
        this._backgrounds = new Map();
        this._connections = [];
        this._pendingClose = new Map();
        this._closeGhosts = new Set();
        this._garbage = 0;
        this._gcSource = 0;
        this._inOverview = Main.overview.visible;
        this._animating = Main.overview.animationInProgress;
        this._injections = new InjectionManager();
        const extension = this;
        // GNOME snapshots the old frame before a size change, waits for the
        // client's new buffer, then animates between the two. The snapshot
        // keeps the look the window had; the new buffer is shown intact
        // until it arrives, and with its own corners while it animates.
        this._injections.overrideMethod(Main.wm, '_prepareAnimationInfo', original => function (...args) {
            const record = extension._windows.get(args[1]);
            if (record)
                extension._prepareSnapshot(record, args[3]);
            try {
                return original.apply(this, args);
            } finally {
                if (record)
                    extension._syncWindow(record);
            }
        });
        for (const method of ['_sizeChangedWindow', '_sizeChangeWindowDone']) {
            this._injections.overrideMethod(Main.wm, method, original => function (...args) {
                try {
                    return original.apply(this, args);
                } finally {
                    const record = extension._windows.get(args[1]);
                    if (record)
                        extension._syncWindow(record);
                }
            });
        }
        // That snapshot is a window-sized texture which only a garbage
        // collection releases; count it once GNOME has dropped it.
        this._injections.overrideMethod(Main.wm, '_clearAnimationInfo', original => function (actor) {
            const content = actor.__animationInfo?.clone?.content ?? null;
            const cleared = original.call(this, actor);
            if (cleared)
                extension._noteGarbage(content);
            return cleared;
        });
        this._injections.overrideMethod(WindowPreview.prototype, '_deleteAll', original => function (...args) {
            try {
                extension._captureClose(this);
            } catch (error) {
                console.warn(`Rounded close snapshot unavailable: ${error.message}`);
            }
            return original.apply(this, args);
        });
        this._injections.overrideMethod(WindowPreview.prototype, '_addWindow', original => function (window) {
            const result = original.call(this, window);
            extension._roundPreview(this);
            return result;
        });
        this._injections.overrideMethod(WorkspaceThumbnail.prototype, '_init', original => function (...args) {
            original.apply(this, args);
            extension._roundThumbnail(this);
        });
        this._injections.overrideMethod(WorkspaceBackground.prototype, '_updateBorderRadius', original => function () {
            original.call(this);
            extension._updateBackground(this);
        });
        this._injections.overrideMethod(WorkspaceBackground.prototype, '_init', original => function (...args) {
            original.apply(this, args);
            extension._roundBackground(this);
        });
        const visit = actor => {
            if (actor instanceof WorkspaceThumbnail)
                this._roundThumbnail(actor);
            if (actor instanceof WindowPreview)
                this._roundPreview(actor);
            if (actor instanceof WorkspaceBackground)
                this._roundBackground(actor);
            for (const child of actor.get_children())
                visit(child);
        };
        visit(Main.layoutManager.overviewGroup);
        this._connect(Main.overview, 'showing', () => {
            this._inOverview = true;
            this._animating = true;
            this._syncWindows();
            this._syncThumbnails();
        });
        this._connect(Main.overview, 'shown', () => {
            this._animating = false;
            this._syncThumbnails();
        });
        this._connect(Main.overview, 'hiding', () => {
            this._clearCloseAnimations();
            this._animating = true;
            this._syncThumbnails();
        });
        this._connect(Main.overview, 'hidden', () => {
            this._inOverview = false;
            this._animating = false;
            this._syncWindows();
        });
        this._connect(global.display, 'window-created', (_, window) => {
            const actor = window.get_compositor_private();
            if (actor)
                this._trackWindow(actor);
        });
        for (const actor of global.get_window_actors())
            this._trackWindow(actor);
        console.log('Rounded Corners Light revision 7 loaded (in-window default shadow)');
    }

    _connect(object, signal, callback, connections = this._connections) {
        connections.push([object, object.connect(signal, callback)]);
    }

    _disconnect(connections) {
        for (const [object, id] of connections.splice(0))
            object.disconnect(id);
    }

    _trackWindow(actor) {
        const window = actor.metaWindow;
        if (!window || this._windows.has(actor))
            return;
        if (![Meta.WindowType.NORMAL, Meta.WindowType.DIALOG, Meta.WindowType.MODAL_DIALOG].includes(window.windowType))
            return;
        const x11 = window.get_client_type() === Meta.WindowClientType.X11;
        const record = {actor, window, x11, target: null, effect: null, volume: null,
            grips: null, focus: window.appears_focused ? 1 : 0, timeline: null, connections: []};
        this._windows.set(actor, record);
        const sync = () => this._syncWindow(record);
        // Only size and state matter: moves and stacking need no work, since
        // everything this extension draws is inside the window actor.
        this._connect(window, 'size-changed', sync, record.connections);
        for (const property of ['maximized-horizontally', 'maximized-vertically', 'fullscreen'])
            this._connect(window, `notify::${property}`, sync, record.connections);
        this._connect(window, 'notify::appears-focused', () => this._fadeFocus(record), record.connections);
        this._connect(actor, 'notify::width', sync, record.connections);
        this._connect(actor, 'notify::height', sync, record.connections);
        // An X11 window can replace its surface actor; keep the effect on the
        // current one and the grips above it.
        if (x11)
            this._connect(actor, 'child-added', sync, record.connections);
        this._connect(actor, 'destroy', () => {
            this._disconnect(record.connections);
            record.timeline?.stop();
            record.timeline = null;
            this._windows.delete(actor);
            // Its framebuffer now waits for the collector.
            this._noteGarbage(record.effect);
            record.effect = null;
            record.target = null;
        }, record.connections);
        sync();
    }

    _syncWindows() {
        for (const record of this._windows.values())
            this._syncWindow(record);
    }

    _syncWindow(record) {
        if (record.syncing)
            return;
        record.syncing = true;
        try {
            this._syncWindowState(record);
        } finally {
            record.syncing = false;
        }
        if (record.effect?.enabled)
            record.effect.queue_repaint();
    }

    _syncWindowState(record) {
        const {actor, window} = record;
        // Between GNOME's snapshot and the client's new buffer the actor is
        // frozen on its old contents, which must not take the new geometry.
        const waitingForBuffer = Main.wm._resizePending.has(actor) ||
            (!!actor.__animationInfo && !Main.wm._resizing.has(actor));
        const floating = !window.fullscreen &&
            !window.maximizedHorizontally && !window.maximizedVertically;
        const desktop = floating && !waitingForBuffer;

        const target = record.x11 ? x11Surface(actor) : actor;
        if (!target || !(desktop || this._inOverview)) {
            // Disabling keeps no buffer alive for long: Clutter 50 drops the
            // framebuffer here and replaces the texture on the next enabled
            // paint, freeing the old one at once (nothing in JS holds it).
            this._setChildren(record, false);
            record.effect?.set_enabled(false);
            return;
        }
        if (record.target !== target) {
            this._dropEffect(record);
            record.target = target;
            record.effect = new CornerEffect();
            record.effect.focus = record.focus;
            target.add_effect_with_name(EFFECT_NAME, record.effect);
            // An X11 window can replace its surface actor; never touch the
            // old one after Clutter destroyed it.
            if (target !== actor) {
                target.connect('destroy', () => {
                    if (record.target === target) {
                        this._noteGarbage(record.effect);
                        record.target = null;
                        record.effect = null;
                    }
                });
            }
        }

        const frameRect = window.get_frame_rect();
        const bufferRect = window.get_buffer_rect();
        const fx = frameRect.x - bufferRect.x;
        const fy = frameRect.y - bufferRect.y;
        const frame = [fx, fy, fx + frameRect.width, fy + frameRect.height];
        const valid = frameRect.width > 0 && frameRect.height > 0;
        record.effect.geometry = valid ? {frame, width: bufferRect.width, height: bufferRect.height,
            desktopMode: desktop ? MODE_SHADOW : MODE_PASS,
            previewMode: floating ? MODE_SHADOW : MODE_CLIP} : null;
        if (valid && desktop)
            record.lastFloating = {frame, width: bufferRect.width, height: bufferRect.height};
        this._setChildren(record, desktop && valid, frame);
        record.effect.set_enabled(true);
    }

    _dropEffect(record) {
        const {effect, target} = record;
        record.effect = null;
        record.target = null;
        if (!effect)
            return;
        this._noteGarbage(effect);
        target?.remove_effect(effect);
    }

    _noteGarbage(item) {
        // Count what is now waiting for the collector: an effect's
        // framebuffer, or a snapshot's texture.
        let bytes = 0;
        if (item instanceof Clutter.OffscreenEffect) {
            const [ok, width, height] = item.get_target_size();
            if (ok)
                bytes = width * height * 4;
        } else if (item) {
            const [ok, width, height] = item.get_preferred_size();
            if (ok)
                bytes = width * height * 4;
        }
        this._garbage += bytes;
        if (this._garbage < GARBAGE_GC_BYTES || this._gcSource)
            return;
        this._gcSource = GLib.timeout_add(GLib.PRIORITY_LOW, GARBAGE_GC_DELAY_MS, () => {
            // A full collection takes a few tens of milliseconds on the main
            // thread: never during an animation, and while the user is busy
            // only once a lot has piled up.
            if (Main.overview.animationInProgress || Main.wm._resizing.size > 0 ||
                Main.wm._mapping.size > 0 || Main.wm._destroying.size > 0 ||
                this._closeGhosts.size > 0)
                return GLib.SOURCE_CONTINUE;
            const idleMs = global.backend.get_core_idle_monitor?.()?.get_idletime() ?? Infinity;
            if (idleMs < GARBAGE_GC_DELAY_MS && this._garbage < 4 * GARBAGE_GC_BYTES)
                return GLib.SOURCE_CONTINUE;
            this._gcSource = 0;
            this._garbage = 0;
            System.gc();
            return GLib.SOURCE_REMOVE;
        });
    }

    _prepareSnapshot(record, change) {
        // Mutter flags the new state before GNOME snapshots the old frame for
        // its size animation, while the actor still holds the old buffer.
        // Show that snapshot as the window looked: square when it leaves
        // maximized or fullscreen, otherwise rounded, without its shadow.
        if (!record.effect)
            return;
        if (change === Meta.SizeChange.UNMAXIMIZE || change === Meta.SizeChange.UNFULLSCREEN) {
            record.effect.set_enabled(false);
            return;
        }
        const last = record.lastFloating;
        const target = record.x11 ? x11Surface(record.actor) : record.actor;
        if (!last || record.target !== target)
            return;
        const [width, height] = target.get_size();
        if (Math.abs(width - last.width) > 0.5 || Math.abs(height - last.height) > 0.5)
            return;
        record.effect.geometry = {frame: last.frame, width: last.width, height: last.height,
            desktopMode: MODE_CLIP, previewMode: MODE_CLIP};
        record.effect.set_enabled(true);
    }

    _setChildren(record, wanted, frame) {
        const {actor, window} = record;
        if (!wanted) {
            record.volume?.destroy();
            record.volume = null;
            for (const grip of record.grips ?? [])
                grip.destroy();
            record.grips = null;
            return;
        }
        const [x1, y1, x2, y2] = frame;
        if (!record.x11) {
            if (!record.volume) {
                // Painted area for the shadow: an empty actor below the
                // surfaces. Window actors union their children's volumes.
                record.volume = new Clutter.Actor({name: 'light-rounded-volume', reactive: false});
                actor.insert_child_below(record.volume, null);
            }
            record.volume.set_position(x1 - SHADOW_EXTENT, y1 - SHADOW_EXTENT);
            record.volume.set_size(x2 - x1 + 2 * SHADOW_EXTENT, y2 - y1 + 2 * SHADOW_EXTENT);
        }
        if (!window.allows_resize())
            return;
        if (!record.grips) {
            record.grips = [0, 1, 2, 3].map(corner => new CornerGrip(window, corner));
            for (const grip of record.grips)
                actor.add_child(grip);
        }
        const radius = Math.min(DESKTOP_RADIUS, (x2 - x1) / 2, (y2 - y1) / 2);
        const span = radius + GRIP_PADDING;
        for (const grip of record.grips) {
            grip.radius = radius;
            grip.set_position(grip.corner % 2 ? x2 - radius : x1 - GRIP_PADDING,
                grip.corner >= 2 ? y2 - radius : y1 - GRIP_PADDING);
            grip.set_size(span, span);
            if (actor.get_last_child() !== record.grips[3])
                actor.set_child_above_sibling(grip, null);
        }
    }

    _fadeFocus(record) {
        const target = record.window.appears_focused ? 1 : 0;
        record.timeline?.stop();
        record.timeline = null;
        const apply = value => {
            record.focus = value;
            if (record.effect) {
                record.effect.focus = value;
                if (record.effect.enabled)
                    record.effect.queue_repaint();
            }
        };
        if (!record.actor.is_mapped() || !St.Settings.get().enable_animations) {
            apply(target);
            return;
        }
        const start = record.focus;
        const timeline = new Clutter.Timeline({actor: record.actor, duration: FOCUS_TRANSITION_MS});
        timeline.set_progress_mode(Clutter.AnimationMode.EASE_OUT_QUAD);
        timeline.connect('new-frame', () =>
            apply(start + (target - start) * timeline.get_progress()));
        timeline.connect('stopped', (_, finished) => {
            if (finished)
                apply(target);
            if (record.timeline === timeline)
                record.timeline = null;
        });
        record.timeline = timeline;
        timeline.start();
    }

    _updateBackground(actor) {
        const content = actor._bgManager?.backgroundActor?.content;
        const monitor = Main.layoutManager.monitors[actor._monitorIndex];
        if (!content || !monitor)
            return;
        const group = actor._backgroundGroup;
        // Unallocated Clutter actors do not have meaningful transformed sizes.
        // Wait for allocation rather than using their undefined output values.
        if (!group.has_allocation())
            return;
        const [width] = group.get_transformed_size();
        if (!Number.isFinite(width) || width < 1)
            return;
        // Native background clipping is expressed in monitor coordinates.
        // Compensate for preview scale, bounded by the monitor's half-height.
        content.rounded_clip_radius = Math.min(
            Math.min(monitor.width, monitor.height) / 2,
            DESKTOP_RADIUS * monitor.width / width);
    }

    _roundBackground(actor) {
        if (this._backgrounds.has(actor))
            return;
        const record = {actor, connections: []};
        this._backgrounds.set(actor, record);
        const update = () => this._updateBackground(actor);
        this._connect(actor._backgroundGroup, 'notify::allocation', update, record.connections);
        this._connect(actor, 'notify::allocation', update, record.connections);
        this._connect(actor, 'destroy', () => {
            this._disconnect(record.connections);
            this._backgrounds.delete(actor);
        }, record.connections);
        update();
    }

    _syncThumbnails() {
        for (const record of this._thumbnails.values()) {
            const enabled = record.actor.get_stage() !== null;
            if (record.effect.enabled !== enabled)
                record.effect.set_enabled(enabled);
        }
    }

    _roundPreview(preview) {
        let record = this._previews.get(preview);
        if (!record) {
            record = {actor: preview.window_container, cloneEffects: new Map(), connections: []};
            this._previews.set(preview, record);
            this._connect(preview, 'destroy', () => {
                this._disconnect(record.connections);
                for (const item of record.cloneEffects.values())
                    this._disconnect(item.connections);
                this._previews.delete(preview);
            }, record.connections);
        }
        for (const clone of record.actor.get_children()) {
            if (record.cloneEffects.has(clone))
                continue;
            const sourceActor = clone.get_source?.();
            if (!sourceActor?.metaWindow)
                continue;
            this._trackWindow(sourceActor);
            const source = this._windows.get(sourceActor);
            if (!source)
                continue;
            this._syncWindow(source);
            const effect = new PreviewContextEffect(source, record.actor);
            const item = {effect, connections: []};
            record.cloneEffects.set(clone, item);
            clone.add_effect_with_name('light-rounded-preview-context', effect);
            this._connect(clone, 'destroy', () => {
                this._disconnect(item.connections);
                record.cloneEffects.delete(clone);
            }, item.connections);
        }
    }

    _captureClose(preview) {
        if (!this._inOverview || this._animating || !St.Settings.get().enable_animations)
            return;
        const window = preview.metaWindow;
        const actor = preview.window_container;
        if (this._pendingClose.has(window) || !actor.has_allocation())
            return;
        const [x, y] = actor.get_transformed_position();
        const [width, height] = actor.get_transformed_size();
        if (width < 1 || height < 1)
            return;
        // Keep a still image until the client really closes. A confirmation
        // dialog or an ignored close request must not hide the live preview.
        const windowActor = window.get_compositor_private();
        if (!windowActor)
            return;
        const content = windowActor.paint_to_content(window.get_frame_rect());
        if (!content)
            return;
        const pending = {window, content, x, y, width, height, signal: 0, timeout: 0};
        this._pendingClose.set(window, pending);
        pending.signal = window.connect('unmanaged', () => {
            this._forgetClose(pending);
            if (this._inOverview && !this._animating)
                this._fadeClose(pending);
            else
                this._noteGarbage(pending.content);
        });
        pending.timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 10000, () => {
            pending.timeout = 0;
            this._forgetClose(pending);
            this._noteGarbage(pending.content);
            return GLib.SOURCE_REMOVE;
        });
    }

    _forgetClose(pending) {
        this._pendingClose.delete(pending.window);
        if (pending.signal) {
            pending.window.disconnect(pending.signal);
            pending.signal = 0;
        }
        if (pending.timeout) {
            GLib.source_remove(pending.timeout);
            pending.timeout = 0;
        }
    }

    _fadeClose({content, x, y, width, height}) {
        const ghost = new St.Widget({
            name: 'light-rounded-close-fade', content,
            x, y, width, height, reactive: false, can_focus: false,
        });
        const effect = new CornerEffect();
        effect.textureRadius = PREVIEW_RADIUS;
        ghost.add_effect_with_name(EFFECT_NAME, effect);
        ghost.set_pivot_point(0.5, 0.5);
        Main.uiGroup.add_child(ghost);
        this._closeGhosts.add(ghost);
        ghost.connect('destroy', () => this._closeGhosts.delete(ghost));
        ghost.ease({
            opacity: 0, scale_x: 0.96, scale_y: 0.96, duration: 180,
            mode: Clutter.AnimationMode.EASE_OUT_QUAD,
            onStopped: () => this._destroyGhost(ghost),
        });
    }

    _destroyGhost(ghost) {
        if (!this._closeGhosts.delete(ghost))
            return;
        this._noteGarbage(ghost.content);
        ghost.destroy();
    }

    _clearCloseAnimations() {
        for (const pending of [...this._pendingClose.values()]) {
            this._forgetClose(pending);
            this._noteGarbage(pending.content);
        }
        for (const ghost of [...this._closeGhosts])
            this._destroyGhost(ghost);
    }

    _roundThumbnail(actor) {
        if (this._thumbnails.has(actor))
            return;
        const effect = new CornerEffect();
        effect.textureRadius = THUMBNAIL_RADIUS;
        effect.set_enabled(false);
        const record = {actor, effect, connections: []};
        this._thumbnails.set(actor, record);
        actor.add_effect_with_name(EFFECT_NAME, effect);
        this._syncThumbnails();
        this._connect(actor, 'notify::mapped', () => this._syncThumbnails(), record.connections);
        this._connect(actor, 'destroy', () => {
            this._disconnect(record.connections);
            this._thumbnails.delete(actor);
        }, record.connections);
    }

    disable() {
        this._clearCloseAnimations();
        this._injections?.clear();
        this._disconnect(this._connections);
        for (const record of this._windows.values()) {
            this._disconnect(record.connections);
            record.timeline?.stop();
            this._dropEffect(record);
            this._setChildren(record, false);
        }
        for (const record of this._previews.values()) {
            this._disconnect(record.connections);
            for (const [clone, item] of record.cloneEffects) {
                this._disconnect(item.connections);
                clone.remove_effect(item.effect);
            }
        }
        for (const record of this._thumbnails.values()) {
            this._disconnect(record.connections);
            record.actor.remove_effect(record.effect);
        }
        for (const record of this._backgrounds.values()) {
            this._disconnect(record.connections);
            record.actor._updateBorderRadius();
        }
        this._backgrounds.clear();
        this._thumbnails.clear();
        this._windows.clear();
        this._previews.clear();
        this._injections = null;
        if (this._gcSource)
            GLib.source_remove(this._gcSource);
        this._gcSource = 0;
    }
}
