# Useful Commands & Notes

---

## 🔵 Bluetooth

```bash
sudo systemctl restart bluetooth
```

---

## 🖥️ Update Kernel

- [ChatGPT Guide](https://chatgpt.com/share/6815b8d8-f12c-8005-b86c-1bc0d85cfa44)

```bash
sudo apt install linux-generic-hwe-24.04
```

---

## 🎵 Download Playlist from YouTube

```bash
yt-dlp -f 137+140 "Playlist Link"
# OR
yt-dlp -f "bv*+ba/b" -o "%(title)s.%(ext)s" "Playlist Link"

# and To update it
sudo yt-dlp -U
```

---

## 📦 Unrar Folder

```bash
unrar x -o+ "Folder.rar" "Folder/"
```

---

## 🎮 Install Nvidia Driver

- [Youtube Guide](https://youtu.be/9Ff9tl-32Wk?si=86SYqIQckN9Hu6PQ)

---

## 🎨 Grub Theme

- [ChatGPT Guide](https://chatgpt.com/share/6813040f-40f0-8003-9f3f-74d279ae0971)

---

## 🖼️ Wallpapers

- [Wallpaper Flare](https://www.wallpaperflare.com/sasuke-and-naruto-digital-wallpaper-uzumaki-naruto-uchiha-sasuke-wallpaper-puhqu/download/2560x1440)

---

## 🔄 Update Ubuntu (Script)

### Create Script

```bash
sudo nvim /usr/local/bin/update-every-thing
sudo chmod +x /usr/local/bin/update-every-thing
```

### Commands

```bash
#!/bin/bash
# Script: update-every-thing
# Function: Update everything in Ubuntu
# Default: skip NVIDIA drivers
# Option: --with-nvidia (update NVIDIA as well)

echo "🚀 Starting full Ubuntu update..."

WITH_NVIDIA=false

# Detect option
if [[ "$1" == "--with-nvidia" ]]; then
  WITH_NVIDIA=true
  echo "⚠️  NVIDIA drivers WILL be updated."
else
  echo "⛔ NVIDIA drivers will be skipped."
  # Hold NVIDIA packages temporarily
  sudo apt-mark hold nvidia-driver-* nvidia-dkms-* nvidia-kernel-* libnvidia-* >/dev/null 2>&1
fi

# Update apt packages
echo "🔄 Updating apt packages..."
sudo apt update -y
sudo apt upgrade -y
sudo apt full-upgrade -y
sudo apt install -y linux-generic
sudo apt autoremove -y
sudo apt autoclean -y

# Update snaps
echo "🔄 Updating snap packages..."
sudo snap refresh

# Update flatpak
echo "🔄 Updating flatpak packages..."
flatpak update -y

# Ubuntu Pro updates
echo "🔄 Checking Ubuntu Pro security status..."
pro security-status || true
sudo pro fix || true

# GNOME extensions update
echo "🔄 Updating GNOME extensions..."
gnome-extensions update || true

# Drivers section
echo "🔄 Updating Ubuntu drivers..."
sudo ubuntu-drivers autoinstall || true

# Release NVIDIA hold if it was set
if [ "$WITH_NVIDIA" = false ]; then
  echo "🔓 Releasing NVIDIA hold..."
  sudo apt-mark unhold nvidia-driver-* nvidia-dkms-* nvidia-kernel-* libnvidia-* >/dev/null 2>&1
fi

echo "✅ Update finished!"

```

---

## ❌ Kill Any Program

```bash
sudo xkill
```

---

## 🐍 Python Virtual Environment (Udemy)

```bash
python3 -m venv my_udemy_env
source my_udemy_env/bin/activate
```

---

## 🎥 YouTube Reference

- [Video](https://www.youtube.com/watch?v=gq-PYZRmRF4)

---

## 🖼️ Run Apps with External Nvidia GPU

```bash
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia <program>
```

## Default GPU Select

```bash
sudo prime-select intel
sudo prime-select nvidia
```

---

## 📝 Clang Format

```bash
clang-format -i -style="{BasedOnStyle: Microsoft, IndentWidth: 2, TabWidth: 2, UseTab: Never}" testing.c
```

---

## 🔒 Nvidia Package Hold/Unhold

```bash
sudo apt-mark hold nvidia-driver-* nvidia-dkms-* nvidia-kernel-* libnvidia-*
sudo apt-mark unhold nvidia-driver-* nvidia-dkms-* nvidia-kernel-* libnvidia-*
sudo apt upgrade
```

---

## 🔄 Change Default Terminal

```bash
sudo update-alternatives --config x-terminal-emulator
```

## replace word in files

```bash
find . -type f -exec sed -i 's/oldword/newword/g' {} +
```

### with special format

```bash
find . -type f -name "*.txt" -exec sed -i 's/oldword/newword/g' {} +
```

### print time of video
```bash
for file in "Session 06 Bash Scripting Essentials.mkv" \
            "Session 07 Linux File System Essentials.mkv" \
            "Session 08 Linux File System Operations – File Management, Linking, and Mounting.mkv" \
            "Session 09 Process Management in Linux – Building A Minimal Linux Distro from Scratch.mkv" \
            "Session 10 Introduction to Networking and Application Layer.mkv"; do
  echo -n "$file: "
  ffprobe -v quiet -show_entries format=duration -of csv="p=0" "$file" | \
  awk '{printf "%02d:%02d:%02d\n",$1/3600,($1%3600)/60,$1%60}'
done
```


### how to create swap file

```bash
sudo swapoff -a
sudo fallocate -l 16G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### How to Enable and Configure zram

This guide explains how to install and set up `zram` on a Linux system (like Ubuntu or Debian) to improve performance by compressing a part of RAM and using it as swap.

### 1. Install and Run zram-tools

First, install the required package, then start the service and enable it to run on boot.

```bash
sudo apt install zram-tools
sudo systemctl enable --now zramswap.service
```

### 2. Configure zramswap Settings

Next, modify the configuration file to specify the algorithm and memory percentage.

Open the file (using `nvim` or your preferred text editor):

```bash
sudo nvim /etc/default/zramswap
```

Set the configuration as follows (this example uses `zstd` for compression and 75% of memory):

```bash
# Compression algorithm selection
# speed: lz4 > zstd > lzo
# compression: zstd > lzo > lz4
# This is not inclusive of all that is available in latest kernels
# See /sys/block/zram0/comp_algorithm (when zram module is loaded) to see
# what is currently set and available for your kernel[1]
# [1]  [https://github.com/torvalds/linux/blob/master/Documentation/blockdev/zram.txt#L86](https://github.com/torvalds/linux/blob/master/Documentation/blockdev/zram.txt#L86)
ALGO=zstd

# Specifies the amount of RAM that should be used for zram
# based on a percentage the total amount of available memory
# This takes precedence and overrides SIZE below
PERCENT=75

# Specifies a static amount of RAM that should be used for
# the ZRAM devices, this is in MiB
#SIZE=256

# Specifies the priority for the swap devices, see swapon(2)
# for more details. Higher number = higher priority
# This should probably be higher than hdd/ssd swaps.
PRIORITY=100
```

### 3. Restart the Service and Verify

Finally, restart the service to apply the new changes, then check that the swap is active.

```bash
sudo systemctl restart zramswap.service
swapon --show
```
