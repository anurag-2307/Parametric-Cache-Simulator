#pragma once
#include <vector>
#include <cstdint>
#include <ctime>
#include <queue>
#include "CacheLine.h"


struct AccessResult{
	bool		is_hit			=	false;
	bool		evicted_dirty	=	false;
	uint64_t 	evicted_addr	=	0;
}; // end struct AccessResult


class CacheSet{
	private:
		//vector of CacheLines > ways
		std::vector<CacheLine> 	ways;
		std::queue<uint64_t> 	way_queue;
		
		uint64_t 	associativity;		//Each CacheSet will have its own associativity.

	public:
		CacheSet( uint64_t associativity );

		AccessResult 	access( uint64_t tag, char type, int rplc );

		AccessResult	access_lru( uint64_t tag, char type, AccessResult& result );

		AccessResult	access_fifo( uint64_t tag, char type, AccessResult& result );

		AccessResult	access_lfu( uint64_t tag, char type, AccessResult& result );
		
		AccessResult	access_random( uint64_t tag, char type, AccessResult& result );
};//end class CacheSet
