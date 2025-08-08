"""
Candidate Blueprint for Mekong Recruitment System
"""

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required

candidate_bp = Blueprint('candidate', __name__)

@candidate_bp.route('/profile')
@login_required
def profile():
    """Candidate profile page."""
    return render_template('candidate/profile.html')

@candidate_bp.route('/assessment')
@login_required
def assessment():
    """Assessment page."""
    return render_template('candidate/assessment.html') 