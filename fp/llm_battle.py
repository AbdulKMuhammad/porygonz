"""
LLM-enhanced battle decision making
Integrates Llama 3.2-1B with Foul Play's MCTS engine
"""
import asyncio
import concurrent.futures
import logging
from copy import deepcopy
from typing import Optional

from fp.battle import Battle, LastUsedMove
from fp.search.main import find_best_move

logger = logging.getLogger(__name__)

# Global LLM player instance (lazy loaded)
_llm_player = None


def get_llm_player():
    """Get or create the global LLM player instance"""
    global _llm_player
    if _llm_player is None:
        logger.info("Initializing LLM Pokemon Player...")
        from porygonz import LLMPokemonPlayer
        _llm_player = LLMPokemonPlayer()
        logger.info("✓ LLM Player ready!")
    return _llm_player


async def async_pick_move_with_llm(battle: Battle, use_llm: bool = True, llm_probability: float = 0.8):
    """
    Pick the best move using LLM + MCTS hybrid approach
    
    Args:
        battle: Current battle state
        use_llm: Whether to use LLM (if False, uses pure MCTS)
        llm_probability: Probability of using LLM vs MCTS fallback
    
    Returns:
        Formatted decision message and request ID
    """
    from fp.run_battle import format_decision
    
    battle_copy = deepcopy(battle)
    if not battle_copy.team_preview:
        battle_copy.user.update_from_request_json(battle_copy.request_json)
    
    if use_llm:
        try:
            # Get LLM decision
            loop = asyncio.get_event_loop()
            llm_player = get_llm_player()
            
            # Run LLM inference in thread pool
            with concurrent.futures.ThreadPoolExecutor() as pool:
                best_move = await loop.run_in_executor(
                    pool,
                    lambda: llm_player.get_hybrid_decision(
                        battle_copy,
                        use_llm_probability=llm_probability
                    )
                )
            
            logger.info(f"🤖 LLM Decision: {best_move}")
            
            # If LLM returned None, fallback to MCTS
            if best_move is None:
                logger.warning("LLM returned None, falling back to MCTS")
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    best_move = await loop.run_in_executor(pool, find_best_move, battle_copy)
                logger.info(f"🎯 MCTS Fallback: {best_move}")
            
        except Exception as e:
            logger.warning(f"LLM failed: {e}, falling back to pure MCTS")
            # Fallback to MCTS
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                best_move = await loop.run_in_executor(pool, find_best_move, battle_copy)
            logger.info(f"🎯 MCTS Fallback: {best_move}")
    else:
        # Pure MCTS
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            best_move = await loop.run_in_executor(pool, find_best_move, battle_copy)
        logger.info(f"🎯 MCTS Decision: {best_move}")
    
    # Record the move
    battle.user.last_selected_move = LastUsedMove(
        battle.user.active.name,
        best_move.removesuffix("-tera").removesuffix("-mega"),
        battle.turn,
    )
    
    return format_decision(battle_copy, best_move)
