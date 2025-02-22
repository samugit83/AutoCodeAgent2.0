from typing import List, Dict    
from neo4j import GraphDatabase, exceptions  


class EGoTEngine:
    def __init__(self, session_id: str, neo4j_uri: str, neo4j_user: str, neo4j_password: str, logger): 
        self.session_id = session_id  # Store session_id as a class attribute
        self.logger = logger
        try:
            self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            self.logger.info("Successfully connected to Neo4j.")
        except exceptions.Neo4jError as e:
            self.logger.error(f"Failed to create the Neo4j driver: {e}")
            raise
   
    def close(self):
        self.driver.close() 
        self.logger.info("Neo4j driver closed.")

    def create_node(self, agent_nickname: str, concept: str, thought: str, name: str, entity_type: str) -> int:
        """
        Creates a new node with a dynamic label based on the session_id.
        Each node is created with a label equal to the stored session_id.
        Returns the internal Neo4j node id.
        """
        query = (
            f"CREATE (n:{self.session_id}:EGOT {{agent_nickname: $agent_nickname, name: $name, concept: $concept, thought: $thought, entity_type: $entity_type}}) "
            "RETURN id(n) as node_id"
        )
        try:
            with self.driver.session() as session:
                result = session.run(query,
                                     agent_nickname=agent_nickname,
                                     name=name,
                                     concept=concept,
                                     thought=thought,
                                     entity_type=entity_type)
                record = result.single()
                node_id = record["node_id"] if record else None
                self.logger.info(f"○○○○ Created node for {agent_nickname} with label {self.session_id} and node_id: {node_id}")
            return node_id
        except exceptions.Neo4jError as e:
            self.logger.error(f"Error creating node: {e}")
            return None

    def create_edge(self, from_node_id: int, to_node_id: int, relation: str) -> None:
        """
        Creates an edge between two nodes, with a custom relation name.
        """
        query = (
            "MATCH (a), (b) "
            "WHERE id(a) = $from_node_id AND id(b) = $to_node_id "
            "MERGE (a)-[r:CONNECTED {relation: $relation}]->(b) "
            "RETURN r"
        )
        try:
            with self.driver.session() as session:
                session.run(query,
                            from_node_id=from_node_id,
                            to_node_id=to_node_id,
                            relation=relation)
                self.logger.info(f"○----○ Created edge from node {from_node_id} to node {to_node_id} with relation '{relation}'.")
        except exceptions.Neo4jError as e:
            self.logger.error(f"Error creating edge: {e}")

    def get_graph(self) -> list:
        """
        Retrieves all nodes and their outgoing relationships for nodes with the dynamic label equal to the stored session_id.
        Returns an array where each object represents a node with:
          - agent_nickname
          - name
          - concept
          - thought
          - node_id
          - relations: an array of objects, each with {relation: <relation name>, to: <node_id>}
        """
        query = f"""
        MATCH (n:{self.session_id})
        OPTIONAL MATCH (n)-[r:CONNECTED]->(m:{self.session_id})
        RETURN n, r, m
        """
        nodes = {}
        try:
            with self.driver.session() as session:
                result = session.run(query)
                for record in result:
                    n = record["n"]
                    node_id = n.id
                    if node_id not in nodes:
                        nodes[node_id] = {
                            "agent_nickname": n.get("agent_nickname"),
                            "name": n.get("name"),
                            "concept": n.get("concept"),
                            "thought": n.get("thought"),
                            "node_id": node_id,
                            "relations": []
                        }
                    r = record["r"]
                    m = record["m"]
                    if r is not None and m is not None:
                        relation_obj = {
                            "relation": r.get("relation"),
                            "to": m.id
                        }
                        nodes[node_id]["relations"].append(relation_obj)
            output_array = list(nodes.values())
            self.logger.info(f"🔢 Retrieved {len(output_array)} nodes for label {self.session_id}.")
            return output_array
        except exceptions.Neo4jError as e:
            self.logger.error(f"Error retrieving graph for {self.session_id}: {e}")
            return []

    def delete_graph(self) -> None:
        """
        Deletes all nodes and their relationships for nodes with the dynamic label equal to the stored session_id.
        """
        query = f"""
        MATCH (n:{self.session_id})
        DETACH DELETE n
        """
        try:
            with self.driver.session() as session:
                session.run(query)
            self.logger.info(f"Deleted all nodes with label {self.session_id}.")
        except exceptions.Neo4jError as e:
            self.logger.error(f"Error deleting nodes for {self.session_id}: {e}")

    def create_multiple_nodes_and_edges(self, evolution_data: List[Dict], agent_nickname: str) -> Dict[int, int]:
        """
        Processes a list of node definitions and creates multiple nodes and their edges in Neo4j.
        
        Each dictionary in evolution_data should contain:
          - 'agent_nickname': str
          - 'name': str
          - 'concept': str
          - 'thought': str
          - 'entity_type': str
          
        Optionally, to create edges, the dictionary can include:
          - 'relation': str
          - 'from': int  (for new nodes, this is the positional index; for existing nodes, the Neo4j node id)
          - 'from_node_type': "new" or "egot_graph"
          - 'to': int    (similarly, positional index for new nodes or Neo4j node id for existing ones)
          - 'to_node_type': "new" or "egot_graph"
        
        The function returns a mapping from the positional index (for new nodes) to their created Neo4j node ids.
        """
        node_mapping = {}  # Maps the index (of new nodes in evolution_data) to their Neo4j node id

        # First pass: Create nodes
        for idx, node_def in enumerate(evolution_data):
            name = node_def.get("name", f"Node_{idx}")
            concept = node_def.get("concept", "")
            thought = node_def.get("thought", "")
            entity_type = node_def.get("entity_type", "")
            node_id = self.create_node(agent_nickname, concept, thought, name, entity_type)
            if node_id is not None:
                node_mapping[idx] = node_id
            else:
                self.logger.error("Failed to create node for index %d", idx)

        # Second pass: Create edges if edge information is provided in the node definitions
        for node_def in evolution_data:
            relation = node_def.get("relation")
            if relation is not None:
                from_spec = node_def.get("from")
                to_spec = node_def.get("to")
                from_node_type = node_def.get("from_node_type")
                to_node_type = node_def.get("to_node_type")
                
                if from_spec is None or to_spec is None or not from_node_type or not to_node_type:
                    self.logger.error("Incomplete edge specification in node definition: %s", node_def)
                    continue

                # Resolve the actual Neo4j node ids based on node type
                if from_node_type == "new":
                    from_node_id = node_mapping.get(from_spec)
                else:  # Assuming the specification already provides a valid Neo4j node id
                    from_node_id = from_spec

                if to_node_type == "new":
                    to_node_id = node_mapping.get(to_spec)
                else:
                    to_node_id = to_spec

                if from_node_id is not None and to_node_id is not None:
                    self.create_edge(from_node_id, to_node_id, relation)
                else:
                    self.logger.error("Edge creation failed for relation '%s': from_node_id=%s, to_node_id=%s",
                                      relation, from_node_id, to_node_id)
        return node_mapping 
    

    