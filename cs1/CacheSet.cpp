#include <iostream>
#include <vector>
#include <cstdint>
#include <queue>
#include "CacheSet.h"

CacheSet::CacheSet(uint64_t associativity)
{
	this->associativity = associativity;
	ways.resize(associativity);
} // end CacheSet constructor.

//=================MODULARIZE access FUNCTION========================//
/*AccessResult CacheSet::access(uint64_t tag, char type, int rplc, uint32_t size )
{
	AccessResult result = {false, false, 0}; // AccessResult object.
	bool found = false;
	int way_hit = -1;
	int way_empty = -1;
	uint64_t max_lru = 0;
	uint64_t way_lru = 0;

	for (uint64_t way = 0; way < associativity; way++)
	{
		if (ways[way].valid)
		{
			if (ways[way].tag == tag)
			{
				found = true;
				way_hit = way;
				break;
			} // end ways[way].tag if
			if (rplc == 1)
			{
				if (ways[way].lru_counter >= max_lru)
				{
					max_lru = ways[way].lru_counter;
					way_lru = way; // remember which way is the oldest (to kick out later).
				} // end max_lru if.
			} // end rplc == 1 if
		} // end ways[way].valid if
		else
		{
			if (way_empty == -1)
			{
				way_empty = way;
			} // end way_empty if
		} // end else
	} // end way for

	int way_update = -1;

	if (found)
	{
		result.is_hit = true;
		way_update = way_hit;
	} // end found if
} // end access function

*/

//=====================FIFO====================//
AccessResult CacheSet::access_fifo(uint64_t tag, char type)
{ // Queue to store the tags

	AccessResult result = {false, false, 0}; // AccessResult object.

	bool found = false;
	int way_hit = -1;
	int way_empty = -1;
	uint64_t max_lru = 0;
	uint64_t way_lru = 0;

	for (uint64_t way = 0; way < associativity; way++)
	{
		if (ways[way].valid)
		{
			if (ways[way].tag == tag)
			{
				found = true;
				way_hit = way;
				break;
			}
		} // end ways[way].valid if
		else
		{
			if (way_empty == -1)
			{
				way_empty = way;
			} // end way_empty if
		} // end else
	} // end way for

	int way_update = -1;
	if (found)
	{
		result.is_hit = true;
		way_update = way_hit;
	} // end if
	else
	{
		result.is_hit = false;

		if (way_empty != -1)
		{
			way_update = way_empty;
			way_queue.push(way_update);
		} // end if
		else
		{
			way_update = way_queue.front();
			way_queue.pop();

			if (ways[way_update].valid && ways[way_update].dirty)
			{
				result.evicted_dirty = true;
				result.evicted_addr = ways[way_update].tag;
			} // end if

			way_queue.push(way_update);
		} // end else

		ways[way_update].valid = true;
		ways[way_update].tag = tag;
	} // end else

	if (type == 'S' || type == 'M')
	{
		ways[way_update].dirty = true;
	} // end S/M if
	else if (!found)
	{
		ways[way_update].dirty = false;
	} // end else if !found

	return result;
} // end access_fifo

//============LRU=====================//
// Scope operator to return struct AccessResult by function 'access'
AccessResult CacheSet::access_lru(uint64_t tag, char type)
{

	AccessResult result = {false, false, 0}; // AccessResult object.

	bool found = false;
	int way_hit = -1;
	int way_empty = -1;
	uint64_t max_lru = 0;
	uint64_t way_lru = 0;

	for (uint64_t way = 0; way < associativity; way++)
	{

		//===============SEARCH=========================//
		if (ways[way].valid)
		{
			if (ways[way].tag == tag)
			{
				found = true;
				way_hit = way;
				break; // if tag has been found.
			} // end ways[way].tag if

			if (ways[way].lru_counter >= max_lru)
			{
				max_lru = ways[way].lru_counter;
				way_lru = way; // remember which way is the oldest (to kick out later).
			} // end max_lru if.

		} // end ways[way].valid if
		else
		{
			if (way_empty == -1)
			{
				way_empty = way;
			} // end ways[way].empty.
		} // end ways[way].valid else.

		//==============================================//
	} // end associativity for.

	//=================ACTION=======================//
	int way_update = -1;

	if (found)
	{
		result.is_hit = true;
		way_update = way_hit;
	} // end found if
	else
	{
		result.is_hit = false;

		if (way_empty != -1)
			way_update = way_empty;
		else
		{
			way_update = way_lru;

			// remove the address out of the cache. Check if the address is valid AND is dirty.
			if (ways[way_update].valid && ways[way_update].dirty)
			{
				result.evicted_dirty = true;
				result.evicted_addr = ways[way_update].tag;
			} // end valid and dirty if.
		} // end way_empty else

		ways[way_update].valid = true;
		ways[way_update].tag = tag;
	} // end found else
	//==============================================//

	//=================METADATA=======================//
	if (type == 'S' || type == 'M')
	{
		ways[way_update].dirty = true;
	} // end S/M if
	else if (!found)
	{
		ways[way_update].dirty = false;
	} // end else if !found

	// increment LRU counter
	for (uint64_t way = 0; way < associativity; way++)
	{
		if (ways[way].valid)
		{
			ways[way].lru_counter++;
		} // end valid
	} // end lru counter for

	ways[way_update].lru_counter = 0;
	//==============================================//

	return result;
} // end AccessResult access.
