




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
        canvas_analysis: Dict,
        flags: Dict,
        canvas_image_url: str = None,
    ) -> bool:
        """
        Store a canvas session with rich structured data in Azure Search and memory cache

        Args:
            session_id (str): The ID of the session
            student_id (str): The ID of the student
            final_response (str): The final response from the AI
            canvas_analysis (Dict): Rich structured analysis from Vision Agent
            flags (Dict): The flags for the session
            canvas_image_url (str): URL to the canvas image in Azure Blob Storage
        """

        logger.info(f"📦 Storing canvas session - session_id={session_id}, student_id={student_id}")

        try:
            # Extract rich structured data from Vision Agent's analysis
            problem_summary = canvas_analysis.get("problem_summary", "")
            expressions = canvas_analysis.get("expressions_found", [])
            
            # Problem classification
            problem_type = canvas_analysis.get("problem_type", "unknown")
            topic = canvas_analysis.get("topic", "unknown")
            subtopic = canvas_analysis.get("subtopic", "unknown")
            difficulty_level = canvas_analysis.get("difficulty_level", "unknown")
            
            # Answer data
            student_answer = canvas_analysis.get("student_answer")
            expected_answer = canvas_analysis.get("expected_answer")
            is_correct = canvas_analysis.get("is_correct")
            
            # Work quality
            shows_work = canvas_analysis.get("shows_work", False)
            work_clarity = canvas_analysis.get("work_clarity", "unclear")
            num_steps_shown = canvas_analysis.get("num_steps_shown", 0)
            
            # Metadata
            confidence = canvas_analysis.get("confidence", 0.0)
            visual_quality = canvas_analysis.get("visual_quality", "unknown")
            num_regions = canvas_analysis.get("num_regions", 0)

            logger.info(f"📊 Analysis: {problem_type} | Topic: {topic} | Difficulty: {difficulty_level}")
            logger.info(f"✅ Correct: {is_correct} | Confidence: {confidence}")

            # Build searchable content (for full-text search)
            content = (
                f"{final_response}\n\n"
                f"Problem: {problem_summary}\n"
                f"Type: {problem_type}\n"
                f"Topic: {topic} ({subtopic})\n"
                f"Difficulty: {difficulty_level}\n"
                f"Expressions: {', '.join(expressions)}\n"
                f"Student Answer: {student_answer}\n"
                f"Expected Answer: {expected_answer}\n"
                f"Correct: {is_correct}\n"
                f"Shows Work: {shows_work}\n"
                f"Clarity: {work_clarity}"
            )

            # Store in Azure Search with rich structured fields
            success = self.azure_search.store_canvas_session(
                session_id=session_id,
                student_id=student_id,
                content=content,
                latex_expressions=expressions,
                agent_feedback=final_response,
                # New structured fields
                problem_type=problem_type,
                topic=topic,
                subtopic=subtopic,
                difficulty_level=difficulty_level,
                student_answer=student_answer,
                expected_answer=expected_answer,
                is_correct=is_correct,
                shows_work=shows_work,
                work_clarity=work_clarity,
                num_steps_shown=num_steps_shown,
                confidence=confidence,
                visual_quality=visual_quality,
                num_regions=num_regions,
                symbol_count=len(expressions),
                needs_help=flags.get("needs_annotation", False)
            )
            if not success:
                logger.error(f"❌ Error storing canvas session in Azure Search")
                return False


            # Store rich structured data in memory cache
            session_summary = {
                "session_id": session_id,
                "timestamp": datetime.now(),
                "problem_summary": problem_summary,
                "expressions": expressions,
                # Classification
                "problem_type": problem_type,
                "topic": topic,
                "subtopic": subtopic,
                "difficulty_level": difficulty_level,
                # Answers
                "student_answer": student_answer,
                "expected_answer": expected_answer,
                "is_correct": is_correct,
                # Work quality
                "shows_work": shows_work,
                "work_clarity": work_clarity,
                "num_steps_shown": num_steps_shown,
                # Metadata
                "confidence": confidence,
                "visual_quality": visual_quality,
                "num_regions": num_regions,
                "agent_feedback": final_response,
                "canvas_image_url": canvas_image_url,
                "canvas_analysis": canvas_analysis  # Store full analysis for reference
            }

            if student_id not in self.recent_sessions:
                self.recent_sessions[student_id] = []
            
            self.recent_sessions[student_id].append(session_summary)
            self.recent_sessions[student_id] = self.recent_sessions[student_id][-5:]
            logger.info(f"💾 Cached in memory - {len(self.recent_sessions[student_id])} recent sessions for student")
            
        
            return True
        except Exception as e:
            logger.error(f"❌ Error storing canvas session: {e}")
            return False
























        
        
          
    def get_recent_context(self, student_id: str) -> Optional[Dict]:
        """
        Get most recent canvas session if within TTL (30 min)
        
        Returns:
            Session summary or None
        """
        logger.info(f"🔍 Searching for recent canvas - student_id={student_id}")
        if student_id not in self.recent_sessions:
            logger.info(f"ℹ️ No sessions in cache for student")
            return None
        
        sessions = self.recent_sessions[student_id]
        if not sessions:
            logger.info(f"ℹ️ Empty session list for student")
            return None
        
        latest = sessions[-1]
        age = datetime.now() - latest["timestamp"]
        
        if age > self.cache_ttl:
            logger.info(f"⏰ Recent session expired (age: {age})")
            return None
        
        logger.info(f"✅ Found recent session (age: {age}, session_id={latest.get('session_id')})")
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
        logger.info(f"🔎 Searching canvas history - student_id={student_id}, query='{query[:50]}...', top_k={top_k}")
        try:
            results = self.azure_search.search_canvas_sessions(
                student_id=student_id,
                query=query,
                top_k=top_k
            )
            
            logger.info(f"✅ Found {len(results)} historical canvas sessions")
            return results
            
        except Exception as e:
            logger.error(f"❌ Canvas history search failed: {e}")
            return []


session_manager = SessionManager()


            