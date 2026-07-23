//
// Created by uv on 22/07/2026.
//

#ifndef CLEARAIR_FIXED_QUEUE_H
#define CLEARAIR_FIXED_QUEUE_H
#include <event_message.h>

#include <cstddef>
namespace Common {
    template <size_t N>
    class FixedQueue {
    public:
        bool push(const Common::Message& msg) {
            size_t next = (m_head + 1) % N;
            if (next == m_tail) return false; // full, drop
            m_buf[m_head] = msg;
            m_head = next;
            return true;
        }

        bool pop(Common::Message& out) {
            if (m_tail == m_head) return false; // empty
            out = m_buf[m_tail];
            m_tail = (m_tail + 1) % N;
            return true;
        }

        bool empty() const { return m_tail == m_head; }

    private:
        Common::Message m_buf[N]{};
        size_t m_head = 0;
        size_t m_tail = 0;
    };
}
using MessageQueue = Common::FixedQueue<32>;
#endif //CLEARAIR_FIXED_QUEUE_H
