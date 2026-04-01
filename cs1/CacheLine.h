#pragma once
#include <cstdint>

struct CacheLine{
    bool        dirty        =   false;
    bool        valid       =   false;
    uint64_t    tag         =   0;
    uint64_t    lru_counter =   0;
}; // end struct CacheLine
