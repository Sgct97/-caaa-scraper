#!/usr/bin/env python3
"""
Test script to verify deterministic judge query enhancement.
Runs the same query multiple times to ensure consistent output.
"""

import sys
import os

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from query_enhancer import QueryEnhancer

def test_judge_enhancer():
    """Test that enhance_judge_query produces consistent results"""
    
    print("\n" + "="*70)
    print("TESTING DETERMINISTIC JUDGE QUERY ENHANCER")
    print("="*70)
    
    # Test cases: various input formats
    test_cases = [
        "Dobrin",           # Last name only
        "Judge Dobrin",     # With title
        "Hon. Dobrin",      # Honorable abbreviation
        "John Dobrin",      # First + Last name
        "Judge John Dobrin", # Full with title
        "WCJ Smith",        # WCJ prefix
    ]
    
    enhancer = QueryEnhancer()
    
    all_passed = True
    
    for test_input in test_cases:
        print(f"\n{'='*50}")
        print(f"Testing: \"{test_input}\"")
        print(f"{'='*50}")
        
        # Run 3 times to verify consistency
        results = []
        for i in range(3):
            params = enhancer.enhance_judge_query(test_input)
            results.append(params.keywords_any)
        
        # Check all results are identical
        if len(set(results)) == 1:
            print(f"\n✅ PASS - Consistent output across 3 runs")
            print(f"   keywords_any: \"{results[0]}\"")
        else:
            print(f"\n❌ FAIL - Inconsistent output!")
            for i, r in enumerate(results):
                print(f"   Run {i+1}: \"{r}\"")
            all_passed = False
    
    # Summary
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED - Judge enhancer is deterministic!")
    else:
        print("❌ SOME TESTS FAILED - Check output above")
    print("="*70)
    
    return all_passed


if __name__ == "__main__":
    success = test_judge_enhancer()
    sys.exit(0 if success else 1)

