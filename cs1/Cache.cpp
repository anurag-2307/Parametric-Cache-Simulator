#include "Cache.h"

Cache::Cache( 	uint64_t size,
				uint64_t block,
				uint64_t assoc,
				Cache* next_level,
				int cache_identifier,
				uint64_t local_hit_time,
				int replacement_policy 
			){
	this->blockSize = block;
	this->associativity = assoc;
	this->numSets	= size / (block * assoc);
	this->next_level= next_level;
	this->cache_identifier = cache_identifier;
    this->local_hit_time = local_hit_time;
	this->replacement_policy = replacement_policy;
	
	offsetBits = __builtin_ctzll(blockSize);
	indexBits  = __builtin_ctzll(numSets);

	sets.reserve(numSets);
	for (uint64_t i = 0; i < numSets; i++) {
  		sets.emplace_back(associativity); 
	} // end for
}//end constructor.

void 	Cache::address_split( uint64_t addr, uint64_t& tag, uint64_t& index ){
	index = (addr >> offsetBits) & ((1ULL << indexBits) - 1);
	tag   = addr >> (offsetBits + indexBits);
}//end address_split function

uint64_t Cache::request_access(char type, uint64_t addr, int cache_identifier, uint32_t size) {
    

    uint64_t total_latency = 0;
    uint64_t line_start = addr / blockSize;
    uint64_t line_end   = (addr + size - 1) / blockSize;

    if (line_start != line_end) {
    	split_accesses++;
        total_latency += internal_lookup(type, addr, cache_identifier, size);
        total_latency += internal_lookup(type, addr + size - 1, cache_identifier, size);
    } else {
        total_latency = internal_lookup(type, addr, cache_identifier, size);
    }

    this->total_cycles += total_latency;
    return total_latency;
}

uint64_t Cache::internal_lookup(char type, uint64_t addr, int cache_identifier, uint32_t size) {

	if (type == 'L' || type == 'I') reads++;
    if (type == 'S') writes++;
    
    uint64_t time_spent = this->local_hit_time;
    uint64_t tag, index;
    
    address_split(addr, tag, index);

    AccessResult res;
    if (replacement_policy == 1) res = sets[index].access_fifo(tag, type);	
    else if (replacement_policy == 2) res = sets[index].access_lru(tag, type);

    if (res.is_hit) {
        hits++;
    } else {
        misses++;
        if (next_level != nullptr) {
        	uint64_t block_aligned_addr = (addr / blockSize) * blockSize;
            time_spent += next_level->request_access('L', block_aligned_addr, cache_identifier + 1, size);
        } else {
            time_spent += MAIN_MEMORY_LATENCY;
        }
    }

    if (res.evicted_dirty) {
        writebacks++;
        if (next_level != nullptr) {
            uint64_t new_addr = (res.evicted_addr << (indexBits + offsetBits)) | (index << offsetBits);
            next_level->request_access('S', new_addr, 2, blockSize);
        }
    }

    return time_spent;
}

void	Cache::print_stats( ){

	uint64_t total_accesses = hits + misses;
	
    std::cout << "--- Cache Simulation Results : L" << cache_identifier << " cache ---\n";
    std::cout << "Total Accesses : " << total_accesses << "\n";
    std::cout << "Reads          : " << reads << "\n";
    std::cout << "Writes         : " << writes << "\n";
    std::cout << "Cache Hits     : " << hits << "\n";
    std::cout << "Cache Misses   : " << misses << "\n";
    std::cout << "Write Backs    : " << writebacks << "\n";
    
    if (total_accesses > 0) {
        std::cout << "Hit Rate       : " << (static_cast<double>(hits) / total_accesses) * 100.0 << " %\n";
        std::cout << "Miss Rate      : " << (static_cast<double>(misses) / total_accesses) * 100.0 << " %\n";
        std::cout << "AMAT	       : " <<  static_cast<double> (this->total_cycles) / total_accesses << "\n";
    }
    std::cout << "Split Accesses : " << split_accesses << "\n";
	std::cout << "====================================================================\n";
}//end print_stats()
