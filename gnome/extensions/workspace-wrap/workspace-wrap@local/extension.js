import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

// GNOME binds both with these modes in windowManager.js.
const BINDINGS = {
    'switch-to-workspace-left': Meta.MotionDirection.LEFT,
    'switch-to-workspace-right': Meta.MotionDirection.RIGHT,
};
const ACTION_MODES = Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW;

// Hands GNOME's own handler a numbered binding, so the popup, the
// Overview case and the workspace-update blocking all stay GNOME's.
const numberedBinding = name => ({get_name: () => name});

export default class WorkspaceWrapExtension extends Extension {
    enable() {
        for (const [name, direction] of Object.entries(BINDINGS)) {
            Main.wm.setCustomKeybindingHandler(name, ACTION_MODES,
                (display, window, event, binding) =>
                    this._switch(display, window, event, binding, direction));
        }
    }

    disable() {
        for (const name of Object.keys(BINDINGS)) {
            Main.wm.setCustomKeybindingHandler(name, ACTION_MODES,
                Main.wm._showWorkspaceSwitcher.bind(Main.wm));
        }
    }

    _switch(display, window, event, binding, direction) {
        const manager = display.get_workspace_manager();
        const active = manager.get_active_workspace();
        const n = manager.n_workspaces;
        const vertical = manager.layout_rows === -1;

        // Only wrap at an edge of a single-row layout; anything else is stock.
        if (n < 2 || vertical || active.get_neighbor(direction) !== active) {
            Main.wm._showWorkspaceSwitcher(display, window, event, binding);
            return;
        }

        const target = active.index() === 0 ? 'last' : '1';
        Main.wm._showWorkspaceSwitcher(display, window, event,
            numberedBinding(`switch-to-workspace-${target}`));
    }
}
