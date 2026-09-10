//
// Created by uv on 05/08/2026.
//

#ifndef CLEARAIR_LOGGER_H
#define CLEARAIR_LOGGER_H
#ifdef  DEBUG
#include <cstdint>
#include <cstring>
#include <cstdio>
#include "cmsis_os2.h"
#include "FreeRTOS.h"
#include "task.h"
#include "timestamp.h"

// All printf-based logging funnels through one blocking UART transmit
// (see __io_putchar in main.c), so two tasks tracing at once can interleave
// mid-string over the wire. stdioMutex() serializes each full log line/trace
// marker so concurrent FreeRTOS tasks can't garble each other's output.
//
// The mutex is created lazily, on first use, rather than by some fixed task
// at a known point in the boot sequence: mainSensorsMsgLoop doesn't
// self-suspend like the sensor task handlers do, so it can call METHODTRACE
// before any particular task has had a chance to create the mutex up front.
// The critical section makes the check-and-create race-free no matter which
// task gets here first.
inline osMutexId_t stdioMutex() {
    static osMutexId_t m = nullptr;
    if (m == nullptr) {
        taskENTER_CRITICAL();
        if (m == nullptr) {
            m = osMutexNew(nullptr);
        }
        taskEXIT_CRITICAL();
    }
    return m;
}

class MethodTracer {
    char name_[64]{};

    protected:
    void logmsg_(const char* lvl, int line, const char* str) {
        osMutexAcquire(stdioMutex(), osWaitForever);
        printf("%lu-%s %s(%i): %s\r\n", getTimestampMs(), lvl, name_, line, str);
        osMutexRelease(stdioMutex());
    }

    public:
    MethodTracer(const char* name, uint8_t len) {
        std::memmove(&name_, name, len > sizeof(name_) ? sizeof(name_) : len);
        osMutexAcquire(stdioMutex(), osWaitForever);
        printf("++++>%lu-%s\r\n", getTimestampMs(), name_);
        osMutexRelease(stdioMutex());
    }

    ~MethodTracer() {
        osMutexAcquire(stdioMutex(), osWaitForever);
        printf("----<%lu-%s\r\n",getTimestampMs(), name_);
        osMutexRelease(stdioMutex());
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
#define MESSAGELOG(str, ...) { osMutexAcquire(stdioMutex(), osWaitForever); printf(str, ##__VA_ARGS__); osMutexRelease(stdioMutex()); }
#else
#define METHODTRACE
#define METHODLOG(lvl, str)
#define METHODLOGF(lvl, fmt_str, ...)
#define METHODLOGS(lvl, fmt_str, ...)
#define MESSAGELOG(str, ...)
#endif
#define LOGMSG printf(">>>:%s\r\n",__PRETTY_FUNCTION__);
#endif //CLEARAIR_LOGGER_H
