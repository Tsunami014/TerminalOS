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
#include <dirent.h>
#include <string.h>

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

// Function to create /dev/input/event* device files
void create_input_devices() {
    mkdir("/dev/input", 0755);
    DIR *dir = opendir("/sys/class/input");
    if (!dir) {
        perror("Failed to open /sys/class/input");
        return;
    }
    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        if (strncmp(entry->d_name, "event", 5) == 0) {  // Look for "event*"
            char dev_path[256];
            snprintf(dev_path, sizeof(dev_path), "/dev/input/%s", entry->d_name);
            mknod(dev_path, S_IFCHR | 0666, makedev(13, atoi(entry->d_name + 5)));
        }
    }
    closedir(dir);
}

int main(void) {
    printf("\033[2J\033[H");
    // Create necessary directories
    mkdir("/proc", 0755);
    mkdir("/sys", 0755);
    mkdir("/dev", 0755);
    
    // Mount necessary file systems
    if (mount("devtmpfs", "/dev", "devtmpfs", 0, NULL) < 0) {
        perror("Failed to mount /dev");
        while (1);
    }
    if (mount("proc", "/proc", "proc", 0, NULL) < 0) {
        perror("Failed to mount /proc");
        while (1);
    }
    if (mount("sysfs", "/sys", "sysfs", 0, NULL) < 0) {
        perror("Failed to mount /sys");
        while (1);
    }
    
    // Create /dev/input/event* files automatically
    create_input_devices();
    
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
    
    // Fork the process to have Python not take over the un-interruptable process
    pid_t pid = fork();
    if (pid < 0) {
        perror("Failed to fork for /start");
        // Since fork failed, fallback immediately.
    } else if (pid == 0) {
        // Child process: execute the /start script.
        execl("/start", "/start", (char *)NULL);
        perror("Failed to execute /start");
        exit(1);
    } else {
        // Parent process: wait for the child to complete.
        int status;
        waitpid(pid, &status, 0);
        fprintf(stderr, "Child /start terminated. Failsafing to /bin/sh...\n");

        reset_terminal_settings();
        
        // Reopen /dev/console to ensure a valid terminal
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
