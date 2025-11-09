"""
Canvas Analyzer for Pocket Professor

This module is responsible for analyzing the canvas and extracting relevant information
"""


from typing import List, Dict, Optional
from vision_analyzer import VisionAnalyzer
from datetime import datetime
import os
import json
import uuid



class CanvasAnalyzer:
    """
    Analyzes the canvas and extracts relevant information

    Features:
    1. Error detection
    2. step by step verification
    3. hint generation
    4. Encouraging feedback
    """

    def __init__(self):
        self.vision_analyzer = VisionAnalyzer()
    

    def analyze_student_work(
        self,
        image_path: str,
        context: Optional[str] = None,
        problem_type: str = "general"
    ) -> Dict:
        """
        Analyzes the canvas and extracts relevant information

        Args:
            image_path (str): Path to the image
            context (Optional[str]): Context for the problem
            problem_type (str): Type of the problem

        Returns:
            Dict: Dictionary containing the analysis results
        """
        try:
            #Build the specialized prompt based on problem type
            prompt= self._build_canvas_prompt(context, problem_type)

            #analyze image using vision api
            analysis_result = self.vision_analyzer.analyze_image(image_path, prompt)

            if not analysis_result["success"]:
                return {
                    "status": "error",
                    "message": "Failed to analyze student work",
                    "error": analysis_result["error"]
                }

            feedback = self._structure_feedback(analysis_result["analysis"], problem_type)

            return {
                "status": "success",
                "message": "Student work analyzed successfully",
                "feedback": feedback,
                "analysis": analysis_result["analysis"],
                "image_path": image_path,
                "context": context,
                "problem_type": problem_type,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "message": "Failed to analyze student work",
                "error": str(e)
            }
    
    def _build_canvas_prompt(self, context: Optional[str], problem_type: str) -> str:
        """
        Builds a specialized prompt for the canvas based on the context and problem type

        Args:
            context (Optional[str]): Context for the problem
            problem_type (str): Type of the problem

        Returns:
            str: Specialized prompt for the canvas
        """
        base_context = f"Context: {context}\n\n" if context else ""

        prompts = {
            "math": f"""{base_context}You are analyzing a student's handwritten math work on a whiteboard.

Your role as Pocket Professor:
1. **Identify what they're trying to solve** - What problem or concept?
2. **Check their work step-by-step** - Are the steps mathematically correct?
3. **Find errors gently** - Point out mistakes without being harsh
4. **Give hints, not answers** - Guide them to the solution
5. **Encourage progress** - Praise correct steps
6. **Suggest next steps** - What should they do next?

Be supportive and educational. Don't solve the problem for them.""",
            
            "physics": f"""{base_context}You are analyzing a student's physics problem work on a whiteboard.

Your role as Pocket Professor:
1. **Identify the physics concept** - What principle are they applying?
2. **Check their approach** - Is their method correct?
3. **Verify units and calculations** - Are units consistent?
4. **Find conceptual errors** - Misunderstandings of physics principles
5. **Provide hints** - Guide without solving
6. **Encourage** - Acknowledge good reasoning

Be a supportive physics tutor.""",
            
            "chemistry": f"""{base_context}You are analyzing a student's chemistry work on a whiteboard.

Your role as Pocket Professor:
1. **Identify the chemistry concept** - Reactions, structures, calculations?
2. **Check notation** - Are chemical formulas correct?
3. **Verify balancing** - For equations, check if balanced
4. **Find errors** - Gently point out mistakes
5. **Provide hints** - Guide their thinking
6. **Encourage** - Praise correct understanding

Be a supportive chemistry tutor.""",
            
            "diagram": f"""{base_context}You are analyzing a student's diagram or concept map on a whiteboard.

Your role as Pocket Professor:
1. **Understand the diagram** - What are they trying to represent?
2. **Check accuracy** - Are relationships correct?
3. **Identify missing elements** - What's missing?
4. **Verify labels** - Are labels accurate and complete?
5. **Suggest improvements** - How can it be clearer?
6. **Encourage** - Praise good organization

Be a supportive visual learning tutor.""",
            
            "general": f"""{base_context}You are analyzing a student's work on a whiteboard.

Your role as Pocket Professor:
1. **Understand what they're working on** - Identify the subject and problem
2. **Check their work** - Look for errors or misconceptions
3. **Provide constructive feedback** - Be specific and helpful
4. **Give hints** - Guide without giving away answers
5. **Encourage learning** - Praise effort and correct thinking
6. **Suggest next steps** - What should they do next?

Be supportive, educational, and encouraging."""
        }
        
        return prompts.get(problem_type, prompts["general"])

    def _structure_feedback(self, analysis: str, problem_type: str) -> Dict:
        """
        Structures the feedback based on the analysis and problem type

        Args:
            analysis (str): Analysis of the student's work
            problem_type (str): Type of the problem

        Returns:
            str: Structured feedback


        For now it only returns simple text analysis, we will do annotations later:)
        """

        return {
            "overall_feedback" : analysis,
            "problem_type": problem_type,
            "feedback_type": "text",
            "encouragement": self._extract_encouragement(analysis),
        }

    def _extract_encouragement(self, analysis: str) -> str:
        """
        Extracts encouragement from the analysis

        Args:
            analysis (str): Analysis of the student's work

        Returns:
            str: Encouragement
        """
        if any(word in analysis.lower() for word in ["correct", "good", "right", "well done"]):
            return "Excellent work! Keep it up! 🌟"
        else:
            return "You're making progress! Let's refine this together. 💪"



        




        
        


        

