# 🎮 Games: Windows games on Fedora, from the Steam library

Everything that was done (November 2026) to get four Windows games running
smoothly under Wine on this laptop, with every controller working, started
from Steam. It is written as **step-by-step instructions for an AI
assistant**, so any AI that can run commands can rebuild the setup on a fresh
install, or find and fix a problem, without starting from zero.

| Game | Its README |
|---|---|
| eFootball PES 2021 | [pes-2021/README.md](pes-2021/README.md) |
| PES 2019 | [pes-2019/README.md](pes-2019/README.md) |
| Blur | [blur/README.md](blur/README.md) |
| WWE 2K Battlegrounds | [wwe-2k-battlegrounds/README.md](wwe-2k-battlegrounds/README.md) |
| Controllers + the Controller Settings app | [controllers/README.md](controllers/README.md) |

## How to use it

Open an AI assistant that can run commands on the laptop (Claude Code or
similar) and paste:

```text
Read games/AI-PROMPT.md in my dotfiles-linux repository and follow it exactly.
Then read the README.md of every game folder under games/.
Goal: every game in my Steam library starts with Play, runs smoothly, and
all my controllers work. Fix anything that is broken. Ask me before
anything that needs my password, downloads something, or deletes something.
```

For one game only, add: `Only fix <game name>.`

بالعربي: افتح أي AI بيقدر يشغّل أوامر على اللابتوب (زي Claude Code)، والزق
الرسالة اللي فوق زي ما هي. هو هيقرا [AI-PROMPT.md](AI-PROMPT.md) والريدمي بتاع كل
لعبة، ويمشي خطوة خطوة، ويسألك قبل أي حاجة محتاجة الباسورد أو تحميل أو مسح.

## What is in this folder

| Path | What | Goes to |
|---|---|---|
| [AI-PROMPT.md](AI-PROMPT.md) | The main instructions: rules, the machine, phases A-F, troubleshooting, final check | — |
| [common/](common/) | Shared launchers and tools: `steam-launch.sh`, `game-env.sh`, `game-session.py`, `pads.sh`, `pad_maps.py`, `pad-settings.py` (Controller Settings app), `play-*.sh`, DXVK configs, PES 2019 start-up fixes, `rumble-boost/` | `/media/Games/common/` |
| [pes-2021/](pes-2021/) | PES 2021's own launcher, `dxvk.conf`, `game-session.py` | `/media/Games/eFootball-PES-2021/` |
| [config/gamemode.ini](config/gamemode.ini) | CPU governor back to normal after a game | `~/.config/gamemode.ini` |
| [config/game-pads/mappings.txt](config/game-pads/mappings.txt) | The owner's saved button map (Twin USB pads) | `~/.config/game-pads/mappings.txt` |
| [tools/steam/steam-shortcut.py](tools/steam/steam-shortcut.py) | Adds a game (or Controller Settings) to Steam as a non-Steam shortcut, Steam Input off, artwork, dock icon | run from here |
| [tools/pes-settings-dat.py](tools/pes-settings-dat.py) | Reads / sets resolution and full screen in PES 2019 / 2021 `settings.dat` | run from here |

The games themselves, their artwork and the saves are **not** in this repository.

## The fixes, in one line each

- **Stutter in every game:** split locks punished by the kernel → user in the
  `gamemode` group, GameMode turns `split_lock_mitigate` off while playing.
- **Judder at 60 fps on a 165 Hz screen:** the screen switches to 60 Hz while a game runs.
- **Steam breaks Wine and the pads:** `steam-launch.sh` starts every game with a clean environment.
- **Controllers:** one map and one player order for every game, set in our
  Controller Settings app; Wine's XInput slot order is computed so Player 1 is Player 1.
- **PES 2021 / 2019 no vibration:** `rumble-boost` makes the game's weak pulses strong enough.
- **PES 2019 white screen:** DXVK must not hide the NVIDIA card.
- **PES 2019 78 s start:** split locks in its start-up code; start-up runs on
  the E-cores and a 48-byte stack shift in the exe → title at 30 s.
- **Blur crash mid-race:** Microsoft's `msvcr90` instead of Wine's.
- **Blur speed:** 32-bit DXVK `d3d9.dll` from Proton in the game folder.
- **WWE closes at once in Steam:** the launcher waits for the real game exe.

Generic version for friends (any game, any distro, with a video):
<https://github.com/abdallah-shehawey/Gaming-on-Linux>
