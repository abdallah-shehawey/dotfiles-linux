# 🐧 Linux App Customization: Editing Exec Permissions & Flags

This guide explains how to modify the launch behavior of Linux applications by customizing `.desktop` files, without altering core system files. This method is useful for forcing applications to run in specific modes (like **Dark Mode**) or passing specific environment variables upon startup.

## 📋 Why Use This Method?

When you want to change how a program opens (e.g., GParted, Chrome, or VS Code), it is **not recommended** to edit the original file located in `/usr/share/applications` because:

1. **System updates** will overwrite your changes.
    
2. The modification affects **all users** on the system.
    

**The Solution:** Copy the file to your local directory `~/.local/share/applications`. The system prioritizes your local file over the system-wide one.

## 🛠️ Step-by-Step Guide

### 1. Create the Local Applications Directory

Ensure the directory for local user applications exists.

```bash
mkdir -p ~/.local/share/applications
```

### 2. Copy the Original Desktop File

Copy the launch file (`.desktop`) of the program you want to modify from the system directory to your local directory. _Example for GParted:_

```bash
cp /usr/share/applications/gparted.desktop ~/.local/share/applications/
```

### 3. Edit the File & Add Settings

Open the copied file using any text editor (like `nvim`, `nano`, or `gedit`).

```bash
nvim ~/.local/share/applications/gparted.desktop
```

#### 💡 How to Edit (The Important Part):

Look for the line starting with **`Exec=`**. This line contains the command the system executes to open the program.

**To enable Dark Mode or change the theme:** You can inject environment variables right before the command.

**Before:**

```bash
Exec=/usr/sbin/gparted %f
```

**After (Example to force a Dark Theme):**

```bash
Exec=env GTK_THEME=Adwaita:dark /usr/sbin/gparted %f
```

_Note: You can add any other program-specific flags here (e.g., `--force-device-scale-factor=1.5` for HiDPI scaling)._

### 4. Update the Desktop Database

To ensure the system recognizes your new changes and uses the local file instead of the system file.

```bash
update-desktop-database ~/.local/share/applications
```

## 📝 Practical Example: Changing Execution Privileges (Sudo/Root)

For some system tools (like GParted), you might want to adjust how they request permissions.

If you want to ensure a program always runs as **Root** or requests a password via the GUI, ensure the `Exec` line uses `pkexec` (Polkit Execution) or the appropriate wrapper for your distribution:

```bash
Exec=pkexec /usr/sbin/gparted
```

## ✅ Conclusion

Once you save the file and run the database update command, the next time you launch the program from your application menu, it will automatically run with your new settings (Dark Mode, custom flags, etc.).