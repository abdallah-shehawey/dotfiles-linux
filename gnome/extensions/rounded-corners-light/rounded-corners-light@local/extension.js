import Clutter from 'gi://Clutter';
import Cogl from 'gi://Cogl';
import GLib from 'gi://GLib';
import Graphene from 'gi://Graphene';
import St from 'gi://St';
import GObject from 'gi://GObject';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {WindowPreview} from 'resource:///org/gnome/shell/ui/windowPreview.js';
import {WorkspaceBackground} from 'resource:///org/gnome/shell/ui/workspace.js';
import {WorkspaceThumbnail} from 'resource:///org/gnome/shell/ui/workspaceThumbnail.js';

const EFFECT_NAME = 'light-rounded-corners';
const DESKTOP_RADIUS = 24;
const PREVIEW_RADIUS = DESKTOP_RADIUS;
const GRIP_PADDING = 4;
const GRIP_INSET = 6;
// Match the inner curve of the 8px indicator with its 3px border.
const THUMBNAIL_RADIUS = 5;
const DECLARATIONS = `
    uniform vec2 lightSize;
    uniform vec4 lightBounds;
    uniform float lightRadius;
    uniform float lightClipOutside;
`;
const FRAGMENT = `
    vec2 p = cogl_tex_coord0_in.xy * lightSize;
    vec2 edge = min(p - lightBounds.xy, lightBounds.zw - p);
    if (edge.x >= 0.0 && edge.y >= 0.0) {
        vec2 delta = max(vec2(lightRadius) - edge, vec2(0.0));
        float distanceSquared = dot(delta, delta);
        float inner = max(0.0, lightRadius - 0.5);
        if (distanceSquared > inner * inner) {
            float coverage = clamp(lightRadius + 0.5 - sqrt(distanceSquared), 0.0, 1.0);
            cogl_color_out *= coverage;
        }
    } else if (lightClipOutside > 0.5) {
        cogl_color_out *= 0.0;
    }
`;

function createWindowShadow() {
    // St caches this subtle shadow outside the window's clipping effect.
    return new St.Widget({
        name: 'light-rounded-shadow',
        reactive: false,
        can_focus: false,
        style: `border-radius: ${DESKTOP_RADIUS}px; background-color: rgba(0,0,0,0.004);
            box-shadow: 0 2px 18px 1px rgba(0,0,0,0.20);`,
    });
}

const CornerGrip = GObject.registerClass({GTypeName: 'LocalRoundedCornerGripV12'},
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
        if (this._pickRadius === r) {
            for (const box of this._pickBoxes)
                this.pick_box(context, box);
            return;
        }
        this._pickRadius = r;
        this._pickBoxes = [];
        const span = r + GRIP_PADDING;
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
            if (start < 0)
                continue;
            const right = (this.corner % 2) === 1;
            const bottom = this.corner >= 2;
            const box = new Clutter.ActorBox({
                x1: right ? span - end : start,
                x2: right ? span - start : end,
                y1: bottom ? span - y - 1 : y,
                y2: bottom ? span - y : y + 1,
            });
            this._pickBoxes.push(box);
            this.pick_box(context, box);
        }
    }
});

const CornerEffect = GObject.registerClass({GTypeName: 'LocalLightCornerEffectV12'},
class CornerEffect extends Shell.GLSLEffect {
    _init() {
        super._init();
        this._sizeUniform = this.get_uniform_location('lightSize');
        this._boundsUniform = this.get_uniform_location('lightBounds');
        this._radiusUniform = this.get_uniform_location('lightRadius');
        this._outsideUniform = this.get_uniform_location('lightClipOutside');
        this._parameters = null;
        this._geometry = '';
    }

    vfunc_build_pipeline() {
        this.add_glsl_snippet(Cogl.SnippetHook.FRAGMENT, DECLARATIONS, FRAGMENT, false);
    }

    update(width, height, bounds, radius) {
        if (this.textureRadius !== undefined)
            return;
        if (width <= 0 || height <= 0)
            return;
        this._parameters = {width, height, bounds, radius};
        this.queue_repaint();
    }

    vfunc_paint_target(node, context) {
        const texture = this.get_texture();
        if (texture) {
            const width = texture.get_width();
            const height = texture.get_height();
            let bounds;
            let radius;
            const smallTexture = this.textureRadius !== undefined;
            let clipOutside = true;
            if (smallTexture) {
                // Offscreen paint bounds include client shadows and a guard
                // border. Mask the allocated frame, not those outer pixels.
                const actor = this.get_actor();
                const box = actor.get_allocation_box();
                const frameWidth = box.get_width();
                const frameHeight = box.get_height();
                const dx = (width - frameWidth) / 2;
                const dy = (height - frameHeight) / 2;
                bounds = [dx, dy, dx + frameWidth, dy + frameHeight];
                const [visibleWidth] = actor.get_transformed_size();
                radius = visibleWidth > 0
                    ? this.textureRadius * frameWidth / visibleWidth : this.textureRadius;
            } else if (this.window) {
                // Read both rectangles at paint time. MetaWindow notifications
                // can arrive before the X11/Wayland surface has its new size.
                const frame = this.window.get_frame_rect();
                const buffer = this.window.get_buffer_rect();
                const actor = this.get_actor();
                const allocation = actor.get_allocation_box();
                const ready = Math.abs(allocation.get_width() - buffer.width) <= 2 &&
                    Math.abs(allocation.get_height() - buffer.height) <= 2 &&
                    width >= buffer.width - 2 && height >= buffer.height - 2;
                if (ready && frame.width > 0 && frame.height > 0) {
                    const dx = (width - buffer.width) / 2;
                    const dy = (height - buffer.height) / 2;
                    const x = frame.x - buffer.x + dx;
                    const y = frame.y - buffer.y + dy;
                    bounds = [x, y, x + frame.width, y + frame.height];
                    radius = DESKTOP_RADIUS;
                    if (this.paintPreview?.get_stage()) {
                        const [visibleWidth] = this.paintPreview.get_transformed_size();
                        if (visibleWidth > 0)
                            radius *= frame.width / visibleWidth;
                    } else if (this.window.fullscreen || this.window.maximizedHorizontally ||
                        this.window.maximizedVertically || this.window.minimized) {
                        // A shared source effect must never round the real
                        // maximized desktop window, only its Overview clone.
                        radius = 0;
                        clipOutside = false;
                    }
                } else {
                    // A buffer in transition must remain fully visible.
                    bounds = [0, 0, width, height];
                    radius = 0;
                    clipOutside = false;
                }
            }
            if (bounds) {
                radius = Math.min(radius, (bounds[2] - bounds[0]) / 2,
                    (bounds[3] - bounds[1]) / 2);
                const geometry = [width, height, ...bounds, radius, clipOutside].join(',');
                if (geometry !== this._geometry) {
                    this._geometry = geometry;
                    this.set_uniform_float(this._sizeUniform, 2, [width, height]);
                    this.set_uniform_float(this._boundsUniform, 4, bounds);
                    this.set_uniform_float(this._radiusUniform, 1, [radius]);
                    this.set_uniform_float(this._outsideUniform, 1, [clipOutside ? 1 : 0]);
                }
            }
        }
        super.vfunc_paint_target(node, context);
    }

});

const PreviewContextEffect = GObject.registerClass({GTypeName: 'LocalRoundedPreviewContextV13'},
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
        this._inOverview = Main.overview.visible;
        this._animating = Main.overview.animationInProgress;
        this._injections = new InjectionManager();
        const extension = this;
        // Disable clipping before GNOME captures its resize animation snapshot.
        this._injections.overrideMethod(Main.wm, '_prepareAnimationInfo', original => function (...args) {
            const actor = args[1];
            const record = extension._windows.get(actor);
            if (record) {
                record.suspended = true;
                record.effect?.set_enabled(false);
            }
            try {
                return original.apply(this, args);
            } finally {
                if (record) {
                    record.suspended = false;
                    extension._syncWindow(record);
                }
            }
        });
        for (const method of ['_sizeChangeWindowDone', '_minimizeWindowDone', '_unminimizeWindowDone']) {
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
            this._syncPreviewEffects();
        });
        this._connect(Main.overview, 'shown', () => {
            this._animating = false;
            this._syncPreviewEffects();
        });
        this._connect(Main.overview, 'hiding', () => {
            this._clearCloseAnimations();
            this._animating = true;
            this._syncPreviewEffects();
        });
        // Mapped/created actors enable their own masks. Scanning every preview
        // on every animation adjustment value is unnecessary.
        this._connect(Main.overview, 'hidden', () => {
            this._inOverview = false;
            this._animating = false;
            this._syncWindows();
        });
        this._connect(global.display, 'restacked', () => this._syncWindows());
        this._connect(global.workspace_manager, 'active-workspace-changed', () => this._syncWindows());
        this._connect(global.display, 'window-created', (_, window) => {
            const actor = window.get_compositor_private();
            if (actor)
                this._trackWindow(actor);
        });
        for (const actor of global.get_window_actors())
            this._trackWindow(actor);
        console.log('Rounded Corners Light revision 5 loaded (cached source masks, native Overview timing)');
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
        const record = {actor, window, target: null, effect: null, connections: []};
        this._windows.set(actor, record);
        const update = () => this._syncWindow(record);
        this._connect(actor, 'notify::first-child', update, record.connections);
        this._connect(actor, 'notify::width', update, record.connections);
        this._connect(actor, 'notify::height', update, record.connections);
        this._connect(actor, 'notify::x', update, record.connections);
        this._connect(actor, 'notify::y', update, record.connections);
        this._connect(actor, 'notify::scale-x', update, record.connections);
        this._connect(actor, 'notify::scale-y', update, record.connections);
        this._connect(actor, 'notify::visible', update, record.connections);
        this._connect(actor, 'notify::opacity', update, record.connections);
        this._connect(actor, 'notify::parent', update, record.connections);
        this._connect(window, 'size-changed', update, record.connections);
        this._connect(window, 'position-changed', update, record.connections);
        this._connect(window, 'notify::maximized-horizontally', update, record.connections);
        this._connect(window, 'notify::maximized-vertically', update, record.connections);
        this._connect(window, 'notify::fullscreen', update, record.connections);
        this._connect(window, 'notify::minimized', update, record.connections);
        this._connect(actor, 'destroy', () => {
            this._disconnect(record.connections);
            this._destroyAdornments(record);
            this._windows.delete(actor);
        }, record.connections);
        update();
    }

    _syncWindows() {
        for (const record of this._windows.values())
            this._syncWindow(record);
    }

    _syncWindow(record) {
        const {actor, window} = record;
        const changingSize = record.suspended || actor.__animationInfo ||
            Main.wm._resizing.has(actor) || Main.wm._resizePending.has(actor) ||
            Main.wm._minimizing.has(actor) || Main.wm._unminimizing.has(actor);
        const enabled = !changingSize && !window.minimized &&
            !window.fullscreen && !window.maximizedHorizontally && !window.maximizedVertically;
        // GNOME's window group and preview visibility transfer the shadow
        // together with the window; do not hide it early on `showing`.
        this._syncAdornments(record, enabled);
        // One source mask serves both the desktop and its live clones. Install
        // it before the first preview paint, including maximized/minimized apps.
        if (changingSize || (!enabled && !this._inOverview && !record.previews?.size)) {
            record.effect?.set_enabled(false);
            return;
        }
        const target = window.get_client_type() === Meta.WindowClientType.X11
            ? actor.get_first_child() : actor;
        if (!target)
            return;
        if (record.target !== target) {
            if (record.effect)
                record.target.remove_effect(record.effect);
            record.target = target;
            record.effect = new CornerEffect();
            record.effect.window = window;
            target.add_effect_with_name(EFFECT_NAME, record.effect);
        }
        // Clutter already invalidates changed buffers and allocations. Moving
        // or restacking an unchanged window must not invalidate its texture.
        record.effect.set_enabled(true);
    }

    _destroyAdornments(record) {
        record.shadow?.destroy();
        record.shadow = null;
        for (const grip of record.grips ?? [])
            grip.destroy();
        record.grips = null;
    }

    _syncAdornments(record, enabled) {
        const {actor, window} = record;
        if (!enabled || !actor.get_stage() || !actor.visible ||
            !window.located_on_workspace(global.workspace_manager.get_active_workspace())) {
            record.shadow?.hide();
            for (const grip of record.grips ?? [])
                grip.hide();
            return;
        }

        const parent = actor.get_parent();
        if (!parent)
            return;

        if (!record.shadow || record.shadow.get_parent() !== parent) {
            this._destroyAdornments(record);
            record.shadow = createWindowShadow();
            parent.add_child(record.shadow);
            if (window.allows_resize()) {
                record.grips = [0, 1, 2, 3].map(corner => new CornerGrip(window, corner));
                for (const grip of record.grips)
                    parent.add_child(grip);
            }
        }

        const frame = window.get_frame_rect();
        // SSD actors include their titlebar; CSD actors start at the buffer's
        // shadow. Convert the actual frame instead of assuming either origin.
        // MetaWindowGroup can be paintable without an allocation, so its
        // transform_stage_point() may fail. Desktop parent groups are unscaled.
        const [parentX, parentY] = parent.get_transformed_position();
        const x = frame.x - parentX;
        const y = frame.y - parentY;
        record.shadow.set_position(x, y);
        record.shadow.set_size(Math.max(1, frame.width), Math.max(1, frame.height));
        record.shadow.opacity = actor.opacity;
        parent.set_child_below_sibling(record.shadow, actor);
        record.shadow.show();
        const radius = Math.min(DESKTOP_RADIUS, frame.width / 2, frame.height / 2);
        const span = radius + GRIP_PADDING;
        for (const grip of record.grips ?? []) {
            grip.radius = radius;
            grip.set_position(x + (grip.corner % 2 ? frame.width - radius : -GRIP_PADDING),
                y + (grip.corner >= 2 ? frame.height - radius : -GRIP_PADDING));
            grip.set_size(span, span);
            parent.set_child_above_sibling(grip, actor);
            grip.visible = !this._inOverview;
        }
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

    _syncPreviewEffects() {
        // Install an enabled mask at construction time, including before the
        // overview's showing signal. Never wait for animation completion.
        for (const records of [this._thumbnails]) {
            for (const record of records.values()) {
                const enabled = record.actor.get_stage() !== null;
                if (record.effect.enabled !== enabled)
                    record.effect.set_enabled(enabled);
            }
        }
    }

    _roundPreview(preview) {
        const actor = preview.window_container;
        if (this._previews.has(preview)) {
            this._bindPreviewClones(this._previews.get(preview));
            return;
        }
        const shadow = createWindowShadow();
        shadow.name = 'light-rounded-preview-shadow';
        shadow.set_pivot_point(0.5, 0.5);
        shadow.add_constraint(new Clutter.BindConstraint({
            source: actor, coordinate: Clutter.BindCoordinate.ALL,
        }));
        preview.add_child(shadow);
        preview.set_child_below_sibling(shadow, actor);
        const record = {actor, shadow, cloneEffects: new Map(), connections: []};
        this._previews.set(preview, record);
        this._bindPreviewClones(record);
        const update = () => {
            // A sibling BindConstraint may be allocated before its source
            // during an overview relayout. Commit the source's new box now,
            // rather than leaving the shadow at last frame's dimensions.
            if (actor.has_allocation())
                shadow.allocate(actor.get_allocation_box());
            shadow.set_scale(actor.scale_x, actor.scale_y);
            shadow.opacity = actor.opacity;
            shadow.visible = actor.visible;
        };
        this._connect(actor, 'notify::allocation', update, record.connections);
        for (const property of ['scale-x', 'scale-y', 'opacity', 'visible'])
            this._connect(actor, `notify::${property}`, update, record.connections);
        this._connect(preview, 'destroy', () => {
            this._disconnect(record.connections);
            this._previews.delete(preview);
            for (const source of this._windows.values()) {
                if (source.previews?.delete(actor)) {
                    this._syncWindow(source);
                }
            }
        }, record.connections);
        update();
    }

    _bindPreviewClones(record) {
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
            source.previews ??= new Set();
            source.previews.add(record.actor);
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
        });
        pending.timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 10000, () => {
            pending.timeout = 0;
            this._forgetClose(pending);
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
            onStopped: () => {
                if (this._closeGhosts.delete(ghost))
                    ghost.destroy();
            },
        });
    }

    _clearCloseAnimations() {
        for (const pending of this._pendingClose.values())
            this._forgetClose(pending);
        for (const ghost of this._closeGhosts) {
            this._closeGhosts.delete(ghost);
            ghost.destroy();
        }
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
        this._syncPreviewEffects();
        const update = () => effect.update(actor.width, actor.height,
            [0, 0, actor.width, actor.height], THUMBNAIL_RADIUS);
        this._connect(actor, 'notify::mapped', () => this._syncPreviewEffects(), record.connections);
        this._connect(actor, 'notify::allocation', update, record.connections);
        this._connect(actor, 'destroy', () => {
            this._disconnect(record.connections);
            this._thumbnails.delete(actor);
        }, record.connections);
        update();
    }

    disable() {
        this._clearCloseAnimations();
        this._injections?.clear();
        this._disconnect(this._connections);
        for (const record of this._windows.values()) {
            this._disconnect(record.connections);
            if (record.effect)
                record.target.remove_effect(record.effect);
            this._destroyAdornments(record);
        }
        for (const record of this._previews.values()) {
            this._disconnect(record.connections);
            for (const [clone, item] of record.cloneEffects) {
                this._disconnect(item.connections);
                clone.remove_effect(item.effect);
            }
            record.shadow.destroy();
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
    }
}
