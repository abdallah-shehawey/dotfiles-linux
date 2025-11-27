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
