## Guide to Customizing GRUB and Improving Boot Time

This guide covers changing the GRUB theme, customizing the menu, and speeding up your system's boot process.

---

## Part 1: Installing a New GRUB Theme

### Step 1: Download the Theme

Find themes on websites like [**GNOME-Look.org**](https://www.gnome-look.org/browse?cat=109).

> ✅ **Tip:** Always check the theme README before installing. Some themes provide an `install.sh` script that automates installation.

---

### Step 2: Extract the Theme Files

```bash
tar -xvf theme-file.tar.gz
```

After extraction, many themes (such as **Vimix**) have a structure like:

```
Vimix-4k/
├── install.sh
├── LICENSE
└── Vimix/
```

---

### Step 3: Install the Theme Using install.sh (Recommended)

> 🚀 This is the **preferred method** if the theme provides an installation script.

1. Enter the extracted directory:
    

```bash
cd Vimix-4k
```

2. Make the installer executable (if needed):
    

```bash
chmod +x install.sh
```

3. Run the installer:
    

```bash
sudo ./install.sh
```

During installation, the script will usually:

- Copy theme files to `/usr/share/grub/themes/`
    
- Ask you to **choose the theme variant based on your screen resolution**
    
- Automatically update the GRUB configuration
    

---

### Step 4: Choosing the Correct Theme Resolution

Choosing the right resolution is **very important** to avoid stretched or blurry GRUB UI.

1. Check your screen resolution:
    

```bash
xrandr | grep '*'
```

Example output:

```
1920x1080  *
```

2. Choose the matching theme variant:
    

|Screen Resolution|Recommended Theme|
|---|---|
|1366×768|1080p|
|1920×1080|1080p|
|2560×1440|2k|
|3840×2160|4k|

> ⚠️ If the installer asks, **always pick the closest lower or equal resolution** — never higher.

---

### Step 5: Manual Installation (If install.sh Is Not Available)

1. Copy the theme directory:
    

```bash
sudo cp -r theme-folder-name /usr/share/grub/themes/
```

2. Edit GRUB config:
    

```bash
sudo nvim /etc/default/grub
```

Add or update:

```bash
GRUB_THEME="/usr/share/grub/themes/theme-folder-name/theme.txt"
```

---

### Step 6: Update GRUB Configuration

#### On Ubuntu / Debian:

```bash
sudo update-grub
```

#### On Fedora:

> Fedora does **NOT** use `update-grub`

**BIOS systems:**

```bash
sudo grub2-mkconfig -o /boot/grub2/grub.cfg
```

**UEFI systems (most modern laptops):**

```bash
sudo grub2-mkconfig -o /boot/efi/EFI/fedora/grub.cfg
```

> ✅ You can check UEFI mode with:

```bash
[ -d /sys/firmware/efi ] && echo UEFI || echo BIOS
```

---

### Step 7: Verify Theme Path on Fedora

Fedora commonly stores themes here:

```bash
/usr/share/grub/themes/
```

Make sure:

- `theme.txt` exists
    
- Path in `GRUB_THEME` is **100% correct**
    

---

✅ **Done!** Reboot and enjoy your new GRUB theme.

---

### Common Problems & Fixes

❌ Theme not showing?

- Secure Boot may block custom themes
    
- Wrong `theme.txt` path
    
- GRUB config not regenerated
    

✅ Fix:

```bash
sudo grub2-mkconfig -o /boot/efi/EFI/fedora/grub.cfg
```

---

💡 **Pro Tip (Fedora + HiDPI):**  
If GRUB looks too small on 4K screens, add:

```bash
GRUB_GFXMODE=1920x1080
GRUB_GFXPAYLOAD_LINUX=keep
```

to `/etc/default/grub` and regenerate GRUB.

---
