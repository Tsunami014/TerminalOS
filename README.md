This project is a Terminal OS: A simple, ASCII OS for the Linux Virtual Terminal, avaliable to all via <kbd>ctrl</kbd>+<kbd>alt</kbd>+<kbd>F1-12</kbd> and then by signing in.

It is recommended to put this (or another that links to this) script (`OS.py` or you can just rename it to `OS` for convenience) somewhere in the PATH or your home folder so you can just run `OS` from the terminal as soon as it starts up.

This probably won't work on most other OS's. I haven't tested it, but it *may* work on any Linux distro. At least, it works on my Linux Mint (Ubuntu-based) system.

# Required packages
- `python3`
- `xsel` (for clipboard functionality)

# To run
Run `sudo OS.py` to start the OS. To exit press `Esc` or `Ctrl+C`.

## To add more apps
Download some python files, **MAKING FULL CARE AS TO NOT DOWNLOAD MALICIOUS CODE**, as this will run any code it sees. Put them in the `external` folder (make one if it doesn't exist) in this directory and they will be added to the OS.

# To use in virtual terminal
To use this in the virtual terminal, press <kbd>ctrl</kbd>+<kbd>alt</kbd>+<kbd>F1-12</kbd> and sign in. Then run the script as you would in a normal terminal.
I suggest tty1 (<kbd>ctrl</kbd>+<kbd>alt</kbd>+<kbd>F1</kbd>) as it is the first one and is the most likely to be free. And with most systems, you can press <kbd>ctrl</kbd>+<kbd>alt</kbd>+<kbd>F7</kbd> to return to the GUI (if not just try every one until one works).

# To make into a bootable OS
1. Download python and build it manually into a `rootfs` (root filesystem) directory
```bash
mkdir -p rootfs rootfs/pycore
wget https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz
tar xzf Python-3.12.0.tgz
rm Python-3.12.0.tgz
cd Python-3.12.0
./configure --disable-shared --enable-optimizations --prefix=$(realpath ../rootfs/pycore)
make -j4
make altinstall
cd ../
```
2. Get apps that will be used
```bash
mkdir -p rootfs/bin
sudo apt install busybox-static
cp /bin/busybox rootfs/bin/sh
```
3. Get libraries required
```bash
# Python libraries
rootfs/pycore/bin/pip3.12 install evdev requests

mkdir -p rootfs/lib rootfs/lib64

sudo apt install libffi8
sudo cp /usr/lib/x86_64-linux-gnu/libffi.so.8 rootfs/lib/x86_64-linux-gnu/libffi.so.8

for file in rootfs/pycore/bin/python3.12; do
    ldd "$file" | grep -P -o "/[^ \n]+" | while read lib; do
        target_dir="rootfs$(dirname "$lib")"
        mkdir -p "$target_dir"
        cp "$lib" "$target_dir"
    done
done
```
4. Copy python code
```bash
cp py rootfs/py -r
```
5. Add the start script
```bash
cat > rootfs/start <<EOF
#!/bin/sh
cd /py
export LANG=$LANG.UTF-8
/pycore/bin/python3.12 OS.py
EOF
chmod +x rootfs/start
```
6. Compile and add the init code
```bash
gcc -static -o rootfs/init init.c
```
7. Pack it into an initrd and move it to the boot folder
```bash
(cd rootfs && find . | cpio -o -H newc) | gzip > initrd-tos.img
sudo mv initrd-tos.img /boot/
```
8. Update the GRUB to have the new OS as an option
```bash
sudo tee /etc/grub.d/40_custom > /dev/null <<EOF
#!/bin/sh
exec tail -n +3 $0

menuentry "Terminal OS"{
            search --set=root --file /boot/vmlinuz
            linux /boot/vmlinuz root=/dev/ram0 rdinit=/init
            initrd /boot/initrd-tos.img
}
EOF
sudo chmod +x /etc/grub.d/40_custom
sudo update-grub
```

Or here it is in one command:
```bash
# Get python
mkdir -p rootfs rootfs/pycore

wget https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz
tar xzf Python-3.12.0.tgz
rm Python-3.12.0.tgz
cd Python-3.12.0

./configure --disable-shared --enable-optimizations --prefix=$(realpath ../rootfs/pycore)
make -j4
make altinstall

cd ../

# Get python libraries required
rootfs/pycore/bin/pip3.12 install evdev requests

# Get apps
mkdir -p rootfs/bin
sudo apt install busybox-static
cp /bin/busybox rootfs/bin/sh

# Get binary libraries required
mkdir -p rootfs/lib rootfs/lib64

sudo apt install libffi8
sudo cp /usr/lib/x86_64-linux-gnu/libffi.so.8 rootfs/lib/x86_64-linux-gnu/libffi.so.8

for file in rootfs/pycore/bin/python3.12; do
    ldd "$file" | grep -P -o "/[^ \n]+" | while read lib; do
        target_dir="rootfs$(dirname "$lib")"
        mkdir -p "$target_dir"
        cp "$lib" "$target_dir"
    done
done

# Copy python code
cp py rootfs/py -r

# Add init shell script
cat > rootfs/start <<EOF
#!/bin/sh
cd /py
export LANG=$LANG.UTF-8
/pycore/bin/python3.12 OS.py
EOF
chmod +x rootfs/start

# Compile init code
gcc -static -o rootfs/init init.c

# Compress into a .img
(cd rootfs && find . | cpio -o -H newc) | gzip > initrd-tos.img
sudo mv initrd-tos.img /boot/

# Add the register to GRUB
sudo tee /etc/grub.d/40_custom > /dev/null <<EOF
#!/bin/sh
exec tail -n +3 $0

menuentry "Terminal OS"{
            search --set=root --file /boot/vmlinuz
            linux /boot/vmlinuz root=/dev/ram0 rdinit=/init
            initrd /boot/initrd-tos.img
}
EOF
sudo chmod +x /etc/grub.d/40_custom
sudo update-grub
```
