#include <iostream>
#include <cstdint>
#include <ctime>
#include <vector>

/*
	CacheSet => 	Vector of CacheLines -> ways

	functions:
		access( tag, type )

	CacheLine:
		bool 		dirty
		bool 		valid
		uint64_t 	lru_counter
		uint64_t 	tag
	For every index, go through each block in the set associative cache, match the tag, get the word (or write).

	TraceRecord 	record

	AccessResult 	result;									//AccessResult object.
		result.is_hit			=	false;
		result.evicted_dirty	=	false;
		result.evicted_addr		=	0;
*/

int main(){

	bool		found 		=	false;
	int			way_empty	=	-1;
	uint64_t	way_lru		=	-1;
	int			way_hit		=	0;
	uint64_t 	max_lru 	=	0;
	
	for( uint64_t way = 0; way < associativity; way++){

		//1. Search
		if( ways[way].valid ){
			if( ways[way].tag == record.tag ){
				found 		=	true;
				way_hit 	=	way;
				break;
			}//end if

			if( ways[way].lru_counter > max_lru ){
				max_lru		=	ways[way].lru_counter;
				ways[way].lru_counter = 0;
			}
		}//end if
		else{
			if( way_empty	==	 -1){
				way_empty	=	way;
			}
		}//end else
	}//end for

	//2. Action
	int		way_update = 0;

	if( found ){
		result.is_hit 	=	true;
		way_update		=	way;
	}
	else{
		if( way_empty != -1){
			way_update	=	way_empty;
		}
		else{
			way_update	=	way_lru;

			if( ways[way_update].valid && ways[way_update].dirty){
				result.evicted_dirty	=	true;
				result.evicted_addr		=	ways[way_updated].tag;
			}
		}//end way_empty else

		ways[way_update].valid	=	true;
		ways[way_update].tag	=	tag;
	}//end found else


	//3. Metadata
	if( type == 'S' || type == 'M'){
		ways[way_update].dirty	=	true;
	}
	else if( !found ) ways[way_update].dirty	=	false;

	for( uint64_t way = 0; way < associativity; way++){
		if( ways[way].valid ){
			ways[way].lru_counter++;
		}
	}

	ways[way_update].lru_counter = 0;
	
}	
