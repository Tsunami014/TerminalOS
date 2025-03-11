#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <sys/wait.h>
#include <termios.h>

// Function to reset terminal settings
void reset_terminal_settings() {
    struct termios term;
    int fd = open("/dev/console", O_RDWR);
    if (fd >= 0) {
        if (tcgetattr(fd, &term) == 0) {
            term.c_lflag |= (ICANON | ECHO);  // Enable canonical mode and echo
            tcsetattr(fd, TCSANOW, &term);
        }
        close(fd);
    }
}

int main(void) {
    // Create necessary directories
    mkdir("/proc", 0755);
    mkdir("/sys", 0755);
    mkdir("/dev", 0755);
    mkdir("/dev/input", 0755);

    // Mount necessary file systems
    if (mount("devtmpfs", "/dev", "devtmpfs", 0, NULL) < 0) {
        perror("Failed to mount /dev");
        while (1); // Halt
    }
    if (mount("proc", "/proc", "proc", 0, NULL) < 0) {
        perror("Failed to mount /proc");
        while (1);
    }
    if (mount("sysfs", "/sys", "sysfs", 0, NULL) < 0) {
        perror("Failed to mount /sys");
        while (1);
    }

    // Open the console device file
    int console_fd = open("/dev/console", O_RDWR);
    if (console_fd >= 0) {
        ioctl(console_fd, TIOCSCTTY, 1);
        dup2(console_fd, 0);
        dup2(console_fd, 1);
        dup2(console_fd, 2);
        close(console_fd);
    } else {
        perror("Failed to open /dev/console");
        while (1);
    }

    // Fork the process to have Python not take over the un-interruptable process (because Python can exit at any time)
    pid_t pid = fork();
    if (pid < 0) {
        perror("Failed to fork for /start");
        // Since fork failed, fallback immediately.
    } else if (pid == 0) {
        // Child process: execute the /start script.
        execl("/start", "/start", (char *)NULL);
        perror("Failed to execute /start");
        exit(1);  // Exit with failure if exec fails.
    } else {
        // Parent process: wait for the child to complete.
        int status;
        waitpid(pid, &status, 0);
        fprintf(stderr, "Child /start terminated. Failsafing to /bin/sh...\n");

        reset_terminal_settings();
        
        // Reopen /dev/console to ensure a valid terminal,
        // especially if the child process may have affected it.
        int fd = open("/dev/console", O_RDWR);
        if (fd >= 0) {
            ioctl(fd, TIOCSCTTY, 1);
            dup2(fd, STDIN_FILENO);
            dup2(fd, STDOUT_FILENO);
            dup2(fd, STDERR_FILENO);
            close(fd);
        } else {
            perror("Failed to re-open /dev/console");
        }
        
        // Failsafe to /bin/sh
        execl("/bin/sh", "/bin/sh", (char *)NULL);
        perror("Failed to execute /bin/sh!");
    }
    
    // Fail-safe loop
    while (1);
    return 1;
}