// Added for the horizontal-tabs layout (chrome/userChrome.css).
// Delete this file to stop forcing these prefs.
user_pref("zen.tabs.vertical", false);
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);

// Ctrl+T floats the address box over the page you are on.
// Zen ties this to the startup screen (ZenSpaceManager.selectStartPage), so
// the price is that a fresh start shows Zen's blank tab with the search box
// instead of the New Tab page:
//   true  = Ctrl+T floats the box   (chosen)
//   false = start on the New Tab page, Ctrl+T opens that page in a tab
user_pref("zen.urlbar.replace-newtab", true);
// Hides the search box on that blank startup screen (the page stays blank):
// user_pref("zen.urlbar.open-on-startup", false);
// Or: bring back the tabs from last time instead of the blank screen, which
// keeps the floating Ctrl+T as well:
// user_pref("zen.workspaces.continue-where-left-off", true);

// where a new tab lands:
//   a tab you open FROM a page (a link) sits right next to that page
user_pref("browser.tabs.insertRelatedAfterCurrent", true);
//   a tab you open yourself (Ctrl+T, the + button) goes to the end
user_pref("browser.tabs.insertAfterCurrent", false);
// Zen puts new tabs right after the pinned ones when this is on; off = the end
user_pref("zen.view.show-newtab-button-top", false);
// tab open / close animations
user_pref("toolkit.cosmeticAnimations.enabled", true);

// Zen's compact mode is built for its vertical sidebar (it parks the whole
// toolbox off the left edge of the window), so it is kept off here - this is
// the pref the toggle writes, and without forcing it the browser comes back
// in that state after a restart.
user_pref("zen.view.compact.enable-at-startup", false);

// Firefox's Ctrl+Tab switcher shows at most SEVEN cards (maxTabPreviews is a
// constant in browser-ctrlTab.js, there is no pref for it), and Zen filters
// out every tab that has not been loaded yet - a restored or auto-unloaded tab
// carries [pending], and ctrlTab.tabList drops it. That is why the panel can
// come up with a handful of tabs while twenty are open. This puts them back in
// the list; the price is that such a card has no thumbnail yet.
user_pref("zen.ctrlTab.show-pending-tabs", true);

// Zen hides the "+" after the last tab unless this is on: vertical-tabs.css
// wraps #tabs-newtab-button in @media -moz-pref("zen.tabs.show-newtab-vertical")
// and ships it display:none otherwise.
user_pref("zen.tabs.show-newtab-vertical", true);

// The bookmarks strip only on the new-tab page (Firefox's own setting).
user_pref("browser.toolbars.bookmarks.visibility", "newtab");
// The downloads button appears on the first download and leaves again.
user_pref("browser.download.autohideButton", true);
