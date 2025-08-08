"""
Auto-Scoring System for Mekong Recruitment System

This module provides automated scoring functionality following AGENT_RULES_DEVELOPER:
- Implement weighted scoring (IQ 40%, Technical 60%)
- Tạo pass/fail logic với configurable thresholds
- Implement auto-approval cho scores ≥70%
- Tạo manual review flag cho scores 50-69%
- Implement auto-rejection cho scores <50%
- Tạo detailed score breakdown
"""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import json
import logging
from dataclasses import dataclass

from . import db
from .models import AssessmentResult, Step1Question, Candidate
from app.utils import log_audit_event

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class ScoringConfig:
    """Configuration for scoring system."""
    # Thresholds
    auto_approval_threshold: float = 70.0
    manual_review_min: float = 50.0
    auto_rejection_threshold: float = 50.0
    
    # Weighted scoring
    iq_weight: float = 0.4  # 40%
    technical_weight: float = 0.6  # 60%
    
    # Category weights (can be customized per position)
    category_weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.category_weights is None:
            self.category_weights = {
                'iq': 0.4,
                'technical': 0.6,
                'problem_solving': 0.3,
                'programming': 0.4,
                'system_design': 0.3
            }

class AutoScoringSystem:
    """
    Automated scoring system for assessments.
    """
    
    def __init__(self, config: ScoringConfig = None):
        """
        Initialize scoring system.
        
        Args:
            config (ScoringConfig): Scoring configuration
        """
        self.config = config or ScoringConfig()
    
    def calculate_question_score(self, question: Step1Question, answer: str) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate score for a single question.
        
        Args:
            question (Step1Question): Question object
            answer (str): Candidate's answer
            
        Returns:
            Tuple[float, Dict[str, Any]]: (score, details)
        """
        max_score = question.points or 1
        score = 0
        details = {
            'question_id': question.id,
            'question_type': question.question_type,
            'category': question.category,
            'difficulty': question.difficulty,
            'max_score': max_score,
            'answer': answer,
            'correct_answer': question.correct_answer if question.question_type == 'multiple_choice' else None,
            'explanation': question.explanation
        }
        
        if not answer:
            details['score'] = 0
            details['reason'] = 'No answer provided'
            return 0, details
        
        if question.question_type == 'multiple_choice':
            # Multiple choice scoring
            if answer == question.correct_answer:
                score = max_score
                details['reason'] = 'Correct answer'
            else:
                score = 0
                details['reason'] = 'Incorrect answer'
        
        elif question.question_type == 'text':
            # Text answer scoring (basic keyword matching)
            score = self._score_text_answer(question, answer, max_score)
            details['reason'] = 'Text answer evaluated'
            details['keywords_found'] = self._extract_keywords(question, answer)
        
        elif question.question_type == 'coding':
            # Coding question scoring
            score = self._score_coding_answer(question, answer, max_score)
            details['reason'] = 'Code evaluated'
        
        details['score'] = score
        return score, details
    
    def _score_text_answer(self, question: Step1Question, answer: str, max_score: float) -> float:
        """
        Score text answer using keyword matching.
        
        Args:
            question (Step1Question): Question object
            answer (str): Candidate's answer
            max_score (float): Maximum possible score
            
        Returns:
            float: Calculated score
        """
        # Extract expected keywords from question explanation or correct answer
        expected_keywords = self._extract_expected_keywords(question)
        if not expected_keywords:
            return max_score * 0.5  # Default 50% for text answers without keywords
        
        # Count matching keywords
        answer_lower = answer.lower()
        matched_keywords = sum(1 for keyword in expected_keywords if keyword.lower() in answer_lower)
        
        # Calculate score based on keyword match percentage
        keyword_score = (matched_keywords / len(expected_keywords)) * max_score
        
        # Bonus for answer length (indicates effort)
        length_bonus = min(len(answer.split()) / 50, 0.2) * max_score
        
        return min(keyword_score + length_bonus, max_score)
    
    def _extract_expected_keywords(self, question: Step1Question) -> List[str]:
        """
        Extract expected keywords from question.
        
        Args:
            question (Step1Question): Question object
            
        Returns:
            List[str]: List of expected keywords
        """
        keywords = []
        
        # Extract from explanation
        if question.explanation:
            # Simple keyword extraction (can be enhanced with NLP)
            important_words = ['important', 'key', 'critical', 'essential', 'must', 'should']
            words = question.explanation.lower().split()
            keywords.extend([word for word in words if len(word) > 4 and word not in important_words])
        
        # Extract from correct answer if available
        if question.correct_answer:
            keywords.extend(question.correct_answer.lower().split())
        
        return list(set(keywords))  # Remove duplicates
    
    def _extract_keywords(self, question: Step1Question, answer: str) -> List[str]:
        """
        Extract keywords from candidate's answer.
        
        Args:
            question (Step1Question): Question object
            answer (str): Candidate's answer
            
        Returns:
            List[str]: List of keywords found
        """
        # Simple keyword extraction
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = answer.lower().split()
        return [word for word in words if len(word) > 3 and word not in stop_words]
    
    def _score_coding_answer(self, question: Step1Question, answer: str, max_score: float) -> float:
        """
        Score coding answer.
        
        Args:
            question (Step1Question): Question object
            answer (str): Candidate's answer
            max_score (float): Maximum possible score
            
        Returns:
            float: Calculated score
        """
        # Basic coding answer evaluation
        # In a real system, this would involve code execution and testing
        
        score = 0
        
        # Check for code structure
        if 'def ' in answer or 'function ' in answer:
            score += max_score * 0.3
        
        # Check for proper syntax indicators
        if '(' in answer and ')' in answer:
            score += max_score * 0.2
        
        # Check for comments (shows understanding)
        if '#' in answer or '//' in answer:
            score += max_score * 0.1
        
        # Check for variable declarations
        if '=' in answer:
            score += max_score * 0.2
        
        # Check for control structures
        if any(keyword in answer for keyword in ['if', 'for', 'while', 'return']):
            score += max_score * 0.2
        
        return min(score, max_score)
    
    def calculate_weighted_score(self, question_scores: List[Dict[str, Any]]) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate weighted score based on question categories.
        
        Args:
            question_scores (List[Dict[str, Any]]): List of question scores with details
            
        Returns:
            Tuple[float, Dict[str, Any]]: (weighted_score, breakdown)
        """
        category_scores = {}
        category_counts = {}
        
        # Group scores by category
        for score_data in question_scores:
            category = score_data['category']
            score = score_data['score']
            max_score = score_data['max_score']
            
            if category not in category_scores:
                category_scores[category] = 0
                category_counts[category] = 0
            
            category_scores[category] += score
            category_counts[category] += max_score
        
        # Calculate category percentages
        category_percentages = {}
        for category in category_scores:
            if category_counts[category] > 0:
                category_percentages[category] = (category_scores[category] / category_counts[category]) * 100
            else:
                category_percentages[category] = 0
        
        # Apply weighted scoring
        weighted_score = 0
        for category, percentage in category_percentages.items():
            weight = self.config.category_weights.get(category, 0.1)  # Default weight
            weighted_score += percentage * weight
        
        # Calculate overall percentage
        total_max_score = sum(score_data['max_score'] for score_data in question_scores)
        total_actual_score = sum(score_data['score'] for score_data in question_scores)
        overall_percentage = (total_actual_score / total_max_score * 100) if total_max_score > 0 else 0
        
        breakdown = {
            'category_scores': category_scores,
            'category_percentages': category_percentages,
            'total_score': total_actual_score,
            'max_score': total_max_score,
            'overall_percentage': overall_percentage,
            'weighted_score': weighted_score,
            'question_details': question_scores
        }
        
        return weighted_score, breakdown
    
    def determine_status(self, percentage: float) -> str:
        """
        Determine assessment status based on percentage.
        
        Args:
            percentage (float): Assessment percentage
            
        Returns:
            str: Status (passed, manual_review, failed)
        """
        if percentage >= self.config.auto_approval_threshold:
            return 'passed'
        elif percentage >= self.config.manual_review_min:
            return 'manual_review'
        else:
            return 'failed'
    
    def process_assessment(self, candidate_id: int, answers: Dict[str, str]) -> AssessmentResult:
        """
        Process complete assessment and generate result.
        
        Args:
            candidate_id (int): Candidate ID
            answers (Dict[str, str]): Question ID to answer mapping
            
        Returns:
            AssessmentResult: Assessment result object
        """
        # Get questions
        question_ids = list(answers.keys())
        questions = Step1Question.query.filter(Step1Question.id.in_(question_ids)).all()
        
        # Calculate individual question scores
        question_scores = []
        total_score = 0
        max_score = 0
        
        for question in questions:
            answer = answers.get(str(question.id), '')
            score, details = self.calculate_question_score(question, answer)
            
            question_scores.append(details)
            total_score += score
            max_score += question.points or 1
        
        # Calculate percentage
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        
        # Calculate weighted score
        weighted_score, breakdown = self.calculate_weighted_score(question_scores)
        
        # Determine status
        status = self.determine_status(percentage)
        
        # Create assessment result
        assessment_result = AssessmentResult(
            candidate_id=candidate_id,
            step='step1',
            score=total_score,
            max_score=max_score,
            percentage=percentage,
            status=status,
            answers=json.dumps(answers),
            question_scores=json.dumps(question_scores),
            weighted_score=weighted_score,
            score_breakdown=json.dumps(breakdown),
            start_time=datetime.utcnow(),  # This should come from session
            end_time=datetime.utcnow(),
            ip_address='127.0.0.1'  # This should come from request
        )
        
        # Save to database
        db.session.add(assessment_result)
        db.session.commit()
        
        # Update candidate status
        candidate = Candidate.query.get(candidate_id)
        if candidate:
            candidate.status = f'step1_{status}'
            db.session.commit()
        
        # Log assessment completion
        log_audit_event(
            user_id=None,
            action='assessment_scored',
            resource_type='assessment',
            resource_id=candidate_id,
            details={
                'candidate_id': candidate_id,
                'score': total_score,
                'max_score': max_score,
                'percentage': percentage,
                'status': status,
                'weighted_score': weighted_score
            }
        )
        
        return assessment_result
    
    def get_scoring_statistics(self) -> Dict[str, Any]:
        """
        Get scoring system statistics.
        
        Returns:
            Dict[str, Any]: Statistics
        """
        total_assessments = AssessmentResult.query.filter_by(step='step1').count()
        passed_assessments = AssessmentResult.query.filter_by(step='step1', status='passed').count()
        manual_review_assessments = AssessmentResult.query.filter_by(step='step1', status='manual_review').count()
        failed_assessments = AssessmentResult.query.filter_by(step='step1', status='failed').count()
        
        avg_score = db.session.query(db.func.avg(AssessmentResult.percentage)).filter_by(step='step1').scalar() or 0
        
        return {
            'total_assessments': total_assessments,
            'passed_assessments': passed_assessments,
            'manual_review_assessments': manual_review_assessments,
            'failed_assessments': failed_assessments,
            'pass_rate': (passed_assessments / total_assessments * 100) if total_assessments > 0 else 0,
            'average_score': avg_score,
            'scoring_config': {
                'auto_approval_threshold': self.config.auto_approval_threshold,
                'manual_review_min': self.config.manual_review_min,
                'auto_rejection_threshold': self.config.auto_rejection_threshold,
                'category_weights': self.config.category_weights
            }
        }

# Global scoring system instance
scoring_system = AutoScoringSystem()

def get_scoring_system() -> AutoScoringSystem:
    """
    Get global scoring system instance.
    
    Returns:
        AutoScoringSystem: Scoring system instance
    """
    return scoring_system 