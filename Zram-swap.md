# Enable and Configure zram on Linux

This guide explains how to enable and configure **zram** on Linux systems  
(**Ubuntu / Debian** and **Fedora**).

zram creates a compressed block device in RAM and is commonly used as **swap**  
to improve system responsiveness under memory pressure.

---

## 1. Install zram

### Ubuntu / Debian

Install `zram-tools` and enable the swap service:

```bash
sudo apt install zram-tools
sudo systemctl enable --now zramswap.service
```

---

### Fedora

Fedora uses **systemd-zram-generator** instead of `zram-tools`.

Install the generator package:

```bash
sudo dnf install zram-generator
```

> Fedora may already ship with a default zram configuration.  
> Creating a config file will override the defaults.

---

## 2. Configure zram

### Ubuntu / Debian Configuration

Edit the configuration file:

```bash
sudo nvim /etc/default/zramswap
```

Example configuration:

```bash
# Compression algorithm selection
# speed:        lz4 > zstd > lzo
# compression:  zstd > lzo > lz4
#
# Available algorithms can be checked at:
# /sys/block/zram0/comp_algorithm
#
ALGO=zstd

# Percentage of total RAM to use for zram
PERCENT=75

# Fixed size in MiB (disabled when PERCENT is set)
#SIZE=256

# Swap priority (higher number = higher priority)
PRIORITY=100
```

Restart the service:

```bash
sudo systemctl restart zramswap.service
```

---

### Fedora Configuration

Create or edit the zram generator configuration file:

```bash
sudo nvim /etc/systemd/zram-generator.conf
```

Minimal and recommended example:

```ini
[zram0]
zram-size = min(ram, 12288)
```

This configuration:

- Uses zram up to the size of RAM
    
- Caps usage at **12 GB**
    
- Uses the kernel default compression algorithm (recommended)
    

> Specifying a compression algorithm is **optional**.  
> Leaving it unset uses the kernel default, which is stable and well-tested.

Apply the configuration:

```bash
sudo systemctl daemon-reexec
sudo reboot
```

---

## 3. Verify zram Status

Check that zram swap is active:

```bash
swapon --show
```

Inspect zram devices:

```bash
zramctl
```

Check the active compression algorithm:

```bash
cat /sys/block/zram0/comp_algorithm
```

---

## Notes

- No manual service start is required on Fedora after reboot
    
- zram is set up early at boot by systemd generators
    
- For most desktop systems, the default compression algorithm is more than sufficient
    

---

## References

- Linux zram documentation  
    [https://www.kernel.org/doc/html/latest/admin-guide/blockdev/zram.html](https://www.kernel.org/doc/html/latest/admin-guide/blockdev/zram.html)
    
- systemd zram generator  
    [https://github.com/systemd/zram-generator](https://github.com/systemd/zram-generator)