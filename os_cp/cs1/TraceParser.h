#pragma once
#include <string>
#include <fstream>
#include <cstdint>
#include <charconv>
#include <string_view>
#include <stdexcept>

struct TraceRecord {
    char        type;
    uint64_t    addr;
    uint32_t    size;
};

class TraceParser {
private:
    std::string instruction;

public:
    bool parse_trace(std::ifstream& traceFile, TraceRecord& current_record) {
        while (getline(traceFile, instruction)) {
            if (instruction.empty()) continue;
            if (instruction[0] == '#' || instruction[0] == '=') continue;

            instruction.erase(0, instruction.find_first_not_of(" \t\r\n"));
            std::string_view sv(instruction);

            size_t first = sv.find_first_not_of(" \t\r\n");
            if (first == std::string_view::npos || sv[first] == '#' || sv[first] == '=') continue;
            sv.remove_prefix(first);

            current_record.type = sv[0];
            sv.remove_prefix(1);

            size_t addr_start = sv.find_first_not_of(" \t");
            if (addr_start == std::string_view::npos) continue;
            sv.remove_prefix(addr_start);

            if (sv.size() >= 2 && sv[0] == '0' && (sv[1] == 'x' || sv[1] == 'X')) sv.remove_prefix(2);

            auto result_addr = std::from_chars(sv.data(), sv.data() + sv.size(), current_record.addr, 16);
            if (result_addr.ec != std::errc{}) continue;

            sv.remove_prefix(result_addr.ptr - sv.data());

            if (!sv.empty() && sv[0] == ',') {
                sv.remove_prefix(1);
                auto res_size = std::from_chars(sv.data(), sv.data() + sv.size(), current_record.size, 10);
                if (res_size.ec != std::errc{}) {
                    throw std::runtime_error("Invalid Trace format");
                }
            }
            return true;
        }
        return false;
    }
};
