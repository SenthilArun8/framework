import os
from langchain_google_genai import ChatGoogleGenerativeAI

# Initialize Singleton LLM
# Use gemini-2.0-flash-exp or gemini-1.5-pro (gemini-1.5-flash is deprecated)
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# Lazy singleton
_llm_instance = None

def get_llm():
    global _llm_instance
    
    if _llm_instance is None:
        # Load environment variables
        load_dotenv()
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            # Fallback for testing/debugging if no key present
            print("⚠️ WARNING: GOOGLE_API_KEY not found. Using placeholder for validation.")
            # For strict Pydantic validation, we might need a dummy key if just testing imports
            # But normally we want it to fail or work.
            # Let's try to load from a known location or just proceed.
            # If this is for CI/CD or local test without key, we might need to mock.
        
        _llm_instance = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp", # Updated model name
            google_api_key=api_key,
            temperature=0.2
        )
            
    return _llm_instance

# Backward compatibility alias (deprecated usage)
# Accessing this will trigger initialization if not careful, 
# but python modules assume top-level execution.
# Better to force users to use get_llm().
# However, to avoid breaking existing `from src.llm_client import llm` imports immediately:
# We can use a property or just leave it, BUT the import itself was crashing.
# So we MUST remove the top-level instantiation.
# Usage `from src.llm_client import llm` will now fail with ImportError unless we define `llm`
# But if we define `llm = get_llm()`, it executes immediately.
# So we will NOT define `llm` at top level. Users must use `get_llm()`.
# I will fix the usage in action_generator.py which already uses `get_llm`.
# But wait, action_generator.py imported `get_llm`? 
# The trace said `from src.llm_client import get_llm` failed?
# No, `action_generator.py` line 12: `from src.llm_client import get_llm`.
# But `llm_client.py` didn't have `get_llm` before! It only had `llm`.
# The USER's edited `action_generator.py` (id: 1246) added `from src.llm_client import get_llm`.
# So the user already expects `get_llm` to exist!

