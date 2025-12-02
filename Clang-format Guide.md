# Clang-Format Setup & Integration Guide

This document explains how to install, configure, and integrate **clang-format** to enforce a consistent C/C++ coding style across Linux environments (Ubuntu, Fedora) and editors such as **VS Code** and **Windsurf**.

---
## 1. Installation

Install `clang-format` based on your Linux distribution.

### Ubuntu / Debian

```bash
sudo apt install clang-format
```

### Fedora / RHEL

```bash
sudo dnf install clang-tools-extra
```

Verify installation:

```bash
clang-format --version
```

---

## 2. Global Configuration

Create a global `.clang-format` file in your home directory. This configuration will be used for all projects unless a project-specific `.clang-format` exists.

```bash
nvim ~/.clang-format
```

Paste the following configuration:

```yaml
BasedOnStyle: Microsoft
IndentWidth: 2
TabWidth: 2
UseTab: Never

BraceWrapping:
  AfterFunction: true
  AfterClass: true
  AfterStruct: true
  AfterControlStatement: true
  AfterNamespace: true
  AfterEnum: true
  SplitEmptyFunction: true
  SplitEmptyRecord: true
  SplitEmptyNamespace: true
```

### What this configuration enforces

- **Microsoft style** as a base
    
- **2-space indentation** (spaces only, no tabs)
    
- **Allman-style braces** (opening brace on a new line)
    
- **No single-line functions**, even if short
    

---

## 3. Editor Integration (VS Code / Windsurf)

### 3.1 Install the Clang-Format Extension

1. Open **Extensions** (`Ctrl + Shift + X`)
    
2. Search for **Clang-Format**
    
3. Install **Clang-Format** by **xaver**
    

Extension ID:

```
xaver.clang-format
```

---

### 3.2 Required Editor Settings

Open your `settings.json`:

```text
Ctrl + Shift + P → Preferences: Open Settings (JSON)
```

Add the following configuration:

```json
{
  "editor.formatOnSave": true,

  "[c]": {
    "editor.defaultFormatter": "xaver.clang-format"
  },
  "[cpp]": {
    "editor.defaultFormatter": "xaver.clang-format"
  },

  "clang-format.executable": "clang-format",
  "clang-format.style": "file",
  "clang-format.fallbackStyle": "Microsoft"
}
```

This ensures:

- `clang-format` is used for both **C** and **C++** files
    
- Formatting automatically happens on **Save (Ctrl + S)**
    
- The formatter reads from the `.clang-format` file
    
---

## 5. Notes & Best Practices

- A `.clang-format` file in a **project root** overrides the global one
    
- No symlinks, no system-wide config copies are required
    
- Avoid deprecated `_clang-format` files
    
- The same setup works across Ubuntu, Fedora, and RHEL
    

---

✅ Once configured, **Ctrl + S** will automatically format your C/C++ code using a consistent, predictable style.