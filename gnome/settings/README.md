# GNOME settings

Taken from the live laptop on 12 Oct 2026 (Fedora 44, GNOME 50.5).

- `extensions.dconf` - the settings of every installed extension, GSConnect
  left out (it holds the paired phone's id). Load it with
  `dconf load /org/gnome/shell/extensions/ < extensions.dconf`.
- `keybindings.dconf` - the window-manager shortcuts. Load it with
  `dconf load /org/gnome/desktop/wm/keybindings/ < keybindings.dconf`.
- `enabled-extensions.txt` - the 18 extensions that are installed and on.
  `org.gnome.shell enabled-extensions` in dconf also lists ~20 names that are
  no longer installed; that list is only a wish list, this file is what runs.

## Settings worth knowing about

| Setting | Value | Why |
|---|---|---|
| Just Perfection `animation` | `1` | GNOME's own animation speed (9 Oct). The key is Just Perfection's: setting `org.gnome.desktop.interface enable-animations` directly is overwritten on every shell reload. |
| Chakra Switch `open-in-overview` | `false` | Alt+Tab does nothing over the Overview and the app grid, like stock GNOME (11 Oct). |
| Super+Tab / Shift+Super+Tab | next / previous workspace | Super+Tab used to switch apps, which Alt+Tab already covers (12 Oct). `switch-applications` is now empty and the two keys sit first in `switch-to-workspace-right` / `-left`. GNOME does not wrap: at the last workspace Super+Tab stops. |
| Wallpaper `picture-uri` / `-dark` | `~/.local/share/backgrounds/background-2639x1440.png` | A Lanczos copy of the 7680x4191 `~/.config/background`; the original cost the shell 167MB of GPU memory for nothing on a 2560x1440 panel (12 Oct). Point both keys back at `file:///home/abdallah-shehawey/.config/background` to revert. |
| Blur My Shell rounded popups | needs `gnome-rounded-blur` | Blur My Shell 74's dynamic blur only rounds menus, Quick Settings, OSD and dialogs when this library is installed (6 Oct). It came from the Copr `aneagle/gnome-rounded-blur`, which now answers 404 for Fedora 44; the installed 1.0.1 keeps working. Source: https://github.com/kancko/gnome-rounded-blur. Check with `dconf read /org/gnome/shell/extensions/blur-my-shell/rounded-blur-found` (expect `true`). |

To make the wallpaper copy again:

```sh
magick ~/.config/background -filter Lanczos -resize x1440 \
  ~/.local/share/backgrounds/background-2639x1440.png
```
