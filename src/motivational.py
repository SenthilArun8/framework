from datetime import datetime
from src.schema import (
    MotivationalState, CoreNeeds, EmotionalState, CognitiveState, 
    AttachmentSystem, CopingStyles, InternalConflict
)
import statistics
import random
import math
import os
from functools import lru_cache
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

@lru_cache(maxsize=1)
def get_intent_llm():
    """Returns a cached instance of the LLM to avoid re-init overhead."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.0
    )

# Default Initialization if missing
DEFAULT_MOTIVATIONAL = MotivationalState(
    # Core Needs: High need for Competence (Imposter Syndrome)
    needs=CoreNeeds(belonging=0.3, autonomy=0.6, security=0.4, competence=0.2, novelty=0.7),
    
    # Emotional State: High Stress, Low Arousal (Burnout)
    emotional_state=EmotionalState(stress=0.8, arousal=0.3, shame=0.2, fear=0.4, longing=0.1),
    
    # Cognitive State: Brain Fog
    cognitive_state=CognitiveState(cognitive_load=0.6, dissociation=0.3, focus_fragility=0.8),
    
    # Attachment: Avoidant (He isolates when stressed)
    attachment=AttachmentSystem(style="avoidant", activation=0.7, protest_tendency=0.2, withdrawal_tendency=0.8),
    
    # Coping: Intellectualization (He uses big words to hide feelings)
    coping=CopingStyles(avoidance=0.5, intellectualization=0.9, over_explaining=0.8, humor_deflection=0.4, aggression=0.1, appeasement=0.2),
    
    # Internal Conflict
    conflicts=[
        InternalConflict(name="Truth vs Graduation", pressure=0.75, polarity=("Reveal Data", "Please Advisor"))
    ],
    fatigue=0.8, # Very tired
    active_strategy={"intellectualization": 1.0}
)

def motivational_update_node(state):
    """
    Subconscious engine that runs BEFORE the thought process.
    Updates needs, calculates pressures, and selects an emergent behavior strategy.
    """
    # 1. Hydrate or Initialize State
    motivational = state.get("motivational")
    profile_data = state.get("profile") # Needed for Traits (Phase 11)
    
    # Phase 11: Get Traits
    from src.schema import PersonalityTraits, PsychologicalProfile
    if profile_data:
        # Check if profile_data is dict or object
        if isinstance(profile_data, dict):
            # Safe access for traits dict or default
            t_data = profile_data.get("traits", {})
            traits = PersonalityTraits(**t_data)
        else:
            traits = profile_data.traits
    else:
        traits = PersonalityTraits() # Default

    if not motivational or isinstance(motivational, dict):
        if not motivational:
            current_state = DEFAULT_MOTIVATIONAL.model_copy(deep=True)
        else:
            current_state = MotivationalState(**motivational)
    else:
        current_state = motivational

    # 2. Decay / Time-based updates
    # Phase 11: Mood Momentum Logic
    current_state.time_since_last_shift += 1
    resistance = current_state.mood_momentum
    
    # Trait-Modulated Decay (Phase 13)
    # Volatility accelerates decay of needs (harder to stay satisfied) and stress? 
    # Or implies faster return to baseline? 
    # Let's say high volatility means faster changes. 
    decay_mult = traits.emotional_volatility
    if decay_mult < 0.2: decay_mult = 0.2 # Clamp minimum decay
    
    # Needs naturally drift
    current_state.needs.security -= (0.01 * decay_mult)
    current_state.needs.novelty -= (0.02 * decay_mult)
    current_state.fatigue += 0.05 

    # 3. Reactive Updates (LLM-based Intent Analysis - Phase 12)
    user_input = state['messages'][-1].content if state['messages'] else ""

    if user_input:
        # Non-linear scaling for cognitive load (Phase 13)
        # load_increase = base * (1 + log(length)) to dampen impact of very long texts vs short texts
        # But user asked for "Nonlinear scaling" implying long texts push load FASTER or More?
        # "Longer conversations may push cognitive_load quickly to max. Nonlinear scaling may be more realistic."
        # If linear is too fast, maybe they mean sub-linear? Or strict exponential?
        # Actually "push quickly to max" implies key is getting to max too fast. So we want sub-linear or sigmoid.
        # Let's use a logistic-like curve or just sqrt/log to diminish return on massive text.
        
        input_len = len(user_input)
        if input_len > 0:
            # Base impact per char is small, but ramps up. 
            # Let's use SQRT to dampen the linear effect of massive pastes.
            # Old: linear based on length > 200.
            # New: Always some load, but non-linear.
            raw_impact = math.sqrt(input_len) / 50.0 # 100 chars -> 0.2, 400 chars -> 0.4
            load_delta = raw_impact * traits.focus_fragility
            current_state.cognitive_state.cognitive_load += load_delta

        try:
            # Use cached LLM
            llm_fast = get_intent_llm()

            intent_prompt = ChatPromptTemplate.from_template("""
            Analyze the INTENT of this message to a survivor character.
            Message: "{input}"
            
            Classify as exactly one of:
            - SUPPORT (Comfort, agreeing, help, praise)
            - CRITICISM (Insult, disagreement, judgment, harsh truth)
            - THREAT (Violence, danger, intimidation)
            - INQUIRY (Asking questions, curiosity)
            - NEUTRAL (Statements, facts, small talk)
            
            Output ONLY the category.
            """)
            
            chain = intent_prompt | llm_fast | StrOutputParser()
            intent = chain.invoke({"input": user_input}).strip().upper()
            
            # Apply Changes based on Intent
            volatility = traits.emotional_volatility
            
            if "SUPPORT" in intent:
                current_state.needs.belonging += (0.1 * volatility)
                current_state.emotional_state.shame -= (0.1 * volatility)
                current_state.attachment.activation -= (0.1 * volatility)
                current_state.emotional_state.stress -= 0.05
            elif "CRITICISM" in intent:
                current_state.needs.competence -= (0.1 * volatility)
                current_state.emotional_state.stress += (0.1 * volatility)
                current_state.emotional_state.shame += (0.05 * volatility)
            elif "THREAT" in intent:
                current_state.needs.security -= (0.2 * volatility)
                current_state.emotional_state.fear += (0.2 * volatility)
                current_state.attachment.activation += (0.1 * volatility)
            elif "INQUIRY" in intent:
                 current_state.emotional_state.arousal += 0.05
            
        except Exception as e:
            print(f"Intent Analysis Failed: {e}. Falling back to heuristics.")
            # Fallback (Expanded)
            if "?" in user_input: 
                current_state.needs.competence -= 0.01
            if "!" in user_input:
                current_state.emotional_state.arousal += 0.02

    # Clamp values 0-1
    for field in current_state.needs.model_fields:
        v = getattr(current_state.needs, field)
        setattr(current_state.needs, field, max(0.0, min(1.0, v)))
    
    current_state.cognitive_state.cognitive_load = max(0.0, min(1.0, current_state.cognitive_state.cognitive_load))
    
    # 4. Calculate Pressures to Determine Strategy Blend
    # Stress Pressure
    stress_pressure = current_state.emotional_state.stress * (1 + current_state.cognitive_state.cognitive_load)
    
    # Attachment Pressure
    if current_state.attachment.style == "anxious":
        attn_pressure = current_state.attachment.activation * 1.3
    elif current_state.attachment.style == "avoidant":
        attn_pressure = (1 - current_state.attachment.activation) * 1.3
    else:
        attn_pressure = current_state.attachment.activation

    # Conflict Pressure (Weighted)
    if current_state.conflicts:
        # Use importance if available (defaults to 1.0)
        # Weighted Average
        total_p = 0
        total_w = 0
        for c in current_state.conflicts:
            w = getattr(c, 'importance', 1.0)
            total_p += c.pressure * w
            total_w += w
            
        conflict_pressure = total_p / total_w if total_w > 0 else 0.0
    else:
        conflict_pressure = 0.0

    # Need Deprivation
    avg_need = statistics.mean([
        current_state.needs.belonging, current_state.needs.autonomy, 
        current_state.needs.security, current_state.needs.competence, 
        current_state.needs.novelty
    ])
    need_pressure = 1.0 - avg_need

    # 5. Calculate Blended Strategy (Phase 11)
    # We assign a score effectively to each "Archetype" based on pressures
    
    blended_map = {}
    
    # Stress-driven strategies
    blended_map["defensive_curt"] = stress_pressure * 0.6
    blended_map["fragmented_thoughts"] = (stress_pressure * current_state.cognitive_state.cognitive_load)
    
    # Attachment-driven
    if current_state.attachment.style == "anxious":
        blended_map["over_explaining_clingy"] = attn_pressure
    else:
        blended_map["shutdown_withdrawal"] = attn_pressure
        
    # Dissociation
    blended_map["spaced_out_drifting"] = current_state.cognitive_state.dissociation
    
    # Conflict
    blended_map["mixed_signals_hesitant"] = conflict_pressure
    
    # Deprivation (Specific needs)
    if current_state.needs.autonomy < 0.4: blended_map["argumentative_assertive"] = (1 - current_state.needs.autonomy)
    if current_state.needs.belonging < 0.4: blended_map["vulnerable_seeking"] = (1 - current_state.needs.belonging)
    if current_state.needs.security < 0.4: blended_map["hyper_vigilant"] = (1 - current_state.needs.security)
    
    # Neutral Baseline (always present to some degree)
    blended_map["neutral"] = 0.2
    
    # Normalize weights so they sum to ~1.0 or are relative
    total = sum(blended_map.values())
    if total > 0:
        for k in blended_map:
            blended_map[k] = round(blended_map[k] / total, 2)
            
    # Remove insignificant weights (< 0.1) to clean up context
    active_strategies = {}
    total_blended = 0
    
    for k, v in blended_map.items():
        # Add stochastic jitter (Phase 13)
        # Random noise +/- 0.05
        jitter = random.uniform(-0.05, 0.05)
        final_v = max(0.0, v + jitter)
        
        if final_v >= 0.1:
            active_strategies[k] = final_v
            total_blended += final_v
            
    # Re-normalize after jitter
    if total_blended > 0:
        for k in active_strategies:
            active_strategies[k] = round(active_strategies[k] / total_blended, 2)
    
    # Fallback
    if not active_strategies:
        active_strategies = {"neutral": 1.0}
        
    current_state.active_strategy = active_strategies
    
    return {"motivational": current_state.model_dump()}
