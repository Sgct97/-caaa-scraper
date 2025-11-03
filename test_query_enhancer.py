#!/usr/bin/env python3
"""
Quick test for query enhancer
"""

from query_enhancer import QueryEnhancer

# Test with a simple query
enhancer = QueryEnhancer(model="gpt-4o-mini")

test_query = "I need cases about injured workers getting denied medical treatment in the last 3 months"

print(f"\nTesting query enhancement:")
print(f"User query: \"{test_query}\"")
print("\n" + "="*60)

search_params = enhancer.enhance_query(test_query)

print("\n" + "="*60)
print("RESULT:")
print(f"  keyword: {search_params.keyword}")
print(f"  keywords_all: {search_params.keywords_all}")
print(f"  keywords_phrase: {search_params.keywords_phrase}")
print(f"  keywords_any: {search_params.keywords_any}")
print(f"  listserv: {search_params.listserv}")
print(f"  date_from: {search_params.date_from}")
print(f"  date_to: {search_params.date_to}")
print(f"  search_in: {search_params.search_in}")

print("\n✓ Query enhancement test complete!")

