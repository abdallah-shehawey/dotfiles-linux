# Zen horizontal tabs

Zen Browser with the tabs on the **same row as the address bar** instead of the
vertical sidebar. Tested on Zen 1.21.15b and 1.23b (Linux).

![row](docs/row.png)

```
[sidebar][<][>][reload][home]  [ address ]  [ tab ][ tab ][ open tab ][ tab ] ... [_][□][X]
```

* one 36px toolbar row, everything on it
* every tab that is not the current one is a **120px box** with its favicon and its title, on its own faint pill - the same size whether the pointer is on it or not; its X fades in under the pointer without moving anything
* a **pinned** tab is a **38px favicon chip** instead, and opens to 120px while the pointer is on it
* the current tab is a **220px pill** with its title
* a full strip squeezes the 120px boxes down towards 24px rather than pushing the last tabs out of the window
* the address box is 280px, the address is centred, domain only
* a **"+"** sits after the last tab
* Ctrl+T's floating search box **fades and scales in**, its results fan in behind it
* a **private window is violet**, not the same black as a normal one
* one motion system: tabs grow and collapse on a single curve, the current
  tab's title slides in, buttons answer a press, split panes ease
* window buttons, app menu, downloads all keep working

## Install

Quit Zen completely, then:

```bash
./install.sh
```

It writes exactly two files into the profile and backs up anything already
there:

| file | what it does |
|---|---|
| `chrome/userChrome.css` | the whole layout |
| `user.js` | the handful of prefs the layout needs |

Nothing else in the profile is touched - bookmarks, history, accounts,
extensions, `zen-themes.css` and the mods folder are left alone.
`./uninstall.sh` deletes the two files and Zen goes back to normal.

## Tuning

Every size lives in one place, the top of `chrome/userChrome.css`:

```css
:root {
  --ctab-row: 36px;      /* height of the whole toolbar row */
  --ctab-strip: 30px;    /* height of the tab strip inside it */
  --ctab-tab: 120px;     /* width of a tab that is not the current one */
  --ctab-chip: 38px;     /* width of a PINNED tab: favicon only */
  --ctab-peek: var(--ctab-tab);   /* a pinned chip while the pointer is on it */
  --ctab-active: 220px;  /* width of the current tab */
  --ctab-label: 12px;    /* the title on a tab that is not the current one */
  --ctab-tab-h: 26px;    /* height of a tab */
  --ctab-right: 158px;   /* space kept for app menu + window buttons */
  --ctab-url: 280px;     /* width of the address box */
  --ctab-newtab: 26px;   /* width of the "+" that follows the last tab */
  --ctab-left: 128px;    /* back / forward / reload / home + their separator */
  --ctab-foot: 34px;     /* the downloads button at the far end of the row */
  --ctab-dl: 300px;      /* the download stack that hangs under that button */
  --ctab-gap: 8px;       /* room on each side of the address box */
  --ctab-private: 128, 116, 255;  /* the private-window accent, as R, G, B */

  --ctab-ease: cubic-bezier(0.2, 0.9, 0.25, 1);   /* things changing size */
  --ctab-ease-in: cubic-bezier(0.16, 1, 0.3, 1);  /* things arriving */
  --ctab-t-tab: 190ms;   /* a tab growing or collapsing */
  --ctab-t-peek: 130ms;  /* the hover preview */
  --ctab-t-omni: 300ms;  /* the floating address box arriving */
  --ctab-t-panel: 110ms;    /* the Ctrl+Tab switcher fading in */
  --ctab-t-menu: 130ms;     /* a panel's rows fading in */
  --ctab-d-menu: 30ms;      /* ...held that long so the popup window exists */
  --ctab-switch-zoom: 1.12; /* how big the Ctrl+Tab switcher is (cap ~1.14) */
  --ctab-t-switch: 130ms;   /* the selection moving from card to card */
  --ctab-switch-pop: 1.035; /* how much the selected card grows */
  --ctab-bm: 32px;          /* the bookmarks strip */
  --ctab-t-fast: 110ms;  /* colour, hover, press */
}
```

Edit, save, restart Zen.

## The prefs, and the one trade-off

`user.js` forces these:

| pref | why |
|---|---|
| `zen.tabs.vertical=false` | horizontal strip |
| `toolkit.legacyUserProfileCustomizations.stylesheets=true` | let Zen read `userChrome.css` |
| `zen.urlbar.replace-newtab=true` | Ctrl+T floats the address box over the page |
| `browser.tabs.insertRelatedAfterCurrent=true` | a link opens next to the page it came from |
| `browser.tabs.insertAfterCurrent=false` | Ctrl+T goes to the end of the strip |
| `zen.view.show-newtab-button-top=false` | new tabs at the end, not before the pinned ones |
| `zen.tabs.show-newtab-vertical=true` | reveals the "+" after the last tab - Zen ships it `display:none` |
| `zen.view.compact.enable-at-startup=false` | compact mode stays off (see below) |
| `toolkit.cosmeticAnimations.enabled=true` | tabs slide open and closed |
| `zen.ctrlTab.show-pending-tabs=true` | a tab that has not loaded yet still counts in the Ctrl+Tab switcher |

**The trade-off:** Zen ties the floating Ctrl+T box and the startup screen to
the *same* pref (`ZenSpaceManager.selectStartPage`). With
`zen.urlbar.replace-newtab=true` you get the floating box on Ctrl+T but Zen
starts on its blank tab; with `false` you start on the New Tab page but Ctrl+T
opens that page in a tab. There is no third setting - `browser.startup.page`,
`browser.startup.homepage=about:newtab` and `zen.urlbar.open-on-startup` were
all tested and none of them changes it. Two alternatives sit commented out at
the top of `user.js`.

## Motion

Zen already animates a lot of the browser in JS, with the Motion library, and
the rule this file follows is **never transition a property Zen is animating**.
A CSS transition on such a property does not replace the JS animation, it puts
an ease in front of every frame the JS writes: with `opacity` in the tab
transition, a new tab's fade crawled `1.00 -> 0.74 -> 0.51 -> ... -> 0.00`
instead of following Motion. So the split is:

| owned by this file | owned by Zen's JS |
|---|---|
| tab `width` / `min-width` / `max-width` / `height` | tab `opacity` and `scale` on open and close |
| the current tab's title sliding in | dragging a tab to reorder |
| button press, favicon hover, the X | pinning, spaces, glance, downloads |
| split-view panes (`inset`) | compact mode |

Two things Zen writes for the **vertical** sidebar are cancelled here, because
in a horizontal row they are a vertical hop: `margin-bottom` on tab open/close
(the horizontal equivalent, the width transition, is already free) and a stray
`transform: translateY()` on the pinned-tabs separator.

Menus and panels are shaped the same way and animate differently, and the
difference is not a choice. A **`<panel>`** - the app menu behind the three
dots, the extension panels - fades its rows in on every open: Gecko adds
`animate` and `panelopen` when it opens and removes them when it closes, and
its rows genuinely re-animate (verified over three consecutive opens of
`#appMenu-popup`: one animation each time, opacity starting at ~0.01). A
**right-click menu does not, and cannot.** A `menupopup` keeps its layout after
the first time it is opened - measured on both `#tabContextMenu` and
`#contentAreaContextMenu`, the rows still report a 174px width with the popup
shut - so the CSS animation is created once, on open #1, and nothing restarts
it: opens #2 to #5 have zero animations and opacity 1. There is nothing to key
a restart on either; a MutationObserver over two full open/close cycles caught
exactly one attribute on the popup, `hasbeenopened="true"`, and it is sticky.
An entrance that plays on the first right-click of a session and never again is
worse than none, so the rows there are left alone.

What was there before was 200ms per row on a 10ms stagger behind a 50ms hold,
which on a 19-row menu meant the last row was not fully visible until **+310ms**
from `popupshown`, arriving one after another - "the menu hangs while it fills
up". The panel entrance that replaced it is one 130ms fade with every row on
the same clock, done at **+130ms**, measured. The 30ms hold in front of it is
not padding: a popup's first painted frame lands several frames after it opens,
and without the hold the fade is over before the window is on screen. Closing
was never animated and cannot be: the popup is torn down synchronously.

Shape reaches the box the same indirect way: `menupopup::part(content)` is not
honoured from USER origin (a `padding: 21px` set that way left the part at
5px), but inherited custom properties cross into the shadow tree, so
`--panel-border-radius` and `--panel-padding` land. Colours are left to Zen -
everything here derives from `currentColor`, so a theme change cannot strand
it. A popup's own frame is **not** animated. On Linux each menu and panel is its
own OS-level window and both routes are closed from a user stylesheet:
`panel::part(content)` is not honoured from USER origin (verified - an
`outline` set that way never reached the element), and `-moz-window-transform`
/ `-moz-window-opacity` are not supported in this build. What a popup's
*contents* do is another matter, but only for some of them: a `<panel>`
re-animates its rows on every open, a `menupopup` keeps its frames and animates
exactly once per session. Which is why the app menu fades in, the Ctrl+Tab
switcher fades in, and the right-click menu simply appears.

### Why one pixel of `#nav-bar` used to be never still

Firefox stops its refresh driver when nothing is changing on screen, and it
does not reset the animation clock when it starts again. An animation created
by a synchronous style flush - which is what Ctrl+T is, since Zen sets the
attributes and immediately measures the box - is stamped with the *last* tick's
time, so if the browser has been quiet for longer than the animation lasts, the
first frame it is ever sampled on is already past its end. Measured here on the
300ms entrance: with the clock idle 868ms it was alive for **0 of the next 97
frames**, and `animationstart` and `animationend` fired in the same
millisecond; with the clock fresh, 285ms and 42 frames. That is the whole
reason clicking "+" always animated and Ctrl+T often did not - reaching for the
mouse repaints the row and refreshes the clock, a keyboard shortcut on a page
that has finished loading does not.

The only lever CSS has is to keep that clock running, and only an animation
Gecko thinks is worth sampling will do it. Clock lag after five seconds of
complete quiet:

| keep-alive | lag |
|---|---|
| none | 58 191 ms |
| a custom property (`--x: 0 -> 1`) | 64 576 ms - throttled, it changes nothing |
| `opacity: .999 -> 1` | 5 590 ms - runs on the compositor, the main thread still sleeps |
| `background-color` on a 1px `::after` | 12 565 ms - XUL box, the pseudo never rendered |
| **`outline-color` on a real 1px outline** | **26 ms** |

That keep-alive is in the file and it is **on**, with one change: the timing
function is `steps(2)`, not `linear`. The animation is still active and still
sampled on every tick - which is all the clock needs - but its value only
changes twice per cycle, so there is nothing to repaint in between. Measured in
a driven window: clock lag after 3.5s of complete quiet, and paints during 1.5s
of idle.

| keeper | clock lag | paints while idle |
|---|---|---|
| none | 3491 ms | 0 |
| `linear` on `#nav-bar` | 6 ms | 3 |
| **`steps(2)` on `#nav-bar`** | **2 ms** | **2** |
| `steps(2)` on the app-menu button | 5 ms | 1 |

An earlier version of this README claimed the linear keeper was compositing the
whole window every frame. That was inferred, never measured, and the table says
otherwise - three paints in a second and a half. The real cost of either is a
refresh tick and one element's style sample per frame.

It runs in every window now, focused or not: the old
`:not(:-moz-window-inactive)` guard is gone, because a window is "inactive"
more often than it looks - a driven window that had been focused and put
fullscreen still matched it - and a keeper that quietly stops leaves exactly
the "it animated once and never again" bug behind. Verified with it on: three
consecutive Ctrl+T boxes and three consecutive Ctrl+Tab panels, clock lag never
above 17ms, every one of them animating.

### The Ctrl+Tab switcher

Only exists if `browser.ctrlTab.sortByRecentlyUsed` is on. Firefox lays it out
as **one screen-wide ribbon**, and that is structural rather than a style
choice - `browser-ctrlTab.js` writes an inline `panel.style.width` of
`canvasWidth * 1.25 * tabCount` (with `canvasWidth` always `availWidth * 0.85 / 7`)
and then positions the popup from that same number, so ~2530px on a 2560px
screen. Overriding the width from CSS would leave the popup anchored where a
2530px box was meant to start, i.e. against the left edge.

So the popup frame is made **invisible** and `#ctrlTab-previews` becomes the
visible card, centred inside it: a dark rounded panel in **one row**, with the
frame staying screen-wide behind it where nobody can see it. One row is
structural too - `ctrlTab.js` positions the popup vertically at
`(availHeight - (canvasHeight * 1.25 + 75)) / 2`, the height of a *single* row
of thumbnails, so a wrapped grid is taller than the estimate, grows downward
from a top computed for a short panel, and sits visibly below centre.

Three things were tried here and measured back out, and the panel is fast
because none of them survived:

| what went, what stayed | why |
|---|---|
| `backdrop-filter: blur(28px)` - **gone** | blurring a ~1800x640 region of a screen-wide transparent popup every frame, over seven scaled canvases, for a card that is 92% opaque anyway |
| four rounded `clip-path`s per card - **gone** | masks, up to 28 of them nested; `border-radius` does the same job on the fast path |
| a staggered per-card fade - **gone** | Firefox already waits 200ms before showing this panel, and the stagger then held the cards invisible for **another 325ms** after `popupshown` |
| one fade on the box - **kept** | 110ms behind a 30ms hold: starts showing at +43ms, done at **+134ms** (mean of three consecutive opens: 132 / 136 / 135), and it replays on every open - unlike a right-click menu, this panel rebuilds its state |
| `zoom: 1.12` - **kept** | the cards are what you are reading, and it is the only way to change their size: `ctrlTab.js` hard-codes `canvasWidth = availWidth * 0.85 / 7`. Cards measure 371px; seven of them drop to 1.05 or the ends are clipped by the popup window |
| the selection *moving* - **added** | the selected card grows to 1.035 and its fill crossfades over 130ms, so holding Tab reads as the highlight travelling along the row rather than teleporting |

None of that touches the number that actually decides how a Ctrl+Tab feels,
which is not in CSS at all: `browser-ctrlTab.js` opens the panel from a
hard-coded `setTimeout(..., 200)` with no pref behind it ("a quick ctrl-tab
just flips back to the MRU tab"), and it measures 205-216ms every time. The
entrance above is the 134ms that follows it.

### What an animation in this popup costs

Every flip was sampled over the 150ms that follows it, six flips per variant,
three rounds, on a 165Hz screen where a flip should collect ~26 frames:

| what is animating | frames per flip | p90 | worst frame |
|---|---|---|---|
| nothing (the highlight jumps) | 25.7 | 6.3ms | 14.4ms |
| any **one** property | 22.3 | 12.4ms | 15.9ms |
| two or three of them | 22.7 | 12.5ms | 15.7ms |
| ...with `box-shadow` among them | 18.5 | 16.5ms | **36.9ms** |

Two things fall out of that. One dropped frame in four is a **flat** cost of
having any animation in this popup - it does not scale with how many
properties move, so `scale` + the fill + the label together cost what `scale`
costs alone. And `box-shadow` is the exception that doubles it, which is why
the focus ring snaps on instead of fading: it also makes the keypress feel
answered instantly while the fill and the growth carry the motion.

As shipped, held-Tab flipping collects 21.8 frames per flip with a median of
6.1ms and a **worst frame of 14.3ms** - still inside a 60Hz budget, let alone
this screen's 6.1ms one, where it costs about one frame in five.

Two measurements that sound like they should have mattered and did not: the
panel's own translucency and its 30px drop shadow (making the box fully opaque
and dropping the shadow changed nothing), and `zoom` (a flip at `zoom: 1`
costs what a flip at 1.12 costs). Repainting the entire panel - all seven
cards, their canvases and their labels - is 1.6ms of CPU, measured with
`drawWindow` over the panel rect, less the 0.47ms the call itself costs.

Rounding is worth a note of its own, because the old one here was wrong.
An inline `borderRadius = "44px"` on a `.ctrlTab-preview` reads back `0px`,
which looked like border-radius being unsupported on those buttons. It is not:
the **Better CtrlTab Panel** mod declares `border-radius: var(--psu-...)
!important` with an unresolvable var, and an author `!important` beats a plain
inline style. The same declaration made from `userChrome.css` wins, because a
USER-origin `!important` outranks an author one - measured, 44px, taken. That
matters for speed, not tidiness: `clip-path: inset(0 round Npx)` rounds these
elements too, and the file used to use it on four elements per card. A rounded
clip-path is a **mask** - the subtree is drawn to an intermediate surface and
composited back through it - and there were up to 28 of those, nested, over
seven ~310px thumbnails, rebuilt on every paint. `border-radius` takes the
rounded-rect fast path.

If the **Better CtrlTab Panel** mod is installed, most of what it declares is
dead: its palette and metrics sit in a commented-out block and it expects Zen
to inject the pref values, so `var(--psu-better_ctrltab-*)` resolves to nothing
- and an unresolvable var does not mean "ignored", it means the whole
declaration computes to the initial value. Its rules win on specificity and
then evaluate to zero, which is where the flat grey sheet, the missing padding
and the square corners came from. Every value here outranks those selectors and
passes through `var(--psu-..., fallback)`, so the mod still wins whenever it
does resolve.

`--ctab-switch-zoom` is the size knob, and ~1.14 is its ceiling: the popup
window is `canvasWidth * 1.25` per tab (~389px) while a card plus its gap is
~341px, so past that the row is wider than the window it lives in and the ends
are cut off. Seven cards hit the `availWidth * 0.99` cap instead and drop to
1.05 on their own.

## The bookmarks strip, and two icons

The strip shows on the new tab page only, which is Firefox's own
`browser.toolbars.bookmarks.visibility = "newtab"`. That pref was already set
in the profile and did nothing, because this file used to carry a flat
`#PersonalToolbar { display: none }` that overrode it - it had to, since Zen
does not keep the strip in `#navigator-toolbox` at all. It lives in
`#zen-appcontent-navbar-container`, which this file pins `position: fixed`
top-right **because the window buttons share that same box**, so the strip was
trapped in a 36px corner. It is now pulled out into a full-width bar of its own
under the toolbar row, and the page is moved down to meet it.

That move has to be a `margin` on `#tabbrowser-tabpanels`, not padding: the
panels inside the deck are `position: absolute; inset: 0`, and an absolute
child resolves `top: 0` against its containing block's **padding box**, so
padding moves nothing. Measured with padding: the page still began at y=42 with
the strip sitting on top of it. With margin: y=74, exactly the strip's height
below the row.

Two icons in the address bar behave differently and only one of them is stuck.
The prompts' anchors (save-password, camera, location) live in
`#notification-popup-box` and already come and go with their prompt.
`#identity-permission-box` is the **key** that stays for as long as a site
holds any permission you have ever granted it - say yes to notifications once
and it is on that site forever. That one is hidden here; what it stands for is
still listed behind the padlock beside it. It is not moved to the right-hand
side because every permission doorhanger anchors to it, and moving the anchor
moves the arrow of every popup that points at it. The downloads button is not a
CSS matter at all - `browser.download.autohideButton` in `user.js` is what
makes it appear on the first download and leave again.

## Private windows

Zen tints a private window with `--zen-primary-color: rgb(11, 10, 11)`
(`zen-theme.css`). On a dark theme that is the same black as a normal window,
so the two are indistinguishable. `--ctab-private` at the top of the CSS paints
the window background, the address pill, the tab chips and a hairline above the
page, and both `[zen-private-window="true"]` (Zen's) and
`[privatebrowsingmode="temporary"]` (Firefox's) are matched.

The **tabs** in a private window used to be missing entirely. A private window
builds its space during init, before `#tabbrowser-tabs` is stamped horizontal,
so `tabs.js` propagates `orient="horizontal"` down to `.workspace-arrowscrollbox`
- a normal window restores its space from the session store afterwards and keeps
the template's `orient="vertical"`. The sideways `writing-mode: vertical-lr`
that makes the vertical strip run horizontally then turned that already-horizontal
row into a column, and every tab landed one full row *below* the toolbar. The
rule is now scoped to `[orient="vertical"]`.

## Compact mode is off

Zen's compact mode is built around the vertical sidebar: it makes
`#navigator-toolbox` a full-height box, parks it off the **left** edge of the
window and slides it back in while the pointer is near that edge. Here the
toolbox *is* the top row, so the state leaves the window with no toolbar and a
page that jumps whenever the pointer reaches the edge. The toggle is taken out
of the row, the pref is forced off, and the CSS puts the state back to normal
in case the keyboard shortcut ever turns it on.

## Does a Zen update wipe this?

No. Both files live in the **profile** (`~/.zen/<profile>/`), and updates
replace the application in `/opt/zen`, not the profile. What an update *can*
do is rename an internal element or class, and then a piece of the layout stops
matching - that is a CSS tweak, not a reinstall. This repo is the backup: after
any update, if something looks off, compare with `chrome/userChrome.css` here.

### What 1.23b changed (2026-10-03)

Four things, all of them the same shape: Zen added a box that assumes the
toolbar is the **left edge** of the window, and here it is the **top**.

| what | what it did | the rule |
|---|---|---|
| a new `#zen-sidebar-top-buttons-customization-target` wrapping the left buttons, both boxes carrying XUL `flex="1"` | the cluster resolved to **2.07px**, so CustomizableUI's overflow check ran `2 - 28` against 128px of buttons and swallowed **reload, home and the sidebar toggle** into a `>>` menu | `min-width: max-content` on both; the box asks for the 128px it holds, the `>>` goes away |
| the **Library** (`zen.library.enabled`), which replaced the downloads button with `#zen-library-button` | its panel is `top: 0` against `#browser`, so it opened **over** the whole row - tabs, address box and back/forward all unclickable - and cloned the window buttons into its own corner | `top: var(--ctab-lib-top)` (42px, where the content area starts) and the clone hidden |
| that button's download stack, `#zen-library-download-list`, `bottom: 100%` | all four cards sat **above** the top of the window, the newest poking 5px back onto the tab strip | turned over to `top: 100%` + `column-reverse`, so it hangs below the row |
| opening the Library writes an inline `transform: translateX(...)` on `#zen-appcontent-wrapper` - a push, so the page slides clear of the panel | the distance is wrong here: **`translateX(-1984px)`** at 2560 wide, which shoves 1984px of the page off the left and leaves its rightmost 576px painted under the panel. That is the "everything falls apart" screenshot | held still while the panel is open (`zen-library[open] ~ #zen-appcontent-wrapper`), and the panel - which has **no background of its own**, it was always drawn against the pushed-away backdrop - given `--zen-main-browser-background` and an edge shadow |

The `zen-sidebar-expanded="true"` trap is the one to remember - the root
carries it permanently with horizontal tabs, so every Zen rule written as
"only when the sidebar is collapsed" never fires here. That is what put the
media-controls bar in the row and the window-buttons clone on the Library.

Not checked on this build: the Ctrl+Tab switcher. Its popup is sized and
centred from `screen.availWidth`, not the window, so a headless run measures
it against a 1366px virtual screen and the numbers mean nothing - it has to
be looked at in a real window.
