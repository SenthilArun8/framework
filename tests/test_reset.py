
import unittest
import sys
import os
import shutil

# Ensure src is in path
current_dir = os.getcwd()
sys.path.append(current_dir)
if current_dir not in sys.path:
    sys.path.append(current_dir)

from src.memory import MemoryStore, seed_memories, MemoryFragment

from unittest.mock import MagicMock
import src.memory

from unittest.mock import patch, MagicMock

class FakeEmbeddings:
    def embed_documents(self, texts):
        return [[0.1] * 768 for _ in texts]
    def embed_query(self, text):
        return [0.1] * 768

class TestReset(unittest.TestCase):
    def setUp(self):
        # Patch the class in src.memory
        self.patcher = patch('src.memory.GoogleGenerativeAIEmbeddings', side_effect=lambda **kwargs: FakeEmbeddings())
        self.MockEmbeddings = self.patcher.start()
        
        # Use a temporary directory
        self.test_dir = "tests/temp_chroma_reset"
        self.store = MemoryStore(persist_directory=self.test_dir)
        
    def tearDown(self):
        self.patcher.stop()
        # Clean up
        self.store = None
        if os.path.exists(self.test_dir):
            try:
                shutil.rmtree(self.test_dir)
            except Exception:
                pass

    def test_clear_and_seed(self):
        # 1. Add some data
        print("\n[Test] Adding initial memories...")
        seed_memories(self.store)
        initial_ids = self.store.vector_store.get()['ids']
        self.assertGreater(len(initial_ids), 0, "Should have seeded memories")
        print(f"[Test] Initial count: {len(initial_ids)}")

        # 2. Clear
        print("[Test] Clearing memories...")
        self.store.clear_memories()
        empty_ids = self.store.vector_store.get()['ids']
        self.assertEqual(len(empty_ids), 0, "Store should be empty after clear")
        print("[Test] Store cleared successfully.")

        # 3. Re-seed
        print("[Test] Re-seeding...")
        seed_memories(self.store)
        reseeded_ids = self.store.vector_store.get()['ids']
        self.assertGreater(len(reseeded_ids), 0, "Should have re-seeded memories")
        print(f"[Test] Reseeded count: {len(reseeded_ids)}")

if __name__ == '__main__':
    unittest.main()
