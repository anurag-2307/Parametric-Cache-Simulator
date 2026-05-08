#include <iostream>
#include <vector>
#include <fstream>
#include <stdexcept>
#include <cstdint>
#include <string>
#include "TraceParser.h"
#include "Cache.h"

#define pf_en true
int main(int argc, char **argv)
{

    if (argc < 2)
    {
        std::cerr << "Failed to run program" << "\n";
        return 1;
    } // end argc if
    //============================DEFAULTS========================================//
    uint64_t l1_size = 8192; // 8KB split
    uint64_t l1_assoc = 4;
    uint64_t l2_size = 1024 * 1024; // 1MB unified
    uint64_t l2_assoc = 8;
    uint64_t blockSize = 64;

    std::string policy = "LRU";
    bool prefetch_enabled = false;
    std::string trace_file = "";
    //==========================================================================//

    int rplc = 0;
    for (int i = 1; i < argc; i++)
    {
        std::string arg = argv[i];

        // --help command
        if (arg == "-h" || arg == "--help")
        {
            std::cout << "Usage: ./cs1op [options] --trace <file>\n";
            std::cout << "Options:\n";
            std::cout << "  --l1-size <bytes>    (Default: 8192)\n";
            std::cout << "  --l2-size <bytes>    (Default: 1048576)\n";
            std::cout << "  --policy <LRU|FIFO>  (Default: LRU)\n";
            std::cout << "  --prefetch <ON|OFF>  (Default: OFF)\n";
            std::cout << "  --trace <file.txt>   (Required)\n";
            return 0; // Exit program
        }

        else if (arg == "--trace" && i + 1 < argc)
        {
            trace_file = argv[++i];
        }
        else if (arg == "--prefetch" && i + 1 < argc)
        {
            std::string pf_val = argv[++i];
            prefetch_enabled = (pf_val == "ON" || pf_val == "on");
        }

        // Parse Integer Arguments
        else if (arg == "--l1-size" && i + 1 < argc)
        {
            l1_size = std::stoull(argv[++i]);
        }
        else if (arg == "--l2-size" && i + 1 < argc)
        {
            l2_size = std::stoull(argv[++i]);
        }
        else if (arg == "--l1-assoc" && i + 1 < argc)
        {
            l1_assoc = std::stoull(argv[++i]);
        }
        else if (arg == "--l2-assoc" && i + 1 < argc)
        {
            l2_assoc = std::stoull(argv[++i]);
        }
        else if (arg == "--policy" && i + 1 < argc)
        {
            std::string pol_val = argv[++i];
            if (pol_val == "FIFO" || pol_val == "fifo")
                rplc = 1;
            else if (pol_val == "LFU" || pol_val == "lfu")
                rplc = 3;
            else if (pol_val == "RANDOM" || pol_val == "random" || pol_val == "Random")
                rplc = 4;
            else
                rplc = 2; // Default to LRU
        }
    }

    // check for valid trace file
    if (trace_file == "")
    {
        std::cerr << "ERROR: You must provide a trace file. Use --trace <file.txt>\n";
        return 1;
    }

    TraceParser parser;
    TraceRecord record;

    //==================CREATE CACHE OBJECTS=========================//

    Cache L2_cache(l2_size, blockSize, l2_assoc, nullptr, 2, L2_HIT_TIME, rplc);

    Cache L1_instr(l1_size / 2, blockSize, l1_assoc, &L2_cache, 1, L1_HIT_TIME, rplc);
    Cache L1_data(l1_size / 2, blockSize, l1_assoc, &L2_cache, 1, L1_HIT_TIME, rplc);
    //===============================================================//

    uint64_t modified_instrs = 0;

    std::ifstream traceFile(trace_file);

    if (!traceFile.is_open())
    {
        std::cerr << "Error opening File." << "\n";
        return 1;
    } // end !traceFile open

    while (parser.parse_trace(traceFile, record))
    {

        if (record.type == 'I')
        {
            L1_instr.request_access('I', record.addr, 1, record.size, prefetch_enabled);
        } // end I if

        else if (record.type == 'M')
        {
            L1_data.request_access('L', record.addr, 1, record.size, prefetch_enabled);
            L1_data.request_access('S', record.addr, 1, record.size, prefetch_enabled);
            modified_instrs++;
        } // end M if
        else
        {
            L1_data.request_access(record.type, record.addr, 1, record.size, prefetch_enabled);
        } // end M else
    } // end while

    std::cout << "\n==================================================================\n";
    std::cout << "Instruction Cache (I-Cache) : \n";
    L1_instr.print_stats();

    std::cout << "\n==================================================================\n";
    std::cout << "Data Cache (D-Cache) : \n";
    L1_data.print_stats();

    std::cout << "\n==================================================================\n";
    std::cout << "Unified L2 Cache : \n";
    L2_cache.print_stats();

    std::cout << "\n\nMODIFIED INSTURCTIONS : " << modified_instrs << "\n\n";
    return 0;
} // end main
