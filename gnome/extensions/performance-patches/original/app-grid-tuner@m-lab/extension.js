/*
 * Compatibility / Internal API usage
 *
 * This extension customizes the GNOME Shell app grid and folder popups by
 * interacting with internal overview and appDisplay structures
 * (e.g. Main.overview._overview._controls._appDisplay, _folderIcons,
 * icon.view._grid, icon._dialog, layout_manager internals, etc.).
 *
 * These are private Shell APIs and can change between GNOME Shell versions.
 * The code therefore performs defensive checks (typeof/function guards,
 * version detection via Config.PACKAGE_VERSION, optional chaining) and may
 * fall back gracefully when a given field or method is not available.
 *
 * As a consequence, behaviour may differ slightly across Shell releases,
 * and updates to GNOME Shell can require adjustments to this extension.
 */

import Clutter from 'gi://Clutter';
import St from 'gi://St';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as Config from 'resource:///org/gnome/shell/misc/config.js';
import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';

const SHELL_VERSION = Config.PACKAGE_VERSION;
const SHELL_MAJOR = parseInt(SHELL_VERSION.split('.')[0], 10);

class AppGridTuner {

  constructor(extension) {
    this.extension = extension;
    this.settings = extension.getSettings();
    this.originalStates = new Map();
    this.originalBackgroundStates = new Map();
    this.isCompatible = this._checkCompatibility();
  }

  _checkCompatibility() {
    try {
      // Check if required components exist
      if (!Main.overview) {
        console.warn('[AppGridTuner] Main.overview not available');
        return false;
      }

      if (!Main.overview._overview || !Main.overview._overview._controls) {
        console.warn('[AppGridTuner] Overview controls not available');
        return false;
      }

      const appDisplay = Main.overview._overview._controls._appDisplay;
      if (!appDisplay) {
        console.warn('[AppGridTuner] App display not available');
        return false;
      }

      return true;
    } catch (e) {
      console.error(`[AppGridTuner] Compatibility check failed: ${e.message}`);
      return false;
    }
  }

  _getAppDisplay() {
    try {
      if (!this.isCompatible) return null;
      return Main.overview._overview._controls._appDisplay;
    } catch (e) {
      console.error(`[AppGridTuner] Failed to get app display: ${e.message}`);
      return null;
    }
  }

  _getBackgroundActors() {
    const actors = [];

    // Top-level overview actor (root container for workspaces, search and app grid)
    const overview = Main.overview && Main.overview._overview;
    if (overview)
      actors.push(overview);

    // Workspaces display (window previews area)
    const workspacesDisplay = overview && overview._workspacesDisplay;
    if (workspacesDisplay && !actors.includes(workspacesDisplay))
      actors.push(workspacesDisplay);

    // Controls container that holds the app display and search area
    const controls = overview && overview._controls;
    if (controls && !actors.includes(controls))
      actors.push(controls);

    // App grid display itself (middle region)
    const appDisplay = this._getAppDisplay();
    if (appDisplay && !actors.includes(appDisplay))
      actors.push(appDisplay);

    return actors;
  }

  _safeExecute(callback, fallback = null) {
    try {
      return callback();
    } catch (e) {
      console.error(`[AppGridTuner] Safe execution failed: ${e.message}`);
      return fallback;
    }
  }

  applyFolderViewChanges() {
    return this._safeExecute(() => {
      const MainAppDisplay = this._getAppDisplay();
      if (!MainAppDisplay) return;

      if (!MainAppDisplay._folderIcons || !Array.isArray(MainAppDisplay._folderIcons)) {
        console.warn('[AppGridTuner] No folder icons available');
        return;
      }

      const activeFolderIcons = new Set(MainAppDisplay._folderIcons);
      this.originalStates.forEach((state, icon) => {
        if (!activeFolderIcons.has(icon))
          this.originalStates.delete(icon);
      });

      MainAppDisplay._folderIcons.forEach(icon => {
        this._safeExecute(() => {
          if (!icon.view || !icon.view._grid || !icon.view._grid.layout_manager) {
            console.warn('[AppGridTuner] Invalid folder icon structure');
            return;
          }

          // Store original state before modifying
          if (!this.originalStates.has(icon)) {
            this.originalStates.set(icon, {
              fixedIconSize: icon.view._grid.layout_manager.fixedIconSize,
              rowsPerPage: icon.view._grid.layout_manager.rowsPerPage,
              columnsPerPage: icon.view._grid.layout_manager.columnsPerPage,
              gridStyle: icon.view._grid.style,
              tileStyle: undefined,
              dialogStyle: undefined,
              innerDialogStyle: undefined,
              scrollContentPadding: undefined,
              scrollPolicy: undefined,
              scrollClip: undefined,
              tile: null,
            });
          }

          const storedState = this.originalStates.get(icon);

          icon.view._grid.layout_manager.fixedIconSize = this.folderIconSize;
          icon.view._grid.layout_manager.rowsPerPage = (Math.ceil(icon.getAppIds().length / this.fColumns) < this.fRows) ? Math.ceil(icon.getAppIds().length / this.fColumns) : this.fRows;
          icon.view._grid.layout_manager.columnsPerPage = (icon.getAppIds().length > this.fColumns) ? this.fColumns : icon.getAppIds().length;

          // Apply folder icon label font size if configured (> 0)
          const originalGridStyle = storedState?.gridStyle || '';
          if (this.folderIconLabelFontSize > 0) {
            icon.view._grid.style =
              `${originalGridStyle} font-size: ${this.folderIconLabelFontSize}px;`;
          } else {
            icon.view._grid.style = originalGridStyle;
          }

          // Apply folder tile styling (background, opacity, border, radius) to the app grid tile
          let tile = null;
          // Try to obtain the actor that visually represents the folder tile
          tile = icon.actor || icon.icon || null;

          if (tile) {
            if (storedState && storedState.tileStyle === undefined) {
              storedState.tile = tile;
              storedState.tileStyle = tile.style || '';
            }

            let tileStyle = storedState && storedState.tileStyle !== undefined
              ? storedState.tileStyle
              : (tile.style || '');

            const primaryTile = this.folderTileBackgroundColor;
            const tileOpacity = Math.max(0, Math.min(1, this.folderTileBackgroundOpacity ?? 1.0));

            const isHex = (c) => !!c && c.startsWith('#') && c.length === 7;

            const hexToRgba = (hex, a) => {
              const r = parseInt(hex.slice(1, 3), 16);
              const g = parseInt(hex.slice(3, 5), 16);
              const b = parseInt(hex.slice(5, 7), 16);
              if (a >= 1)
                return `rgb(${r}, ${g}, ${b})`;
              return `rgba(${r}, ${g}, ${b}, ${a})`;
            };

            if (isHex(primaryTile)) {
              const c1 = hexToRgba(primaryTile, tileOpacity);
              tileStyle += ` background-color: ${c1};`;
            }

            if (this.folderTileBorderRadius > 0) {
              tileStyle += ` border-radius: ${this.folderTileBorderRadius}px;`;
            }

            if (this.folderTileBorderColor && this.folderTileBorderColor.startsWith('#')) {
              tileStyle += ` border: 1px solid ${this.folderTileBorderColor};`;
            }

            tile.style = tileStyle;
          }
          
          if (icon._ensureFolderDialog) {
            icon._ensureFolderDialog();
          }
          
          if (icon._dialog && icon._dialog.child) {
            if (storedState && storedState.dialogStyle === undefined) {
              storedState.dialogStyle = icon._dialog.child.style || '';
            }

            const dialogWidth = Math.min(
              Math.max(
                icon.view._grid.layout_manager.columnsPerPage * (this.folderIconSize + this.folderItemSpacing) + this.folderPopupWidth,
                this.folderPopupWidth
              ),
              800
            );

            // Compute dialog height based on configured rows, icon size and offsets,
            // but cap it relative to the available stage height to avoid clipping
            // large icons while keeping the dialog within the screen.
            const computedDialogHeight =
              icon.view._grid.layout_manager.rowsPerPage * (this.folderIconSize + this.folderItemHeightOffset) +
              this.folderPopupHeightOffset;

            let maxDialogHeight = 600;
            const stage = global.stage;
            const stageHeight = stage && (stage.get_height ? stage.get_height() : stage.height);
            if (stageHeight && stageHeight > 0)
              maxDialogHeight = Math.floor(stageHeight * 0.8);

            const dialogHeight = Math.min(computedDialogHeight, maxDialogHeight);
            const horizontalPadding = this.folderSidePadding || 0;

            icon._dialog.child.style =
              `${storedState?.dialogStyle || ''} box-sizing: border-box; height: ${dialogHeight}px; ` +
              `width: ${dialogWidth}px; padding-left: ${horizontalPadding}px; ` +
              `padding-right: ${horizontalPadding}px;`;

            if (storedState && storedState.dialogStyle === undefined)
              storedState.dialogStyle = icon._dialog.child.style || '';

            let dialogStyle = storedState && storedState.dialogStyle !== undefined
              ? storedState.dialogStyle
              : (icon._dialog.child.style || '');

            const primary = this.folderPopupBackgroundColor;
            const opacity = Math.max(0, Math.min(1, this.folderPopupBackgroundOpacity ?? 1.0));

            const isHex = (c) => !!c && c.startsWith('#') && c.length === 7;

            const hexToRgba = (hex, a) => {
              const r = parseInt(hex.slice(1, 3), 16);
              const g = parseInt(hex.slice(3, 5), 16);
              const b = parseInt(hex.slice(5, 7), 16);
              if (a >= 1)
                return `rgb(${r}, ${g}, ${b})`;
              return `rgba(${r}, ${g}, ${b}, ${a})`;
            };

            // Background: solid color with adjustable opacity
            if (isHex(primary)) {
              const c1 = hexToRgba(primary, opacity);
              dialogStyle += ` background-color: ${c1};`;
            }

            // Optional border radius override (> 0)
            if (this.folderPopupBorderRadius > 0) {
              dialogStyle += ` border-radius: ${this.folderPopupBorderRadius}px;`;
            }

            // Optional border color override
            if (this.folderPopupBorderColor && this.folderPopupBorderColor.startsWith('#')) {
              dialogStyle += ` border: 1px solid ${this.folderPopupBorderColor};`;
            }

            icon._dialog.child.style = dialogStyle;

            let inner = null;
            if (icon._dialog.child && icon._dialog.child.get_first_child)
              inner = icon._dialog.child.get_first_child();

            if (inner) {
              if (storedState && storedState.innerDialogStyle === undefined)
                storedState.innerDialogStyle = inner.style || '';

              let innerStyle = storedState && storedState.innerDialogStyle !== undefined
                ? storedState.innerDialogStyle
                : (inner.style || '');

              const primary = this.folderPopupBackgroundColor;
              const opacity = Math.max(0, Math.min(1, this.folderPopupBackgroundOpacity ?? 1.0));

              const isHex = (c) => !!c && c.startsWith('#') && c.length === 7;

              const hexToRgba = (hex, a) => {
                const r = parseInt(hex.slice(1, 3), 16);
                const g = parseInt(hex.slice(3, 5), 16);
                const b = parseInt(hex.slice(5, 7), 16);
                if (a >= 1)
                  return `rgb(${r}, ${g}, ${b})`;
                return `rgba(${r}, ${g}, ${b}, ${a})`;
              };

              // Background: solid color with adjustable opacity
              if (isHex(primary)) {
                const c1 = hexToRgba(primary, opacity);
                innerStyle += ` background-color: ${c1};`;
              }

              // Optional border radius override (> 0)
              if (this.folderPopupBorderRadius > 0) {
                innerStyle += ` border-radius: ${this.folderPopupBorderRadius}px;`;
              }

              // Optional border color override
              if (this.folderPopupBorderColor && this.folderPopupBorderColor.startsWith('#')) {
                innerStyle += ` border: 1px solid ${this.folderPopupBorderColor};`;
              }

              inner.style = innerStyle;
            }

            if (icon._dialog._scrollView) {
              const scrollView = icon._dialog._scrollView;

              if (storedState) {
                if (storedState.scrollClip === undefined) {
                  storedState.scrollClip = scrollView.clip_to_allocation ?? false;
                }
                if (storedState.scrollPolicy === undefined && scrollView.get_policy) {
                  storedState.scrollPolicy = scrollView.get_policy();
                }
                if (storedState.scrollContentPadding === undefined && scrollView.content_padding) {
                  const padding = scrollView.content_padding;
                  storedState.scrollContentPadding = {
                    left: padding.left ?? 0,
                    right: padding.right ?? 0,
                    top: padding.top ?? 0,
                    bottom: padding.bottom ?? 0,
                  };
                }
              }

              scrollView.clip_to_allocation = true;
              scrollView.content_padding = new Clutter.Margin({
                left: horizontalPadding,
                right: horizontalPadding,
                top: 0,
                bottom: 0,
              });

              if (scrollView.set_policy) {
                scrollView.set_policy(St.PolicyType.NEVER, St.PolicyType.AUTOMATIC);
              }
            }

            // Apply or remove the helper class that hides the folder title
            if (this.hideFolderTitle) {
                if (icon._dialog.add_style_class_name)
                   icon._dialog.add_style_class_name('app-grid-tuner-hide-folder-title');
            } else {
                if (icon._dialog.remove_style_class_name)
                   icon._dialog.remove_style_class_name('app-grid-tuner-hide-folder-title');
            }
          }
          if (icon.view._redisplay) {
            icon.view._redisplay();
          }

          const grid = icon.view._grid;
          const layoutManager = grid && grid.layout_manager;

          if (layoutManager) {
            if (SHELL_MAJOR < 47) {
              if (layoutManager._adjustIconSize) {
                layoutManager._adjustIconSize();
              }
            } else {
              if (grid.queue_relayout) {
                grid.queue_relayout();
              } else if (layoutManager._adjustIconSize) {
                layoutManager._adjustIconSize();
              }
            }
          }
        });
      });
    });
  }

  applyAnimationSettings() {
    return this._safeExecute(() => {
      const MainAppDisplay = this._getAppDisplay();
      if (!MainAppDisplay) return;

      // Apply page switch animation time
      if (MainAppDisplay._pageIndicators) {
        const originalStyle = this.originalGridState?.pageIndicatorStyle || '';
        MainAppDisplay._pageIndicators.style =
          `${originalStyle} transition-duration: ${this.pageSwitchAnimationTime}ms;`;
      }

      // Apply open animation time for folder dialogs
      if (MainAppDisplay._folderIcons && Array.isArray(MainAppDisplay._folderIcons)) {
        MainAppDisplay._folderIcons.forEach(icon => {
          this._safeExecute(() => {
            if (icon._dialog && icon._dialog.child) {
              const originalStyle = this.originalStates.get(icon)?.dialogStyle || '';
              icon._dialog.child.style =
                `${originalStyle} transition-duration: ${this.openAnimationTime}ms;`;
            }
          });
        });
      }
    });
  }

  applyBackgroundMode() {
    return this._safeExecute(() => {
      const actors = this._getBackgroundActors();
      if (!actors.length) return;

      // Root overview actor – this is where we want the single, unified overlay/gradient
      const rootOverview = Main.overview && Main.overview._overview;

      const mode = this.backgroundMode || 'system';

      for (const actor of actors) {
        if (!actor) continue;

        const isRoot = rootOverview && actor === rootOverview;

        if (!this.originalBackgroundStates.has(actor)) {
          this.originalBackgroundStates.set(actor, {
            style: actor.style || '',
            hadTransparentClass: actor.has_style_class_name?.('app-grid-tuner-bg-transparent') || false,
          });
        } else {
          actor.style = this.originalBackgroundStates.get(actor).style;
        }

        // Clear any background class we manage
        if (actor.remove_style_class_name) {
          actor.remove_style_class_name('app-grid-tuner-bg-transparent');
        }

        // Clear any background-related styles previously applied by the extension
        if (typeof actor.style === 'string' && actor.style.length > 0) {
          actor.style = actor.style
            .replace(/background-color:[^;]*;?/g, '')
            .replace(/background-image:[^;]*;?/g, '')
            .replace(/background-gradient-direction:[^;]*;?/g, '')
            .replace(/background-gradient-start:[^;]*;?/g, '')
            .replace(/background-gradient-end:[^;]*;?/g, '');
        }

        if (mode === 'transparent') {
          // Make all actors transparent so that the Shell's own background becomes visible
          if (actor.add_style_class_name)
            actor.add_style_class_name('app-grid-tuner-bg-transparent');
        } else if (mode === 'solid-color') {
          const color = this.backgroundColor;
          if (isRoot && color && color.startsWith('#')) {
            actor.style = (actor.style || '') + `background-color: ${color};`;
          }
        } else if (mode === 'gradient') {
          const primary = this.backgroundColor;
          const secondary = this.gradientSecondaryColor;

          const isHex = (c) => !!c && c.startsWith('#') && c.length === 7;

          let color1 = null;
          let color2 = null;

          if (isHex(primary) && isHex(secondary)) {
            // Use two explicit colors for the gradient
            color1 = primary;
            color2 = secondary;
          } else if (isHex(primary)) {
            // Derive the second color automatically as a slightly darker shade
            const r = parseInt(primary.slice(1, 3), 16);
            const g = parseInt(primary.slice(3, 5), 16);
            const b = parseInt(primary.slice(5, 7), 16);

            const shade = (v, factor) => {
              const nv = Math.max(0, Math.min(255, Math.round(v * factor)));
              const hex = nv.toString(16).padStart(2, '0');
              return hex;
            };

            color1 = primary;
            const r2 = shade(r, 0.8);
            const g2 = shade(g, 0.8);
            const b2 = shade(b, 0.8);
            color2 = `#${r2}${g2}${b2}`;
          }

          if (!color1 || !color2)
            continue;

          // Use GNOME Shell's specific gradient properties instead of standard background-image,
          // because the Shell CSS engine supports these reliably.
          const type = this.gradientType || 'linear-vertical';
          const direction = (type === 'linear-horizontal') ? 'horizontal' : 'vertical';

          // These properties are used and supported in gnome-shell.css as well.
          if (isRoot) {
            actor.style = (actor.style || '') +
              `background-gradient-direction: ${direction};` +
              `background-gradient-start: ${color1};` +
              `background-gradient-end: ${color2};`;
          }
        }
      }
    });
  }

  _updateDynamicStylesheet(color) {
    // General-purpose dynamic stylesheet for label color and app hover tile styles.
    // Unload existing dynamic stylesheet immediately
    if (this._dynamicStylesheet) {
      const themeContext = St.ThemeContext.get_for_stage(global.stage);
      const theme = themeContext.get_theme();
      if (theme) {
        theme.unload_stylesheet(this._dynamicStylesheet);
      }
      this._dynamicStylesheet = null;
    }

    const {
      labelColor,
      labelStyle,
      labelShadowColor,
      appHoverTileEnabled,
      appHoverTileBackgroundColor,
      appHoverTileBackgroundOpacity,
      appHoverTileBorderColor,
      appHoverTileBorderRadius,
    } = color || {};

    let cssContent = '';

    // Dynamic label color (app grid labels)
    if (labelColor && labelColor.startsWith('#')) {
      cssContent += `
.app-grid-tuner-dynamic-color .icon-label,
.app-grid-tuner-dynamic-color .overview-icon-label,
.app-grid-tuner-dynamic-color StLabel {
  color: ${labelColor} !important;
}
`;
    }

    const normalizedLabelStyle = labelStyle && labelStyle.length >= 2 &&
      labelStyle.startsWith("'") &&
      labelStyle.endsWith("'")
      ? labelStyle.slice(1, -1)
      : labelStyle;

    if (normalizedLabelStyle) {
      let styleForCss = normalizedLabelStyle;
      if (labelShadowColor && labelShadowColor.startsWith('#')) {
        styleForCss = styleForCss.replace(
          /text-shadow:\s*([^;]*?)(#[0-9a-fA-F]{6}|rgb[a]?\([^)]+\))/g,
          `text-shadow: $1${labelShadowColor}`
        );
      }

      const declarations = styleForCss
        .split(';')
        .map(part => part.trim())
        .filter(Boolean)
        .map(part => {
          const separatorIndex = part.indexOf(':');
          if (separatorIndex === -1)
            return null;
          const property = part.slice(0, separatorIndex).trim();
          const value = part.slice(separatorIndex + 1).trim();
          return `${property}: ${value} !important;`;
        })
        .filter(Boolean);

      if (!declarations.some(part => part.startsWith('text-shadow:')))
        declarations.push('text-shadow: none !important;');

      cssContent += `
.app-grid-tuner-label-style .icon-label,
.app-grid-tuner-label-style .overview-icon-label,
.app-grid-tuner-label-style StLabel {
  ${declarations.join('\n  ')}
}
`;
    }

    // Dynamic app hover tile styling
    if (appHoverTileEnabled) {
      const isHex = (c) => !!c && c.startsWith('#') && c.length === 7;
      const opacity = Math.max(0, Math.min(1, appHoverTileBackgroundOpacity ?? 0.08));

      const hexToRgba = (hex, a) => {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        if (a >= 1)
          return `rgb(${r}, ${g}, ${b})`;
        return `rgba(${r}, ${g}, ${b}, ${a})`;
      };

      const declarations = [];

      if (isHex(appHoverTileBackgroundColor)) {
        const bg = hexToRgba(appHoverTileBackgroundColor, opacity);
        declarations.push(`background-color: ${bg};`);
      }

      if (appHoverTileBorderRadius && appHoverTileBorderRadius > 0) {
        declarations.push(`border-radius: ${appHoverTileBorderRadius}px;`);
      }

      if (appHoverTileBorderColor && appHoverTileBorderColor.startsWith('#')) {
        declarations.push(`box-shadow: 0 0 0 1px ${appHoverTileBorderColor};`);
      }

      if (declarations.length > 0) {
        cssContent += `
.app-grid-tuner-app-hover .app-well-app:hover {
  ${declarations.join('\n  ')}
}
`;
      }
    }

    if (!cssContent.trim())
      return;

    const cacheDir = GLib.get_user_cache_dir();
    const tunerDir = GLib.build_filenamev([cacheDir, 'app-grid-tuner']);
    const cssPath = GLib.build_filenamev([tunerDir, 'dynamic.css']);

    if (GLib.mkdir_with_parents(tunerDir, 0o755) !== 0) {
      // directory creation failed, but we try writing anyway
    }

    const file = Gio.File.new_for_path(cssPath);
    
    try {
      const [success] = file.replace_contents(
        cssContent,
        null,
        false,
        Gio.FileCreateFlags.REPLACE_DESTINATION,
        null
      );

      if (success) {
        const themeContext = St.ThemeContext.get_for_stage(global.stage);
        if (themeContext) {
          const theme = themeContext.get_theme();
          if (theme) {
            theme.load_stylesheet(file);
            this._dynamicStylesheet = file;
          }
        }
      }
    } catch (e) {
      console.error(`[AppGridTuner] Failed to write dynamic stylesheet: ${e.message}`);
    }
  }

  startAppGridTuning() {
    if (!this.isCompatible) {
      console.warn('[AppGridTuner] Extension is not compatible with current GNOME Shell version');
      return;
    }

    return this._safeExecute(() => {
      const MainAppDisplay = this._getAppDisplay();
      if (!MainAppDisplay) return;

      let appGrid = MainAppDisplay._grid;
      if (!appGrid) {
        console.warn('[AppGridTuner] App grid not available');
        return;
      }

      if (this.reloadSignal) {
        this.settings.disconnect(this.reloadSignal);
        this.reloadSignal = 0;
      }

      this.reloadSignal = this.settings.connect('changed::reload-signal', () => {
        this.undoChanges();
        this.startAppGridTuning();
      });

      const gridRows = this.settings.get_int("appgrid-max-rows");
      const gridCols = this.settings.get_int("appgrid-max-columns");
      const rawLabelStyle = this.settings.get_string("label-style") || "";
      const labelStyle = rawLabelStyle.length >= 2 &&
        rawLabelStyle.startsWith("'") &&
        rawLabelStyle.endsWith("'")
        ? rawLabelStyle.slice(1, -1)
        : rawLabelStyle;
      const labelColor = this.settings.get_string("label-color") || "";
      const labelShadowColor = this.settings.get_string("label-shadow-color") || "";
      const appHoverTileEnabled = this.settings.get_boolean("app-hover-tile-enabled");
      const appHoverTileBackgroundColor = this.settings.get_string("app-hover-tile-background-color") || '';
      const appHoverTileBackgroundOpacity = this.settings.get_double("app-hover-tile-background-opacity");
      const appHoverTileBorderColor = this.settings.get_string("app-hover-tile-border-color") || '';
      const appHoverTileBorderRadius = this.settings.get_int("app-hover-tile-border-radius");
      
      // Reset any previously applied label color and tile classes
      const knownLabelColorClasses = [
        'app-grid-tuner-label-blue',
        'app-grid-tuner-label-green',
        'app-grid-tuner-label-orange',
        'app-grid-tuner-label-red',
        'app-grid-tuner-custom-color',
        'app-grid-tuner-dynamic-color',
        'app-grid-tuner-label-style',
      ];
      if (appGrid.remove_style_class_name) {
        for (const cls of knownLabelColorClasses)
          appGrid.remove_style_class_name(cls);
        appGrid.remove_style_class_name('app-grid-tuner-app-hover');
      }

      // Apply the selected label color class (if any)
      if (labelColor && appGrid.add_style_class_name) {
        if (labelColor.startsWith('#')) {
           appGrid.add_style_class_name('app-grid-tuner-dynamic-color');
        } else {
           appGrid.add_style_class_name(labelColor);
        }
      }

      if (labelStyle && appGrid.add_style_class_name)
        appGrid.add_style_class_name('app-grid-tuner-label-style');

      // Update dynamic stylesheet for label color and app hover tile styling
      this._updateDynamicStylesheet({
        labelColor: labelColor && labelColor.startsWith('#') ? labelColor : null,
        labelStyle: labelStyle || null,
        labelShadowColor: labelShadowColor && labelShadowColor.startsWith('#') ? labelShadowColor : null,
        appHoverTileEnabled,
        appHoverTileBackgroundColor,
        appHoverTileBackgroundOpacity,
        appHoverTileBorderColor,
        appHoverTileBorderRadius,
      });

      // Apply hover tile styling for app icons if enabled
      if (appHoverTileEnabled && appGrid.add_style_class_name) {
        appGrid.add_style_class_name('app-grid-tuner-app-hover');
      }

      // Apply app icon label font size only when explicitly configured (> 0).
      // A value of 0 means "use system default" and should not override font size.
      const appIconFontSize = this.settings.get_double("app-icon-font-size");
      let fontSizeStyle = "";
      if (appIconFontSize > 0) {
        fontSizeStyle = `font-size: ${appIconFontSize}px;`;
      }

      if (!this.originalGridState) {
        this.originalGridState = {
          fixedIconSize: appGrid.layout_manager.fixedIconSize,
          rowsPerPage: appGrid.layout_manager.rowsPerPage,
          columnsPerPage: appGrid.layout_manager.columnsPerPage,
          gridModes: appGrid._gridModes?.map(mode => ({...mode})),
          currentMode: appGrid._currentMode,
          style: appGrid.style,
          pageIndicatorStyle: MainAppDisplay._pageIndicators?.style || '',
          adaptToSize: MainAppDisplay.adaptToSize,
        };
      }

      appGrid.style = `${this.originalGridState?.style || ''} ${fontSizeStyle}`;

      this.iconSize = this.settings.get_int("appgrid-icon-size");
      this.folderIconSize = this.settings.get_int("folder-icon-size");
      this.hideFolderTitle = this.settings.get_boolean("hide-folder-title");
      this.fRows = this.settings.get_int("folder-max-rows");
      this.fColumns = this.settings.get_int("folder-max-columns");
      this.sidePadding = this.settings.get_int("side-padding");
      this.folderSidePadding = this.settings.get_int("folder-side-padding");
      this.folderPopupWidth = this.settings.get_int("folder-popup-width");
      this.folderPopupHeightOffset = this.settings.get_int("folder-popup-height-offset");
      this.folderItemSpacing = this.settings.get_int("folder-item-spacing");
      this.folderItemHeightOffset = this.settings.get_int("folder-item-height-offset");
      this.folderPopupBackgroundColor = this.settings.get_string("folder-popup-background-color") || '';
      this.folderPopupBackgroundOpacity = this.settings.get_double("folder-popup-background-opacity");
      this.folderPopupBorderColor = this.settings.get_string("folder-popup-border-color") || '';
      this.folderPopupBorderRadius = this.settings.get_int("folder-popup-border-radius");
      this.folderTileBackgroundColor = this.settings.get_string("folder-tile-background-color") || '';
      this.folderTileBackgroundOpacity = this.settings.get_double("folder-tile-background-opacity");
      this.folderTileBorderColor = this.settings.get_string("folder-tile-border-color") || '';
      this.folderTileBorderRadius = this.settings.get_int("folder-tile-border-radius");
      this.folderIconLabelFontSize = this.settings.get_double("folder-icon-font-size");
      this.openAnimationTime = this.settings.get_int("open-animation-time");
      this.pageSwitchAnimationTime = this.settings.get_int("page-switch-animation-time");
      this.backgroundMode = this.settings.get_string("appgrid-background-mode") || 'system';
      this.backgroundColor = this.settings.get_string("appgrid-background-color") || '';
      this.gradientType = this.settings.get_string("appgrid-gradient-type") || 'linear-vertical';
      this.gradientSecondaryColor = this.settings.get_string("appgrid-gradient-secondary-color") || '';
      
      appGrid.layout_manager.fixedIconSize = this.iconSize;
      
      // Store and override adaptToSize function safely
      if (MainAppDisplay.adaptToSize) {
        this.defaultAdaptToSizeFunction = MainAppDisplay.adaptToSize;
        MainAppDisplay.adaptToSize = this.overriddenAdaptToSizeFunction.bind(this);
      }

      if(MainAppDisplay._folderIcons && MainAppDisplay._folderIcons.length > 0) {
        this.applyFolderViewChanges();
      }
       
      if (this.reloadingSig) {
        MainAppDisplay.disconnect(this.reloadingSig);
      }

      this.reloadingSig = MainAppDisplay.connect("view-loaded", ()=> {
        this.applyFolderViewChanges();  
        this.applyAnimationSettings();
      });

      // Apply initial animation and background settings
      this.applyAnimationSettings();   
      this.applyBackgroundMode();

      // Apply grid modes via API and enforce mode 0
      if (appGrid.setGridModes) {
        appGrid.setGridModes([{ rows: gridRows, columns: gridCols }]);
      } else if (appGrid._gridModes && appGrid._gridModes[0]) {
        appGrid._gridModes[0] = { rows: gridRows, columns: gridCols };
      }

      appGrid._currentMode = 0; 
      appGrid.layout_manager.rowsPerPage      = gridRows;
      appGrid.layout_manager.columnsPerPage   = gridCols;

      // Force re-layout and icon size recomputation
      appGrid.layout_manager.fixedIconSize = this.iconSize;
      if (appGrid.layout_manager._pageWidth !== undefined) {
        appGrid.layout_manager._pageWidth--;
        appGrid.layout_manager.adaptToSize(appGrid.layout_manager._pageWidth, appGrid.layout_manager._pageHeight);
      }

      if (MainAppDisplay._redisplay) {
        MainAppDisplay._redisplay();
      }
    });
  }

  undoChanges() {
    return this._safeExecute(() => {
      const MainAppDisplay = this._getAppDisplay();
      if (!MainAppDisplay) return;

      let appGrid = MainAppDisplay._grid;
      if (!appGrid || !appGrid.layout_manager) return;

      // Restore original grid state
      if (this.originalGridState) {
        if (appGrid.layout_manager._pageWidth !== undefined) {
          appGrid.layout_manager._pageWidth--;
        }
        
        if (this.defaultAdaptToSizeFunction && MainAppDisplay.adaptToSize) {
          MainAppDisplay.adaptToSize = this.defaultAdaptToSizeFunction;
        }
        
        appGrid.layout_manager.fixedIconSize = this.originalGridState.fixedIconSize;
        appGrid.layout_manager.rowsPerPage = this.originalGridState.rowsPerPage;
        appGrid.layout_manager.columnsPerPage = this.originalGridState.columnsPerPage;
        appGrid.style = this.originalGridState.style;

        if (this.originalGridState.gridModes && appGrid.setGridModes) {
          appGrid.setGridModes(this.originalGridState.gridModes);
        } else if (this.originalGridState.gridModes && appGrid._gridModes) {
          appGrid._gridModes = this.originalGridState.gridModes.map(mode => ({...mode}));
        }

        if (this.originalGridState.currentMode !== undefined)
          appGrid._currentMode = this.originalGridState.currentMode;

        if (MainAppDisplay._pageIndicators)
          MainAppDisplay._pageIndicators.style = this.originalGridState.pageIndicatorStyle;

        if (appGrid.layout_manager._pageWidth !== undefined && appGrid.layout_manager._pageHeight !== undefined) {
          appGrid.layout_manager.adaptToSize(appGrid.layout_manager._pageWidth, appGrid.layout_manager._pageHeight);
        }
      }
      
      // Restore folder states
      this.originalStates.forEach((originalState, icon) => {
        this._safeExecute(() => {
          if (icon.view && icon.view._grid && icon.view._grid.layout_manager) {
            icon.view._grid.layout_manager.fixedIconSize = originalState.fixedIconSize;
            icon.view._grid.layout_manager.rowsPerPage = originalState.rowsPerPage;
            icon.view._grid.layout_manager.columnsPerPage = originalState.columnsPerPage;
            if (originalState.gridStyle !== undefined) {
              icon.view._grid.style = originalState.gridStyle;
            }
          }

          if (originalState.tile && originalState.tileStyle !== undefined)
            originalState.tile.style = originalState.tileStyle;

          if (icon._dialog && icon._dialog.child) {
            if (icon._dialog.remove_style_class_name)
              icon._dialog.remove_style_class_name('app-grid-tuner-hide-folder-title');

            if (originalState.dialogStyle !== undefined) {
              icon._dialog.child.style = originalState.dialogStyle;
            }

            // Style only the inner content actor (the visible dark box),
            // so the full-screen overlay behind it keeps the theme appearance.
            let inner = null;
            try {
              if (icon._dialog.child && icon._dialog.child.get_first_child)
                inner = icon._dialog.child.get_first_child();
            } catch (e) {
              inner = null;
            }

            if (inner && originalState.innerDialogStyle !== undefined) {
              inner.style = originalState.innerDialogStyle;
            }

            if (icon._dialog._scrollView) {
              const scrollView = icon._dialog._scrollView;

              if (originalState.scrollClip !== undefined) {
                scrollView.clip_to_allocation = originalState.scrollClip;
              }

              if (originalState.scrollContentPadding) {
                scrollView.content_padding = new Clutter.Margin({
                  left: originalState.scrollContentPadding.left,
                  right: originalState.scrollContentPadding.right,
                  top: originalState.scrollContentPadding.top,
                  bottom: originalState.scrollContentPadding.bottom,
                });
              }

              if (originalState.scrollPolicy && scrollView.set_policy) {
                const [hPolicy, vPolicy] = originalState.scrollPolicy;
                scrollView.set_policy(hPolicy, vPolicy);
              }
            }
          }
        });
      });

      const knownLabelColorClasses = [
        'app-grid-tuner-label-blue',
        'app-grid-tuner-label-green',
        'app-grid-tuner-label-orange',
        'app-grid-tuner-label-red',
        'app-grid-tuner-custom-color',
        'app-grid-tuner-dynamic-color',
        'app-grid-tuner-label-style',
        'app-grid-tuner-app-hover',
      ];
      if (appGrid.remove_style_class_name) {
        for (const className of knownLabelColorClasses)
          appGrid.remove_style_class_name(className);
      }

      this.originalBackgroundStates.forEach((state, actor) => {
        actor.style = state.style;
        if (!state.hadTransparentClass)
          actor.remove_style_class_name('app-grid-tuner-bg-transparent');
      });
      this.originalBackgroundStates.clear();

      if (this.reloadingSig) {
        MainAppDisplay.disconnect(this.reloadingSig);
        this.reloadingSig = 0;
      }
      
      if (MainAppDisplay._redisplay) {
        MainAppDisplay._redisplay();
      }
    });
  }

  destroy() {
    if (this.reloadSignal) {
      this.settings.disconnect(this.reloadSignal);
      this.reloadSignal = 0;
    }

    const appDisplay = this._getAppDisplay();
    if (this.reloadingSig && appDisplay) {
      appDisplay.disconnect(this.reloadingSig);
      this.reloadingSig = 0;
    }

    this.undoChanges();
    
    // Unload dynamic stylesheet
    if (this._dynamicStylesheet) {
      const themeContext = St.ThemeContext.get_for_stage(global.stage);
      const theme = themeContext.get_theme();
      if (theme) {
        theme.unload_stylesheet(this._dynamicStylesheet);
      }
      this._dynamicStylesheet = null;
    }
    
    // Clear stored states and internal references
    this.originalStates.clear();
    this.originalGridState = null;
    this.defaultAdaptToSizeFunction = null;
    this.reloadingSig = 0;
    this.settings = null;
    this.extension = null;
  }
  
  overriddenAdaptToSizeFunction(width, height) {
    return this._safeExecute(() => {
      const MainAppDisplay = this._getAppDisplay();
      if (!MainAppDisplay) return;

      // Safely get indicator height
      let indicatorHeight = 0;
      if (MainAppDisplay._pageIndicators && MainAppDisplay._pageIndicators.get_preferred_height) {
        try {
          [, indicatorHeight] = MainAppDisplay._pageIndicators.get_preferred_height(-1);
        } catch (e) {
          console.warn(`[AppGridTuner] Failed to get indicator height: ${e.message}`);
        }
      }
      height -= indicatorHeight;

      let box = new Clutter.ActorBox({
        x2: width,
        y2: height,
      });
      
      // Safely apply theme nodes
      try {
        if (MainAppDisplay.get_theme_node) {
          box = MainAppDisplay.get_theme_node().get_content_box(box);
        }
        if (MainAppDisplay._scrollView && MainAppDisplay._scrollView.get_theme_node) {
          box = MainAppDisplay._scrollView.get_theme_node().get_content_box(box);
        }
        if (MainAppDisplay._grid && MainAppDisplay._grid.get_theme_node) {
          box = MainAppDisplay._grid.get_theme_node().get_content_box(box);
        }
      } catch (e) {
        console.warn(`[AppGridTuner] Theme node application failed: ${e.message}`);
      }

      const availWidth = box.get_width();
      const availHeight = box.get_height();

      let pageHeight = availHeight;
      let hPadding = this.sidePadding || 0;
      // Allow negative padding to override system padding, but ensure reasonable minimum
      let pageWidth = availWidth - hPadding * 2;
      
      // Ensure pageWidth doesn't exceed available width by too much (safety check)
      if (hPadding < 0) {
        pageWidth = Math.min(pageWidth, availWidth * 1.2); // Max 20% over available width
      }

      if (MainAppDisplay._grid && MainAppDisplay._grid.layout_manager && MainAppDisplay._grid.layout_manager.adaptToSize) {
        MainAppDisplay._grid.layout_manager.adaptToSize(pageWidth, pageHeight);
      }

      const vPadding = Math.floor((availHeight - (MainAppDisplay._grid?.layout_manager?.pageHeight || 0)) / 2);

      if (MainAppDisplay._scrollView) {
        MainAppDisplay._scrollView.content_padding = new Clutter.Margin({
          left: hPadding,
          right: hPadding,
          top: vPadding,
          bottom: vPadding,
        });
      }

      MainAppDisplay._availWidth = availWidth;
      MainAppDisplay._availHeight = availHeight;

      MainAppDisplay._pageIndicatorOffset = hPadding;
      MainAppDisplay._pageArrowOffset = Math.max(hPadding - 80, 0);
    });
  }  
    
}

export default class AppGridTunerExtension extends Extension {
  enable() {
    this.appGridTuner = new AppGridTuner(this);
    this.appGridTuner.startAppGridTuning();
  }

  disable() {
    this.appGridTuner?.destroy();
    this.appGridTuner = null;
  }
}
