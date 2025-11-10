# PorygonZ: LLM-Enhanced Pokemon Battle Bot ![PorygonZ](https://www.smogon.com/dex/media/sprites/xy/porygon-z.gif)

## Overview

**PorygonZ** is a fork of [Foul Play](https://github.com/pmariglia/foul-play), an advanced Pokemon battle bot that uses Monte Carlo Tree Search (MCTS) to play competitive battles on [Pokemon Showdown](https://pokemonshowdown.com/). This fork extends the original project by integrating a local Large Language Model (LLM) for strategic decision-making, creating a hybrid AI system that combines traditional search algorithms with modern language model reasoning.

## What's New in PorygonZ

### LLM Integration

PorygonZ incorporates **Qwen 2.5-1.5B Instruct**, a lightweight but capable instruction-tuned language model, to make battle decisions. The LLM analyzes the current battle state and generates strategic moves based on:

- Active Pokemon matchups and type advantages
- HP percentages and status conditions
- Available moves and their effects
- Team composition and reserve Pokemon
- Field conditions (weather, terrain, hazards)
- Opponent's known moves and abilities

### Hybrid Decision System

The bot uses a **probabilistic hybrid approach**:

1. **LLM Decision Path** (configurable probability)
   - Model analyzes comprehensive battle state
   - Generates reasoning and decision in structured format
   - Parses and validates the decision
   - Falls back to MCTS if parsing fails

2. **MCTS Fallback** (original Foul Play)
   - Proven search-based decision making
   - Always available as safety net
   - Used when LLM is disabled or fails

### Key Features

- **Local Model Execution**: Runs Qwen 2.5-1.5B locally (no API calls)
- **Apple Silicon Optimized**: Uses MPS (Metal Performance Shaders) for GPU acceleration
- **Configurable Probability**: Adjust LLM usage from 0% to 100%
- **Structured Output**: LLM generates reasoning + decision in parsable format
- **Robust Parsing**: Handles incomplete outputs, typos, and sentence-form decisions
- **Verbose Logging**: Beautiful formatted output showing LLM reasoning
- **Automatic Fallback**: Seamlessly switches to MCTS on errors

## Usage

### Basic LLM Battle

```bash
python run.py \
  --websocket-uri wss://sim3.psim.us/showdown/websocket \
  --ps-username YOUR_USERNAME \
  --ps-password YOUR_PASSWORD \
  --bot-mode search_ladder \
  --pokemon-format gen9randombattle \
  --use-llm \
  --llm-probability 0.8
```

### Accept Challenges with Custom Team

```bash
python run.py \
  --websocket-uri wss://sim3.psim.us/showdown/websocket \
  --ps-username YOUR_USERNAME \
  --ps-password YOUR_PASSWORD \
  --bot-mode accept_challenge \
  --pokemon-format gen9ou \
  --team-name gen9/ou/your_team \
  --run-count 999 \
  --use-llm
```

### LLM Options

- **`--use-llm`**: Enable LLM decision making (default: disabled)
- **`--llm-probability <0.0-1.0>`**: Probability of using LLM vs MCTS (default: 0.8)

## Model Details

### Qwen 2.5-1.5B Instruct

- **Size**: 1.5 billion parameters (~3GB memory)
- **Type**: Instruction-tuned chat model
- **Context**: 32K tokens
- **Speed**: ~2-4 seconds per decision on Apple Silicon
- **Location**: `~/.llama/hf_models/Qwen2.5-1.5B-Instruct/`

### Prompt Engineering

The model receives a structured prompt including current battle state, team info, available actions, and field conditions. It generates a concise 2-3 sentence reasoning followed by a specific move decision.

## Roadmap

### Phase 1: Foundation (Complete)
- ✅ Local LLM integration with Qwen 2.5-1.5B
- ✅ Hybrid LLM + MCTS decision system
- ✅ Structured prompt engineering
- ✅ Robust output parsing
- ✅ Apple Silicon GPU acceleration

### Phase 2: Data Collection (In Progress)
- 🔄 Battle replay logging system
- 🔄 Decision tracking and analysis
- 🔄 Win/loss correlation with decision types
- 🔄 Dataset preparation for training

### Phase 3: Reinforcement Learning (Planned)
- 📋 Implement PPO (Proximal Policy Optimization) for battle decisions
- 📋 Reward shaping based on battle outcomes
- 📋 Self-play training loop
- 📋 Policy gradient optimization
- 📋 Value network for position evaluation
- 📋 Integration with existing MCTS for exploration

### Phase 4: Large-Scale Training (Planned)
- 📋 Scrape and process Pokemon Showdown replay database
- 📋 Parse battle logs into training format
- 📋 Filter high-ELO games for quality data
- 📋 Fine-tune Qwen on expert battle decisions
- 📋 Multi-format training (OU, UU, Random Battles)
- 📋 Continuous learning from new battles

### Phase 5: Online Learning (Future)
- 📋 Real-time learning during Showdown battles
- 📋 Opponent modeling and adaptation
- 📋 Meta-game awareness and strategy updates
- 📋 A/B testing of model improvements
- 📋 Automated model versioning and rollback
- 📋 Performance monitoring and analytics

## Technical Architecture

```
Battle State
     ↓
[LLM Decision Path]          [MCTS Path]
     ↓                            ↓
Qwen 2.5-1.5B Model    →    Poke-Engine Search
     ↓                            ↓
Parse & Validate      →      Best Move Found
     ↓                            ↓
     └──────→ [Move Execution] ←─┘
                ↓
         [Battle Outcome]
                ↓
         [Training Data]
```

### Core Components

- **`porygonz.py`**: LLM player class with model loading, prompting, and parsing
- **`fp/llm_battle.py`**: Integration layer between LLM and battle system
- **`fp/run_battle.py`**: Main battle loop with hybrid decision logic
- **`config.py`**: CLI configuration for LLM options

## Training Strategy

### Reinforcement Learning Approach

1. **Reward Signal**
   - Win/Loss: +1/-1 final reward
   - HP Differential: Intermediate rewards
   - Faint Count: Penalty for losing Pokemon
   - Turn Efficiency: Reward for faster wins

2. **Policy Optimization**
   - Use LLM as policy network
   - Fine-tune on battle trajectories
   - Optimize for expected cumulative reward
   - Balance exploration (MCTS) vs exploitation (LLM)

3. **Self-Play Training**
   - PorygonZ vs PorygonZ matches
   - Iterative improvement through competition
   - Curriculum learning (easy → hard formats)

### Dataset Construction

1. **Showdown Replay Mining**
   - Target: 100K+ high-ELO battles
   - Formats: Gen 9 OU, Random Battles, VGC
   - Parse: Turn-by-turn states and decisions
   - Filter: ELO > 1500, complete games only

2. **Data Format**
   ```json
   {
     "battle_id": "gen9ou-2024-12345",
     "turn": 5,
     "state": {
       "active": {...},
       "team": [...],
       "opponent": [...]
     },
     "decision": "switch garchomp",
     "outcome": "win",
     "elo": 1650
   }
   ```

3. **Training Pipeline**
   - Preprocess: Normalize state representations
   - Augment: Generate alternative valid moves
   - Balance: Equal win/loss samples
   - Split: 80% train, 10% val, 10% test

### Online Learning Integration

During live Showdown battles:

1. **Experience Buffer**: Store (state, action, reward) tuples
2. **Batch Updates**: Periodic fine-tuning on recent battles
3. **Opponent Adaptation**: Learn opponent patterns within match
4. **Meta-Learning**: Track format trends and adjust strategy

## Performance Targets

### Current Baseline
- **MCTS Only**: ~1200-1400 ELO (Gen 9 Random Battle)
- **LLM Hybrid**: ~1100-1300 ELO (experimental)

### Training Goals
- **Phase 3 (RL)**: 1400-1500 ELO
- **Phase 4 (Large-scale)**: 1500-1600 ELO
- **Phase 5 (Online)**: 1600+ ELO

## Installation

See [pmariglia/foul-play](https://github.com/pmariglia/foul-play) for Foul Play setup instructions.

### Additional Requirements for LLM

```bash
pip install transformers torch accelerate
```

## Contributing

This is an experimental research project. Contributions welcome in:

- Prompt engineering improvements
- Training data collection scripts
- RL algorithm implementations
- Performance benchmarking
- Documentation

## Credits

- **Original Foul Play**: [pmariglia/foul-play](https://github.com/pmariglia/foul-play)
- **Poke Engine**: [pmariglia/poke-engine](https://github.com/pmariglia/poke-engine)
- **Qwen Model**: [Qwen/Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)

## License

Same as original Foul Play project.
