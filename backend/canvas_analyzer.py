"""
Canvas Analyzer for Pocket Professor

This module is responsible for analyzing the canvas and extracting relevant information
"""


from typing import List, Dict, Optional
from vision_analyzer import VisionAnalyzer
from datetime import datetime
from prompts.canvas_prompts import get_canvas_prompt
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
        image_path: str
    ) -> Dict:
        """
        Analyzes the canvas and extracts relevant information

        Args:
            image_path (str): Path to the image

        Returns:
            Dict: Dictionary containing the analysis results
        """
        try:

            detection=self.vision_analyzer.detect_problem_type_and_context(image_path)
            if detection["success"]:
                problem_type = detection["problem_type"]
                context = detection["context"]
            else:
                problem_type = "general"
                context = ""
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

        return get_canvas_prompt(problem_type, context)

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



        




        
        


        

