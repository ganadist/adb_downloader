#include <stdio.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>

#include <cutils/properties.h>
#include <cutils/android_reboot.h>

#define COMMAND_PORT 9123

#define SHELL "/dev/d/sh"

static int command_s = 0;

static int prepare_socket(int port)
{
    struct sockaddr_in addr;
    int s;
    memset(&addr, 0, sizeof(addr));
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_family = AF_INET;

    s = socket(AF_INET, SOCK_STREAM, 0);
    if (s < 0) {
        perror("socket:");
        return -1;
    }

    int enable = 1;
    if (setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &enable, sizeof(enable)) < 0) {
        perror("setsockopt");
        return -1;
    }

    if (bind(s, (const struct sockaddr *)&addr, sizeof(addr)) != 0) {
        perror("bind:");
        return -1;
    }
    
    if (listen(s, 1) != 0) {
        perror("listen:");
        return -1;
    }

    return s;
}

static int accept_socket(int s) {
    struct sockaddr_in remote;
    socklen_t remote_len;
    int sock = accept(command_s, (struct sockaddr *)&remote, &remote_len);
    if (sock < 0) {
        perror("accept");
        return -1;
    }
    /*
    int f = fcntl(sock, F_GETFL);
    fcntl(sock, F_SETFL, f | O_NONBLOCK);
    */
    return sock;
}

static void print_prop(const char* key, const char*name, void *data) {
    FILE *f = data;
    fprintf(f, "[%s]: [%s]\n", key, name);
}

static int run_command(int fd, char *command) {
    pid_t pid = fork();
    if (pid == 0) {
        if (fd != STDIN_FILENO) {
            dup2(fd, STDIN_FILENO);
            close(fd);
        }
        char* cmd[5];
        cmd[0] = SHELL;
        cmd[1] = "-c";
        cmd[2] = command;
        cmd[3] = NULL;
        execvp(cmd[0], cmd);
        exit(-1);
    }
    int status;
    waitpid(pid, &status, 0);
    return status;
}

int handle_cmd(char* cmd, char* arg, FILE *f) {

    printf("cmd = \"%s\", arg = \"%s\"\n", cmd, arg);
    int status;
    int s = fileno(f);
    if (!strcmp(cmd, "write")) {
        char *filename = arg;
        char command[BUFSIZ];

        sprintf(command, "gzip -cd - | dd of=%s", filename);
        printf("build write command\n");
        run_command(s, command);
    } else if (!strcmp(cmd, "run")) {
        char *command = arg;
        run_command(s, command);
    } else if (!strcmp(cmd, "ping")) {
        write(s, "pong", 4);
    } else if (!strcmp(cmd, "getprop")) {
        if (arg == NULL) {
            (void)property_list(print_prop, f);
        } else {
            char value[PROPERTY_VALUE_MAX];
            property_get(arg, value, "");
            fprintf(f, "%s\n", value);
        }
    } else if (!strcmp(cmd, "setprop")) {
        char* arg2 = strchr(arg, ' ');
        if (arg2 == NULL) {
            printf("setprop %s is invalid syntax\n", arg);
        } else {
            *arg2 = '\0';
            arg2++;
            if (property_set(arg, arg2)) {
                fprintf(stderr, "could not set property\n");
            }
        }
    } else if (!strcmp(cmd, "reboot")) {
        if (android_reboot(ANDROID_RB_RESTART, 0, 0) < 0) {
            perror("reboot");
            exit(EXIT_FAILURE);
        }
    } else if (!strcmp(cmd, "exit")) {
        exit(0);
    } else {
        printf("unknown command: %s %s\n", cmd, arg);
    }
    return 0;
}

int main(int argc, char **argv)
{
    command_s = prepare_socket(COMMAND_PORT);
    if (command_s < 0) {
        return -1;
    }

    while (1) {
        int s = accept_socket(command_s);
        FILE *f = fdopen(s, "rw");
        char buf[BUFSIZ];
        char *cmd, *arg;
        int n;
        cmd = fgets(buf, BUFSIZ, f);
        n = strlen(buf);
        if (buf[n-1] == '\n')
            buf[n-1] = '\0';
        arg = strchr(buf, ' ');
        if (arg) {
            *arg = '\0';
            arg++;
        }
        handle_cmd(cmd, arg, f);
        fclose(f);
        close(s);
    }
    close(command_s);
    return 0;
}
