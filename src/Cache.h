#pragma once
#include <iostream>
#include <vector>
#include <cstdint>
#include "CacheSet.h"

constexpr int L1_HIT_TIME = 4;
constexpr int L2_HIT_TIME = 15;
constexpr int MAIN_MEMORY_LATENCY = 200;
class Cache
{
private:
	//=======CORE PARAMETERS FOR CACHE======//
	uint64_t numSets;
	uint64_t blockSize;
	uint64_t associativity;
	//======================================//

	//==========ADDRESS VARIABLES============//
	uint64_t indexBits;
	uint64_t offsetBits;
	//=======================================//

	//=========PERFORMANCE COUNTERS============//
	uint64_t hits = 0;
	uint64_t misses = 0;
	uint64_t reads = 0;
	uint64_t writes = 0;
	uint64_t writebacks = 0;
	uint64_t local_hit_time = 0;
	uint64_t total_cycles = 0;
	uint64_t split_accesses = 0;
	//=========================================//

	int cache_identifier = 0;
	int replacement_policy = 0;
	Cache *next_level; // point to the next level L1->L2->L3->main memory

	std::vector<CacheSet> sets;

	void address_split(uint64_t addr, uint64_t &tag, uint64_t &index);

public:
	Cache(uint64_t size,
		  uint64_t block,
		  uint64_t assoc,
		  Cache *next_level,
		  int cache_identifier,
		  uint64_t local_hit_time,
		  int replacement_policy);

	uint64_t request_access(char type, uint64_t addr, int cache_identifier, uint32_t size, bool pf_en);
	uint64_t internal_lookup(char type, uint64_t addr, int cache_identifier, uint32_t size, bool pf_en);

	void print_stats();

}; // end class Cache
