




from typing import List, Dict, Optional
from datetime import datetime, timedelta
from app.services.azure_search_service import AzureSearchService
from app.core.logger import get_logger
logger = get_logger(__name__)

class SessionManager:
    def __init__(self):
        self.azure_search = AzureSearchService()
        self.recent_sessions = {}
        self.cache_ttl = timedelta(minutes=30)

    
    def store_canvas_session(
        self,
        session_id:str,
        student_id: str,
        final_response: str,
        symbols: List[Dict],
        flags: Dict,
    ) -> bool:
        """
        Store a canvas session in the recent sessions cache and Azure Search

        Args:
            session_id (str): The ID of the session
            student_id (str): The ID of the student
            final_response (str): The final response from the AI
            symbols (List[Dict]): List of symbols in LAtex
            flags (Dict): The flags for the session
        """

        try:
            latex_list = [s.get("latex", "") for s in symbols if s.get("latex", "") != ""]
            content = (
                f"{final_response}\n\n"
                f"Detected Expressions: {', '.join(latex_list)}\n\n"
                f"Symbol Count: {len(latex_list)}"
            )

            success = self.azure_search.store_canvas_session(
                session_id=session_id,
                student_id= student_id,
                content=content,
                latex_expressions=latex_list,
                agent_feedback=final_response,
                symbol_count=len(latex_list),
                needs_help=flags.get("needs_annotation", False)
            )

            if not success:
                logger.warning("Failed to store canvas session in Azure Search")
            

            #store in memory cache as well

            session_summary = {
                "session_id": session_id,
                "timestamp": datetime.now(),
                "latex_expressions": latex_list,
                "agent_feedback": final_response,
                "symbol_count": len(symbols),
                "needs_help": flags.get("needs_annotation", False)
            }

            if student_id not in self.recent_sessions:
                self.recent_sessions[student_id] = []
            
            self.recent_sessions[student_id].append(session_summary)
            
            self.recent_sessions[student_id] = self.recent_sessions[student_id][-5:]
            
            return True
        except Exception as e:
            logger.error(f"Error storing canvas session: {e}")
            return False

    def get_recent_context(self, student_id: str) -> Optional[Dict]:
        """
        Get most recent canvas session if within TTL (30 min)
        
        Returns:
            Session summary or None
        """
        if student_id not in self.recent_sessions:
            return None
        
        sessions = self.recent_sessions[student_id]
        if not sessions:
            return None
        
        latest = sessions[-1]
        age = datetime.now() - latest["timestamp"]
        
        if age > self.cache_ttl:
            logger.info(f"Recent session expired (age: {age})")
            return None
        
        logger.info(f"Found recent session (age: {age})")
        return latest

    def search_canvas_history(
        self,
        student_id: str,
        query: str,
        top_k: int = 3
    ) -> List[Dict]:
        """
        Search student's canvas history via Azure Search
        
        Returns:
            List of relevant sessions with scores
        """
        try:
            results = self.azure_search.search_canvas_sessions(
                student_id=student_id,
                query=query,
                top_k=top_k
            )
            
            logger.info(f"Found {len(results)} historical sessions")
            return results
            
        except Exception as e:
            logger.error(f"Canvas history search failed: {e}")
            return []


session_manager = SessionManager()


            