# 🎯 POSITION & QUESTION MANAGEMENT SYSTEM

## **📋 1. POSITION MANAGEMENT**

### **A. Tạo Vị Trí Mới (Admin/HR)**

#### **Position Creation Form:**
```html
<!-- Admin Interface: Create New Position -->
<div class="position-form">
  <h3>Create New Position</h3>
  
  <form id="positionForm">
    <div class="form-group">
      <label>Position Title:</label>
      <input type="text" name="title" required placeholder="e.g., Lead Software Developer">
    </div>
    
    <div class="form-group">
      <label>Department:</label>
      <select name="department" required>
        <option value="engineering">Engineering</option>
        <option value="product">Product</option>
        <option value="design">Design</option>
        <option value="marketing">Marketing</option>
      </select>
    </div>
    
    <div class="form-group">
      <label>Level:</label>
      <select name="level" required>
        <option value="junior">Junior (0-2 years)</option>
        <option value="mid">Mid-level (3-5 years)</option>
        <option value="senior">Senior (5-8 years)</option>
        <option value="lead">Lead (8+ years)</option>
      </select>
    </div>
    
    <div class="form-group">
      <label>Salary Range (VND/month):</label>
      <input type="number" name="salary_min" placeholder="Min salary">
      <input type="number" name="salary_max" placeholder="Max salary">
    </div>
    
    <div class="form-group">
      <label>Job Description:</label>
      <textarea name="description" rows="5" required>
        - Technical skills required
        - Experience level
        - Responsibilities
        - Team size
        - Project scope
      </textarea>
    </div>
    
    <div class="form-group">
      <label>Required Skills:</label>
      <div class="skills-tags">
        <input type="text" name="skills" placeholder="Python, React, AWS...">
        <small>Separate skills with commas</small>
      </div>
    </div>
    
    <div class="form-group">
      <label>Hiring Timeline:</label>
      <input type="date" name="target_start_date">
      <input type="number" name="hiring_urgency" min="1" max="5" placeholder="Urgency (1-5)">
    </div>
    
    <button type="submit">Create Position</button>
  </form>
</div>
```

#### **Position Database Model:**
```python
# database/models.py
class Position(db.Model):
    __tablename__ = 'positions'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    level = db.Column(db.String(20), nullable=False)  # junior, mid, senior, lead
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    description = db.Column(db.Text, nullable=False)
    required_skills = db.Column(db.Text)  # JSON array of skills
    target_start_date = db.Column(db.Date)
    hiring_urgency = db.Column(db.Integer, default=3)  # 1-5 scale
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    candidates = db.relationship('Candidate', backref='position', lazy=True)
    step1_questions = db.relationship('PositionStep1Questions', backref='position', lazy=True)
    step2_questions = db.relationship('PositionStep2Questions', backref='position', lazy=True)
    step3_questions = db.relationship('PositionStep3Questions', backref='position', lazy=True)
```

### **B. Position List Management:**

#### **Admin Dashboard - Position Management:**
```html
<!-- Position Management Dashboard -->
<div class="position-dashboard">
  <div class="header">
    <h2>Position Management</h2>
    <button onclick="createPosition()">+ Add New Position</button>
  </div>
  
  <div class="position-filters">
    <select id="departmentFilter">
      <option value="">All Departments</option>
      <option value="engineering">Engineering</option>
      <option value="product">Product</option>
    </select>
    
    <select id="levelFilter">
      <option value="">All Levels</option>
      <option value="junior">Junior</option>
      <option value="mid">Mid-level</option>
      <option value="senior">Senior</option>
      <option value="lead">Lead</option>
    </select>
    
    <select id="statusFilter">
      <option value="">All Status</option>
      <option value="active">Active</option>
      <option value="paused">Paused</option>
      <option value="closed">Closed</option>
    </select>
  </div>
  
  <div class="position-list">
    <table>
      <thead>
        <tr>
          <th>Position</th>
          <th>Department</th>
          <th>Level</th>
          <th>Salary Range</th>
          <th>Candidates</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Lead Software Developer</td>
          <td>Engineering</td>
          <td>Lead</td>
          <td>10M - 15M VND</td>
          <td>5 candidates</td>
          <td><span class="status active">Active</span></td>
          <td>
            <button onclick="editPosition(1)">Edit</button>
            <button onclick="manageQuestions(1)">Questions</button>
            <button onclick="viewCandidates(1)">Candidates</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
```

---

## **❓ 2. QUESTION MANAGEMENT BY STEP**

### **A. Step 1: Auto-Scored Questions**

#### **Question Bank Structure:**
```python
# Step 1 Questions - Auto-scored multiple choice
class Step1Question(db.Model):
    __tablename__ = 'step1_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # iq, technical
    category = db.Column(db.String(50))  # logical, spatial, programming, etc.
    difficulty = db.Column(db.String(20))  # easy, medium, hard
    options = db.Column(db.Text)  # JSON array of options
    correct_answer = db.Column(db.String(10), nullable=False)
    explanation = db.Column(db.Text)
    points = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Position-specific assignments
    position_assignments = db.relationship('PositionStep1Questions', backref='question', lazy=True)
```

#### **Position-Question Assignment:**
```python
class PositionStep1Questions(db.Model):
    __tablename__ = 'position_step1_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('step1_questions.id'), nullable=False)
    is_required = db.Column(db.Boolean, default=False)  # Always include this question
    weight = db.Column(db.Float, default=1.0)  # Question weight in scoring
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

#### **Question Selection Interface:**
```html
<!-- Step 1 Question Management -->
<div class="question-management">
  <h3>Step 1 Questions for: Lead Software Developer</h3>
  
  <div class="question-categories">
    <div class="category">
      <h4>IQ Questions (10 required)</h4>
      <div class="question-list">
        <div class="question-item">
          <input type="checkbox" id="iq1" checked>
          <label for="iq1">
            <strong>Pattern Recognition:</strong>
            <p>In the sequence 2, 6, 12, 20, 30, ?, what comes next?</p>
            <span class="difficulty medium">Medium</span>
            <span class="points">1 point</span>
          </label>
        </div>
        <!-- More IQ questions... -->
      </div>
    </div>
    
    <div class="category">
      <h4>Technical Questions (15 required)</h4>
      <div class="question-list">
        <div class="question-item">
          <input type="checkbox" id="tech1" checked>
          <label for="tech1">
            <strong>Programming Fundamentals:</strong>
            <p>Which data structure is best for implementing undo/redo functionality?</p>
            <span class="difficulty hard">Hard</span>
            <span class="points">2 points</span>
          </label>
        </div>
        <!-- More technical questions... -->
      </div>
    </div>
  </div>
  
  <div class="scoring-config">
    <h4>Scoring Configuration</h4>
    <div class="config-item">
      <label>IQ Weight:</label>
      <input type="range" min="0" max="100" value="40" id="iqWeight">
      <span id="iqWeightValue">40%</span>
    </div>
    <div class="config-item">
      <label>Technical Weight:</label>
      <input type="range" min="0" max="100" value="60" id="techWeight">
      <span id="techWeightValue">60%</span>
    </div>
    <div class="config-item">
      <label>Pass Threshold:</label>
      <input type="number" value="70" min="0" max="100" id="passThreshold">%
    </div>
  </div>
  
  <button onclick="saveStep1Config()">Save Configuration</button>
</div>
```

### **B. Step 2: Manual Evaluation Questions**

#### **Question Structure:**
```python
# Step 2 Questions - Open-ended, manually evaluated
class Step2Question(db.Model):
    __tablename__ = 'step2_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))  # architecture, programming, problem_solving
    difficulty = db.Column(db.String(20))
    time_minutes = db.Column(db.Integer, default=15)
    evaluation_criteria = db.Column(db.Text)  # JSON array of criteria
    related_technologies = db.Column(db.Text)  # JSON array
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Position assignments
    position_assignments = db.relationship('PositionStep2Questions', backref='question', lazy=True)
```

#### **Interviewer Evaluation Interface:**
```html
<!-- Step 2 Interview Evaluation -->
<div class="step2-evaluation">
  <h3>Technical Interview Evaluation</h3>
  <p>Candidate: John Doe | Position: Lead Software Developer</p>
  
  <div class="question-evaluation">
    <div class="question">
      <h4>Question 1: IoT Gateway Architecture</h4>
      <p class="question-content">
        Design an IoT Gateway for industrial device management system...
      </p>
      <div class="candidate-response">
        <h5>Candidate Response:</h5>
        <p>"I would design the gateway with the following components..."</p>
      </div>
      
      <div class="evaluation-form">
        <div class="criteria">
          <label>Technical Knowledge (1-10):</label>
          <input type="number" min="1" max="10" value="8" class="score">
        </div>
        <div class="criteria">
          <label>Problem Solving (1-10):</label>
          <input type="number" min="1" max="10" value="7" class="score">
        </div>
        <div class="criteria">
          <label>Communication (1-10):</label>
          <input type="number" min="1" max="10" value="9" class="score">
        </div>
        <div class="criteria">
          <label>Overall Assessment:</label>
          <select class="recommendation">
            <option value="approve">Approve for Step 3</option>
            <option value="borderline">Borderline - Needs discussion</option>
            <option value="reject">Reject</option>
          </select>
        </div>
        <div class="notes">
          <label>Interviewer Notes:</label>
          <textarea rows="3" placeholder="Detailed feedback..."></textarea>
        </div>
      </div>
    </div>
  </div>
  
  <div class="overall-evaluation">
    <h4>Overall Evaluation</h4>
    <div class="summary">
      <p><strong>Average Score:</strong> <span id="avgScore">8.0</span>/10</p>
      <p><strong>Recommendation:</strong> <span id="finalRecommendation">Approve</span></p>
    </div>
    <button onclick="submitStep2Evaluation()">Submit Evaluation</button>
  </div>
</div>
```

### **C. Step 3: Executive Interview Questions**

#### **Question Structure:**
```python
# Step 3 Questions - Executive level evaluation
class Step3Question(db.Model):
    __tablename__ = 'step3_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    interviewer_type = db.Column(db.String(20))  # cto, ceo, both
    category = db.Column(db.String(50))  # technical_leadership, business, culture
    time_minutes = db.Column(db.Integer, default=5)
    evaluation_criteria = db.Column(db.Text)  # JSON array
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Position assignments
    position_assignments = db.relationship('PositionStep3Questions', backref='question', lazy=True)
```

#### **Executive Interview Package:**
```html
<!-- Step 3 Interview Package Export -->
<div class="step3-package">
  <h3>Final Interview Package</h3>
  <p>Candidate: John Doe | Position: Lead Software Developer</p>
  
  <div class="interview-sections">
    <div class="section">
      <h4>CTO Interview (45 minutes)</h4>
      <div class="questions">
        <div class="question">
          <h5>1. Technology Strategy Alignment</h5>
          <p>As Tech Lead for Mekong's 50-year IoT roadmap, how would you...</p>
          <div class="evaluation-criteria">
            <strong>Evaluation Criteria:</strong>
            <ul>
              <li>Strategic thinking</li>
              <li>Technical depth</li>
              <li>Long-term vision</li>
            </ul>
          </div>
        </div>
        <!-- More CTO questions... -->
      </div>
    </div>
    
    <div class="section">
      <h4>CEO Interview (30 minutes)</h4>
      <div class="questions">
        <div class="question">
          <h5>1. Market Understanding</h5>
          <p>How do you understand the ASEAN IoT market opportunity...</p>
          <div class="evaluation-criteria">
            <strong>Evaluation Criteria:</strong>
            <ul>
              <li>Market knowledge</li>
              <li>Business acumen</li>
              <li>Strategic thinking</li>
            </ul>
          </div>
        </div>
        <!-- More CEO questions... -->
      </div>
    </div>
  </div>
  
  <div class="scoring-sheet">
    <h4>Scoring Sheet</h4>
    <table>
      <thead>
        <tr>
          <th>Question</th>
          <th>CTO Score (1-10)</th>
          <th>CEO Score (1-10)</th>
          <th>Notes</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Technology Strategy</td>
          <td><input type="number" min="1" max="10"></td>
          <td><input type="number" min="1" max="10"></td>
          <td><textarea rows="2"></textarea></td>
        </tr>
        <!-- More rows... -->
      </tbody>
    </table>
  </div>
  
  <div class="final-decision">
    <h4>Final Decision</h4>
    <div class="decision-form">
      <label>CTO Recommendation:</label>
      <select>
        <option value="approve">Approve</option>
        <option value="reject">Reject</option>
      </select>
      
      <label>CEO Recommendation:</label>
      <select>
        <option value="approve">Approve</option>
        <option value="reject">Reject</option>
      </select>
      
      <label>Final Decision:</label>
      <select>
        <option value="hired">Hired</option>
        <option value="rejected">Not Selected</option>
      </select>
      
      <label>Salary Offer (VND/month):</label>
      <input type="number" placeholder="e.g., 12000000">
      
      <label>Start Date:</label>
      <input type="date">
    </div>
  </div>
  
  <button onclick="exportStep3Package()">Export PDF Package</button>
</div>
```

---

## **⚙️ 3. WORKFLOW INTEGRATION**

### **A. Position-Based Question Selection:**

#### **Smart Question Assignment:**
```python
def assign_questions_to_position(position_id, step_number):
    """
    Automatically assign appropriate questions based on position requirements
    """
    position = Position.query.get(position_id)
    
    if step_number == 1:
        # Step 1: Auto-scored questions
        questions = select_step1_questions_by_position(position)
        return {
            'iq_questions': questions['iq'][:10],  # 10 IQ questions
            'technical_questions': questions['technical'][:15],  # 15 technical
            'scoring_config': {
                'iq_weight': 0.4,
                'technical_weight': 0.6,
                'pass_threshold': 70
            }
        }
    
    elif step_number == 2:
        # Step 2: Manual evaluation questions
        questions = select_step2_questions_by_position(position)
        return {
            'questions': questions[:8],  # 8 questions total
            'evaluation_criteria': get_evaluation_criteria(position.level)
        }
    
    elif step_number == 3:
        # Step 3: Executive questions
        questions = select_step3_questions_by_position(position)
        return {
            'cto_questions': questions['cto'][:9],  # 9 CTO questions
            'ceo_questions': questions['ceo'][:6],  # 6 CEO questions
            'scoring_weights': {
                'cto_weight': 0.6,
                'ceo_weight': 0.4
            }
        }

def select_step1_questions_by_position(position):
    """
    Select questions based on position requirements
    """
    # Get position skills and level
    required_skills = json.loads(position.required_skills)
    level = position.level
    
    # Filter questions by relevance
    iq_questions = Step1Question.query.filter_by(
        question_type='iq',
        is_active=True
    ).all()
    
    technical_questions = Step1Question.query.filter_by(
        question_type='technical',
        is_active=True
    ).filter(
        Step1Question.category.in_(required_skills)
    ).all()
    
    # Adjust difficulty based on level
    if level == 'junior':
        technical_questions = [q for q in technical_questions if q.difficulty in ['easy', 'medium']]
    elif level == 'lead':
        technical_questions = [q for q in technical_questions if q.difficulty in ['medium', 'hard']]
    
    return {
        'iq': random.sample(iq_questions, min(10, len(iq_questions))),
        'technical': random.sample(technical_questions, min(15, len(technical_questions)))
    }
```

### **B. Scoring and Evaluation Workflow:**

#### **Step 1 Auto-Scoring:**
```python
def auto_score_step1(candidate_id, answers):
    """
    Automatically score Step 1 assessment
    """
    candidate = Candidate.query.get(candidate_id)
    position = candidate.position
    
    # Get scoring configuration
    config = get_step1_config(position.id)
    
    # Calculate scores
    iq_score = calculate_iq_score(answers['iq'], config['iq_weight'])
    tech_score = calculate_technical_score(answers['technical'], config['technical_weight'])
    
    total_score = iq_score + tech_score
    percentage = (total_score / 100) * 100
    
    # Auto-approval logic
    if percentage >= config['pass_threshold']:
        approve_step1(candidate, auto_approved=True)
        return {'status': 'approved', 'score': percentage}
    elif percentage >= 50:
        flag_for_manual_review(candidate, percentage)
        return {'status': 'manual_review', 'score': percentage}
    else:
        reject_candidate(candidate, percentage)
        return {'status': 'rejected', 'score': percentage}
```

#### **Step 2 Manual Evaluation:**
```python
def submit_step2_evaluation(interviewer_id, candidate_id, evaluations):
    """
    Submit Step 2 manual evaluation
    """
    candidate = Candidate.query.get(candidate_id)
    
    # Calculate overall score
    total_score = sum(eval['score'] for eval in evaluations) / len(evaluations)
    
    # Determine recommendation
    if total_score >= 6 and evaluations[-1]['recommendation'] == 'approve':
        approve_step2(candidate, interviewer_id)
        return {'status': 'approved', 'score': total_score}
    else:
        reject_candidate(candidate, 'step2_failed')
        return {'status': 'rejected', 'score': total_score}
```

#### **Step 3 Executive Decision:**
```python
def process_step3_decision(candidate_id, cto_evaluation, ceo_evaluation):
    """
    Process final hiring decision
    """
    candidate = Candidate.query.get(candidate_id)
    
    # Calculate weighted final score
    final_score = (cto_evaluation['score'] * 0.6 + 
                  ceo_evaluation['score'] * 0.4)
    
    # Both must approve for hiring
    if (cto_evaluation['decision'] == 'approve' and 
        ceo_evaluation['decision'] == 'approve'):
        
        # Create hiring record
        hiring = HiringDecision(
            candidate_id=candidate_id,
            cto_score=cto_evaluation['score'],
            ceo_score=ceo_evaluation['score'],
            final_score=final_score,
            salary_offered=ceo_evaluation.get('salary'),
            start_date=ceo_evaluation.get('start_date'),
            decision='hired'
        )
        
        db.session.add(hiring)
        candidate.status = 'hired'
        db.session.commit()
        
        return {'status': 'hired', 'salary': ceo_evaluation.get('salary')}
    else:
        candidate.status = 'rejected_final'
        db.session.commit()
        return {'status': 'rejected'}
```

---

## **📊 4. ADMIN INTERFACE FOR QUESTION MANAGEMENT**

### **A. Question Bank Management:**

#### **Admin Dashboard - Question Management:**
```html
<!-- Question Bank Management -->
<div class="question-management-dashboard">
  <div class="header">
    <h2>Question Bank Management</h2>
    <button onclick="importQuestions()">Import Questions</button>
    <button onclick="exportQuestions()">Export Questions</button>
  </div>
  
  <div class="question-tabs">
    <button class="tab active" onclick="showStep1Questions()">Step 1 Questions</button>
    <button class="tab" onclick="showStep2Questions()">Step 2 Questions</button>
    <button class="tab" onclick="showStep3Questions()">Step 3 Questions</button>
  </div>
  
  <div class="question-filters">
    <select id="categoryFilter">
      <option value="">All Categories</option>
      <option value="iq">IQ Questions</option>
      <option value="technical">Technical Questions</option>
    </select>
    
    <select id="difficultyFilter">
      <option value="">All Difficulties</option>
      <option value="easy">Easy</option>
      <option value="medium">Medium</option>
      <option value="hard">Hard</option>
    </select>
    
    <input type="text" placeholder="Search questions..." id="searchQuestions">
  </div>
  
  <div class="question-list">
    <!-- Step 1 Questions Table -->
    <table id="step1QuestionsTable">
      <thead>
        <tr>
          <th><input type="checkbox" id="selectAll"></th>
          <th>Question</th>
          <th>Type</th>
          <th>Category</th>
          <th>Difficulty</th>
          <th>Points</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <!-- Question rows... -->
      </tbody>
    </table>
  </div>
</div>
```

### **B. Bulk Question Import:**

#### **Import Interface:**
```html
<!-- Question Import Modal -->
<div class="import-modal">
  <h3>Import Questions</h3>
  
  <div class="import-options">
    <label>Import Format:</label>
    <select id="importFormat">
      <option value="json">JSON</option>
      <option value="excel">Excel</option>
      <option value="csv">CSV</option>
    </select>
    
    <label>Step:</label>
    <select id="importStep">
      <option value="1">Step 1 (Auto-scored)</option>
      <option value="2">Step 2 (Manual evaluation)</option>
      <option value="3">Step 3 (Executive interview)</option>
    </select>
  </div>
  
  <div class="file-upload">
    <input type="file" id="questionFile" accept=".json,.xlsx,.csv">
    <p>Upload your question file here</p>
  </div>
  
  <div class="import-preview">
    <h4>Preview (first 5 questions):</h4>
    <div id="previewContent">
      <!-- Preview content will be loaded here -->
    </div>
  </div>
  
  <div class="import-actions">
    <button onclick="validateImport()">Validate</button>
    <button onclick="confirmImport()">Import Questions</button>
    <button onclick="cancelImport()">Cancel</button>
  </div>
</div>
```

---

## **🎯 SUMMARY**

### **✅ Position Management:**
- ✅ **Create positions** với detailed job descriptions
- ✅ **Assign questions** automatically based on position requirements
- ✅ **Configure scoring** per position và level
- ✅ **Track candidates** per position

### **✅ Question Management by Step:**
- ✅ **Step 1:** Auto-scored multiple choice (IQ + Technical)
- ✅ **Step 2:** Manual evaluation open-ended questions
- ✅ **Step 3:** Executive interview questions (CTO + CEO)

### **✅ Scoring & Approval:**
- ✅ **Step 1:** Auto-approval ≥70%, manual review 50-69%, auto-reject <50%
- ✅ **Step 2:** Interviewer manual scoring và approval
- ✅ **Step 3:** Executive combined decision với weighted scoring

### **✅ Admin Features:**
- ✅ **Question bank management** với bulk import/export
- ✅ **Position-specific question assignment**
- ✅ **Scoring configuration** per position
- ✅ **Evaluation criteria** management

**System này cho phép HR tạo vị trí, assign câu hỏi phù hợp, và có workflow approval rõ ràng cho từng step!** 🚀 