# 🎮 Games: Windows games on Fedora, from the Steam library

Everything that was done (November 2026) to get four Windows games running
smoothly under Wine on this laptop, with every controller working, started
from Steam with their pictures. It is written as **step-by-step instructions
for an AI assistant**, plus two scripts that install and check all of it, so
any AI (or you) can rebuild the setup on a fresh install, or find and fix a
problem, without starting from zero.

| Game | Its README |
|---|---|
| eFootball PES 2021 | [pes-2021/README.md](pes-2021/README.md) |
| PES 2019 | [pes-2019/README.md](pes-2019/README.md) |
| Blur | [blur/README.md](blur/README.md) |
| WWE 2K Battlegrounds | [wwe-2k-battlegrounds/README.md](wwe-2k-battlegrounds/README.md) |
| Controllers + the Controller Settings app (and installing it in Steam) | [controllers/README.md](controllers/README.md) |
| Performance: split locks, CPU cores, 60 Hz, GPU | [performance/README.md](performance/README.md) |

## How to use it

**Yourself, in a terminal:**

```bash
cd ~/Projects/dotfiles-linux/games
./check.sh       # shows what is fine (✓) and what is broken (✗), changes nothing
./install.sh     # fixes what is missing (close Steam first); run it again any time
```

`install.sh` never asks for your password itself: if something needs `sudo`,
it prints the exact command at the end under **THE OWNER MUST DO**.

**With an AI** that can run commands on the laptop (Claude Code or similar),
paste:

```text
Read games/AI-PROMPT.md in my dotfiles-linux repository and follow it exactly.
Then read the README.md of every game folder under games/.
Goal: every game in my Steam library starts with Play, runs smoothly, and
all my controllers work. Fix anything that is broken. Ask me before
anything that needs my password, downloads something, or deletes something.
```

For one game only, add: `Only fix <game name>.`

بالعربي: افتح Terminal في الفولدر ده واكتب `./check.sh` تشوف إيه شغال وإيه لأ، وبعدين
`./install.sh` (اقفل Steam الأول) يصلّح الناقص. أو افتح أي AI بيقدر يشغّل أوامر على
اللابتوب (زي Claude Code) والزق الرسالة اللي فوق زي ما هي: هيقرا
[AI-PROMPT.md](AI-PROMPT.md) والريدمي بتاع كل لعبة، ويمشي خطوة خطوة، ويسألك قبل أي حاجة
محتاجة الباسورد أو تحميل أو مسح.

## What is in this folder

| Path | What | Goes to |
|---|---|---|
| [AI-PROMPT.md](AI-PROMPT.md) | The main instructions: rules, the machine, phases A-F, troubleshooting, final check | — |
| [install.sh](install.sh) / [check.sh](check.sh) | Install everything / check everything (`lib.sh` holds the game table they share) | run from here |
| [common/](common/) | Shared launchers and tools: `steam-launch.sh`, `game-env.sh`, `game-session.py`, `pads.sh`, `pad_maps.py`, `pad-settings.py` (Controller Settings app), `play-*.sh`, DXVK configs, PES 2019 start-up fixes, `rumble-boost/` | `/media/Games/common/` |
| [pes-2021/](pes-2021/) | PES 2021's own launcher, `dxvk.conf`, `game-session.py` | `/media/Games/eFootball-PES-2021/` |
| `<game>/art/` | Steam pictures for each game: `cover.png`, `wide.png`, `hero.png`, `logo.png`, `icon.png` | Steam's `grid/` folder + the icon theme |
| `<game>/settings/` | The owner's game settings: PES `settings.dat` + in-game settings (Arabic commentary, graphics), Blur `settings.xml`, WWE `GameUserSettings.ini` | the game's settings folder |
| [config/gamemode.ini](config/gamemode.ini) | CPU governor back to normal after a game | `~/.config/gamemode.ini` |
| [config/game-pads/mappings.txt](config/game-pads/mappings.txt) | The owner's saved button map (Twin USB pads) | `~/.config/game-pads/mappings.txt` |
| [config/applications/](config/applications/) | Hidden `.desktop` files that give each game window its dock icon | `~/.local/share/applications/` |
| [tools/steam/steam-shortcut.py](tools/steam/steam-shortcut.py) | Adds or updates a game (or Controller Settings) in Steam: launcher, pictures, icon, Steam Input off, overlay off, dock icon | run from here |
| [tools/pes-settings-dat.py](tools/pes-settings-dat.py) | Reads / sets resolution and full screen in PES 2019 / 2021 `settings.dat` | run from here |

The games themselves and the game saves are **not** in this repository.

## The fixes, in one line each

- **Stutter in every game:** split locks punished by the kernel → user in the
  `gamemode` group, GameMode turns `split_lock_mitigate` off while playing.
- **Judder at 60 fps on a 165 Hz screen:** the screen switches to 60 Hz while a game runs.
- **Games on the slow cores:** pinned to the P-cores 0-11.
- **Steam breaks Wine and the pads:** `steam-launch.sh` starts every game with a clean environment.
- **Controllers:** one map and one player order for every game, set in our
  Controller Settings app (it is in the Steam library too); Wine's XInput slot
  order is computed so Player 1 is Player 1.
- **PES 2021 / 2019 no vibration:** `rumble-boost` makes the game's weak pulses strong enough.
- **PES 2019 white screen:** DXVK must not hide the NVIDIA card.
- **PES 2019 78 s start:** split locks in its start-up code; start-up runs on
  the E-cores and a 48-byte stack shift in the exe → title at 30 s.
- **PES settings tool shows nothing:** resolution written straight into `settings.dat`.
- **Blur crash mid-race:** Microsoft's `msvcr90` instead of Wine's.
- **Blur speed:** 32-bit DXVK `d3d9.dll` from Proton in the game folder.
- **WWE closes at once in Steam:** the launcher waits for the real game exe.
- **Games in Steam with their pictures, and the right dock icon** for every game window.

Generic version for friends (any game, any distro, with a video):
<https://github.com/abdallah-shehawey/Gaming-on-Linux>
