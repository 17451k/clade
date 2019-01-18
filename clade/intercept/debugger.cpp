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

#include <iostream>
#include <fstream>
#include <string>
#include <vector>

#include <windows.h>
#include <psapi.h>
#include <winternl.h>

#ifdef _M_X64
int procParamsOffset = 0x20;
int cmdLineOffset = 0x70;
int curDirPathOffset = 0x38;
#else
int procParamsOffset = 0x10;
int cmdLineOffset = 0x40;
int curDirPathOffset = 0x24;
#endif // _M_X64

// Function pointer declaration
// NTAPI = Native Windows API
typedef NTSTATUS (NTAPI *_NtQueryInformationProcess)(HANDLE, DWORD, PVOID, DWORD, PDWORD);


// PEB - process environment block, low-level data stracture containing various information
// Address of the PEB can be obtained using NTAPI function NtQueryInformationProcess
// But the function itself is not public. Its address can be found in ntdll.dll.
PVOID GetPebAddress(HANDLE ProcessHandle) {
    HINSTANCE hinstLib = LoadLibrary(TEXT("ntdll.dll"));

    if (!hinstLib) {
        std::cerr << "Could not get handle to ntdll module: error code " << GetLastError() << std::endl;
        exit(GetLastError());
    }

    _NtQueryInformationProcess NtQueryInformationProcess = (_NtQueryInformationProcess) GetProcAddress(hinstLib, "NtQueryInformationProcess");

    if (!NtQueryInformationProcess) {
        std::cerr << "Could not get address of NtQueryInformationProcess function: error code " << GetLastError() << std::endl;
        exit(GetLastError());
    }

    PROCESS_BASIC_INFORMATION pbi;
    // Writes infortmation about the process to pbi structure
    NtQueryInformationProcess(ProcessHandle, ProcessBasicInformation, &pbi, sizeof(pbi), 0);

    FreeLibrary(hinstLib);

    return pbi.PebBaseAddress;
}


PVOID GetUserProcParamsAddress(HANDLE hProcess) {
    PVOID pebAddress = GetPebAddress(hProcess);
    PCHAR procParamsAddress = (PCHAR)pebAddress + procParamsOffset;
    PVOID rtlUserProcParamsAddress;

    if (!ReadProcessMemory(hProcess, procParamsAddress, &rtlUserProcParamsAddress, sizeof(PVOID), NULL)) {
        std::cerr << "Could not read the address of ProcessParameters: error code " << GetLastError() << std::endl;
        exit(GetLastError());
    }

    return rtlUserProcParamsAddress;
}


UNICODE_STRING GetCmdLineStruct(HANDLE hProcess) {
    PVOID rtlUserProcParamsAddress = GetUserProcParamsAddress(hProcess);

    UNICODE_STRING cmdLineStruct;
    PCHAR cmdLineAddress = (PCHAR)rtlUserProcParamsAddress + cmdLineOffset;

    // read the CommandLine UNICODE_STRING structure
    if (!ReadProcessMemory(hProcess, cmdLineAddress, &cmdLineStruct, sizeof(cmdLineStruct), NULL)) {
        std::cerr << "Could not read CommandLine address: error code " << GetLastError() << std::endl;
        exit(GetLastError());
    }

    return cmdLineStruct;
}


char *GetCmdLine(HANDLE hProcess) {
    UNICODE_STRING cmdLineStruct = GetCmdLineStruct(hProcess);
    wchar_t *_cmdLine = new wchar_t[cmdLineStruct.Length];

    // read the command line
    if (!ReadProcessMemory(hProcess, cmdLineStruct.Buffer, _cmdLine, cmdLineStruct.Length, NULL)) {
        std::cerr << "Could not read the command line string: error code " << GetLastError() << std::endl;
        exit(GetLastError());
    }

    // convert wchar_t* to char*
    size_t cmdLineLen = cmdLineStruct.Length / 2;
    size_t charsConverted;
    char *cmdLine = new char[cmdLineLen + 1];

    wcstombs_s(&charsConverted, cmdLine, cmdLineLen + 1, _cmdLine, cmdLineLen);
    cmdLine[cmdLineLen] = 0;

    delete[] _cmdLine;

    return cmdLine;
}


UNICODE_STRING GetCurDirPathStruct(HANDLE hProcess) {
    PVOID rtlUserProcParamsAddress = GetUserProcParamsAddress(hProcess);

    UNICODE_STRING curDirPathStruct;
    PCHAR curDirPathAddress = (PCHAR)rtlUserProcParamsAddress + curDirPathOffset;

    // read the CommandLine UNICODE_STRING structure
    if (!ReadProcessMemory(hProcess, curDirPathAddress, &curDirPathStruct, sizeof(curDirPathStruct), NULL)) {
        std::cerr << "Could not read CurrentDirectoryPath address: error code " << GetLastError() << std::endl;
        exit(GetLastError());
    }

    return curDirPathStruct;
}


char *GetCurDirPath(HANDLE hProcess) {
    UNICODE_STRING curDirPathStruct = GetCurDirPathStruct(hProcess);
    wchar_t *_curDirPath = new wchar_t[curDirPathStruct.Length];

    // read the command line
    if (!ReadProcessMemory(hProcess, curDirPathStruct.Buffer, _curDirPath, curDirPathStruct.Length, NULL)) {
        std::cerr << "Could not read the CurrentDirectoryPath string: error code " << GetLastError() << std::endl;
        exit(GetLastError());
    }

    // convert wchar_t* to char*
    size_t curDirPathLen = curDirPathStruct.Length / 2;
    size_t charsConverted;
    char *curDirPath = new char[curDirPathLen + 1];

    wcstombs_s(&charsConverted, curDirPath, curDirPathLen + 1, _curDirPath, curDirPathLen);
    curDirPath[curDirPathLen] = 0;

    delete[] _curDirPath;

    return curDirPath;
}


char *GetPathToProcExecutable(HANDLE hProcess) {
    char *which = new char[MAX_PATH];
    GetModuleFileNameExA(hProcess, NULL, which, MAX_PATH);
    return which;
}


void HandleCreateProcess(CREATE_PROCESS_DEBUG_INFO const &createProcess) {
    HANDLE hProcess = createProcess.hProcess;

    char *cmdLine = GetCmdLine(hProcess);
    char *curDirPath = GetCurDirPath(hProcess);
    char *which = GetPathToProcExecutable(hProcess);

    char *data_file = getenv("CLADE_INTERCEPT");

    if (!data_file) {
        std::cerr << "Environment is not prepared: CLADE_INTERCEPT is not specified" << std::endl;
        exit(EXIT_FAILURE);
    }

    std::fstream cladeTxt;
    cladeTxt.open(data_file, std::ios_base::app);

    cladeTxt << curDirPath << "||0||" << which << "||";

    // TODO: fix spaces inside quotes
    bool underQuotes = FALSE;
    for (unsigned int i = 0; i < strlen(cmdLine); i++) {
        if (cmdLine[i] != ' ' || underQuotes)
            cladeTxt << cmdLine[i];
        else
            cladeTxt << "||";

        if (cmdLine[i] == '"')
                underQuotes = !underQuotes;
    }
    cladeTxt << std::endl;
    cladeTxt.close();

    delete[] cmdLine;
    delete[] curDirPath;
    delete[] which;

    // file handle should be closed, but process handle (hProcess) shouldn't
    if(createProcess.hFile)
        CloseHandle(createProcess.hFile);
}


void EnterDebugLoop() {
    // Store ids of all currently debugging processes
    // Stop debugging once this array is empty
    std::vector<DWORD> processIds;

    while (TRUE) {
        DEBUG_EVENT DebugEvent;
        WaitForDebugEvent(&DebugEvent, INFINITE);

        if (DebugEvent.dwDebugEventCode == CREATE_PROCESS_DEBUG_EVENT) {
            processIds.push_back(DebugEvent.dwProcessId);
            HandleCreateProcess(DebugEvent.u.CreateProcessInfo);
        }
        else if (DebugEvent.dwDebugEventCode == EXIT_PROCESS_DEBUG_EVENT) {
            for (auto it = processIds.begin(); it != processIds.end(); ) {
                if (*it == DebugEvent.dwProcessId)
                    it = processIds.erase(it);
                else
                    ++it;
            }

            if (!processIds.size())
                return;
        }

        DWORD continueStatus = DBG_CONTINUE;
        // In case of exceptions ContinueDebugEvent should be called with DBG_EXCEPTION_NOT_HANDLED
        if (DebugEvent.dwDebugEventCode == EXCEPTION_DEBUG_EVENT) {
            continueStatus = DBG_EXCEPTION_NOT_HANDLED;
        }

        ContinueDebugEvent(DebugEvent.dwProcessId, DebugEvent.dwThreadId, continueStatus);
    }
}


void CreateProcessToDebug(int argc, char **argv) {
    // Make a single string from argv[] array
    std::string cmdLine = "C:\\windows\\system32\\cmd.exe /c ";
    for (int i = 0; i < argc; i++) {
        if (!cmdLine.empty())
            cmdLine += ' ';

        if (strchr( argv[i], ' ' ))
            cmdLine += '"' + argv[i] + '"';
        else
            cmdLine += argv[i];
    }

    // Some structs necessary to perform CreateProcess call
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;

    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    // TODO: Check why handle inheritance is set to TRUE
    // Create new process
    if(!CreateProcessA(NULL,                 // No module name (use command line)
        const_cast<char *>(cmdLine.c_str()), // Command line
        NULL,           // Process handle not inheritable
        NULL,           // Thread handle not inheritable
        TRUE,           // Set handle inheritance to TRUE
        DEBUG_PROCESS,  // Process creation flags. DEBUG_PROCESS allows to debug created process and all its childs
        NULL,           // Use parent's environment block
        NULL,           // Use parent's starting directory
        &si,            // Pointer to STARTUPINFO structure
        &pi ))          // Pointer to PROCESS_INFORMATION structure
    {
        std::cerr <<  "CreateProcess failed: error code " << GetLastError() << std::endl;
        exit(EXIT_FAILURE);
    }

    // We don't need the process and thread handles returned by the CreateProcess call
    // as the debug API will provide them, so we close these handles immediately.
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
}


int main(int argc, char **argv) {
    if (argc <= 1) {
        std::cerr << "Command to execute is missing" << std::endl;
        exit(EXIT_FAILURE);
    }

    ++argv;
    --argc;

    // Use the normal heap manager to remove additional checking
    // that are enabled when process runs in debug mode
    _putenv("_NO_DEBUG_HEAP=1");

    CreateProcessToDebug(argc, argv);
    EnterDebugLoop();

    return 0;
}
