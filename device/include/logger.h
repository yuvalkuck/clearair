//
// Created by uv on 05/08/2026.
//

#ifndef CLEARAIR_LOGGER_H
#define CLEARAIR_LOGGER_H
#include <cstdint>
#include <cstring>
#include <cstdio>

class MethodTracer {
    char name_[64]{};
    public:
    MethodTracer(const char *name, uint8_t len) {
        std::memmove(&name_, name, len>sizeof(name_)?sizeof(name_):len);
        printf("++++>%s\n",name_);

    }
    ~MethodTracer() {
        printf("---->%s\n",name_);
    }
};
#ifdef  DEBUG
#define METHODTRACE MethodTracer(__func__,sizeof(__func__)-1);
#define LOGTRACE(fmt, ...) printf(fmt, ##__VA_ARGS__);
#else
#define METHODTRACE
#define LOGTRACE(fmt, ...)
#endif
#endif //CLEARAIR_LOGGER_H
