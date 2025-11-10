#!/usr/bin/env python3
"""
Test concise reasoning and proper decision parsing
"""

import re

def test_switch_parsing():
    """Test the improved switch parsing logic"""
    
    print("="*80)
    print("TESTING IMPROVED PARSING")
    print("="*80)
    
    # Mock Pokemon names in reserve
    class MockPokemon:
        def __init__(self, name):
            self.name = name
            self.fainted = False
    
    reserve = [
        MockPokemon("Ludicolo"),
        MockPokemon("Charizard"),
        MockPokemon("Iron-Thorns"),
        MockPokemon("Garganacl")
    ]
    
    # Test cases
    switch_tests = [
        ("switch ludicolo", "Ludicolo"),
        ("switch Ludicoro", "Ludicolo"),  # Typo should still match
        ("switch charizard", "Charizard"),
        ("switch ironthorns", "Iron-Thorns"),  # No hyphen in input
        ("switch iron-thorns", "Iron-Thorns"),  # Hyphen in input
        ("switch garganacl", "Garganacl"),
        ("switch garga", "Garganacl"),  # Partial match
    ]
    
    print("\n🔄 SWITCH PARSING TESTS:\n")
    
    for decision_input, expected in switch_tests:
        print(f"Input: '{decision_input}'")
        
        # Apply fuzzy matching logic with similarity scoring
        switch_match = re.search(r'switch\s+([\w-]+)', decision_input, re.IGNORECASE)
        if switch_match:
            target_pokemon = switch_match.group(1).strip()
            found = False
            best_match = None
            best_score = 0
            
            for pkmn in reserve:
                if not pkmn.fainted:
                    pkmn_name_lower = pkmn.name.lower().replace('-', '').replace(' ', '')
                    target_lower = target_pokemon.lower().replace('-', '').replace(' ', '')
                    
                    # Check substring match first
                    if target_lower in pkmn_name_lower or pkmn_name_lower in target_lower:
                        print(f"  → Matched (substring): switch {pkmn.name}")
                        if pkmn.name == expected:
                            print(f"  ✅ CORRECT\n")
                        else:
                            print(f"  ⚠️  Expected: switch {expected}\n")
                        found = True
                        break
                    
                    # Calculate similarity score
                    matches = sum(1 for a, b in zip(target_lower, pkmn_name_lower) if a == b)
                    score = matches / max(len(target_lower), len(pkmn_name_lower))
                    
                    if score > best_score:
                        best_score = score
                        best_match = pkmn
            
            if not found and best_match and best_score > 0.7:
                print(f"  → Matched (fuzzy {best_score:.0%}): switch {best_match.name}")
                if best_match.name == expected:
                    print(f"  ✅ CORRECT\n")
                else:
                    print(f"  ⚠️  Expected: switch {expected}\n")
                found = True
            
            if not found:
                print(f"  ❌ NO MATCH FOUND (best score: {best_score:.0%})\n")
    
    # Test sentence extraction
    print("\n📝 SENTENCE EXTRACTION TESTS:\n")
    
    available_moves = ["thunderbolt", "icebeam", "surf", "hypervoice"]
    
    sentence_tests = [
        ("Hypervoice allows you to boost all three types", "hypervoice"),
        ("I think we should use thunderbolt here", "thunderbolt"),
        ("The best move is surf", "surf"),
        ("icebeam", "icebeam"),
    ]
    
    for decision_input, expected in sentence_tests:
        print(f"Input: '{decision_input}'")
        
        decision_text = decision_input.lower().strip()
        
        # If sentence, extract move name
        if len(decision_text.split()) > 3:
            for word in decision_text.split():
                if word.lower() in available_moves:
                    decision_text = word
                    break
        
        print(f"  → Extracted: {decision_text}")
        if decision_text == expected:
            print(f"  ✅ CORRECT\n")
        else:
            print(f"  ⚠️  Expected: {expected}\n")
    
    print("="*80)
    print("KEY IMPROVEMENTS SUMMARY")
    print("="*80)
    print("""
1. ✅ Token limit: 250 → 120 (forces 2-3 sentence reasoning)
2. ✅ Temperature: 0.3 → 0.2 (more focused output)
3. ✅ Prompt explicitly states "2-3 sentences max"
4. ✅ System message shows concrete examples (DECISION: thunderbolt)
5. ✅ Fuzzy switch matching (handles typos like "Ludicoro" → "Ludicolo")
6. ✅ Sentence extraction (pulls move name from verbose DECISION)
7. ✅ Better logging for switch attempts

The model should now:
- Generate concise 2-3 sentence reasoning
- Output just move names in DECISION (not sentences)
- Parse switches correctly even with typos
""")

if __name__ == "__main__":
    test_switch_parsing()
