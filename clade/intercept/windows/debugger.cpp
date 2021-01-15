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
#include <sstream>
#include <fstream>
#include <string>
#include <algorithm>
#include <locale>
#include <codecvt>
#include <functional>
#include <map>

#include <windows.h>
#include <shellapi.h>
#include <psapi.h>
#include <winternl.h>

#include "client.h"

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
typedef NTSTATUS(NTAPI *_NtQueryInformationProcess)(HANDLE, DWORD, PVOID, DWORD, PDWORD);

// Required to get access to InheritedFromUniqueProcessId
typedef struct MY_PROCESS_BASIC_INFORMATION {
    NTSTATUS ExitStatus;
    PPEB PebBaseAddress;
    ULONG_PTR AffinityMask;
    LONG BasePriority;
    ULONG_PTR UniqueProcessId;
    ULONG_PTR InheritedFromUniqueProcessId;
} PBI;

PBI GetPbi(HANDLE hProcess)
{
    HINSTANCE hinstLib = LoadLibrary(TEXT("ntdll.dll"));

    if (!hinstLib)
    {
        std::cerr << "Could not get handle to ntdll module: error code " << GetLastError() << std::endl;
        exit(GetLastError());
    }

    _NtQueryInformationProcess NtQueryInformationProcess = (_NtQueryInformationProcess)GetProcAddress(hinstLib, "NtQueryInformationProcess");

    if (!NtQueryInformationProcess)
    {
        std::cerr << "Could not get address of NtQueryInformationProcess function: error code " << GetLastError() << std::endl;
        exit(GetLastError());
    }

    PBI pbi;

    NtQueryInformationProcess(hProcess, ProcessBasicInformation, &pbi, sizeof(pbi), 0);

    FreeLibrary(hinstLib);

    return pbi;
}

// PEB - process environment block, low-level data stracture containing various information
// Address of the PEB can be obtained using NTAPI function NtQueryInformationProcess
// But the function itself is not public. Its address can be found in ntdll.dll.

PVOID GetUserProcParamsAddress(HANDLE hProcess, PBI &pbi)
{
    PVOID pebAddress = pbi.PebBaseAddress;
    PCHAR procParamsAddress = (PCHAR)pebAddress + procParamsOffset;
    PVOID rtlUserProcParamsAddress;

    if (!ReadProcessMemory(hProcess, procParamsAddress, &rtlUserProcParamsAddress, sizeof(PVOID), NULL))
    {
        std::cerr << "Could not read the address of ProcessParameters: error code " << GetLastError() << std::endl;
        exit(GetLastError());
    }

    return rtlUserProcParamsAddress;
}

UNICODE_STRING GetCmdLineStruct(HANDLE hProcess, PBI &pbi)
{
    PVOID rtlUserProcParamsAddress = GetUserProcParamsAddress(hProcess, pbi);

    UNICODE_STRING cmdLineStruct;
    PCHAR cmdLineAddress = (PCHAR)rtlUserProcParamsAddress + cmdLineOffset;

    // read the CommandLine UNICODE_STRING structure
    if (!ReadProcessMemory(hProcess, cmdLineAddress, &cmdLineStruct, sizeof(cmdLineStruct), NULL))
    {
        std::cerr << "Could not read CommandLine address: error code " << GetLastError() << std::endl;
        exit(GetLastError());
    }

    return cmdLineStruct;
}

wchar_t *GetCmdLine(HANDLE hProcess, PBI &pbi)
{
    UNICODE_STRING cmdLineStruct = GetCmdLineStruct(hProcess, pbi);
    size_t cmdLineLen = cmdLineStruct.Length / 2;
    wchar_t *cmdLine = new wchar_t[cmdLineLen + 1];

    // read the command line
    if (!ReadProcessMemory(hProcess, cmdLineStruct.Buffer, cmdLine, cmdLineStruct.Length, NULL))
    {
        std::cerr << "Could not read the command line string: error code " << GetLastError() << std::endl;
        exit(GetLastError());
    }

    cmdLine[cmdLineLen] = 0;

    return cmdLine;
}

UNICODE_STRING GetCurDirPathStruct(HANDLE hProcess, PBI &pbi)
{
    PVOID rtlUserProcParamsAddress = GetUserProcParamsAddress(hProcess, pbi);

    UNICODE_STRING curDirPathStruct;
    PCHAR curDirPathAddress = (PCHAR)rtlUserProcParamsAddress + curDirPathOffset;

    // read the CommandLine UNICODE_STRING structure
    if (!ReadProcessMemory(hProcess, curDirPathAddress, &curDirPathStruct, sizeof(curDirPathStruct), NULL))
    {
        std::cerr << "Could not read CurrentDirectoryPath address: error code " << GetLastError() << std::endl;
        exit(GetLastError());
    }

    return curDirPathStruct;
}

wchar_t *GetCurDirPath(HANDLE hProcess, PBI &pbi)
{
    UNICODE_STRING curDirPathStruct = GetCurDirPathStruct(hProcess, pbi);
    size_t curDirPathLen = curDirPathStruct.Length / 2;
    wchar_t *curDirPath = new wchar_t[curDirPathLen + 1];

    // read the command line
    if (!ReadProcessMemory(hProcess, curDirPathStruct.Buffer, curDirPath, curDirPathStruct.Length, NULL))
    {
        std::cerr << "Could not read the CurrentDirectoryPath string: error code " << GetLastError() << std::endl;
        exit(GetLastError());
    }

    curDirPath[curDirPathLen] = 0;

    return curDirPath;
}

wchar_t *GetPathToProcExecutable(HANDLE hProcess)
{
    wchar_t *which = new wchar_t[MAX_PATH];
    GetModuleFileNameExW(hProcess, NULL, which, MAX_PATH);
    return which;
}

bool IsFileExist(std::wstring& fileName)
{
    return !!std::ifstream(fileName);
}

wchar_t *ProcessCommandFiles(const wchar_t *_cmdLine)
{
    std::wstring cmdLine = _cmdLine;

    size_t beginning = 0;

    // A command file is specified by an at sign (@) followed by a filename
    // There can be several command files in the command line (cmdLine variable)
    // All of them must be read. and they content must be inserted in the command line string
    while ((beginning = cmdLine.find(L"@", beginning)) != std::wstring::npos)
    {
        const wchar_t *endSymbols = L" ";

        // Sometimes command files are escaped, like this: @"path/to the/file.rsp"
        // Then last symbols should be '" '
        if (cmdLine.at(beginning + 1) == '"')
        {
            endSymbols = L"\" ";
        }

        // There should be "cmdLine.find(endSymbols, beginning) - 1"
        // but we have to support two cases, when ending symbols are " " and "\" ".
        size_t end = cmdLine.find(endSymbols, beginning) + (wcslen(endSymbols) - 2);

        if (end > wcslen(_cmdLine)) {
            // +1 is needed for @"file.txt"\n cases
            end = wcslen(_cmdLine) - wcslen(endSymbols) + 1;
        }

        size_t fileNameBeginning = beginning + 1;
        size_t fileNameLen = end - fileNameBeginning + 1;

        if (cmdLine.at(beginning + 1) == '"')
        {
            fileNameBeginning = fileNameBeginning + 1;
            fileNameLen = fileNameLen - 2;
        }

        std::wstring fileName = cmdLine.substr(fileNameBeginning, fileNameLen);

        // If file does not exist than it is not a command file
        if (!IsFileExist(fileName))
        {
            beginning++;
            continue;
        }

        // Read command file line by line
        std::wifstream infile(fileName, std::ios::binary);

        // detect UTF-16
        wchar_t bom_buf[2];
        infile.read(bom_buf, 2);
        infile.seekg(0, infile.beg);
        if (bom_buf[0] == 0xFF && bom_buf[1] == 0xFE || bom_buf[0] == 0xFE && bom_buf[1] == 0xFF) {
            // apply BOM-sensitive UTF-16 facet
            infile.imbue(std::locale(infile.getloc(),
                                    new std::codecvt_utf16<wchar_t, 0x10ffff, std::consume_header>));
        }

        std::wstring replacement;

        std::wstring line;
        while (std::getline(infile, line))
        {
            // Remove \r characters from the end of the string
            if (!line.empty() && *line.rbegin() == '\r')
            {
                line.erase(line.length() - 1, 1);
            }

            // Special case: /link option  must always occur last
            size_t link_beginning = line.find(L"/link");

            if (link_beginning != std::wstring::npos)
            {
                cmdLine += L" " + line.substr(link_beginning, std::wstring::npos);
                line = line.substr(0, link_beginning);
            }

            if (replacement.empty() || replacement.back() == ' ')
                replacement += line;
            else
                replacement += L" " + line;
        }

        cmdLine.replace(beginning, end - beginning + 1, replacement);
    }

    wchar_t *cmdLineRet = new wchar_t[cmdLine.length() + 1];
    std::wcscpy(cmdLineRet, cmdLine.c_str());
    return cmdLineRet;
}

void HandleCreateProcess(CREATE_PROCESS_DEBUG_INFO const &createProcess, PBI &pbi, int ppid)
{
    HANDLE hProcess = createProcess.hProcess;

    wchar_t *cmdLine = GetCmdLine(hProcess, pbi);
    wchar_t *curDirPath = GetCurDirPath(hProcess, pbi);
    wchar_t *which = GetPathToProcExecutable(hProcess);

    wchar_t *data_file = _wgetenv(L"CLADE_INTERCEPT");

    if (!data_file)
    {
        std::cerr << "Environment is not prepared: CLADE_INTERCEPT is not specified" << std::endl;
        exit(EXIT_FAILURE);
    }

    std::wostringstream data;
    data << curDirPath << L"||" << ppid << L"||" << which;

    wchar_t **cmdList;
    int nArgs;

    wchar_t *processedCmdLine = ProcessCommandFiles(cmdLine);
    cmdList = CommandLineToArgvW(processedCmdLine, &nArgs);

    if (!cmdList)
    {
        std::cerr << "CommandLineToArgvW failed: error code " << GetLastError() << std::endl;
        exit(EXIT_FAILURE);
    }

    for (int i = 0; i < nArgs; i++)
    {
        data << L"||" << cmdList[i];
    }

    data << std::endl;

    if (_wgetenv(L"CLADE_PREPROCESS"))
        SendData(data.str().c_str());
    else
    {
        std::wfstream cladeTxt;
        cladeTxt.open(data_file, std::ios_base::app);
        cladeTxt << data.str();
        cladeTxt.close();
    }

    delete[] cmdLine;
    delete[] processedCmdLine;
    delete[] curDirPath;
    delete[] which;
    LocalFree(cmdList);

    // file handle should be closed, but process handle (hProcess) shouldn't
    if (createProcess.hFile)
        CloseHandle(createProcess.hFile);
}

void EnterDebugLoop(DWORD build_pid)
{
    // Store map of windows process ids to my custom process ids
    std::map<ULONG_PTR, int> pidGraph;
    // Current maximum parent process id
    int max_pid = 0;

    DEBUG_EVENT DebugEvent;

    while (TRUE)
    {
        WaitForDebugEvent(&DebugEvent, INFINITE);

        if (DebugEvent.dwDebugEventCode == CREATE_PROCESS_DEBUG_EVENT)
        {
            PBI pbi = GetPbi(DebugEvent.u.CreateProcessInfo.hProcess);

            // Add first PPID to the map and assign 0 as its value
            auto search = pidGraph.find(pbi.InheritedFromUniqueProcessId);
            if (search == pidGraph.end()) {
                pidGraph[pbi.InheritedFromUniqueProcessId] = max_pid++;
            }

            /// Add PID to the map and assign max_pid as its value
            pidGraph[pbi.UniqueProcessId] = max_pid++;

            HandleCreateProcess(DebugEvent.u.CreateProcessInfo, pbi, pidGraph.at(pbi.InheritedFromUniqueProcessId));
        }
        else if (DebugEvent.dwDebugEventCode == EXIT_PROCESS_DEBUG_EVENT)
        {
            // Stop debugging once main build process is finished
            if (DebugEvent.dwProcessId == build_pid)
                return;
        }
        else if (DebugEvent.dwDebugEventCode == LOAD_DLL_DEBUG_EVENT)
        {
            // close the handle to the loaded DLL.
            if (DebugEvent.u.LoadDll.hFile)
                CloseHandle(DebugEvent.u.LoadDll.hFile);
        }

        DWORD continueStatus = DBG_CONTINUE;
        // In case of exceptions ContinueDebugEvent should be called with DBG_EXCEPTION_NOT_HANDLED
        if (DebugEvent.dwDebugEventCode == EXCEPTION_DEBUG_EVENT)
        {
            continueStatus = DBG_EXCEPTION_NOT_HANDLED;
        }

        ContinueDebugEvent(DebugEvent.dwProcessId, DebugEvent.dwThreadId, continueStatus);
    }
}

DWORD CreateProcessToDebug(int argc, wchar_t **argv)
{
    // Make a single string from argv[] array
    std::wstringstream cmdLine;

    cmdLine << L"C:\\windows\\system32\\cmd.exe /c";

    for (int i = 0; i < argc; i++)
    {
        cmdLine << ' ';

        if (wcschr(argv[i], ' '))
            cmdLine << '"' << argv[i] << '"';
        else
            cmdLine << argv[i];
    }

    // Some structs necessary to perform CreateProcess call
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;

    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    // TODO: Check why handle inheritance is set to TRUE
    // Create new process
    if (!CreateProcessW(
        NULL,                                           // No module name (use command line)
        const_cast<wchar_t *>(cmdLine.str().c_str()),   // Command line
        NULL,                                           // Process handle not inheritable
        NULL,                                           // Thread handle not inheritable
        TRUE,                                           // Set handle inheritance to TRUE
        DEBUG_PROCESS,                                  // Process creation flags. DEBUG_PROCESS allows to debug created process and all its childs
        NULL,                                           // Use parent's environment block
        NULL,                                           // Use parent's starting directory
        &si,                                            // Pointer to STARTUPINFO structure
        &pi))                                           // Pointer to PROCESS_INFORMATION structure
    {
        std::cerr << "CreateProcess failed: error code " << GetLastError() << std::endl;
        exit(EXIT_FAILURE);
    }

    // We don't need the process and thread handles returned by the CreateProcess call
    // as the debug API will provide them, so we close these handles immediately.
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    // Return process ID of the main build process
    return pi.dwProcessId;
}

int wmain(int argc, wchar_t **argv)
{
    if (argc <= 1)
    {
        std::cerr << "Command to execute is missing" << std::endl;
        exit(EXIT_FAILURE);
    }

    ++argv;
    --argc;

    // Use the normal heap manager to remove additional checking
    // that are enabled when process runs in debug mode
    _putenv("_NO_DEBUG_HEAP=1");

    DWORD pid = CreateProcessToDebug(argc, argv);
    EnterDebugLoop(pid);

    return 0;
}
