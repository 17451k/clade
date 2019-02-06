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

#define WIN32_LEAN_AND_MEAN

#include <iostream>
#include <windows.h>
#include <winternl.h>
#include <winsock2.h>
#include <ws2tcpip.h>

// For socket client functionality need to link with Ws2_32.lib, Mswsock.lib, and Advapi32.lib
#pragma comment(lib, "Ws2_32.lib")
#pragma comment(lib, "Mswsock.lib")
#pragma comment(lib, "AdvApi32.lib")

#define DEFAULT_BUFLEN 1024


void SendData(const wchar_t *wdata)
{
    WSADATA wsaData;
    SOCKET ConnectSocket = INVALID_SOCKET;
    struct addrinfo *result = NULL,
                    *ptr = NULL,
                    hints;
    char recvbuf[DEFAULT_BUFLEN];
    int r;
    int recvbuflen = DEFAULT_BUFLEN;

    char *host = getenv("CLADE_INET_HOST");
    char *port = getenv("CLADE_INET_PORT");

    if (!host || !port)
    {
        std::cerr << "Server adress is not specified" << std::endl;
        exit(EXIT_FAILURE);
    }

    // Initialize Winsock
    r = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (r != 0)
    {
        std::cerr << "WSAStartup failed: error code " << r << std::endl;
        exit(EXIT_FAILURE);
    }

    ZeroMemory(&hints, sizeof(hints));
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;

    // Resolve the server address and port
    r = getaddrinfo(host, port, &hints, &result);
    if (r != 0)
    {
        std::cerr << "getaddrinfo failed: error code " << r << std::endl;
        WSACleanup();
        exit(EXIT_FAILURE);
    }

    // Attempt to connect to an address until one succeeds
    for (ptr = result; ptr != NULL; ptr = ptr->ai_next)
    {

        // Create a SOCKET for connecting to server
        ConnectSocket = socket(ptr->ai_family, ptr->ai_socktype,
                               ptr->ai_protocol);
        if (ConnectSocket == INVALID_SOCKET)
        {
            std::cerr << "Socket failed: error code " << GetLastError() << std::endl;
            WSACleanup();
            exit(EXIT_FAILURE);
        }

        // Connect to server.
        r = connect(ConnectSocket, ptr->ai_addr, (int)ptr->ai_addrlen);
        if (r == SOCKET_ERROR)
        {
            closesocket(ConnectSocket);
            ConnectSocket = INVALID_SOCKET;
            continue;
        }
        break;
    }

    freeaddrinfo(result);

    if (ConnectSocket == INVALID_SOCKET)
    {
        std::cerr << "Unable to connect to server" << std::endl;
        WSACleanup();
        exit(EXIT_FAILURE);
    }

    // convert wchar_t* to char*
    size_t dataLen = wcslen(wdata);
    size_t charsConverted;
    char *data = new char[dataLen + 1];

    wcstombs_s(&charsConverted, data, dataLen + 1, wdata, dataLen);
    data[dataLen] = 0;

    // Send data
    r = send(ConnectSocket, data, (int)strlen(data), 0);
    if (r == SOCKET_ERROR)
    {
        std::cerr << "Send failed: error code " << GetLastError() << std::endl;
        closesocket(ConnectSocket);
        WSACleanup();
        exit(EXIT_FAILURE);
    }

    // shutdown the connection since no more data will be sent
    r = shutdown(ConnectSocket, SD_SEND);
    if (r == SOCKET_ERROR)
    {
        std::cerr << "Shutdown failed: error code " << GetLastError() << std::endl;
        closesocket(ConnectSocket);
        WSACleanup();
        exit(EXIT_FAILURE);
    }

    // Receive until the peer closes the connection
    do
    {
        r = recv(ConnectSocket, recvbuf, recvbuflen, 0);
    } while (r > 0);

    // cleanup
    closesocket(ConnectSocket);
    WSACleanup();

    return;
}
