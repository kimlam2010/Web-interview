"""
Data Analytics Module

Advanced analytics system with question effectiveness analysis,
candidate scoring trends, interviewer bias detection, recruitment
funnel analysis, cost-per-hire calculations, and predictive analytics.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, func, desc, extract, case
from app.models import (
    db, Candidate, Position, AssessmentResult, InterviewEvaluation, 
    ExecutiveDecision, User, Step2Question, Step3Question
)
from app.decorators import hr_required, admin_required
from app.security import audit_log, rate_limit, security_check

data_analytics_bp = Blueprint('data_analytics', __name__)


class QuestionEffectivenessAnalyzer:
    """Analyzes question effectiveness and performance."""
    
    @staticmethod
    def analyze_question_effectiveness(question_type: str = None, 
                                     position_id: int = None,
                                     date_from: datetime = None,
                                     date_to: datetime = None) -> Dict[str, Any]:
        """Analyze question effectiveness across different metrics."""
        if not date_from:
            date_from = datetime.now() - timedelta(days=90)
        if not date_to:
            date_to = datetime.now()
        
        # Get question usage data
        query = db.session.query(
            Question.id,
            Question.content,
            Question.category,
            func.count(AssessmentResult.id).label('times_used'),
            func.avg(AssessmentResult.score).label('avg_score'),
            func.count(case([(AssessmentResult.status == 'passed', 1)])).label('passed_count')
        ).outerjoin(AssessmentResult, Question.id == AssessmentResult.question_id)
        
        if position_id:
            query = query.filter(Question.position_id == position_id)
        if date_from:
            query = query.filter(AssessmentResult.completed_at >= date_from)
        if date_to:
            query = query.filter(AssessmentResult.completed_at <= date_to)
        
        results = query.group_by(Question.id, Question.content, Question.category).all()
        
        # Calculate effectiveness metrics
        effectiveness_data = []
        for row in results:
            total_used = row.times_used or 0
            if total_used > 0:
                pass_rate = (row.passed_count / total_used * 100) if row.passed_count else 0
                difficulty_score = 100 - pass_rate
                
                effectiveness_data.append({
                    'question_id': row.id,
                    'content': row.content[:100] + '...' if len(row.content) > 100 else row.content,
                    'category': row.category,
                    'times_used': total_used,
                    'avg_score': round(row.avg_score, 2) if row.avg_score else 0,
                    'pass_rate': round(pass_rate, 2),
                    'difficulty_score': round(difficulty_score, 2),
                    'effectiveness_score': round((row.avg_score or 0) * (total_used / 10), 2)
                })
        
        return {
            'questions': effectiveness_data,
            'summary': {
                'total_questions': len(effectiveness_data),
                'avg_effectiveness': round(np.mean([q['effectiveness_score'] for q in effectiveness_data]), 2) if effectiveness_data else 0,
                'avg_difficulty': round(np.mean([q['difficulty_score'] for q in effectiveness_data]), 2) if effectiveness_data else 0
            }
        }


class CandidateScoringTrendsAnalyzer:
    """Analyzes candidate scoring trends over time."""
    
    @staticmethod
    def analyze_scoring_trends(position_id: int = None,
                              date_from: datetime = None,
                              date_to: datetime = None) -> Dict[str, Any]:
        """Analyze scoring trends over time."""
        if not date_from:
            date_from = datetime.now() - timedelta(days=180)
        if not date_to:
            date_to = datetime.now()
        
        # Get daily scoring data
        query = db.session.query(
            func.date(AssessmentResult.completed_at).label('date'),
            func.avg(AssessmentResult.score).label('avg_score'),
            func.count(AssessmentResult.id).label('total_candidates'),
            func.count(case([(AssessmentResult.status == 'passed', 1)])).label('passed_count')
        ).filter(AssessmentResult.completed_at.between(date_from, date_to))
        
        if position_id:
            query = query.join(Candidate).filter(Candidate.position_id == position_id)
        
        results = query.group_by(func.date(AssessmentResult.completed_at)).order_by(func.date(AssessmentResult.completed_at)).all()
        
        # Convert to DataFrame for trend analysis
        data = []
        for row in results:
            pass_rate = (row.passed_count / row.total_candidates * 100) if row.total_candidates > 0 else 0
            data.append({
                'date': row.date,
                'avg_score': round(row.avg_score, 2) if row.avg_score else 0,
                'total_candidates': row.total_candidates,
                'passed_count': row.passed_count,
                'pass_rate': round(pass_rate, 2)
            })
        
        return {
            'trends': data,
            'analysis': {
                'total_periods': len(data),
                'avg_score_overall': round(np.mean([d['avg_score'] for d in data]), 2) if data else 0,
                'avg_pass_rate_overall': round(np.mean([d['pass_rate'] for d in data]), 2) if data else 0
            }
        }


class InterviewerBiasDetector:
    """Detects potential interviewer bias in evaluations."""
    
    @staticmethod
    def detect_interviewer_bias(interviewer_id: int = None,
                               date_from: datetime = None,
                               date_to: datetime = None) -> Dict[str, Any]:
        """Detect potential bias in interviewer evaluations."""
        if not date_from:
            date_from = datetime.now() - timedelta(days=90)
        if not date_to:
            date_to = datetime.now()
        
        # Get interviewer evaluation data
        query = db.session.query(
            InterviewEvaluation.interviewer_id,
            User.username.label('interviewer_name'),
            func.count(InterviewEvaluation.id).label('total_evaluations'),
            func.avg(InterviewEvaluation.score).label('avg_score'),
            func.count(case([(InterviewEvaluation.recommendation == 'hire', 1)])).label('hire_count'),
            func.count(case([(InterviewEvaluation.recommendation == 'reject', 1)])).label('reject_count')
        ).join(User, InterviewEvaluation.interviewer_id == User.id)\
         .filter(InterviewEvaluation.evaluated_at.between(date_from, date_to))
        
        if interviewer_id:
            query = query.filter(InterviewEvaluation.interviewer_id == interviewer_id)
        
        results = query.group_by(InterviewEvaluation.interviewer_id, User.username).all()
        
        bias_analysis = []
        for row in results:
            total_evaluations = row.total_evaluations or 0
            if total_evaluations > 0:
                hire_rate = (row.hire_count / total_evaluations * 100) if row.hire_count else 0
                reject_rate = (row.reject_count / total_evaluations * 100) if row.reject_count else 0
                
                # Calculate bias indicators
                bias_score = abs(hire_rate - 50) + abs(reject_rate - 30)
                
                bias_analysis.append({
                    'interviewer_id': row.interviewer_id,
                    'interviewer_name': row.interviewer_name,
                    'total_evaluations': total_evaluations,
                    'avg_score': round(row.avg_score, 2) if row.avg_score else 0,
                    'hire_rate': round(hire_rate, 2),
                    'reject_rate': round(reject_rate, 2),
                    'bias_score': round(bias_score, 2),
                    'bias_level': 'high' if bias_score > 30 else 'medium' if bias_score > 15 else 'low'
                })
        
        return {
            'interviewers': bias_analysis,
            'summary': {
                'total_interviewers': len(bias_analysis),
                'avg_bias_score': round(np.mean([b['bias_score'] for b in bias_analysis]), 2) if bias_analysis else 0,
                'high_bias_count': len([b for b in bias_analysis if b['bias_level'] == 'high']),
                'medium_bias_count': len([b for b in bias_analysis if b['bias_level'] == 'medium']),
                'low_bias_count': len([b for b in bias_analysis if b['bias_level'] == 'low'])
            }
        }


class RecruitmentFunnelAnalyzer:
    """Analyzes recruitment funnel performance."""
    
    @staticmethod
    def analyze_recruitment_funnel(position_id: int = None,
                                 date_from: datetime = None,
                                 date_to: datetime = None) -> Dict[str, Any]:
        """Analyze recruitment funnel performance."""
        if not date_from:
            date_from = datetime.now() - timedelta(days=90)
        if not date_to:
            date_to = datetime.now()
        
        # Get funnel data
        total_candidates = db.session.query(func.count(Candidate.id))\
            .filter(Candidate.created_at.between(date_from, date_to)).scalar()
        
        step1_completed = db.session.query(func.count(AssessmentResult.id))\
            .filter(and_(
                AssessmentResult.step == 1,
                AssessmentResult.completed_at.between(date_from, date_to)
            )).scalar()
        
        step1_passed = db.session.query(func.count(AssessmentResult.id))\
            .filter(and_(
                AssessmentResult.step == 1,
                AssessmentResult.status == 'passed',
                AssessmentResult.completed_at.between(date_from, date_to)
            )).scalar()
        
        step2_completed = db.session.query(func.count(InterviewEvaluation.id))\
            .filter(and_(
                InterviewEvaluation.step == 2,
                InterviewEvaluation.evaluated_at.between(date_from, date_to)
            )).scalar()
        
        step2_passed = db.session.query(func.count(InterviewEvaluation.id))\
            .filter(and_(
                InterviewEvaluation.step == 2,
                InterviewEvaluation.recommendation == 'hire',
                InterviewEvaluation.evaluated_at.between(date_from, date_to)
            )).scalar()
        
        step3_completed = db.session.query(func.count(ExecutiveDecision.id))\
            .filter(ExecutiveDecision.completed_at.between(date_from, date_to)).scalar()
        
        step3_hired = db.session.query(func.count(ExecutiveDecision.id))\
            .filter(and_(
                ExecutiveDecision.final_decision == 'hire',
                ExecutiveDecision.completed_at.between(date_from, date_to)
            )).scalar()
        
        # Calculate conversion rates
        step1_conversion = (step1_completed / total_candidates * 100) if total_candidates > 0 else 0
        step1_pass_rate = (step1_passed / step1_completed * 100) if step1_completed > 0 else 0
        step2_conversion = (step2_completed / step1_passed * 100) if step1_passed > 0 else 0
        step2_pass_rate = (step2_passed / step2_completed * 100) if step2_completed > 0 else 0
        step3_conversion = (step3_completed / step2_passed * 100) if step2_passed > 0 else 0
        step3_hire_rate = (step3_hired / step3_completed * 100) if step3_completed > 0 else 0
        
        overall_conversion = (step3_hired / total_candidates * 100) if total_candidates > 0 else 0
        
        return {
            'funnel_data': [
                {
                    'stage': 'Total Candidates',
                    'count': total_candidates,
                    'conversion_rate': 100.0,
                    'drop_off': 0
                },
                {
                    'stage': 'Step 1 - Assessment',
                    'count': step1_completed,
                    'conversion_rate': round(step1_conversion, 2),
                    'drop_off': round(100 - step1_conversion, 2)
                },
                {
                    'stage': 'Step 1 - Passed',
                    'count': step1_passed,
                    'conversion_rate': round(step1_pass_rate, 2),
                    'drop_off': round(100 - step1_pass_rate, 2)
                },
                {
                    'stage': 'Step 2 - Interview',
                    'count': step2_completed,
                    'conversion_rate': round(step2_conversion, 2),
                    'drop_off': round(100 - step2_conversion, 2)
                },
                {
                    'stage': 'Step 2 - Passed',
                    'count': step2_passed,
                    'conversion_rate': round(step2_pass_rate, 2),
                    'drop_off': round(100 - step2_pass_rate, 2)
                },
                {
                    'stage': 'Step 3 - Executive',
                    'count': step3_completed,
                    'conversion_rate': round(step3_conversion, 2),
                    'drop_off': round(100 - step3_conversion, 2)
                },
                {
                    'stage': 'Hired',
                    'count': step3_hired,
                    'conversion_rate': round(step3_hire_rate, 2),
                    'drop_off': round(100 - step3_hire_rate, 2)
                }
            ],
            'summary': {
                'overall_conversion_rate': round(overall_conversion, 2),
                'total_candidates': total_candidates,
                'total_hired': step3_hired,
                'bottleneck_stage': 'Step 1' if step1_conversion < 50 else 'Step 2' if step2_conversion < 50 else 'Step 3'
            }
        }


class CostPerHireCalculator:
    """Calculates cost-per-hire metrics."""
    
    @staticmethod
    def calculate_cost_per_hire(position_id: int = None,
                               date_from: datetime = None,
                               date_to: datetime = None) -> Dict[str, Any]:
        """Calculate cost-per-hire metrics."""
        if not date_from:
            date_from = datetime.now() - timedelta(days=90)
        if not date_to:
            date_to = datetime.now()
        
        # Get hiring data
        hired_candidates = db.session.query(
            ExecutiveDecision.candidate_id,
            ExecutiveDecision.completed_at,
            Candidate.created_at,
            Position.title.label('position_title')
        ).join(Candidate).join(Position)\
         .filter(and_(
             ExecutiveDecision.final_decision == 'hire',
             ExecutiveDecision.completed_at.between(date_from, date_to)
         )).all()
        
        if not hired_candidates:
            return {'cost_analysis': [], 'summary': {}}
        
        # Calculate time-to-hire and costs
        cost_analysis = []
        total_time_to_hire = 0
        total_costs = 0
        
        for candidate in hired_candidates:
            time_to_hire = (candidate.completed_at - candidate.created_at).days
            total_time_to_hire += time_to_hire
            
            # Estimate costs
            base_cost = 5000000  # 5M VND base cost
            time_multiplier = 1 + (time_to_hire / 30)
            estimated_cost = base_cost * time_multiplier
            total_costs += estimated_cost
            
            cost_analysis.append({
                'candidate_id': candidate.candidate_id,
                'position': candidate.position_title,
                'time_to_hire_days': time_to_hire,
                'estimated_cost_vnd': round(estimated_cost, 0),
                'hire_date': candidate.completed_at.strftime('%Y-%m-%d')
            })
        
        avg_time_to_hire = total_time_to_hire / len(hired_candidates)
        avg_cost_per_hire = total_costs / len(hired_candidates)
        
        return {
            'cost_analysis': cost_analysis,
            'summary': {
                'total_hires': len(hired_candidates),
                'avg_time_to_hire_days': round(avg_time_to_hire, 1),
                'avg_cost_per_hire_vnd': round(avg_cost_per_hire, 0),
                'total_cost_vnd': round(total_costs, 0),
                'cost_efficiency': 'high' if avg_cost_per_hire < 10000000 else 'medium' if avg_cost_per_hire < 20000000 else 'low'
            }
        }


class PredictiveAnalyticsFramework:
    """Predictive analytics framework for recruitment."""
    
    @staticmethod
    def predict_candidate_success(candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict candidate success probability."""
        # Extract features
        assessment_score = candidate_data.get('assessment_score', 0)
        interview_score = candidate_data.get('interview_score', 0)
        experience_years = candidate_data.get('experience_years', 0)
        education_level = candidate_data.get('education_level', 'bachelor')
        position_level = candidate_data.get('position_level', 'junior')
        
        # Simple scoring model
        score = 0
        
        # Assessment score weight (40%)
        score += (assessment_score / 100) * 40
        
        # Interview score weight (30%)
        score += (interview_score / 10) * 3
        
        # Experience weight (20%)
        experience_score = min(experience_years / 10, 1) * 20
        score += experience_score
        
        # Education weight (10%)
        education_scores = {
            'high_school': 5,
            'bachelor': 8,
            'master': 10,
            'phd': 10
        }
        score += education_scores.get(education_level, 8)
        
        # Position level adjustment
        level_adjustments = {
            'junior': 0,
            'mid': 5,
            'senior': 10,
            'lead': 15
        }
        score += level_adjustments.get(position_level, 0)
        
        # Calculate success probability
        success_probability = min(score, 100) / 100
        
        return {
            'success_probability': round(success_probability, 4),
            'recommendation': 'hire' if success_probability > 0.7 else 'review' if success_probability > 0.5 else 'reject',
            'confidence_level': 'high' if abs(success_probability - 0.5) > 0.3 else 'medium' if abs(success_probability - 0.5) > 0.1 else 'low'
        }


# Route Definitions

@data_analytics_bp.route('/analytics')
@login_required
@hr_required
@rate_limit('analytics', {'requests': 30, 'window': 3600})
@audit_log('view_analytics')
def analytics_dashboard():
    """Main analytics dashboard."""
    return render_template('analytics/dashboard.html')


@data_analytics_bp.route('/analytics/question-effectiveness')
@login_required
@hr_required
@rate_limit('analytics', {'requests': 20, 'window': 3600})
@audit_log('analyze_question_effectiveness')
def question_effectiveness_analysis():
    """Analyze question effectiveness."""
    try:
        question_type = request.args.get('question_type', 'step1')
        position_id = request.args.get('position_id', type=int)
        date_from_str = request.args.get('date_from')
        date_to_str = request.args.get('date_to')
        
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d') if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d') if date_to_str else None
        
        analysis = QuestionEffectivenessAnalyzer.analyze_question_effectiveness(
            question_type=question_type,
            position_id=position_id,
            date_from=date_from,
            date_to=date_to
        )
        
        return jsonify({
            'success': True,
            'data': analysis
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@data_analytics_bp.route('/analytics/scoring-trends')
@login_required
@hr_required
@rate_limit('analytics', {'requests': 20, 'window': 3600})
@audit_log('analyze_scoring_trends')
def scoring_trends_analysis():
    """Analyze candidate scoring trends."""
    try:
        position_id = request.args.get('position_id', type=int)
        date_from_str = request.args.get('date_from')
        date_to_str = request.args.get('date_to')
        
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d') if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d') if date_to_str else None
        
        analysis = CandidateScoringTrendsAnalyzer.analyze_scoring_trends(
            position_id=position_id,
            date_from=date_from,
            date_to=date_to
        )
        
        return jsonify({
            'success': True,
            'data': analysis
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@data_analytics_bp.route('/analytics/interviewer-bias')
@login_required
@hr_required
@rate_limit('analytics', {'requests': 20, 'window': 3600})
@audit_log('detect_interviewer_bias')
def interviewer_bias_detection():
    """Detect interviewer bias."""
    try:
        interviewer_id = request.args.get('interviewer_id', type=int)
        date_from_str = request.args.get('date_from')
        date_to_str = request.args.get('date_to')
        
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d') if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d') if date_to_str else None
        
        analysis = InterviewerBiasDetector.detect_interviewer_bias(
            interviewer_id=interviewer_id,
            date_from=date_from,
            date_to=date_to
        )
        
        return jsonify({
            'success': True,
            'data': analysis
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@data_analytics_bp.route('/analytics/recruitment-funnel')
@login_required
@hr_required
@rate_limit('analytics', {'requests': 20, 'window': 3600})
@audit_log('analyze_recruitment_funnel')
def recruitment_funnel_analysis():
    """Analyze recruitment funnel."""
    try:
        position_id = request.args.get('position_id', type=int)
        date_from_str = request.args.get('date_from')
        date_to_str = request.args.get('date_to')
        
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d') if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d') if date_to_str else None
        
        analysis = RecruitmentFunnelAnalyzer.analyze_recruitment_funnel(
            position_id=position_id,
            date_from=date_from,
            date_to=date_to
        )
        
        return jsonify({
            'success': True,
            'data': analysis
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@data_analytics_bp.route('/analytics/cost-per-hire')
@login_required
@hr_required
@rate_limit('analytics', {'requests': 20, 'window': 3600})
@audit_log('calculate_cost_per_hire')
def cost_per_hire_calculation():
    """Calculate cost-per-hire metrics."""
    try:
        position_id = request.args.get('position_id', type=int)
        date_from_str = request.args.get('date_from')
        date_to_str = request.args.get('date_to')
        
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d') if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d') if date_to_str else None
        
        analysis = CostPerHireCalculator.calculate_cost_per_hire(
            position_id=position_id,
            date_from=date_from,
            date_to=date_to
        )
        
        return jsonify({
            'success': True,
            'data': analysis
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@data_analytics_bp.route('/analytics/predict-candidate', methods=['POST'])
@login_required
@hr_required
@rate_limit('analytics', {'requests': 10, 'window': 3600})
@audit_log('predict_candidate_success')
def predict_candidate_success():
    """Predict candidate success probability."""
    try:
        candidate_data = request.get_json()
        
        if not candidate_data:
            return jsonify({'success': False, 'error': 'No candidate data provided'}), 400
        
        prediction = PredictiveAnalyticsFramework.predict_candidate_success(candidate_data)
        
        return jsonify({
            'success': True,
            'prediction': prediction
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# API Endpoints for AJAX

@data_analytics_bp.route('/api/analytics/question-effectiveness')
@login_required
@rate_limit('api', {'requests': 50, 'window': 3600})
def api_question_effectiveness():
    """API endpoint for question effectiveness analysis."""
    return question_effectiveness_analysis()


@data_analytics_bp.route('/api/analytics/scoring-trends')
@login_required
@rate_limit('api', {'requests': 50, 'window': 3600})
def api_scoring_trends():
    """API endpoint for scoring trends analysis."""
    return scoring_trends_analysis()


@data_analytics_bp.route('/api/analytics/interviewer-bias')
@login_required
@rate_limit('api', {'requests': 50, 'window': 3600})
def api_interviewer_bias():
    """API endpoint for interviewer bias detection."""
    return interviewer_bias_detection()


@data_analytics_bp.route('/api/analytics/recruitment-funnel')
@login_required
@rate_limit('api', {'requests': 50, 'window': 3600})
def api_recruitment_funnel():
    """API endpoint for recruitment funnel analysis."""
    return recruitment_funnel_analysis()


@data_analytics_bp.route('/api/analytics/cost-per-hire')
@login_required
@rate_limit('api', {'requests': 50, 'window': 3600})
def api_cost_per_hire():
    """API endpoint for cost-per-hire calculation."""
    return cost_per_hire_calculation() 