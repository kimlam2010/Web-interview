# 🎯 WORKFLOW & ROLES MANAGEMENT - DETAILED SPECIFICATION

## **👥 USER ROLES & RESPONSIBILITIES**

### **🔐 ADMIN ROLE (System Administrator)**

#### **Core Responsibilities:**
- ✅ **Question Bank Management:** Full CRUD operations
- ✅ **User Management:** Create, edit, delete all user accounts
- ✅ **System Configuration:** Link expiration, scoring thresholds, email templates
- ✅ **Data Management:** Database backup, export, analytics
- ✅ **Security Management:** Access control, audit logs, system monitoring
- ✅ **Approval Override:** Can override any decision at any step
- ✅ **Credential Management:** Manage candidate temporary credentials

#### **Specific Permissions:**
```python
ADMIN_PERMISSIONS = {
    # Question Management
    'create_questions': True,
    'edit_questions': True,
    'delete_questions': True,
    'bulk_import_questions': True,
    'backup_questions': True,
    
    # User Management
    'create_users': True,
    'edit_users': True,
    'deactivate_users': True,
    'reset_passwords': True,
    'assign_roles': True,
    
    # System Configuration
    'modify_settings': True,
    'configure_links': True,
    'set_thresholds': True,
    'manage_email_templates': True,
    
    # Data & Analytics
    'export_all_data': True,
    'view_audit_logs': True,
    'system_analytics': True,
    'database_operations': True,
    
    # Candidate Management
    'view_all_candidates': True,
    'delete_candidates': True,
    'extend_any_link': True,
    'override_decisions': True
}
```

---

### **👩‍💼 HR ROLE (Human Resources)**

#### **Core Responsibilities:**
- ✅ **Candidate Management:** Add, edit, track candidates
- ✅ **Link Management:** Generate, send, extend assessment links
- ✅ **Interview Coordination:** Schedule Step 2 and Step 3 interviews
- ✅ **Results Review:** Evaluate assessment results, make recommendations
- ✅ **Communication:** Email candidates, manage correspondence

#### **Specific Permissions:**
```python
HR_PERMISSIONS = {
    # Candidate Management
    'add_candidates': True,
    'edit_candidates': True,
    'view_all_candidates': True,
    'upload_cv_files': True,
    'track_progress': True,
    
    # Link Management
    'generate_step1_links': True,
    'generate_step2_links': True,
    'extend_own_links': True,      # Can extend links for their candidates
    'resend_links': True,
    'view_link_status': True,
    
    # Interview Management
    'schedule_step2': True,
    'select_step2_questions': True,
    'schedule_step3': True,
    'export_step3_questions': True,
    
    # Communication
    'send_emails': True,
    'use_email_templates': True,
    'view_email_history': True,
    
    # Reporting
    'view_reports': True,
    'export_candidate_data': True,
    'generate_summaries': True,
    
    # Limitations
    'manage_questions': False,     # Cannot modify question bank
    'delete_candidates': False,    # Cannot delete candidates
    'system_config': False,       # Cannot modify system settings
    'create_users': False         # Cannot create new users
}
```

---

### **👨‍💼 INTERVIEWER ROLE (Technical Interviewers)**

#### **Core Responsibilities:**
- ✅ **Step 2 Evaluation:** Conduct and score technical interviews
- ✅ **Question Selection:** Choose appropriate questions for interviews
- ✅ **Candidate Assessment:** Provide detailed evaluation and recommendations
- ✅ **Notes & Feedback:** Document interview insights and candidate performance
- ✅ **Step 2 Approval:** Technical approval to proceed to Step 3
- ✅ **Technical Recommendation:** Provide technical hiring recommendation

---

### **👔 EXECUTIVE ROLE (CTO + CEO)**

#### **Core Responsibilities:**
- ✅ **Step 3 Final Interview:** Conduct final assessment interviews
- ✅ **Final Hiring Decision:** Make ultimate hiring decisions
- ✅ **Compensation Approval:** Approve salary and benefits packages
- ✅ **Strategic Oversight:** High-level recruitment strategy
- ✅ **Technical Override:** Can override technical recommendations if needed

#### **Specific Permissions:**
```python
INTERVIEWER_PERMISSIONS = {
    # Interview Management
    'view_assigned_candidates': True,
    'conduct_step2_interviews': True,
    'score_step2_responses': True,
    'select_interview_questions': True,
    
    # Evaluation
    'provide_recommendations': True,
    'add_interview_notes': True,
    'rate_candidates': True,
    'submit_evaluations': True,
    
    # Question Access
    'view_step2_questions': True,
    'suggest_new_questions': True,  # Can suggest but not add directly
    'report_question_issues': True,
    
    # Limited Access
    'view_own_interviews_only': True,
    'no_candidate_management': True,
    'no_link_generation': True,
    'no_step1_access': True,
    'no_step3_access': True
}
```

---

## **🔑 TEMPORARY CREDENTIALS MANAGEMENT**

### **🎯 Credential Generation Workflow**

#### **When Credentials Are Created:**
- ✅ **Automatic:** Generated when HR creates new candidate
- ✅ **Immediate:** Created with Step 1 assessment link
- ✅ **Temporary:** Expires with assessment link
- ✅ **Single-use:** One candidate per credential set

#### **Credential Format:**
```python
def generate_candidate_credentials(candidate):
    """
    Generate temporary login credentials for candidate
    """
    # Username: first_name + last 4 digits of phone
    username = f"{candidate.first_name.lower()}_{candidate.phone[-4:]}"
    
    # Password: 8-character secure password
    password = generate_secure_password(
        length=8,
        include_uppercase=True,
        include_lowercase=True, 
        include_numbers=True,
        exclude_ambiguous=True  # No 0, O, 1, l, I
    )
    
    # Expiration matches assessment link
    expires_at = datetime.now() + timedelta(days=7)
    
    return {
        'username': username,
        'password': password,
        'expires_at': expires_at,
        'candidate_id': candidate.id,
        'is_temporary': True,
        'max_attempts': 3,
        'session_timeout': 60  # minutes
    }
```

### **📧 Credential Delivery**

#### **Email Template:**
```html
Subject: Your Assessment Credentials - Mekong Technology

Dear {{ candidate.full_name }},

Thank you for your interest in the {{ position }} position at Mekong Technology.

Your online assessment is ready. Please use the following credentials:

🔗 Assessment Link: {{ assessment_url }}
👤 Username: {{ username }}
🔐 Password: {{ password }}

⏰ This link expires on: {{ expiry_date }} at {{ expiry_time }}

Important Notes:
- Complete the assessment within 30 minutes once started
- Ensure stable internet connection
- Use a desktop/laptop for best experience
- Contact HR if you encounter any issues

Best regards,
HR Team - Mekong Technology
```

### **🔒 Security Features**

#### **Access Control:**
- ✅ **Time-limited:** Credentials expire with link
- ✅ **Attempt Limiting:** Max 3 failed login attempts
- ✅ **Session Timeout:** 60-minute active session
- ✅ **IP Tracking:** Monitor login locations
- ✅ **Auto-logout:** 30 minutes of inactivity

#### **Monitoring:**
```python
def track_candidate_access(username, ip_address, user_agent):
    """
    Track candidate login attempts and access patterns
    """
    access_log = CandidateAccessLog(
        username=username,
        ip_address=ip_address,
        user_agent=user_agent,
        timestamp=datetime.now(),
        action='login_attempt'
    )
    
    # Check for suspicious activity
    recent_attempts = get_recent_login_attempts(username, hours=1)
    if len(recent_attempts) > 5:
        flag_suspicious_activity(username, ip_address)
    
    db.session.add(access_log)
    db.session.commit()
```

---

## **⚡ APPROVAL WORKFLOW SYSTEM**

### **📊 Step 1: Auto-Approval Logic**

#### **Automatic Approval Thresholds:**
```python
STEP1_APPROVAL_RULES = {
    'auto_approve': 70,     # >= 70% automatically approved
    'manual_review': [50, 69],  # 50-69% requires HR review
    'auto_reject': 49       # < 50% automatically rejected
}

def process_step1_results(candidate, assessment_results):
    """
    Process Step 1 results with automatic approval logic
    """
    total_score = assessment_results['percentage']
    
    if total_score >= 70:
        # Auto-approve and generate Step 2 link
        approve_step1(candidate, auto_approved=True)
        generate_step2_credentials(candidate)
        send_step1_approved_email(candidate)
        
    elif 50 <= total_score <= 69:
        # Flag for HR manual review
        flag_for_manual_review(candidate, assessment_results)
        send_manual_review_email(candidate)
        notify_hr_manual_review(candidate)
        
    else:  # < 50%
        # Auto-reject
        reject_step1(candidate, auto_rejected=True)
        send_rejection_email(candidate)
        update_candidate_status(candidate, 'rejected_step1')
```

#### **HR Manual Review Process:**
```python
def hr_manual_review_step1(hr_user, candidate_id, decision, notes):
    """
    HR manual review for borderline Step 1 scores
    """
    candidate = Candidate.query.get(candidate_id)
    
    # Verify HR has permission for manual review
    if not hr_user.can('manual_review_step1'):
        raise PermissionError("Insufficient permissions")
    
    # Log the manual review decision
    review_log = ManualReviewLog(
        candidate_id=candidate_id,
        reviewer_id=hr_user.id,
        step=1,
        original_score=candidate.step1_score,
        decision=decision,  # 'approve' or 'reject'
        notes=notes,
        reviewed_at=datetime.now()
    )
    
    if decision == 'approve':
        approve_step1(candidate, auto_approved=False, reviewed_by=hr_user.id)
        generate_step2_credentials(candidate)
        send_step1_approved_email(candidate)
    else:
        reject_step1(candidate, auto_rejected=False, reviewed_by=hr_user.id)
        send_rejection_email(candidate)
    
    db.session.add(review_log)
    db.session.commit()
```

### **🎯 Step 2: Interviewer Approval**

#### **Technical Interview Approval:**
```python
def interviewer_approve_step2(interviewer, candidate_id, scores, recommendation, notes):
    """
    Interviewer approval process for Step 2
    """
    candidate = Candidate.query.get(candidate_id)
    
    # Calculate overall Step 2 score
    overall_score = calculate_step2_overall_score(scores)
    
    # Create evaluation record
    evaluation = Step2Evaluation(
        candidate_id=candidate_id,
        interviewer_id=interviewer.id,
        scores=json.dumps(scores),
        overall_score=overall_score,
        recommendation=recommendation,  # 'approve', 'reject', 'borderline'
        notes=notes,
        evaluated_at=datetime.now()
    )
    
    # Approval logic
    min_score = current_app.config['APPROVAL_WORKFLOW']['step2_min_score_to_pass']
    
    if overall_score >= min_score and recommendation in ['approve', 'borderline']:
        approve_step2(candidate, interviewer.id)
        schedule_step3_notification(candidate)
        send_step2_approved_email(candidate)
    else:
        reject_step2(candidate, interviewer.id)
        send_step2_rejection_email(candidate)
    
    db.session.add(evaluation)
    db.session.commit()
```

### **🏆 Step 3: Executive Final Approval**

#### **CTO + CEO Combined Decision:**
```python
def process_step3_final_decision(cto_evaluation, ceo_evaluation, candidate_id):
    """
    Process final hiring decision from CTO and CEO
    """
    candidate = Candidate.query.get(candidate_id)
    
    # Calculate weighted final score
    cto_weight = current_app.config['APPROVAL_WORKFLOW']['step3_cto_weight']
    ceo_weight = current_app.config['APPROVAL_WORKFLOW']['step3_ceo_weight']
    
    final_score = (cto_evaluation['score'] * cto_weight + 
                  ceo_evaluation['score'] * ceo_weight)
    
    # Both executives must approve
    require_both = current_app.config['APPROVAL_WORKFLOW']['step3_require_both_cto_ceo']
    
    if require_both:
        final_decision = (cto_evaluation['decision'] == 'approve' and 
                         ceo_evaluation['decision'] == 'approve')
    else:
        final_decision = (cto_evaluation['decision'] == 'approve' or 
                         ceo_evaluation['decision'] == 'approve')
    
    # Create final evaluation record
    final_evaluation = Step3FinalEvaluation(
        candidate_id=candidate_id,
        cto_score=cto_evaluation['score'],
        ceo_score=ceo_evaluation['score'],
        final_score=final_score,
        cto_decision=cto_evaluation['decision'],
        ceo_decision=ceo_evaluation['decision'],
        final_decision='hired' if final_decision else 'rejected',
        salary_offered=ceo_evaluation.get('salary_offered'),
        start_date=ceo_evaluation.get('start_date'),
        notes=f"CTO: {cto_evaluation['notes']} | CEO: {ceo_evaluation['notes']}",
        decided_at=datetime.now()
    )
    
    # Update candidate status
    candidate.status = 'hired' if final_decision else 'rejected_final'
    candidate.final_score = final_score
    
    # Send final decision email
    send_final_decision_email(candidate, final_evaluation)
    
    db.session.add(final_evaluation)
    db.session.commit()
```

---

## **🔗 LINK MANAGEMENT WORKFLOW**

### **📝 Candidate Creation & Link Generation**

#### **Who Can Create Candidates:**
- ✅ **HR Users:** Primary responsibility
- ✅ **Admin Users:** Full access
- ❌ **Interviewer Users:** No access

#### **Link Generation Process:**
```python
def create_candidate_with_links(hr_user, candidate_data):
    """
    Complete workflow for candidate creation and link generation
    """
    # Step 1: Validate HR permissions
    if not hr_user.can('add_candidates'):
        raise PermissionError("Insufficient permissions")
    
    # Step 2: Create candidate record
    candidate = Candidate(
        full_name=candidate_data['full_name'],
        email=candidate_data['email'],
        phone=candidate_data['phone'],
        position=candidate_data['position'],
        hr_user_id=hr_user.id,
        status='new'
    )
    
    # Step 3: Generate Step 1 assessment link
    step1_token = generate_secure_token(candidate.id, step=1)
    step1_link = AssessmentLink(
        candidate_id=candidate.id,
        step=1,
        token=step1_token,
        expires_at=datetime.now() + timedelta(days=7),  # Default 7 days
        created_by=hr_user.id,
        is_active=True,
        use_count=0
    )
    
    # Step 4: Save to database
    db.session.add(candidate)
    db.session.add(step1_link)
    db.session.commit()
    
    # Step 5: Send invitation email
    send_step1_invitation(candidate, step1_link)
    
    return candidate, step1_link
```

---

### **⏰ Link Expiration Management**

#### **Default Expiration Rules:**
```python
LINK_EXPIRATION_RULES = {
    'step1': {
        'default_days': 7,
        'min_days': 1,
        'max_days': 30,
        'weekend_auto_extend': True,
        'reminder_schedule': [24, 3]  # Hours before expiry
    },
    'step2': {
        'default_days': 3,
        'min_days': 1,
        'max_days': 14,
        'weekend_auto_extend': True,
        'reminder_schedule': [24, 6]  # Hours before expiry
    }
}
```

#### **Who Can Extend Links:**
- ✅ **Admin:** Can extend any link, any duration
- ✅ **HR:** Can extend links for their candidates within limits
- ❌ **Interviewer:** No link management access

#### **Extension Process:**
```python
def extend_link(user, link_id, new_expiry_date):
    """
    Extend assessment link expiration
    """
    link = AssessmentLink.query.get(link_id)
    
    # Permission check
    if user.role == 'admin':
        # Admin can extend any link
        pass
    elif user.role == 'hr':
        # HR can only extend their own candidates' links
        if link.candidate.hr_user_id != user.id:
            raise PermissionError("Can only extend your own candidates' links")
        
        # Check extension limits
        max_extension = get_max_extension_for_step(link.step)
        if new_expiry_date > (link.created_at + timedelta(days=max_extension)):
            raise ValidationError(f"Cannot extend beyond {max_extension} days")
    else:
        raise PermissionError("Insufficient permissions")
    
    # Update link expiration
    link.expires_at = new_expiry_date
    link.extended_by = user.id
    link.extended_at = datetime.now()
    
    # Log the extension
    log_link_extension(link, user, new_expiry_date)
    
    db.session.commit()
    
    # Notify candidate of extension
    send_extension_notification(link.candidate, link)
```

---

### **📧 Automated Reminder System**

#### **Reminder Schedule:**
```python
def send_automated_reminders():
    """
    Daily cron job to send assessment reminders
    """
    current_time = datetime.now()
    
    # Get links expiring in 24 hours
    links_24h = AssessmentLink.query.filter(
        AssessmentLink.expires_at.between(
            current_time + timedelta(hours=23),
            current_time + timedelta(hours=25)
        ),
        AssessmentLink.is_active == True,
        AssessmentLink.reminder_24h_sent == False
    ).all()
    
    for link in links_24h:
        send_reminder_email(link.candidate, link, hours_remaining=24)
        link.reminder_24h_sent = True
    
    # Get links expiring in 3 hours (Step 1) or 6 hours (Step 2)
    for link in get_urgent_expiring_links():
        hours_remaining = (link.expires_at - current_time).total_seconds() / 3600
        send_urgent_reminder(link.candidate, link, hours_remaining)
        link.urgent_reminder_sent = True
    
    # Handle expired links
    expired_links = AssessmentLink.query.filter(
        AssessmentLink.expires_at < current_time,
        AssessmentLink.is_active == True
    ).all()
    
    for link in expired_links:
        handle_expired_link(link)
    
    db.session.commit()

def handle_expired_link(link):
    """
    Handle expired assessment links
    """
    # Deactivate the link
    link.is_active = False
    link.expired_at = datetime.now()
    
    # Notify HR user
    notify_hr_link_expired(link)
    
    # Auto-generate new link if configured
    if should_auto_regenerate_link(link):
        new_link = create_new_assessment_link(link.candidate, link.step)
        send_new_link_notification(link.candidate, new_link)
```

---

## **❓ QUESTION BANK MANAGEMENT**

### **🔧 Admin Question Management Interface**

#### **Web Interface for Question Management:**
```html
<!-- Admin Question Management Dashboard -->
<div class="question-management-dashboard">
    <h2>Question Bank Management</h2>
    
    <!-- Quick Stats -->
    <div class="stats-grid">
        <div class="stat-card">
            <h3>Total Questions</h3>
            <span class="number">{{ total_questions }}</span>
        </div>
        <div class="stat-card">
            <h3>Step 1 IQ</h3>
            <span class="number">{{ iq_questions_count }}</span>
        </div>
        <div class="stat-card">
            <h3>Step 1 Technical</h3>
            <span class="number">{{ technical_questions_count }}</span>
        </div>
        <div class="stat-card">
            <h3>Step 2 Questions</h3>
            <span class="number">{{ step2_questions_count }}</span>
        </div>
    </div>
    
    <!-- Actions -->
    <div class="action-buttons">
        <button onclick="showAddQuestionModal()" class="btn btn-primary">
            Add New Question
        </button>
        <button onclick="showBulkImportModal()" class="btn btn-secondary">
            Bulk Import
        </button>
        <button onclick="exportQuestions()" class="btn btn-info">
            Export Questions
        </button>
        <button onclick="backupQuestions()" class="btn btn-warning">
            Backup Database
        </button>
    </div>
    
    <!-- Question List with Filters -->
    <div class="question-filters">
        <select id="step-filter">
            <option value="">All Steps</option>
            <option value="step1_iq">Step 1 - IQ</option>
            <option value="step1_technical">Step 1 - Technical</option>
            <option value="step2_lead">Step 2 - Lead Developer</option>
            <option value="step2_engineer">Step 2 - Software Engineer</option>
            <option value="step3_cto">Step 3 - CTO</option>
            <option value="step3_ceo">Step 3 - CEO</option>
        </select>
        
        <select id="category-filter">
            <option value="">All Categories</option>
            <option value="programming">Programming</option>
            <option value="iot">IoT/Industrial</option>
            <option value="architecture">System Architecture</option>
            <option value="leadership">Leadership</option>
        </select>
        
        <input type="text" id="search-questions" placeholder="Search questions...">
    </div>
    
    <!-- Question List Table -->
    <table class="questions-table">
        <thead>
            <tr>
                <th>ID</th>
                <th>Step</th>
                <th>Category</th>
                <th>Question Preview</th>
                <th>Difficulty</th>
                <th>Points</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody id="questions-list">
            <!-- Questions loaded dynamically -->
        </tbody>
    </table>
</div>
```

#### **Bulk Import Functionality:**
```python
def bulk_import_questions(file_path, import_format, user):
    """
    Admin bulk import questions from various formats
    """
    # Permission check
    if not user.can('bulk_import_questions'):
        raise PermissionError("Insufficient permissions")
    
    # Backup current questions before import
    if current_app.config['QUESTION_MANAGEMENT']['backup_before_update']:
        backup_questions_database(user.id)
    
    try:
        if import_format == 'json':
            questions_data = import_from_json(file_path)
        elif import_format == 'excel':
            questions_data = import_from_excel(file_path)
        elif import_format == 'csv':
            questions_data = import_from_csv(file_path)
        else:
            raise ValueError("Unsupported import format")
        
        # Validate questions
        validation_results = validate_questions_batch(questions_data)
        if validation_results['errors']:
            return {
                'success': False,
                'errors': validation_results['errors'],
                'imported': 0
            }
        
        # Import valid questions
        imported_count = 0
        for question_data in questions_data:
            question = create_question_from_data(question_data)
            db.session.add(question)
            imported_count += 1
        
        db.session.commit()
        
        # Log the import
        log_question_import(user.id, imported_count, import_format)
        
        return {
            'success': True,
            'imported': imported_count,
            'errors': []
        }
        
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'errors': [str(e)],
            'imported': 0
        }
```

---

### **👩‍💼 HR Question Selection Interface**

#### **Step 2 Question Selection for HR:**
```html
<!-- HR Question Selection for Step 2 Interview -->
<div class="step2-question-selection">
    <h3>Select Technical Interview Questions</h3>
    
    <div class="candidate-info">
        <h4>Candidate: {{ candidate.full_name }}</h4>
        <p>Position: {{ candidate.position }}</p>
        <p>Step 1 Score: {{ candidate.step1_score }}%</p>
    </div>
    
    <!-- Question Filters -->
    <div class="question-filters">
        <label>
            <input type="radio" name="position-focus" value="lead" 
                   {% if candidate.position == 'Lead Software Developer' %}checked{% endif %}>
            Lead Developer Focus
        </label>
        <label>
            <input type="radio" name="position-focus" value="engineer"
                   {% if candidate.position == 'Software Engineer' %}checked{% endif %}>
            Software Engineer Focus
        </label>
        
        <select id="difficulty-filter">
            <option value="">All Difficulties</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
        </select>
        
        <select id="time-filter">
            <option value="">Any Duration</option>
            <option value="5">5 minutes</option>
            <option value="10">10 minutes</option>
            <option value="15">15 minutes</option>
            <option value="20">20 minutes</option>
        </select>
    </div>
    
    <!-- Question Categories -->
    <div class="question-categories">
        <div class="category-section">
            <h4>System Architecture (Select 3-4 questions)</h4>
            <div class="questions-grid" data-category="architecture">
                <!-- Questions loaded dynamically -->
            </div>
            <div class="selected-count">Selected: <span>0</span>/4</div>
        </div>
        
        <div class="category-section">
            <h4>Programming & Development (Select 3-4 questions)</h4>
            <div class="questions-grid" data-category="programming">
                <!-- Questions loaded dynamically -->
            </div>
            <div class="selected-count">Selected: <span>0</span>/4</div>
        </div>
        
        <div class="category-section">
            <h4>Industrial IoT & Technology (Select 3-4 questions)</h4>
            <div class="questions-grid" data-category="iot">
                <!-- Questions loaded dynamically -->
            </div>
            <div class="selected-count">Selected: <span>0</span>/4</div>
        </div>
    </div>
    
    <!-- Interview Schedule -->
    <div class="interview-schedule">
        <h4>Schedule Technical Interview</h4>
        <div class="schedule-form">
            <label>Interview Date:
                <input type="datetime-local" name="interview_date" required>
            </label>
            <label>Interviewer:
                <select name="interviewer_id">
                    {% for interviewer in available_interviewers %}
                    <option value="{{ interviewer.id }}">{{ interviewer.full_name }}</option>
                    {% endfor %}
                </select>
            </label>
            <label>Location/Platform:
                <input type="text" name="location" placeholder="e.g., Google Meet, Office Room 302">
            </label>
        </div>
    </div>
    
    <!-- Actions -->
    <div class="actions">
        <button onclick="previewInterview()" class="btn btn-info">
            Preview Interview
        </button>
        <button onclick="scheduleInterview()" class="btn btn-primary">
            Schedule Interview
        </button>
        <button onclick="generateStep2Link()" class="btn btn-success">
            Generate Interview Link
        </button>
    </div>
</div>
```

---

## **📊 WORKFLOW AUTOMATION**

### **🤖 Automated Processes**

#### **Daily Automated Tasks:**
```python
# scheduled_tasks.py - Cron jobs for automation

@app.cli.command()
def daily_maintenance():
    """Daily maintenance tasks"""
    
    # 1. Send assessment reminders
    send_assessment_reminders()
    
    # 2. Handle expired links
    process_expired_links()
    
    # 3. Auto-extend weekend expiries
    auto_extend_weekend_links()
    
    # 4. Generate daily reports
    generate_daily_reports()
    
    # 5. Cleanup old files
    cleanup_old_exports()
    
    # 6. Database optimization
    optimize_database()

def send_assessment_reminders():
    """Send automated reminders based on schedule"""
    
    # 24-hour reminders
    links_24h = get_links_expiring_in_hours(24)
    for link in links_24h:
        if not link.reminder_24h_sent:
            send_reminder_email(link, 24)
            link.reminder_24h_sent = True
    
    # 3-hour urgent reminders for Step 1
    step1_links_3h = get_step1_links_expiring_in_hours(3)
    for link in step1_links_3h:
        if not link.urgent_reminder_sent:
            send_urgent_reminder(link, 3)
            link.urgent_reminder_sent = True
    
    # 6-hour reminders for Step 2
    step2_links_6h = get_step2_links_expiring_in_hours(6)
    for link in step2_links_6h:
        if not link.urgent_reminder_sent:
            send_urgent_reminder(link, 6)
            link.urgent_reminder_sent = True
    
    db.session.commit()

def auto_extend_weekend_links():
    """Auto-extend links expiring on weekends"""
    
    if not current_app.config['REMINDER_SCHEDULE']['weekend_auto_extend']:
        return
    
    weekend_expiring_links = get_weekend_expiring_links()
    
    for link in weekend_expiring_links:
        # Extend to next Monday 9 AM
        next_monday = get_next_monday_9am(link.expires_at)
        link.expires_at = next_monday
        link.auto_extended = True
        link.auto_extend_reason = "Weekend auto-extension"
        
        # Notify candidate and HR
        send_auto_extension_notification(link)
    
    db.session.commit()
```

---

### **📈 Analytics & Reporting**

#### **HR Dashboard Analytics:**
```python
def get_hr_dashboard_data(hr_user):
    """Generate dashboard data for HR users"""
    
    # Get candidates managed by this HR user
    candidates = Candidate.query.filter_by(hr_user_id=hr_user.id).all()
    
    dashboard_data = {
        'total_candidates': len(candidates),
        'active_step1': len([c for c in candidates if c.status == 'step1']),
        'active_step2': len([c for c in candidates if c.status == 'step2']),
        'ready_for_step3': len([c for c in candidates if c.status == 'step3']),
        'hired': len([c for c in candidates if c.status == 'hired']),
        'rejected': len([c for c in candidates if c.status == 'rejected']),
        
        # Link statistics
        'active_links': get_active_links_count(hr_user.id),
        'expiring_soon': get_expiring_soon_count(hr_user.id),
        'expired_links': get_expired_links_count(hr_user.id),
        
        # Performance metrics
        'avg_step1_score': calculate_avg_step1_score(candidates),
        'pass_rate_step1': calculate_step1_pass_rate(candidates),
        'avg_step2_score': calculate_avg_step2_score(candidates),
        
        # Recent activity
        'recent_completions': get_recent_completions(hr_user.id, days=7),
        'upcoming_interviews': get_upcoming_interviews(hr_user.id),
        
        # Time metrics
        'avg_time_to_complete_step1': calculate_avg_completion_time(candidates, 'step1'),
        'avg_time_step1_to_step2': calculate_avg_progression_time(candidates, 'step1', 'step2')
    }
    
    return dashboard_data
```

---

## **🔐 SECURITY & AUDIT**

### **🛡️ Security Measures**

#### **Link Security Implementation:**
```python
def generate_secure_token(candidate_id, step):
    """Generate secure assessment token"""
    
    token_data = {
        'candidate_id': candidate_id,
        'step': step,
        'timestamp': int(time.time()),
        'random': secrets.token_urlsafe(16)
    }
    
    # Create hash
    token_string = f"{token_data['candidate_id']}_{token_data['step']}_{token_data['timestamp']}_{token_data['random']}"
    token_hash = hashlib.sha256(token_string.encode()).hexdigest()
    
    return token_hash[:32]  # 32 character token

def validate_assessment_token(token, candidate_id, step):
    """Validate assessment token security"""
    
    link = AssessmentLink.query.filter_by(
        token=token,
        candidate_id=candidate_id,
        step=step,
        is_active=True
    ).first()
    
    if not link:
        return False, "Invalid or expired link"
    
    # Check expiration
    if link.expires_at < datetime.now():
        link.is_active = False
        db.session.commit()
        return False, "Link has expired"
    
    # Check one-time use
    if current_app.config['LINK_SECURITY']['one_time_use'] and link.use_count > 0:
        return False, "Link has already been used"
    
    # Optional: Check IP restriction
    if current_app.config['LINK_SECURITY']['ip_restriction']:
        if not validate_ip_restriction(link, request.remote_addr):
            return False, "Access denied from this IP address"
    
    return True, "Valid token"
```

#### **Audit Logging:**
```python
def log_user_action(user, action, details, ip_address=None):
    """Log user actions for audit trail"""
    
    audit_log = AuditLog(
        user_id=user.id,
        action=action,
        details=json.dumps(details),
        ip_address=ip_address or request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        timestamp=datetime.now()
    )
    
    db.session.add(audit_log)
    db.session.commit()

# Example usage:
# log_user_action(current_user, 'link_extended', {
#     'candidate_id': candidate.id,
#     'link_id': link.id,
#     'old_expiry': old_expiry.isoformat(),
#     'new_expiry': new_expiry.isoformat()
# })
```

---

## **📋 IMPLEMENTATION CHECKLIST**

### **✅ Phase 1: Core Workflow (Week 1)**
- ✅ **User roles & permissions system**
- ✅ **Candidate creation & link generation**
- ✅ **Basic link expiration management**
- ✅ **HR question selection interface**
- ✅ **Email notification system**

### **✅ Phase 2: Advanced Features (Week 2)**
- ✅ **Automated reminder system**
- ✅ **Weekend auto-extension**
- ✅ **Admin question management interface**
- ✅ **Bulk import functionality**
- ✅ **Analytics dashboard**

### **✅ Phase 3: Security & Optimization (Week 3)**
- ✅ **Enhanced link security**
- ✅ **Audit logging system**
- ✅ **Performance optimization**
- ✅ **Database backup automation**
- ✅ **System monitoring**

### **✅ Phase 4: Testing & Deployment (Week 4)**
- ✅ **Comprehensive testing**
- ✅ **User acceptance testing**
- ✅ **Production deployment**
- ✅ **User training**
- ✅ **Documentation finalization**

---

*This document provides the complete workflow and roles management specification for the Mekong Recruitment System.* 🚀