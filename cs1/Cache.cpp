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

uint64_t Cache::request_access(char type, uint64_t addr, int cache_identifier, uint32_t size, bool pf_en) {
    
    uint64_t total_latency = 0;
    uint64_t line_start = addr / blockSize;
    uint64_t line_end   = (addr + size - 1) / blockSize;

    if (line_start != line_end) {
    	split_accesses++;
        total_latency += internal_lookup(type, addr, cache_identifier, size, pf_en);
        total_latency += internal_lookup(type, addr + size - 1, cache_identifier, size, pf_en);
    } else {
        total_latency = internal_lookup(type, addr, cache_identifier, size, pf_en);
    }

    this->total_cycles += total_latency;
    return total_latency;
}

uint64_t Cache::internal_lookup(char type, uint64_t addr, int cache_identifier, uint32_t size, bool pf_en ) {

	if (type == 'L' || type == 'I') reads++;
    if (type == 'S') writes++;
    
    uint64_t time_spent = this->local_hit_time;
    uint64_t tag, index;
    
    address_split(addr, tag, index);
    AccessResult res;
    res = sets[index].access(tag, type, replacement_policy);
	
    if (res.is_hit) {
        hits++;
    } // end if res.is_hit
    else {
        misses++;
        if (next_level != nullptr) {
        	uint64_t block_aligned_addr = (addr / blockSize) * blockSize;
            time_spent += next_level->request_access('L', block_aligned_addr, cache_identifier + 1, size, pf_en);


			if(pf_en){
				uint64_t next_addr = block_aligned_addr + blockSize;
				uint64_t next_tag, next_index;

				address_split(next_addr, next_tag, next_index);
				AccessResult prefetch_res = sets[next_index].access(next_tag, 'L', replacement_policy);

				if( !prefetch_res.is_hit ){
					next_level->request_access('L', next_addr, cache_identifier+1, size,pf_en);	
				} // end not prefetch not hit

	            if( prefetch_res.evicted_dirty ){
	            	writebacks++;
	            	uint64_t prefetch_new_addr = (prefetch_res.evicted_addr << (indexBits + offsetBits)) | (next_index << offsetBits);
	            	next_level->request_access('S', prefetch_new_addr, 2, blockSize, pf_en);
	            } // end prefetch evicted_dirty
            }//end prefetch_enable
        } //end if
        else {
            time_spent += MAIN_MEMORY_LATENCY;
        } //end else
    } //end else

    if (res.evicted_dirty) {
        writebacks++;
        if (next_level != nullptr) {
            uint64_t new_addr = (res.evicted_addr << (indexBits + offsetBits)) | (index << offsetBits);
            next_level->request_access('S', new_addr, 2, blockSize, pf_en);
        } //end if
    }//end if

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
	std::cout << "\nReplacement Policy used : ";
	if		( replacement_policy == 1 ) std::cout << "FIFO" << "\n";
	else if	( replacement_policy == 2 ) std::cout << "LRU" << "\n";
	else if	( replacement_policy == 3 ) std::cout << "LFU" << "\n";
	else if	( replacement_policy == 4 ) std::cout << "Random" << "\n";
	std::cout << "====================================================================\n";
}//end print_stats()
