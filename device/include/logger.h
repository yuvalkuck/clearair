//
// Created by uv on 05/08/2026.
//

#ifndef CLEARAIR_LOGGER_H
#define CLEARAIR_LOGGER_H
#include <cstdint>
#include <cstring>
#include <cstdio>

class MethodTracer {
    char name_[128]{};

    public:
    MethodTracer(const char* name, uint8_t len) {
        std::memmove(&name_, name, len > sizeof(name_) ? sizeof(name_) : len);
        printf("++++>%s\r\n", name_);
    }

    ~MethodTracer() {
        printf("---->%s\r\n", name_);
    }
    void error(int line, const char* str) {
        printf("Error(%i): %s\r\n", line, str);
    }
};
#ifdef  DEBUG
#include "fmt/base.h"
#define METHODTRACE MethodTracer __methodTracer(__PRETTY_FUNCTION__,sizeof(__PRETTY_FUNCTION__)-1);
#define METHODTRACE_E(fmt_str, ...) { char traceBuffer[128]={0}; fmt::format_to_n(traceBuffer, sizeof(traceBuffer)-1,fmt_str,##__VA_ARGS__); __methodTracer.error(__LINE__, traceBuffer);}
#define LOGTRACE(fmt_str, ...) {char traceBuffer[128]={0}; fmt::format_to_n(traceBuffer, sizeof(traceBuffer)-1,fmt_str,##__VA_ARGS__); printf("%s\r\n", traceBuffer);}
#define METHODENTER printf("MethodEnter:%s\r\n",__PRETTY_FUNCTION__);
#else
#define METHODTRACE
#define METHODTRACE_E
#define LOGTRACE(fmt, ...)
#define METHODENTER
#endif
#endif //CLEARAIR_LOGGER_H
