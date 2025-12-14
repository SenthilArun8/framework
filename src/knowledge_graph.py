from neo4j import GraphDatabase
import socket

class KnowledgeGraph:
    def __init__(self, uri, user, password):
        print(f"[DEBUG] KnowledgeGraph.__init__ called with uri={uri}")
        # Skip port check and just try to create driver with timeout
        # The driver creation itself has connection_timeout which should prevent hanging
        self.driver = None
        self.uri = uri
        
        try:
            # Create driver with aggressive timeouts
            from neo4j import GraphDatabase
            
            auth_token = (user, password) if user and password else None
            print(f"[DEBUG] Creating Neo4j driver with auth={auth_token if auth_token else 'None'}")
            
            self.driver = GraphDatabase.driver(
                uri, 
                auth=auth_token,
                connection_timeout=2.0,  # 2 seconds
                max_connection_lifetime=60,
                connection_acquisition_timeout=2.0
            )
            print(f"[DEBUG] Neo4j driver created (lazy connection)")
        except Exception as e:
            print(f"[ERROR] Neo4j driver creation failed: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def check_connection(self):
        print(f"[DEBUG] check_connection() called")
        if not self.driver:
            print(f"[DEBUG] No driver, returning False")
            return False
            
        # Use threading to enforce timeout on the connection check
        import threading
        result = [False]
        error = [None]
        
        def _check():
            try:
                print(f"[DEBUG] Attempting to connect to Neo4j...")
                with self.driver.session() as session:
                    session.run("RETURN 1").consume()  # consume() forces execution
                print(f"[DEBUG] Neo4j connection successful!")
                result[0] = True
            except Exception as e:
                error[0] = e
        
        thread = threading.Thread(target=_check, daemon=True)
        thread.start()
        thread.join(timeout=3.0)  # 3 second timeout
        
        if thread.is_alive():
            print(f"Neo4j Connection Failed: Connection timeout after 3 seconds")
            return False
        elif error[0]:
            print(f"Neo4j Connection Failed: {error[0]}")
            return False
        else:
            return result[0]

    # --- 0. INITIALIZATION ---
    def ensure_relationship_exists(self, char_name, user_name):
        """Ensures the base TRUSTS relationship exists so we can update it."""
        if not self.driver: return
        with self.driver.session() as session:
            session.run("""
                MERGE (c:Character {name: $char_name})
                MERGE (u:User {name: $user_name})
                MERGE (c)-[r:TRUSTS]->(u)
                ON CREATE SET r.level = 50.0
            """, char_name=char_name, user_name=user_name)

    # --- 1. INSERTING MEMORIES (The "Learning" Phase) ---
    def add_interaction_event(self, char_name, user_name, summary, sentiment):
        """
        Creates a graph link: (Elias)-[:INTERACTED_WITH]->(Event)<-[:PARTICIPATED_IN]-(User)
        """
        if not summary: return # Don't log empty stats
        if not self.driver: return
        
        with self.driver.session() as session:
            session.run("""
                MERGE (c:Character {name: $char_name})
                MERGE (u:User {name: $user_name})
                CREATE (e:Event {summary: $summary, sentiment: $sentiment, timestamp: timestamp()})
                CREATE (c)-[:EXPERIENCED]->(e)
                CREATE (u)-[:PARTICIPATED_IN]->(e)
            """, char_name=char_name, user_name=user_name, summary=summary, sentiment=sentiment)

    # --- 2. UPDATING RELATIONSHIPS (The "Growth" Phase) ---
    def update_trust(self, char_name, user_name, delta):
        """
        Updates the 'TRUSTS' edge property dynamically.
        """
        if delta == 0: return # No change
        if not self.driver: return
        
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Character {name: $char_name})-[r:TRUSTS]->(u:User {name: $user_name})
                SET r.level = r.level + $delta
                RETURN r.level
            """, char_name=char_name, user_name=user_name, delta=delta)

    # --- 3. THE KILLER FEATURE: INDIRECT QUERYING ---
    def get_opinion_on_topic(self, char_name, topic):
        """
        Finds why the character cares about a topic by traversing the graph.
        Example: Elias -> HATES -> Empire -> DESTROYED -> Home
        """
        if not self.driver: return []
        with self.driver.session() as session:
            # We look for paths of length 1 to 2
            # (Character)-[]-(Topic) OR (Character)-[]-()-[]-(Topic)
            # To avoid finding the User node as a "Topic" connection, we might blacklist types or just be generic.
            result = session.run("""
                MATCH path = (c:Character {name: $char_name})-[*1..2]-(target {name: $topic})
                WHERE NOT 'User' IN labels(target)
                RETURN path LIMIT 1
            """, char_name=char_name, topic=topic)
            
            # Simple formatter
            paths = []
            for record in result:
                path = record["path"]
                # Convert path to readable string "Elias -[TRUSTS]-> User"
                # This is a bit complex in raw python, simplifying output for now
                rel_strs = []
                for rel in path.relationships:
                    rel_strs.append(f"-[:{rel.type}]->") 
                paths.append("...".join(rel_strs))
            return paths

    def clear_database(self):
        """Wipes the entire database. DANGEROUS."""
        if not self.driver: return
        print(f"[WARNING] Wiping Neo4j Database...")
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def get_viz_data(self):
        """Fetches nodes and edges for visualization."""
        if not self.driver: return {"nodes": [], "edges": []}
        
        with self.driver.session() as session:
            # Fetch all nodes and relationships (limit to prevent explosion)
            result = session.run("""
                MATCH (n)-[r]->(m)
                RETURN n, r, m LIMIT 100
            """)
            
            nodes = {}
            edges = []
            
            for record in result:
                n, r, m = record["n"], record["r"], record["m"]
                
                # Format Nodes
                n_id = str(n.id) # Neo4j internal ID
                m_id = str(m.id)
                
                # Labels
                n_label = list(n.labels)[0] if n.labels else "Node"
                m_label = list(m.labels)[0] if m.labels else "Node"
                
                # Name property or fallback
                n_name = n.get("name", n_label)
                m_name = m.get("name", m_label)
                
                if n_id not in nodes:
                    nodes[n_id] = {"id": n_id, "label": n_name, "group": n_label}
                if m_id not in nodes:
                    nodes[m_id] = {"id": m_id, "label": m_name, "group": m_label}
                
                # Edge
                edges.append({
                    "from": n_id,
                    "to": m_id,
                    "label": r.type,
                    "arrows": "to"
                })
                
            return {"nodes": list(nodes.values()), "edges": edges}
