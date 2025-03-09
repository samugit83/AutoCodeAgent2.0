import os
import re
import uuid 
import random  
import json
import logging
import chromadb
from uuid import uuid4
from models.models import create_embeddings, call_model
from neo4j import GraphDatabase, exceptions
import spacy
import numpy as np
from params import PARAMS

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class HybridVectorGraphRag:
    def __init__(self):
        """
        Constructor: Initializes ChromaDB client, Neo4j driver, loads SpaCy, and sets up logging.
        """
        self.logger = logging.getLogger(__name__)
        self.embedding_vector_model = PARAMS["HYBRID_VECTOR_GRAPH_RAG_EMBEDDING_VECTOR_MODEL"]
        self.summarization_graph_node_model = PARAMS["HYBRID_VECTOR_GRAPH_RAG_SUMMARIZATION_GRAPH_NODE_MODEL"]
        self.collection_name = "hybrid_vector_graph_rag"

        # Initialize ChromaDB client
        db_path = PARAMS["CHROMA_DB_PATH"]
        if not db_path:
            raise EnvironmentError("CHROMA_DB_PATH environment variable not set.")

        try: 
            self.client = chromadb.PersistentClient(path=db_path)
            self.logger.debug("ChromaDB client initialized successfully.")
        except TypeError as e:
            raise RuntimeError(f"Error initializing Chroma client: {e}")

        # Initialize Neo4j driver
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USER")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not all([neo4j_uri, neo4j_user, neo4j_password]):
            raise EnvironmentError("Neo4j connection details are not fully set in environment variables.")

        try:
            self.neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            self.logger.debug("Neo4j driver initialized successfully.")
        except exceptions.Neo4jError as e:
            raise RuntimeError(f"Error initializing Neo4j driver: {e}")

        # Ensure Neo4j constraints and indexes are in place
        self._setup_neo4j_constraints()

        # Create or get an existing collection in ChromaDB
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

        # Initialize SpaCy (choose a model that has vectors if you want to rely on built-in similarity)
        try:
            self.nlp = spacy.load("en_core_web_sm")
            self.logger.debug("SpaCy model loaded successfully.")
        except Exception as e:
            self.logger.error(f"Error loading SpaCy model: {e}")
            raise RuntimeError(f"SpaCy model loading failed: {e}")

    @staticmethod
    def generate_random_hex_color():
        """
        Generates a random hex color string.
        """
        return "#{:06x}".format(random.randint(0, 0xFFFFFF))

    @staticmethod
    def generate_corpus_uuid():
        """
        Generates a UUIDv4 string for corpus identification.
        """
        return str(uuid.uuid4())

    def _setup_neo4j_constraints(self):
        """
        Sets up necessary constraints and indexes in Neo4j to ensure data integrity and query performance.
        """
        with self.neo4j_driver.session() as session:
            try:
                # Ensure the 'id' property is unique for Chunk nodes
                session.run("""
                CREATE CONSTRAINT chunk_id_unique_constraint IF NOT EXISTS
                FOR (c:Chunk)
                REQUIRE c.id IS UNIQUE
                """)
                self.logger.debug("Ensured unique constraint on Chunk.id.")

                # Ensure an index on the 'id' property for faster lookups
                session.run("""
                CREATE INDEX chunk_id_index IF NOT EXISTS
                FOR (c:Chunk)
                ON (c.id)
                """)
                self.logger.debug("Ensured index on Chunk.id.")
            except exceptions.Neo4jError as e:
                self.logger.error(f"Error setting up Neo4j constraints/indexes: {e}")
                raise RuntimeError(f"Neo4j constraints/indexes setup failed: {e}")

    def split_text_into_chunks(self, text, max_chars, overlap):
        """
        Splits a large text into smaller chunks with a specified max length and optional overlap.
        """
        chunks = []
        start = 0
        while start < len(text):
            end = min(len(text), start + max_chars)
            chunk = text[start:end]
            if end < len(text):
                # Overlap
                overlap_start = max(0, end - overlap)
                start = overlap_start
            else:
                start = end
            chunks.append(chunk.strip())
        return chunks

    def summarize_text(self, text: str) -> str:
        """
        Summarizes the given text using the custom call_model function.
        """
        summ_length = PARAMS["HYBRID_VECTOR_GRAPH_RAG_SUMMARIZATION_GRAPH_NODE_LENGTH"] 
        prompt = f"Summarize the following text in {summ_length} words: {text}"
        try:
            summary = call_model(
                chat_history=[{"role": "user", "content": prompt}],
                model=self.summarization_graph_node_model
            )

            summary = summary.strip()
            if not summary:
                raise ValueError("Summarization model returned an empty summary.")
            return summary
        except Exception as e:
            self.logger.error(f"Error during summarization: {e}")
            raise RuntimeError(f"Summarization failed: {e}")

    def lemmatize_text(self, text: str) -> str:
        """
        Lemmatizes the given text using SpaCy.
        """
        doc = self.nlp(text)
        lemmatized = ' '.join([token.lemma_ for token in doc if not token.is_punct and not token.is_stop])
        return lemmatized

    def ingest(self, texts: list[str]):
        """
        Main method to:
          1) Split text into chunks,
          2) Create embeddings of full chunks for ChromaDB,
          3) Summarize & lemmatize each chunk,
          4) Create embeddings of the lemmatized summary,
          5) Create a node for each chunk in Neo4j storing summary + embedding + color + Corpus_<id> label,
          6) Create similarity edges to existing nodes in Neo4j.
        """
        max_chars = PARAMS["HYBRID_VECTOR_GRAPH_RAG_CHUNK_SIZE"]
        overlap = PARAMS["HYBRID_VECTOR_GRAPH_RAG_OVERLAP"]

        if not texts:
            raise ValueError("No texts provided for ingestion.")

        # 1) Split text into chunks
        all_chunks = []
        for text in texts:
            stripped_text = text.strip()
            if len(stripped_text) > max_chars:
                chunks = self.split_text_into_chunks(stripped_text, max_chars, overlap)
                all_chunks.extend(chunks)
            else:
                all_chunks.append(stripped_text)

        if not all_chunks:
            raise ValueError("No valid text found in the provided inputs.")

        # Assign a unique color and corpus label for this ingestion
        color = self.generate_random_hex_color()
        corpus_uuid = self.generate_corpus_uuid()
        corpus_label = f"Corpus_{corpus_uuid.replace('-', '')}"  # Remove hyphens for label safety

        self.logger.debug(f"Assigned color {color} and corpus label {corpus_label} to the new ingestion.")

        # Generate unique IDs for each chunk (UUIDv4)
        chunk_ids = [str(uuid4()) for _ in all_chunks]
        if len(chunk_ids) != len(set(chunk_ids)):
            self.logger.error("Duplicate chunk IDs detected during ingestion.")
            raise ValueError("Duplicate chunk IDs found.")

        # Prepare doc objects
        docs = []
        for unique_id, chunk in zip(chunk_ids, all_chunks):
            docs.append({
                'id': unique_id,
                'text': chunk,
                'metadata': {'collection_name': self.collection_name}
            })

        # 2) Create embeddings using the specified model for the full chunk text
        texts_to_embed = [doc['text'] for doc in docs]
        try:
            embeddings = create_embeddings(texts_to_embed, model=self.embedding_vector_model)
            if len(embeddings) != len(docs):
                raise ValueError("Mismatch between number of embeddings and documents.")
        except Exception as e:
            self.logger.error(f"Error during embedding creation: {e}")
            raise RuntimeError(f"Embedding creation failed: {e}")

        # 3) Add documents to ChromaDB
        ids = [doc['id'] for doc in docs]
        metadatas = [doc['metadata'] for doc in docs]

        try:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts_to_embed,
                metadatas=metadatas
            )
            self.logger.debug(f"Added {len(docs)} documents to ChromaDB.")
        except Exception as e:
            self.logger.error(f"Error adding documents to ChromaDB: {e}")
            raise RuntimeError(f"ChromaDB ingestion failed: {e}")

        # 4) Summarize & lemmatize each chunk, create lemma embeddings, store in Neo4j
        with self.neo4j_driver.session() as session:
            for doc, chunk_embedding in zip(docs, embeddings):
                chunk_id = doc['id']
                text = doc['text']

                # Summarize
                summary = self.summarize_text(text)

                # Lemmatize summary
                lemmatized_summary = self.lemmatize_text(summary)

                # 4b) Create an embedding of the lemmatized summary
                try:
                    lemma_embedding = create_embeddings(
                        [lemmatized_summary],
                        model=self.embedding_vector_model
                    )[0]  # returns a list of embeddings, take the first
                except Exception as e:
                    self.logger.error(f"Error creating embedding for lemmatized summary: {e}")
                    continue  # Skip this chunk

                # 5) Create node in Neo4j with summary + lemma embedding + color + Corpus_<id> label
                try:
                    session.write_transaction(
                        self._create_node,
                        chunk_id,
                        lemmatized_summary,
                        lemma_embedding,
                        color,        # Pass the assigned color
                        corpus_label  # Pass the corpus label
                    )
                    self.logger.debug(f"Created Neo4j node for chunk ID: {chunk_id} with color {color} and label {corpus_label}")
                except Exception as e:
                    self.logger.error(f"Error creating node in Neo4j for chunk ID {chunk_id}: {e}")
                    continue  # Skip creating edges for this chunk

                # 6) Create similarity edges with existing nodes
                try:
                    self.create_similarity_edges_for_new_chunk(chunk_id, lemma_embedding)
                except Exception as e:
                    self.logger.error(f"Error creating similarity edges for chunk ID {chunk_id}: {e}")
                    continue  # Proceed with next chunk

        self.close_neo4j_driver()

        return {
            "status": "success",
            "message": f"Successfully ingested {len(docs)} documents into ChromaDB and Neo4j graph."
        }

    @staticmethod
    def _create_node(tx, chunk_id, lemmatized_summary, lemma_embedding, color, corpus_label):
        """
        Creates or merges a Chunk node with a static label and a dynamic corpus label,
        storing the lemmatized summary, embedding, and color.
        """
        # Construct the Cypher query with both static and dynamic labels
        query = f"""
        MERGE (c:Chunk:{corpus_label} {{id: $chunk_id}})
        SET c.lemmatized_summary = $lemmatized_summary,
            c.embedding = $lemma_embedding,
            c.color = $color
        """
        tx.run(query, chunk_id=chunk_id, lemmatized_summary=lemmatized_summary, lemma_embedding=lemma_embedding, color=color)

    def create_similarity_edges_for_new_chunk(self, new_chunk_id: str, new_lemma_embedding: list[float]):
        """
        Creates new 'SIMILAR_TO' edges from the newly created chunk node to all
        existing chunks in Neo4j if the cosine similarity of embeddings > threshold.
        """

        threshold = PARAMS["HYBRID_VECTOR_GRAPH_RAG_SIMILARITY_EDGE_THRESHOLD"]

        with self.neo4j_driver.session() as session:
            try:
                # 1) Get all other chunks (id, embedding) except the new one
                existing_chunks = session.read_transaction(self._get_all_other_chunks, new_chunk_id)
            except Exception as e:
                self.logger.error(f"Error retrieving existing chunks from Neo4j: {e}")
                return  # Exit the method

        for chunk_record in existing_chunks:
            old_chunk_id = chunk_record["id"]
            old_embedding = chunk_record["embedding"] or []

            # Validate that old_chunk_id is a string and old_embedding is a list
            if not isinstance(old_chunk_id, str):
                self.logger.warning(f"Skipping chunk with invalid id type: {old_chunk_id}")
                continue
            if not isinstance(old_embedding, list) or not all(isinstance(x, (int, float)) for x in old_embedding):
                self.logger.warning(f"Skipping chunk with invalid embedding: {old_chunk_id}")
                continue

            if old_embedding:  # ensure we have an embedding to compare
                sim_score = self.compute_cosine_similarity(new_lemma_embedding, old_embedding)

                # 2) If similarity is above threshold, create or merge a relationship
                if sim_score >= threshold:
                    try:
                        with self.neo4j_driver.session() as session:
                            session.write_transaction(
                                self._create_edge,
                                new_chunk_id,
                                old_chunk_id,
                                sim_score
                            )
                        self.logger.debug(
                            f"Created SIMILAR_TO edge from {new_chunk_id} --> {old_chunk_id} with weight={sim_score:.3f}"
                        )
                    except Exception as e:
                        self.logger.error(f"Error creating SIMILAR_TO edge between {new_chunk_id} and {old_chunk_id}: {e}")
                        continue  # Proceed with next chunk

    @staticmethod
    def _get_all_other_chunks(tx, new_chunk_id: str):
        """
        Retrieves the id and embedding of all existing Chunk nodes except the newly added chunk.
        """
        query = """
        MATCH (c:Chunk)
        WHERE c.id <> $new_chunk_id
        RETURN c.id as id, c.embedding as embedding
        """
        result = tx.run(query, new_chunk_id=new_chunk_id)
        return [record for record in result]

    @staticmethod
    def compute_cosine_similarity(vec1, vec2):
        """
        Computes the cosine similarity between two vectors (lists or np.ndarrays).
        """
        vec1 = np.array(vec1, dtype=float)
        vec2 = np.array(vec2, dtype=float)
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return dot_product / (norm1 * norm2) 

    @staticmethod
    def _create_edge(tx, source_id: str, target_id: str, weight: float):
        """
        Creates or merges a 'SIMILAR_TO' relationship with a 'weight' property.
        """
        query = """
        MATCH (source:Chunk {id: $source_id})
        MATCH (target:Chunk {id: $target_id})
        MERGE (source)-[rel:SIMILAR_TO]->(target)
        SET rel.weight = $weight
        """
        tx.run(query, source_id=source_id, target_id=target_id, weight=weight)

    def retrieve(
        self, 
        question: str
    ):
        """
        Demonstrates an iterative BFS approach with LLM checks:
        1) Retrieve top_k chunks from ChromaDB (vector DB).
        2) Start BFS in Neo4j, level by level.
        3) After each level, gather the context from visited nodes, 
            ask an LLM "Is this context enough?" 
        4) If LLM says it's enough, stop. Otherwise, proceed deeper.
        5) Return final answer after BFS stops or max_depth is reached.
        """

        threshold = PARAMS["HYBRID_VECTOR_GRAPH_RAG_SIMILARITY_RETRIEVE_THRESHOLD"]
        max_depth = PARAMS["HYBRID_VECTOR_GRAPH_RAG_QUERY_MAX_DEPTH"]
        top_k = PARAMS["HYBRID_VECTOR_GRAPH_RAG_QUERY_TOP_K"]
        max_context_length = PARAMS["HYBRID_VECTOR_GRAPH_RAG_QUERY_MAX_CONTEXT_LENGTH"]

        # ----------------------------------------------------------------------------
        # Step 1) Embed the user query and retrieve top_k relevant chunks from ChromaDB
        # ----------------------------------------------------------------------------
        self.logger.info(f"Received query: '{question}' (top_k={top_k}, threshold={threshold}, max_depth={max_depth}).")

        try:
            query_embedding = create_embeddings([question], model=self.embedding_vector_model)[0]
            self.logger.debug("Successfully created embedding for user query.")
        except Exception as e:
            self.logger.error(f"Error creating embedding for user query: {e}")
            raise RuntimeError("Query embedding failed") from e

        try:
            results = self.collection.query(query_embeddings=[query_embedding], n_results=top_k)
            self.logger.info(f"Retrieved top {top_k} chunks from ChromaDB based on query similarity.")
        except Exception as e:
            self.logger.error(f"Error querying ChromaDB: {e}")
            raise RuntimeError("ChromaDB query failed") from e

        # The structure of 'results' depends on your ChromaDB version/config:
        initial_ids = results["ids"][0]          # list of retrieved doc IDs
        initial_texts = results["documents"][0]  # list of retrieved doc texts

        # ----------------------------------------------------------------------------
        # Step 2) Initialize BFS queue with the retrieved chunk IDs
        # ----------------------------------------------------------------------------
        visited = set()
        queue = []

        # Each element in queue: (chunk_id, depth)
        for chunk_id in initial_ids:
            queue.append((chunk_id, 0))
        visited.update(initial_ids)

        # Keep track of *all* discovered chunk IDs
        all_related_chunk_ids = set(initial_ids)

        self.logger.info(f"Initialized BFS queue with {len(initial_ids)} chunks from initial retrieval.")

        # ----------------------------------------------------------------------------
        # Step 3) BFS loop with iterative LLM check after each “layer”
        # ----------------------------------------------------------------------------
        current_depth = 0

        while current_depth <= max_depth and queue:
            # Gather all chunk IDs at this depth
            current_layer_ids = []
            while queue and queue[0][1] == current_depth:
                node_id, depth = queue.pop(0)
                if depth == current_depth:
                    current_layer_ids.append(node_id)

            if not current_layer_ids:
                # No nodes at this depth, so we can break early.
                break

            self.logger.info(f"Processing BFS depth {current_depth}, with {len(current_layer_ids)} node(s) at this level.")

            # ------------------------------------------------------------------------
            # (a) Retrieve the text from ChromaDB for all nodes visited so far
            # ------------------------------------------------------------------------
            all_related_chunk_ids.update(current_layer_ids)
            all_related_chunk_ids_list = list(all_related_chunk_ids)

            # Retrieve from ChromaDB
            try:
                retrieved_context = self.collection.get(ids=all_related_chunk_ids_list)
                self.logger.debug(f"Retrieved context for {len(all_related_chunk_ids_list)} total chunks so far.")
            except Exception as e:
                self.logger.error(f"Error retrieving chunks by ID: {e}")
                retrieved_context = None

            if not retrieved_context or "documents" not in retrieved_context:
                self.logger.warning("No context found or missing 'documents' in retrieval.")
                combined_context_texts = initial_texts  # fallback
            else:
                combined_context_texts = retrieved_context["documents"]

            # ------------------------------------------------------------------------
            # (b) Check if the context so far is enough using an LLM meta-prompt
            # ------------------------------------------------------------------------
            full_context = "\n\n".join(combined_context_texts)
            if len(full_context) > max_context_length:
                full_context = full_context[:max_context_length] + "...[truncated]"

            self.logger.info(f"Asking LLM if the context (length={len(full_context)}) is sufficient to answer the question.")
            if self._check_if_enough_context(question, full_context):
                # If True, we conclude BFS early
                self.logger.info("LLM indicates the context is enough; stopping BFS expansion.")
                break

            # ------------------------------------------------------------------------
            # (c) If not enough, expand BFS to the next depth level
            # ------------------------------------------------------------------------
            self.logger.info(f"Context not yet sufficient, expanding to BFS depth {current_depth + 1}.")
            with self.neo4j_driver.session() as session:
                for node_id in current_layer_ids:
                    # Read neighbors
                    neighbors = session.read_transaction(
                        self._get_neighbors_above_threshold, 
                        node_id, 
                        threshold
                    )
                    for neighbor_record in neighbors:
                        neighbor_id = neighbor_record["id"]
                        if neighbor_id not in visited:
                            visited.add(neighbor_id)
                            all_related_chunk_ids.add(neighbor_id)
                            queue.append((neighbor_id, current_depth + 1))
            
            # Move to the next BFS depth
            current_depth += 1

        # ----------------------------------------------------------------------------
        # Step 4) After BFS stops (or reaches max_depth), we have our final context
        #         Build the final answer using the full context
        # ----------------------------------------------------------------------------
        self.logger.info(f"BFS completed at depth {current_depth}. Now retrieving final context for all discovered chunks.")

        all_related_chunk_ids_list = list(all_related_chunk_ids)
        try:
            retrieved_context = self.collection.get(ids=all_related_chunk_ids_list)
        except Exception as e:
            self.logger.error(f"Error retrieving chunks by ID for final context: {e}")
            retrieved_context = None

        if not retrieved_context or "documents" not in retrieved_context:
            self.logger.warning("No final context found or missing 'documents'.")
            final_context_texts = []
        else:
            final_context_texts = retrieved_context["documents"]

        full_context = "\n\n".join(final_context_texts)
        if len(full_context) > max_context_length:
            full_context = full_context[:max_context_length] + "...[truncated]"

        self.logger.info(f"Full context: {full_context}")

        # Build final question prompt
        final_prompt = (
            f"Use the following context to answer the user's question. Provide a detailed and complete response, as long as possible with all the information acquired from the context.\n\n"
            f"Context:\n{full_context}\n\n"
            f"Question:\n{question}\n"
            "Provide a concise answer:"
        )   

        self.logger.info("Calling the LLM to produce the final answer.") 
        try:
            final_answer = call_model(
                chat_history=[{"role": "user", "content": final_prompt}],
                model=self.summarization_graph_node_model
            ).strip()
        except Exception as e:
            self.logger.error(f"Error calling the model for final answer: {e}")  
            raise RuntimeError("Failed to generate an answer from the model.") from e

        self.logger.info(f"related_chunk_ids: {list(all_related_chunk_ids)}")
        self.logger.info(f"visited_depth: {current_depth}")
        self.logger.info(f"Final answer: {final_answer}")

        return final_answer


    def _check_if_enough_context(self, question: str, context: str) -> bool:
        """
        Calls an LLM with a simple meta-prompt to see if the context is 
        likely sufficient to answer the question.

        Expects a JSON response of the form:
        { "enough_context": true } 
        or
        { "enough_context": false }
        
        Returns True if enough_context is true, otherwise False.
        """
        check_prompt = (
            "You are a system that checks if the context is sufficient to answer the question.\n"
            "Answer strictly in valid JSON with a single key: 'enough_context' boolean.\n"
            f"Question: {question}\n\n"
            f"Context: {context}\n\n"
            "Is this context enough to fully answer the question?\n"
            "Reply strictly with JSON in the format: {\"enough_context\": true} or {\"enough_context\": false}"
        )

        self.logger.info("Prompting LLM to determine if the current context is sufficient.")
        try:
            response = call_model(
                chat_history=[{"role": "user", "content": check_prompt}],
                model=self.summarization_graph_node_model
            )
        except Exception as e:
            self.logger.error(f"Error calling LLM for context check: {e}")
            # If there's an error, assume it's not enough context.
            return False

        try:
            parsed = json.loads(self.sanitize_gpt_json_response(response))
            enough = bool(parsed.get("enough_context", False))
            self.logger.info(f"LLM context check response: {parsed}")
            return enough
        except Exception as parse_err:
            self.logger.warning(f"Could not parse JSON from LLM response: {response}\nError: {parse_err}")
            # Default to "not enough" context if parsing fails
            return False


    @staticmethod
    def _get_neighbors_above_threshold(tx, chunk_id: str, threshold: float):
        """
        Fetch neighbors connected via :SIMILAR_TO edges with weight >= threshold.
        Returns a list of records, each with { 'id': some_neighbor_id }.
        """
        query = """
        MATCH (c:Chunk {id: $chunk_id})-[r:SIMILAR_TO]->(neighbor:Chunk)
        WHERE r.weight >= $threshold
        RETURN neighbor.id as id
        """
        result = tx.run(query, chunk_id=chunk_id, threshold=threshold)
        return [record for record in result]
    
    @staticmethod
    def sanitize_gpt_json_response(response_str: str) -> str:
        response_str = re.sub(r'^```json\s*', '', response_str, flags=re.MULTILINE)
        response_str = re.sub(r'```$', '', response_str, flags=re.MULTILINE)
        return response_str.strip()

    def close_neo4j_driver(self):
        """
        Closes the Neo4j driver connection.
        """
        try:
            self.neo4j_driver.close()
            self.logger.debug("Neo4j driver connection closed.")
        except exceptions.Neo4jError as e:
            self.logger.error(f"Error closing Neo4j driver: {e}")
