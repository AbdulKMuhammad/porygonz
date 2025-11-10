from fp.battle import Battle
from fp.search.main import find_best_move
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

class LLMPokemonPlayer:
    def __init__(self, model_name=None, hf_token=None, verbose=True):
        """
        Initialize with Qwen 2.5-1.5B Instruct model
        
        Args:
            model_name: Model path or HuggingFace ID
                       Default: ~/.llama/hf_models/Qwen2.5-1.5B-Instruct
                       Alternatives:
                       - "Qwen/Qwen2.5-0.5B-Instruct" (smaller, faster)
                       
            hf_token: HuggingFace token for gated models (optional)
            verbose: If True, logs LLM reasoning for each decision (default: True)
        """
        self.verbose = verbose
        # Use local Qwen model by default
        from pathlib import Path
        if model_name is None:
            local_model = Path.home() / ".llama/hf_models/Qwen2.5-1.5B-Instruct"
            if local_model.exists():
                model_name = str(local_model)
                print(f"Using local Qwen 2.5-1.5B Instruct model")
            else:
                print(f"Local model not found at: {local_model}")
                print("    Run: python download_instruction_model.py")
                print("    Falling back to HuggingFace download...")
                model_name = "Qwen/Qwen2.5-1.5B-Instruct"
        
        print(f"Loading model: {model_name}")
        
        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                token=hf_token
            )
            
            # Load model with optimized settings
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.bfloat16,  # Use bfloat16 for efficiency
                device_map="auto",
                low_cpu_mem_usage=True,
                token=hf_token
            )
            
            # Set pad token if not set
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            print(f"✓ Model loaded successfully on {self.model.device}")
            
        except Exception as e:
            print(f"\n✗ ERROR loading model: {e}")
            if "gated repo" in str(e) or "401" in str(e):
                print("\n TIP: You're trying to load a gated HuggingFace model")
                print("   Download an ungated model with:")
                print("   python download_instruction_model.py")
            else:
                print("\n TIP: Make sure you have downloaded a model:")
                print("   python download_instruction_model.py")
            raise
        
    def battle_state_to_prompt(self, battle: Battle) -> str:
        """Convert Foul Play battle state to LLM prompt with comprehensive battle info"""

        my_active = battle.user.active
        opp_active = battle.opponent.active

        # Format moves with detailed info
        moves_list = [f"{m.name} (Power: {m.base_power}, Type: {m.type})" for m in my_active.moves if not m.disabled]
        switches_list = [p.name for p in battle.user.reserve if not p.fainted]

        prompt = f"""You are an expert Pokemon battler in Gen 9 OU format.

Current Battle State:
---
YOUR ACTIVE POKEMON:
- {my_active.name} ({', '.join(my_active.types)})
- HP: {my_active.hp}/{my_active.max_hp} ({my_active.hp_percent}%)
- Stats: Atk {my_active.attack}, Def {my_active.defense}, SpA {my_active.special_attack}, SpD {my_active.special_defense}, Spe {my_active.speed}
- Status: {my_active.status or "Healthy"}
- Boosts: {my_active.boosts}

OPPONENT'S ACTIVE POKEMON:
- {opp_active.name} ({', '.join(opp_active.types)})
- HP: {opp_active.hp_percent}%
- Status: {opp_active.status or "Healthy"}
- Boosts: {opp_active.boosts}

YOUR TEAM:
{self._format_team(battle.user.reserve)}

OPPONENT'S REVEALED POKEMON:
{self._format_team(battle.opponent.reserve)}

AVAILABLE ACTIONS:
Moves: {moves_list}
Switches: {switches_list}

FIELD CONDITIONS:
- Weather: {battle.weather or "None"}
- Terrain: {battle.field or "None"}
- Hazards (Your side): {battle.user.side_conditions}
- Hazards (Opp side): {battle.opponent.side_conditions}

Analyze the situation and choose the best move.

Format your response EXACTLY as:
REASONING: [2-3 sentences max explaining your strategy]
DECISION: [exact move name only, e.g., 'thunderbolt' or 'switch charizard']

IMPORTANT: 
- Keep reasoning to 2-3 sentences maximum
- DECISION must be ONLY the move name or 'switch pokemonname' (no extra words)
- You MUST complete the DECISION line
"""
        return prompt
    
    def _format_team(self, pokemon_list):
        """Format Pokemon team for display"""
        available = [f"- {p.name}: {p.hp_percent}% HP, {p.status or 'Healthy'}" 
                     for p in pokemon_list if not p.fainted]
        return "\n".join(available) if available else "- (None available)"
    
    def get_llm_decision(self, battle: Battle):
        """Get move decision from LLM using chat template"""
        import logging
        logger = logging.getLogger(__name__)
        
        prompt = self.battle_state_to_prompt(battle)
        
        # Format for chat template with comprehensive battle analysis
        messages = [
            {"role": "system", "content": "You are an expert Pokemon battle AI. Be concise. Format:\nREASONING: [2-3 sentences max]\nDECISION: [movename only]\n\nExamples:\nDECISION: thunderbolt\nDECISION: switch charizard\n\nDO NOT write sentences in DECISION, just the move/switch."},
            {"role": "user", "content": prompt}
        ]

        # Apply chat template
        formatted_prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        inputs = self.tokenizer(formatted_prompt, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=250,        # Limited for concise reasoning (2-3 sentences) + DECISION
                temperature=0.2,           # Lower temp for more focused output
                top_p=0.9,                 # Standard sampling
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
                repetition_penalty=1.15,   # Prevent loops
                no_repeat_ngram_size=3,    # Prevent repeating phrases
            )
        
        # Decode only the generated tokens (skip the prompt)
        full_response = self.tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:],
            skip_special_tokens=True
        )

        # Log raw output for debugging
        logger.debug(f"Raw LLM output: {repr(full_response)}")

        # Parse and display reasoning
        decision = self._parse_and_display_reasoning(full_response, battle)

        # If parsing failed, use MCTS fallback
        if decision is None:
            logger.warning("⚠️  LLM parsing failed, using MCTS fallback")
            decision = self._get_foulplay_decision(battle)
            logger.info(f"🎮 MCTS Fallback Decision: {decision}")

        return decision
    
    def _parse_and_display_reasoning(self, llm_output: str, battle: Battle):
        """Parse LLM output, display formatted reasoning, and return decision"""
        import logging
        import re
        logger = logging.getLogger(__name__)

        # Clean the output first - remove special tokens and weird characters
        llm_output = llm_output.strip()
        llm_output = re.sub(r'[^\x20-\x7E\n]', '', llm_output)  # Keep only printable ASCII

        # Validate output isn't complete gibberish
        if len(llm_output) < 10 or not any(c.isalpha() for c in llm_output):
            logger.warning(f"⚠️  LLM produced invalid output: {repr(llm_output[:100])}")
            if self.verbose:
                self._display_reasoning(battle, "[Model output was invalid]", "[Using fallback]")
            return None  # Trigger fallback

        # Extract reasoning and decision sections (handle misspellings)
        reasoning_match = re.search(r'REASON(?:ING|NING)?:\s*(.+?)(?=DECISION:|$)', llm_output, re.IGNORECASE | re.DOTALL)
        decision_match = re.search(r'DECISION:\s*(.+?)(?:\n|$)', llm_output, re.IGNORECASE)

        reasoning_text = reasoning_match.group(1).strip() if reasoning_match else "[No reasoning provided]"
        
        # If no DECISION found, try to extract last meaningful line
        if not decision_match:
            logger.debug("No DECISION: found, trying to extract last line")
            lines = [l.strip() for l in llm_output.split('\n') if l.strip()]
            if lines:
                # Try to find a line that looks like a move/switch
                for line in reversed(lines[-3:]):  # Check last 3 lines
                    if len(line) < 50 and any(c.isalpha() for c in line):
                        decision_text = line
                        break
                else:
                    decision_text = lines[-1] if lines else llm_output.strip()
            else:
                decision_text = llm_output.strip()
        else:
            decision_text = decision_match.group(1).strip()
        
        # Clean up decision text - remove common prefixes and extra words
        decision_text = re.sub(r'^(SWITCH:|MOVE:)\s*', '', decision_text, flags=re.IGNORECASE)
        # If decision is a full sentence, try to extract just the move name (first word that looks like a move)
        if len(decision_text.split()) > 3:
            logger.debug(f"Decision looks like a sentence: {decision_text[:50]}")
            # Try to find a move name in the available moves
            my_active = battle.user.active
            available_moves = [m.name.lower() for m in my_active.moves if not m.disabled]
            for word in decision_text.split():
                if word.lower() in available_moves:
                    decision_text = word
                    logger.debug(f"Extracted move from sentence: {decision_text}")
                    break

        # If decision is still gibberish, log and fallback
        if len(decision_text) > 100:
            logger.warning(f"⚠️  Decision text too long: {repr(decision_text[:50])}")
            if self.verbose:
                self._display_reasoning(battle, reasoning_text, "[Decision too long - using fallback]")
            return None

        # Display formatted reasoning output
        if self.verbose:
            self._display_reasoning(battle, reasoning_text, decision_text)

        # Parse decision to game action
        return self._parse_decision_text(decision_text, battle, logger)

    def _display_reasoning(self, battle: Battle, reasoning: str, decision_raw: str):
        """Display formatted LLM reasoning with battle context"""
        import logging
        logger = logging.getLogger(__name__)
        
        my_active = battle.user.active
        opp_active = battle.opponent.active
        
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║" + " 🤖 LLM BATTLE ANALYSIS".ljust(78) + "║")
        logger.info("╠" + "═" * 78 + "╣")
        logger.info("║" + f" Turn {battle.turn} │ {my_active.name} ({my_active.hp_percent}% HP) vs {opp_active.name} ({opp_active.hp_percent}% HP)".ljust(78) + "║")
        logger.info("╠" + "═" * 78 + "╣")
        logger.info("║" + " 💭 REASONING:".ljust(78) + "║")
        logger.info("║" + "".ljust(78) + "║")
        
        # Word wrap reasoning text to fit within box
        wrapped_reasoning = self._wrap_text(reasoning, 74)
        for line in wrapped_reasoning:
            logger.info("║  " + line.ljust(76) + "║")
        
        logger.info("║" + "".ljust(78) + "║")
        logger.info("╠" + "═" * 78 + "╣")
        logger.info("║" + " 🎯 DECISION:".ljust(78) + "║")
        logger.info("║" + "".ljust(78) + "║")
        logger.info("║  " + decision_raw.ljust(76) + "║")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
    
    def _wrap_text(self, text: str, width: int):
        """Wrap text to specified width, preserving words"""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + len(current_line) <= width:
                current_line.append(word)
                current_length += len(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines if lines else [text[:width]]
    
    def _parse_decision_text(self, decision_text: str, battle: Battle, logger):
        """Convert decision text to Foul Play action format"""
        import re
        
        # Clean up the decision text
        decision_text = decision_text.lower().strip()
        
        # Check if it's a switch
        if 'switch' in decision_text:
            switch_match = re.search(r'switch\s+([\w-]+)', decision_text, re.IGNORECASE)
            if switch_match:
                target_pokemon = switch_match.group(1).strip()
                logger.debug(f"Trying to switch to: {target_pokemon}")
                # Find matching Pokemon in reserve (fuzzy match)
                best_match = None
                best_score = 0
                
                for pkmn in battle.user.reserve:
                    if not pkmn.fainted:
                        # Normalize both names
                        pkmn_name_lower = pkmn.name.lower().replace('-', '').replace(' ', '')
                        target_lower = target_pokemon.lower().replace('-', '').replace(' ', '')
                        
                        # Check for substring match
                        if target_lower in pkmn_name_lower or pkmn_name_lower in target_lower:
                            decision = f"switch {pkmn.name}"
                            if self.verbose:
                                logger.info(f"✅ Parsed switch: {decision}")
                            return decision
                        
                        # Calculate similarity score (count matching characters)
                        matches = sum(1 for a, b in zip(target_lower, pkmn_name_lower) if a == b)
                        score = matches / max(len(target_lower), len(pkmn_name_lower))
                        
                        if score > best_score:
                            best_score = score
                            best_match = pkmn
                
                # If we have a decent match (>70% similar), use it
                if best_match and best_score > 0.7:
                    decision = f"switch {best_match.name}"
                    if self.verbose:
                        logger.info(f"✅ Parsed switch (fuzzy match {best_score:.0%}): {decision}")
                    return decision
                
                logger.warning(f"⚠️  Could not find Pokemon matching '{target_pokemon}' in reserve")
        
        # Otherwise, try to find a move
        my_active = battle.user.active
        available_moves = [m.name for m in my_active.moves if not m.disabled]
        
        # Try exact match first
        for move in available_moves:
            if move.lower() in decision_text or decision_text in move.lower():
                if self.verbose:
                    logger.info(f"✅ Parsed: {move}")
                return move
        
        # If no match found, return first available move as fallback
        if available_moves:
            decision = available_moves[0]
            if self.verbose:
                logger.warning(f"⚠️  Parse failed, using fallback: {decision}")
            return decision
        
        # Last resort: return None to trigger MCTS fallback
        logger.error(f"❌ Could not parse decision: {decision_text}")
        return None
    
    def get_hybrid_decision(self, battle: Battle, use_llm_probability=0.8):
        """
        Hybrid approach: Use LLM most of the time, 
        fall back to Foul Play's engine for safety
        """
        import random
        
        if random.random() < use_llm_probability:
            try:
                return self.get_llm_decision(battle)
            except Exception as e:
                print(f"LLM failed: {e}, using Foul Play fallback")
                return self._get_foulplay_decision(battle)
        else:
            return self._get_foulplay_decision(battle)
    
    def _get_foulplay_decision(self, battle: Battle):
        """Use Foul Play's MCTS engine"""
        # Foul Play's battle state → best move using Monte Carlo Tree Search
        best_move = find_best_move(battle)
        return best_move