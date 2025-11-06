# dotfiles-ubuntu

Personal dotfiles and customizations for Ubuntu, including **Zsh**, **Neovim**, and other system tweaks.  
This repository helps me (and others) quickly set up the same development environment on a new machine.

---

## 📂 Repository Structure

```text
dotfiles-ubuntu/
├── zsh/        # Zsh configurations (.zshrc, etc.)
├── nvim/       # Neovim configuration files
├── README.md   # Project documentation
```

---

## ⚙️ Zsh Setup

Before using the provided `.zshrc` config, make sure you have the following installed:

### 1. Install Zsh
```bash
sudo apt install zsh -y
```

### 2. Install Oh My Zsh
```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
```

### 3. (Optional) Install Recommended Plugins
```bash
git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting
```

### 4. Backup Your Current Config
```bash
cp ~/.zshrc ~/.zshrc.backup
```

### 5. Apply the Provided Config
```bash
cp ./zsh/.zshrc ~/.zshrc
```

### 6. Reload Config
```bash
source ~/.zshrc
```

### 7. Make Zsh the Default Shell
```bash
chsh -s $(which zsh)
```

---

## 📝 Neovim Setup

The `nvim/` folder contains my custom **Neovim** configuration.  
To use it, follow these steps:

### 1. Install Neovim
```bash
sudo apt install neovim -y
```

### 2. Backup Current Config
```bash
mv ~/.config/nvim ~/.config/nvim.backup
```

### 3. Copy This Repo Config
```bash
cp -r ./nvim ~/.config/
```

### 4. Open Neovim
```bash
nvim
```

Your custom setup should load automatically.

---

## 🔗 Using Symlinks (Alternative to Copy)

Instead of copying files, you can create **symlinks** so that updates in this repo are reflected instantly:

```bash
# Clone repo
git clone https://github.com/abdallah-shehawey/dotfiles-ubuntu.git ~/dotfiles-ubuntu

# Symlink Zsh config
ln -sf ~/dotfiles-ubuntu/zsh/.zshrc ~/.zshrc

# Symlink Neovim config
ln -sfn ~/dotfiles-ubuntu/nvim/nvim ~/.config/nvim
```

---

## 📌 Notes

- Tested on **Ubuntu 22.04+**  
- Requires internet connection for installing plugins & dependencies  
- Feel free to fork/modify to fit your own workflow  
