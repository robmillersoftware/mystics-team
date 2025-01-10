"""Feedback management functionality for the developer agent."""
from typing import List, Dict, Any
import logging
import time

class FeedbackManager:
    """Handles feedback integration and management."""
    
    def __init__(self, agent):
        """Initialize the feedback manager.
        
        Args:
            agent: The developer agent instance
        """
        self.agent = agent
        self.logger = logging.getLogger(__name__)
        self.feedback_history = []
        
    def integrate_feedback(self, feedback: Dict[str, Any]) -> None:
        """Integrate feedback into the agent's knowledge base.
        
        Args:
            feedback: Dictionary containing feedback details including:
                     - type (review/implementation)
                     - content (the actual feedback)
                     - context (code or PR context)
                     - outcome (success/failure)
                     - timestamp (optional)
        """
        # Preserve the existing timestamp or use current time as fallback
        feedback_copy = feedback.copy()
        if "timestamp" not in feedback_copy:
            feedback_copy["timestamp"] = time.time()
        self.feedback_history.append(feedback_copy)
        
    def get_relevant_feedback(self, context: str) -> List[Dict[str, Any]]:
        """Retrieve relevant feedback based on current context.
        
        Args:
            context: The current development context (e.g., task description, code)
            
        Returns:
            List[Dict[str, Any]]: List of relevant feedback entries
        """
        # Generate embeddings for context and feedback entries
        context_embedding = self.agent.generate_embedding(context)
        
        # Calculate similarity scores for all feedback
        scored_feedback = []
        for entry in self.feedback_history:
            entry_embedding = self.agent.generate_embedding(entry["context"])
            similarity = self._calculate_similarity(context_embedding, entry_embedding)
            self.logger.debug(f"Similarity with entry '{entry['context']}': {similarity}")
            
            if similarity > 0.8:  # Standard threshold for cosine similarity
                scored_feedback.append((similarity, entry))
                
        # Sort by similarity score (descending) and then by timestamp (descending)
        return [entry for _, entry in sorted(
            scored_feedback,
            key=lambda x: (x[0], x[1].get("timestamp", 0)),
            reverse=True
        )][:5]
        
    def format_feedback_for_prompt(self, feedback: List[Dict[str, Any]]) -> str:
        """Format feedback history for inclusion in the prompt.
        
        Args:
            feedback: List of feedback entries to format
            
        Returns:
            str: Formatted feedback string
        """
        if not feedback:
            return "No relevant previous feedback available."
            
        formatted = []
        for entry in feedback:
            if entry["outcome"] == "success":
                formatted.append(f"Previous Success Pattern:\n{entry.get('code', 'No code available')}")
            else:
                formatted.append(f"Previous Issues to Avoid:\n{entry['content']}")
                
        return "\n\n".join(formatted)
        
    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            float: Cosine similarity score
        """
        # Simple dot product for now - could be replaced with more sophisticated similarity
        return sum(a * b for a, b in zip(embedding1, embedding2)) 