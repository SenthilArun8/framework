import os
import sys
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load env vars from root
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, ".env"))

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "")
PASSWORD = os.getenv("NEO4J_PASSWORD", "")

def seed_graph():
    print(f"Connecting to {URI}...")
    
    # Handle Auth=None for local no-auth DB
    auth_token = (USER, PASSWORD) if USER and PASSWORD else None
    
    driver = GraphDatabase.driver(
        URI, 
        auth=auth_token,
        connection_timeout=5.0
    )
    
    cypher_seed = """
    // Entities
    CREATE (leo:Character {name: "Leo", role: "Grad Student"})
    CREATE (council:Faction {name: "City Council", ideology: "Bureaucracy", threat: 6})
    CREATE (prof:Character {name: "Professor Halloway", role: "Advisor"})
    CREATE (project:Concept {name: "The Waterfront Redevelopment"})
    CREATE (tech:Concept {name: "LiDAR Scanning"})

    // Relationships (The Logic)
    CREATE (leo)-[:RELIES_ON {sentiment: "Obsessive"}]->(tech)
    CREATE (prof)-[:CRITICIZES {reason: "Too impersonal"}]->(tech)

    // The Plot
    CREATE (council)-[:APPROVED]->(project)
    CREATE (tech)-[:REVEALS_FLAWS_IN]->(project)
    CREATE (leo)-[:KNOWS_TRUTH_ABOUT]->(project)

    // Leo is scared of Halloway but respects him
    CREATE (leo)-[:FEARS {intensity: 0.8}]->(prof)
    CREATE (leo)-[:RESPECTS {intensity: 0.6}]->(prof)
    """

    try:
        with driver.session() as session:
            # 1. Clear DB
            print("Cleaning Database...")
            session.run("MATCH (n) DETACH DELETE n")
            
            # 2. Seed Data
            print("Seeding new data...")
            session.run(cypher_seed)
            
            # 3. Verify
            result = session.run("MATCH (n) RETURN count(n) as count")
            count = result.single()["count"]
            print(f"✅ Success! Graph now contains {count} nodes.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    seed_graph()
