This project is a Terminal OS: A simple, ASCII OS for the Linux Virtual Terminal, avaliable to all via <kbd>ctrl</kbd>+<kbd>alt</kbd>+<kbd>F1-12</kbd> and then by signing in.

It is recommended to put this (or another that links to this) script (`OS.py` or you can just rename it to `OS` for convenience) somewhere in the PATH or your home folder so you can just run `OS` from the terminal as soon as it starts up.

This probably won't work on most other OS's. I haven't tested it, but it *may* work on any Linux distro. At least, it works on my Linux Mint (Ubuntu-based) system.

# Required packages
- `python3`
- `xsel` (for clipboard functionality)

# To run
Run `OS.py` to start the OS. To exit press `Esc` or `Ctrl+C`.

## To add more apps
Download some python files, **MAKING FULL CARE AS TO NOT DOWNLOAD MALICIOUS CODE**, as this will run any code it sees. Put them in the `external` folder (make one if it doesn't exist) in this direcroty and they will be added to the OS.
