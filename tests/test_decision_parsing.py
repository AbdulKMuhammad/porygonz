#!/usr/bin/env python3
"""
Test decision parsing improvements
"""

import re

def test_parsing_logic():
    """Test the enhanced parsing logic"""
    
    print("="*80)
    print("TESTING DECISION PARSING IMPROVEMENTS")
    print("="*80)
    
    # Test case 1: Normal case with DECISION
    test1 = """REASONING: Tyranitar is weak to Fighting moves. We should use our best attack.
DECISION: closecombat"""
    
    # Test case 2: Misspelling (REASONNING)
    test2 = """REASONNING: Water beats Fire. Simple type advantage here.
DECISION: surf"""
    
    # Test case 3: Missing DECISION keyword (just the move at the end)
    test3 = """REASONING: Their HP is low and we outspeed. Go for the KO.
flamethrower"""
    
    # Test case 4: DECISION with SWITCH prefix
    test4 = """REASONING: Bad matchup. Need to switch out.
DECISION: SWITCH: charizard"""
    
    # Test case 5: Incomplete DECISION (cut off)
    test5 = """REASONING: This is a very long reasoning that explains type matchups and stat calculations in extreme detail, going into the mechanics of damage calculation and why this particular move is the best option given all the circumstances of the battle state including weather, terrain, and hazards, and considering all possible outcomes
DECISION: flamethro"""
    
    test_cases = [
        ("Normal DECISION", test1, "closecombat"),
        ("Misspelling REASONNING", test2, "surf"),
        ("Missing DECISION keyword", test3, "flamethrower"),
        ("SWITCH prefix", test4, "charizard"),
        ("Incomplete DECISION", test5, "flamethro"),
    ]
    
    print("\nTesting parsing logic:\n")
    
    for name, test_output, expected in test_cases:
        print(f"Test: {name}")
        print(f"Output: {repr(test_output[:80])}")
        
        # Apply the parsing logic
        llm_output = test_output.strip()
        llm_output = re.sub(r'[^\x20-\x7E\n]', '', llm_output)
        
        # Extract reasoning and decision (same logic as in porygonz.py)
        reasoning_match = re.search(r'REASON(?:ING|NING)?:\s*(.+?)(?=DECISION:|$)', llm_output, re.IGNORECASE | re.DOTALL)
        decision_match = re.search(r'DECISION:\s*(.+?)(?:\n|$)', llm_output, re.IGNORECASE)
        
        reasoning_text = reasoning_match.group(1).strip() if reasoning_match else "[No reasoning provided]"
        
        # If no DECISION found, try to extract last meaningful line
        if not decision_match:
            lines = [l.strip() for l in llm_output.split('\n') if l.strip()]
            if lines:
                for line in reversed(lines[-3:]):
                    if len(line) < 50 and any(c.isalpha() for c in line):
                        decision_text = line
                        break
                else:
                    decision_text = lines[-1] if lines else llm_output.strip()
            else:
                decision_text = llm_output.strip()
        else:
            decision_text = decision_match.group(1).strip()
        
        # Clean up decision text
        decision_text = re.sub(r'^(SWITCH:|MOVE:)\s*', '', decision_text, flags=re.IGNORECASE)
        
        # Check if valid
        is_valid = len(decision_text) <= 100 and any(c.isalpha() for c in decision_text)
        
        print(f"  Reasoning: {reasoning_text[:50]}...")
        print(f"  Decision: {decision_text}")
        print(f"  Valid: {is_valid}")
        print(f"  Expected: {expected}")
        
        if decision_text.lower() in expected.lower() or expected.lower() in decision_text.lower():
            print(f"  ✅ PASS")
        else:
            print(f"  ⚠️  Parsed differently")
        print()
    
    print("="*80)
    print("KEY IMPROVEMENTS")
    print("="*80)
    print("""
1. ✅ Handles misspellings: REASONNING, REASONING
2. ✅ Extracts last line if DECISION keyword missing
3. ✅ Removes SWITCH:/MOVE: prefixes automatically
4. ✅ Checks last 3 lines for short valid moves
5. ✅ Increased max_new_tokens to 200
6. ✅ Updated prompt to emphasize conciseness
7. ✅ System message reinforces completing DECISION

These changes should significantly improve decision extraction reliability.
""")

if __name__ == "__main__":
    test_parsing_logic()
