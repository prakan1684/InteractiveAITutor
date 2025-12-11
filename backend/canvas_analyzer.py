"""
Canvas Analyzer for Pocket Professor

This module is responsible for analyzing the canvas and extracting relevant information
"""


from typing import List, Dict, Optional
from vision_analyzer import VisionAnalyzer
from datetime import datetime
from prompts.canvas_prompts import get_canvas_prompt, ANNOTATION_PROMPT
import os
import json
import uuid
import re
from logging_config import setup_logging
setup_logging(level="INFO")

from logger import get_logger
logger = get_logger(__name__)

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
            logger.info("detection started")
            detection=self.vision_analyzer.detect_problem_type_and_context(image_path)
            logger.info(
                """
                Detection result:
                success: %s
                problem_type: %s
                context: %s
                """,
                detection.get("success"),
                detection.get("problem_type"),
                detection.get("context")
            )
    

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
            logger.info(
                """
                Analysis result:
                success: %s
                analysis: %s
                image_path: %s
                query: %s
                """,
                analysis_result.get("success"),
                analysis_result.get("analysis"),
                analysis_result.get("image_path"),
                analysis_result.get("query")
            )
            

            if not analysis_result["success"]:
                return {
                    "status": "error",
                    "message": "Failed to analyze student work",
                    "error": analysis_result["error"]
                }

            logger.info("feedback generation started")

            feedback = self._structure_feedback(analysis_result["analysis"], problem_type)

            logger.info(
                """
                Feedback generation result:
                status: %s
                feedback: %s
                problem: %s
                analysis: %s
                hints: %s
                encouragement: %s
                next_step: %s
                mistakes: %s
                """,
                feedback.get("status"),
                feedback.get("feedback"),
                feedback.get("problem"),
                feedback.get("analysis"),
                feedback.get("hints"),
                feedback.get("encouragement"),
                feedback.get("next_step"),
                feedback.get("mistakes")
            )

            return {
                "status": "success",
                "problem_type": problem_type,
                "context": context,
                "feedback": {
                    "problem": feedback.get("problem", ""),
                    "analysis": feedback.get("analysis", ""),
                    "hints": feedback.get("hints", ""),
                    "mistakes": feedback.get("mistakes", ""),
                    "next_step": feedback.get("next_step", ""),
                    "encouragement": feedback.get("encouragement", "")
                }
                
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

        sections = {
            "PROBLEM": "",
            "ANALYSIS": "",
            "HINTS": "",
            "NEXT_STEP": "",
            "MISTAKES": "",
            "ENCOURAGEMENT": ""
        }

        pattern = r"(PROBLEM|ANALYSIS|HINTS|NEXT_STEP|MISTAKES|ENCOURAGEMENT):\s*([\s\S]*?)(?=\n[A-Z_]+:|$)" 
        matches = re.findall(pattern, analysis)

        for section, content in matches:
            sections[section] = content.strip()

        hint_lines = [
            h.strip("-• ").strip()
            for h in sections["HINTS"].split("\n")
            if h.strip()
        ]
        mistake_lines = [
            m.strip("-• ").strip()
            for m in sections["MISTAKES"].split("\n")
            if m.strip()
        ]

        return {
            "status": "success",
            "problem_type": problem_type,
            "problem": sections["PROBLEM"],
            "analysis": sections["ANALYSIS"],
            "hints": hint_lines,
            "next_step": sections["NEXT_STEP"],
            "mistakes": mistake_lines,
            "encouragement": sections["ENCOURAGEMENT"]
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
    
    def annotate_student_work(self, image_path: str) -> Dict:
        """
        Annotates the student's work

        Args:
            image_path (str): Path to the image

        Returns:
            Dict: Dictionary containing the annotations
        """
        try:
            logger.info("annotation started")
            detection = self.vision_analyzer.detect_problem_type_and_context(image_path)
            logger.info(
                """
                Annotation detection result:
                success: %s
                problem_type: %s
                context: %s
                """,
                detection.get("success"),
                detection.get("problem_type"),
                detection.get("context")
            )


            if detection["success"]:
                problem_type = detection["problem_type"] or ""
                context = detection["context"] or ""
            else:
                problem_type = "general"
                context = ""
            prompt= f"Context: {context}\nProblem Type: {problem_type}\n\n{ANNOTATION_PROMPT}"
            result = self.vision_analyzer.annotate_image(image_path, prompt)

            logger.info(
                """
                Annotation result:
                success: %s
                annotations: %s
                metadata: %s
                raw: %s
                model: %s
                """,
                result.get("success"),
                result.get("annotations"),
                result.get("metadata"),
                result.get("raw"),
                result.get("model")
            )
            if not result["success"]:
                return {
                    "status": "error",
                    "message": "Failed to annotate student work",
                    "error": result["error"]
                }
            return {
                "status": "success",
                'annotations': result.get("annotations", []),
                'metadata': {
                    "problem_type": problem_type,
                    "context": context,
                    "confidence": detection.get("confidence"),
                    **(result.get("metadata") or {}),
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": "Failed to annotate student work",
                "error": str(e)
            }



        




        
        


        

