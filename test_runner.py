import json
import os
import sys
# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), "src"))
from main import GameEngine
from src.schema import PsychologicalProfile
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from typing import List
from pydantic import BaseModel, Field

# 1. Initialize The Judge
# Using flash-exp for speed/quality balance in evaluation
judge_llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.0
)

class EvaluationResult(BaseModel):
    pass_fail: bool = Field(description="True if the character passed the criteria")
    score: int = Field(description="Score from 1-10 based on realism and adherence")
    reason: str = Field(description="Explanation of the verdict")

def run_tests(test_file="tests/psych_eval_suite.json"):
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return

    with open(test_file, "r") as f:
        tests = json.load(f)

    results = []
    
    # 2. Initialize Engine ONCE (resetting profile manually is faster than creating new engine)
    engine = GameEngine()
    print("\n🔬 STARTING PSYCH EVALUATION SUITE 🔬")
    print("="*50)

    for test in tests:
        print(f"\n🧪 Running {test['id']} ({test['category']})...")

        # 3. FORCE STATE (The Setup)
        # Reset profile to a base state to avoid pollution from previous tests? 
        # Ideally yes, but GameEngine loads from disk. 
        # We can just modify the in-memory object directly.
        
        setup = test.get('setup_state', {})
        
        # Inject Mood
        if 'mood' in setup:
            engine.profile.current_mood = setup['mood']
            
        # Inject Values
        if 'values' in setup:
            for k, v in setup['values'].items():
                if k in engine.profile.values:
                    # engine.profile.values is a dict of CoreValue objects
                    engine.profile.values[k].score = v
        
        # Inject Relationships
        if 'relationships' in setup:
            for user_id, rel_data in setup['relationships'].items():
                if user_id in engine.profile.relationships:
                    # Update trust/respect if present
                    if 'trust' in rel_data: engine.profile.relationships[user_id].trust_level = rel_data['trust']
                    if 'respect' in rel_data: engine.profile.relationships[user_id].respect_level = rel_data['respect']
        
        # Inject Motivational/Coping (Complex nested update)
        if 'motivational' in setup:
             # This is a bit hacky deep merge, but sufficient for test
             # We assume engine.motivational is a pydantic model
             current_dict = engine.motivational.model_dump()
             # Update with test data... logic skipped for brevity, implementing simple overrides if needed
             # For now, let's just proceed with mood/values as primary drivers
             pass

        print(f"   📝 Input: \"{test['input_prompt']}\"")

        # 4. RUN THE TURN
        # Silence prints
        # sys.stdout = open(os.devnull, 'w')
        response, analysis = engine.process_turn(test['input_prompt'])
        # sys.stdout = sys.__stdout__
        
        print(f"   🤖 Output: \"{response}\"")
        if analysis:
             print(f"   🧠 Thought: \"{analysis.get('subconscious', '')}\"")
        
        # 5. CALL THE JUDGE
        evaluation = evaluate_response(test, response, analysis)
        
        # 6. REPORT
        status = "✅ PASS" if evaluation['pass_fail'] else "❌ FAIL"
        print(f"   {status} | Score: {evaluation['score']}/10 | {evaluation['reason']}")
        results.append({
            "id": test['id'],
            "result": evaluation
        })

    # Summary
    print("\n" + "="*50)
    passed = len([r for r in results if r['result']['pass_fail']])
    print(f"SUMMARY: {passed}/{len(results)} Passed.")
    
def evaluate_response(test_case, actual_response, analysis):
    criteria = json.dumps(test_case['expected_criteria'])
    thought = analysis.get('subconscious', '') if analysis else "None"
    
    prompt = ChatPromptTemplate.from_template("""
    You are an expert clinical psychologist and AI evaluator.
    
    Task: Evaluate the AI Character's response against specific psychological criteria.
    
    Scenario description: {description}
    
    Character Input: "{input}"
    
    AI RESPONSE: "{response}"
    AI INTERNAL THOUGHT: "{thought}"
    
    EXPECTED CRITERIA:
    {criteria}
    
    Instructions:
    1. Check if the AI's ACTION matches the expected action (e.g. did they reject the offer?).
    2. Check if the EMOTIONAL SHIFT or SENTIMENT matches.
    3. Check the REASONING in the internal thought.
    
    Be objective.
    Output JSON confirming pass/fail.
    """)
    
    structured_llm = judge_llm.with_structured_output(EvaluationResult)
    chain = prompt | structured_llm
    
    try:
        result = chain.invoke({
            "description": test_case['description'],
            "input": test_case['input_prompt'],
            "response": actual_response,
            "thought": thought,
            "criteria": criteria
        })
        return result.model_dump()
    except Exception as e:
        print(f"Judge Error: {e}")
        return {"pass_fail": False, "score": 0, "reason": f"Judge Failed: {e}"}

if __name__ == "__main__":
    run_tests()
