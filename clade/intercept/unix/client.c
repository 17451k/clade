/*
 * Copyright (c) 2019 ISP RAS (http://www.ispras.ru)
 * Ivannikov Institute for System Programming of the Russian Academy of Sciences
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/un.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include "env.h"

static void send_data_unix(const char *msg, char *address) {
    int sockfd;

    struct sockaddr_un addr;

    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, address, sizeof(addr.sun_path)-1);

    sockfd = socket(AF_UNIX, SOCK_STREAM, 0);

    if (0 != connect(sockfd, (struct sockaddr *) &addr, sizeof(struct sockaddr_un))) {
        fprintf(stderr, "Couldn't connect to the socket %s: ", address);
        perror("");
        exit(EXIT_FAILURE);
    }

    ssize_t  r = write(sockfd, msg, strlen(msg));

    if (r == -1) {
        perror("Failed to write to the socket");
    }

    // We need to wait until the server finished message processing and close the socket
    char buf[1024];
    while ((r = read(sockfd, buf, sizeof(buf)-1)) > 0) {}
}

static void send_data_inet(const char *msg, char *host, char *port) {
    int sockfd;

    struct sockaddr_in addr;

    addr.sin_family = AF_INET;
    addr.sin_port = htons(atoi(port));

    if (!inet_aton(host, &(addr.sin_addr))) {
        perror("Invalid ip and port");
        exit(EXIT_FAILURE);
    }

    sockfd = socket(AF_INET, SOCK_STREAM, 0);

    if (0 != connect(sockfd, (struct sockaddr*)&addr, sizeof(addr))) {
        fprintf(stderr, "Couldn't connect to the server %s:%s ", host, port);
        perror("");
        exit(EXIT_FAILURE);
    }

    ssize_t r = write(sockfd, msg, strlen(msg));

    if (r == -1) {
        perror("Failed to write to the socket");
    }

    // We need to wait until the server finished message processing and close the socket
    char buf[1024];
    while ((r = read(sockfd, buf, sizeof(buf)-1)) > 0) {}
}

void send_data(const char *msg) {
    char* host = getenv(CLADE_INET_HOST_ENV);
    char* port = getenv(CLADE_INET_PORT_ENV);
    char* address = getenv(CLADE_UNIX_ADDRESS_ENV);

    // Use UNIX sockets if address is not NULL
    if (address) {
        send_data_unix(msg, address);
    }
    // Else try to use TCP/IP sockets
    else if (host && port) {
        send_data_inet(msg, host, port);
    }
    else {
        perror("Server adress is not specified");
        exit(EXIT_FAILURE);
    }
}
