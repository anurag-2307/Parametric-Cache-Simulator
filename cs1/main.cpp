#include <iostream>
#include <vector>
#include <fstream>
#include <stdexcept>
#include <cstdint>
#include "TraceParser.h"
#include "Cache.h"

#define rplc 2

int main(int argc, char** argv){

	if( argc < 2 ){
		std::cerr << "Failed to run program" << "\n";
		return 1;
	}//end argc if
	
	uint64_t cacheSize 		= 16384;
	uint64_t blockSize 		= 128;
	uint64_t associativity 	= 8;

	TraceParser parser;
	TraceRecord record;

	//==================CREATE CACHE OBJECTS=========================//
	Cache L2_cache( (2048*2048), blockSize, (associativity*2), nullptr, 2, L2_HIT_TIME,	rplc );

	Cache L1_instr( (cacheSize/2), blockSize, associativity, &L2_cache, 1, L1_HIT_TIME, rplc );
	Cache L1_data ( (cacheSize/2), blockSize, associativity, &L2_cache, 1, L1_HIT_TIME, rplc );
	//===============================================================//


	std::ifstream traceFile(argv[1]);

	if( !traceFile.is_open() ){
		std::cerr << "Error opening File." << "\n";
		return 1;
	}//end !traceFile open

	while( parser.parse_trace( traceFile, record ) ){

		if( record.type == 'I' ){
			L1_instr.request_access( 'I', record.addr, 1, record.size );
		}//end I if

		else if( record.type == 'M' ){
			L1_data.request_access( 'L', record.addr, 1, record.size );
			L1_data.request_access( 'S', record.addr, 1, record.size );
		}//end M if
		else{
			L1_data.request_access( record.type, record.addr, 1, record.size );
		}//end M else
	}//end while


	std::cout << "\n==================================================================\n";
	std::cout << "Instruction Cache (I-Cache) : \n"; 
	L1_instr.print_stats();


	std::cout << "\n==================================================================\n";
	std::cout << "Data Cache (D-Cache) : \n";
	L1_data.print_stats();


	std::cout << "\n==================================================================\n";
	std::cout << "Unified L2 Cache : \n";
	L2_cache.print_stats();
	return 0;
}//end main
