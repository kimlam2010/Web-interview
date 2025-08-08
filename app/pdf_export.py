"""
PDF Export System for Mekong Recruitment System

This module provides PDF export functionality following AGENT_RULES_DEVELOPER:
- Professional PDF generation cho assessment results
- Executive decision reports
- Candidate evaluation summaries
- Customizable templates
- Multi-language support
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
import json
import os
from typing import Dict, Any, Optional

# Temporarily comment out WeasyPrint to avoid library issues
# from weasyprint import HTML, CSS

from . import db
from .models import db, Candidate, Position, Step1Question, Step2Question, Step3Question, InterviewEvaluation, AssessmentResult, User, ExecutiveDecision
from .decorators import hr_required
from app.utils import log_activity

pdf_export_bp = Blueprint('pdf_export', __name__)


@pdf_export_bp.route('/export/cto-questions/<int:candidate_id>')
@login_required
@hr_required
def export_cto_questions(candidate_id):
    """Export CTO questions for Step 3 interview."""
    try:
        candidate = Candidate.query.get_or_404(candidate_id)
        position = Position.query.get(candidate.position_id)
        
        # Get CTO questions (Step 3, CTO category)
        cto_questions = Step3Question.query.filter_by(
            step=3, category='CTO'
        ).limit(9).all()  # 9 questions for 45 minutes
        
        # Generate PDF
        pdf_content = render_template('pdf/cto_questions.html',
                                    candidate=candidate,
                                    position=position,
                                    questions=cto_questions,
                                    export_date=datetime.now())
        
        # Create PDF
        pdf_file = generate_pdf(pdf_content, f"CTO_Questions_{candidate.name.replace(' ', '_')}")
        
        log_activity(current_user.id, 'pdf_exported', 
                    f'Exported CTO questions for candidate {candidate_id}')
        
        return send_file(pdf_file, as_attachment=True, 
                        download_name=f"CTO_Questions_{candidate.name.replace(' ', '_')}.pdf")
    except Exception as e:
        log_activity(current_user.id, 'error', f'CTO PDF export error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})


@pdf_export_bp.route('/export/ceo-questions/<int:candidate_id>')
@login_required
@hr_required
def export_ceo_questions(candidate_id):
    """Export CEO questions for Step 3 interview."""
    try:
        candidate = Candidate.query.get_or_404(candidate_id)
        position = Position.query.get(candidate.position_id)
        
        # Get CEO questions (Step 3, CEO category)
        ceo_questions = Step3Question.query.filter_by(
            step=3, category='CEO'
        ).limit(6).all()  # 6 questions for 30 minutes
        
        # Generate PDF
        pdf_content = render_template('pdf/ceo_questions.html',
                                    candidate=candidate,
                                    position=position,
                                    questions=ceo_questions,
                                    export_date=datetime.now())
        
        # Create PDF
        pdf_file = generate_pdf(pdf_content, f"CEO_Questions_{candidate.name.replace(' ', '_')}")
        
        log_activity(current_user.id, 'pdf_exported', 
                    f'Exported CEO questions for candidate {candidate_id}')
        
        return send_file(pdf_file, as_attachment=True, 
                        download_name=f"CEO_Questions_{candidate.name.replace(' ', '_')}.pdf")
    except Exception as e:
        log_activity(current_user.id, 'error', f'CEO PDF export error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})


@pdf_export_bp.route('/export/complete-interview/<int:candidate_id>')
@login_required
@hr_required
def export_complete_interview(candidate_id):
    """Export complete interview package for Step 3."""
    try:
        candidate = Candidate.query.get_or_404(candidate_id)
        position = Position.query.get(candidate.position_id)
        
        # Get Step 1 and Step 2 results
        step1_result = AssessmentResult.query.filter_by(
            candidate_id=candidate_id, step=1
        ).first()
        
        step2_evaluations = InterviewEvaluation.query.filter_by(
            candidate_id=candidate_id
        ).all()
        
        # Get CTO and CEO questions
        cto_questions = Step3Question.query.filter_by(step=3, category='CTO').limit(9).all()
        ceo_questions = Step3Question.query.filter_by(step=3, category='CEO').limit(6).all()
        
        # Generate complete PDF
        pdf_content = render_template('pdf/complete_interview.html',
                                    candidate=candidate,
                                    position=position,
                                    step1_result=step1_result,
                                    step2_evaluations=step2_evaluations,
                                    cto_questions=cto_questions,
                                    ceo_questions=ceo_questions,
                                    export_date=datetime.now())
        
        # Create PDF
        pdf_file = generate_pdf(pdf_content, f"Complete_Interview_{candidate.name.replace(' ', '_')}")
        
        log_activity(current_user.id, 'pdf_exported', 
                    f'Exported complete interview package for candidate {candidate_id}')
        
        return send_file(pdf_file, as_attachment=True, 
                        download_name=f"Complete_Interview_{candidate.name.replace(' ', '_')}.pdf")
    except Exception as e:
        log_activity(current_user.id, 'error', f'Complete interview PDF export error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})


@pdf_export_bp.route('/export/scoring-rubric')
@login_required
@hr_required
def export_scoring_rubric():
    """Export scoring rubric for Step 3 interviews."""
    try:
        # Generate PDF
        pdf_content = render_template('pdf/scoring_rubric.html',
                                    export_date=datetime.now())
        
        # Create PDF
        pdf_file = generate_pdf(pdf_content, "Scoring_Rubric")
        
        log_activity(current_user.id, 'pdf_exported', 'Exported scoring rubric')
        
        return send_file(pdf_file, as_attachment=True, 
                        download_name="Scoring_Rubric.pdf")
    except Exception as e:
        log_activity(current_user.id, 'error', f'Scoring rubric PDF export error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})


@pdf_export_bp.route('/export/compensation-guide')
@login_required
@hr_required
def export_compensation_guide():
    """Export compensation guide for negotiations."""
    try:
        # Get all positions for salary ranges
        positions = Position.query.all()
        
        # Generate PDF
        pdf_content = render_template('pdf/compensation_guide.html',
                                    positions=positions,
                                    export_date=datetime.now())
        
        # Create PDF
        pdf_file = generate_pdf(pdf_content, "Compensation_Guide")
        
        log_activity(current_user.id, 'pdf_exported', 'Exported compensation guide')
        
        return send_file(pdf_file, as_attachment=True, 
                        download_name="Compensation_Guide.pdf")
    except Exception as e:
        log_activity(current_user.id, 'error', f'Compensation guide PDF export error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})


@pdf_export_bp.route('/export/candidate-report/<int:candidate_id>')
@login_required
@hr_required
def export_candidate_report(candidate_id):
    """Export comprehensive candidate report."""
    try:
        candidate = Candidate.query.get_or_404(candidate_id)
        position = Position.query.get(candidate.position_id)
        
        # Get all assessment results
        step1_result = AssessmentResult.query.filter_by(
            candidate_id=candidate_id, step=1
        ).first()
        
        step2_evaluations = InterviewEvaluation.query.filter_by(
            candidate_id=candidate_id
        ).all()
        
        # Calculate overall progress
        progress_data = calculate_candidate_progress(candidate_id)
        
        # Generate PDF
        pdf_content = render_template('pdf/candidate_report.html',
                                    candidate=candidate,
                                    position=position,
                                    step1_result=step1_result,
                                    step2_evaluations=step2_evaluations,
                                    progress_data=progress_data,
                                    export_date=datetime.now())
        
        # Create PDF
        pdf_file = generate_pdf(pdf_content, f"Candidate_Report_{candidate.name.replace(' ', '_')}")
        
        log_activity(current_user.id, 'pdf_exported', 
                    f'Exported candidate report for candidate {candidate_id}')
        
        return send_file(pdf_file, as_attachment=True, 
                        download_name=f"Candidate_Report_{candidate.name.replace(' ', '_')}.pdf")
    except Exception as e:
        log_activity(current_user.id, 'error', f'Candidate report PDF export error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})


# Helper functions

def generate_pdf(html_content, filename):
    """Generate PDF from HTML content."""
    try:
        # Configure fonts
        font_config = FontConfiguration()
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.close()
        
        # Generate PDF
        HTML(string=html_content).write_pdf(
            temp_file.name,
            font_config=font_config,
            presentational_hints=True
        )
        
        return temp_file.name
    except Exception as e:
        log_activity(current_user.id, 'error', f'PDF generation error: {str(e)}')
        raise e


def calculate_candidate_progress(candidate_id):
    """Calculate candidate progress through recruitment steps."""
    progress = {
        'step1_completed': False,
        'step1_score': 0,
        'step1_status': 'not_started',
        'step2_completed': False,
        'step2_score': 0,
        'step2_status': 'not_started',
        'step3_ready': False,
        'overall_progress': 0
    }
    
    # Step 1 progress
    step1_result = AssessmentResult.query.filter_by(
        candidate_id=candidate_id, step=1
    ).first()
    
    if step1_result:
        progress['step1_completed'] = True
        progress['step1_score'] = step1_result.score
        progress['step1_status'] = step1_result.status
        
        if step1_result.status in ['passed', 'manual_review']:
            progress['overall_progress'] += 33
    
    # Step 2 progress
    step2_evaluations = InterviewEvaluation.query.filter_by(
        candidate_id=candidate_id
    ).all()
    
    if step2_evaluations:
        completed_evaluations = [e for e in step2_evaluations if e.status == 'completed']
        if completed_evaluations:
            progress['step2_completed'] = True
            progress['step2_score'] = sum(e.overall_score for e in completed_evaluations) / len(completed_evaluations)
            progress['step2_status'] = 'completed'
            progress['overall_progress'] += 33
    
    # Step 3 readiness
    if progress['step1_completed'] and progress['step1_status'] in ['passed', 'manual_review']:
        if progress['step2_completed'] and progress['step2_score'] >= 7:
            progress['step3_ready'] = True
            progress['overall_progress'] += 34
    
    return progress


def cleanup_temp_files():
    """Clean up temporary PDF files."""
    try:
        temp_dir = tempfile.gettempdir()
        for filename in os.listdir(temp_dir):
            if filename.startswith('temp_') and filename.endswith('.pdf'):
                file_path = os.path.join(temp_dir, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
    except Exception as e:
        log_activity(current_user.id, 'error', f'Temp file cleanup error: {str(e)}') 