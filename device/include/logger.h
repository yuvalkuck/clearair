//
// Created by uv on 05/08/2026.
//

#ifndef CLEARAIR_LOGGER_H
#define CLEARAIR_LOGGER_H
#ifdef  DEBUG
#include <cstdint>
#include <cstring>
#include <cstdio>
class MethodTracer {
    char name_[64]{};

    protected:
    void logmsg_(const char* lvl, int line, const char* str) {
        printf("%s %s(%i): %s\r\n", lvl, name_, line, str);
    }

    public:
    MethodTracer(const char* name, uint8_t len) {
        std::memmove(&name_, name, len > sizeof(name_) ? sizeof(name_) : len);
        printf("++++>%s\r\n", name_);
    }

    ~MethodTracer() {
        printf("----<%s\r\n", name_);
    }

    void fatal(int line, const char* str) { logmsg_("Fatal", line, str); }
    void error(int line, const char* str) { logmsg_("Error", line, str); }
    void debug(int line, const char* str) { logmsg_("Debug", line, str); }
    void trace(int line, const char* str) { logmsg_("Trace", line, str); }
    void warn(int line, const char* str) { logmsg_("Warning", line, str); }
    void info(int line, const char* str) { logmsg_("Info", line, str); }
};

#include "fmt/base.h"
#define METHODTRACE MethodTracer __methodTracer(__PRETTY_FUNCTION__,sizeof(__PRETTY_FUNCTION__)-1);
#define METHODLOG(lvl, str) __methodTracer.lvl(__LINE__, str);
#define METHODLOGF(lvl, fmt_str, ...) { char traceBuffer[64]={0}; fmt::format_to_n(traceBuffer, sizeof(traceBuffer)-1,fmt_str,##__VA_ARGS__); __methodTracer.lvl(__LINE__, traceBuffer);}
#define METHODLOGS(lvl, fmt_str, ...) { char traceBuffer[64]={0}; snprintf(traceBuffer, sizeof(traceBuffer)-1, fmt_str, ##__VA_ARGS__); __methodTracer.lvl(__LINE__, traceBuffer);}
#define MESSAGELOG(str, ...) printf(str, ##__VA_ARGS__);
#else
#define METHODTRACE
#define METHODLOG(lvl, str)
#define METHODLOGF(lvl, fmt_str, ...)
#define METHODLOGS(lvl, fmt_str, ...)
#define MESSAGELOG(str, ...)
#endif
#define LOGMSG printf(">>>:%s\r\n",__PRETTY_FUNCTION__);
#endif //CLEARAIR_LOGGER_H
