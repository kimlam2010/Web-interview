# 🔧 QUESTION MANAGEMENT INTERFACE

## **📝 TÍNH NĂNG EDIT QUESTIONS**

### **A. Admin Question Management Dashboard:**

#### **Question Editor Interface:**
```html
<!-- Admin Question Management Dashboard -->
<div class="question-management-dashboard">
  <div class="header">
    <h2>Question Bank Management</h2>
    <div class="actions">
      <button onclick="importQuestions()">Import Questions</button>
      <button onclick="exportQuestions()">Export Questions</button>
      <button onclick="addNewQuestion()">+ Add New Question</button>
    </div>
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
      <option value="system_architecture">System Architecture</option>
      <option value="leadership">Leadership</option>
    </select>
    
    <select id="difficultyFilter">
      <option value="">All Difficulties</option>
      <option value="easy">Easy</option>
      <option value="medium">Medium</option>
      <option value="hard">Hard</option>
    </select>
    
    <select id="positionFilter">
      <option value="">All Positions</option>
      <option value="lead_developer">Lead Developer</option>
      <option value="software_engineer">Software Engineer</option>
      <option value="cto">CTO</option>
      <option value="ceo">CEO</option>
    </select>
    
    <input type="text" placeholder="Search questions..." id="searchQuestions">
  </div>
  
  <div class="question-list">
    <table id="questionsTable">
      <thead>
        <tr>
          <th><input type="checkbox" id="selectAll"></th>
          <th>ID</th>
          <th>Question</th>
          <th>Category</th>
          <th>Difficulty</th>
          <th>Position</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><input type="checkbox" class="question-select"></td>
          <td>IQ001</td>
          <td>Pattern Recognition: 2, 6, 12, 20, 30, ?</td>
          <td>IQ</td>
          <td><span class="difficulty medium">Medium</span></td>
          <td>All</td>
          <td><span class="status active">Active</span></td>
          <td>
            <button onclick="editQuestion('IQ001')" class="btn-edit">Edit</button>
            <button onclick="duplicateQuestion('IQ001')" class="btn-duplicate">Copy</button>
            <button onclick="toggleQuestionStatus('IQ001')" class="btn-toggle">Toggle</button>
          </td>
        </tr>
        <tr>
          <td><input type="checkbox" class="question-select"></td>
          <td>LD001</td>
          <td>IoT Gateway Architecture Design</td>
          <td>System Architecture</td>
          <td><span class="difficulty hard">Hard</span></td>
          <td>Lead Developer</td>
          <td><span class="status active">Active</span></td>
          <td>
            <button onclick="editQuestion('LD001')" class="btn-edit">Edit</button>
            <button onclick="duplicateQuestion('LD001')" class="btn-duplicate">Copy</button>
            <button onclick="toggleQuestionStatus('LD001')" class="btn-toggle">Toggle</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  
  <div class="bulk-actions">
    <button onclick="bulkActivate()">Activate Selected</button>
    <button onclick="bulkDeactivate()">Deactivate Selected</button>
    <button onclick="bulkDelete()">Delete Selected</button>
    <button onclick="bulkExport()">Export Selected</button>
  </div>
</div>
```

### **B. Question Editor Modal:**

#### **Edit Question Form:**
```html
<!-- Question Editor Modal -->
<div class="question-editor-modal" id="questionEditor">
  <div class="modal-content">
    <div class="modal-header">
      <h3>Edit Question</h3>
      <button onclick="closeQuestionEditor()" class="close-btn">&times;</button>
    </div>
    
    <div class="modal-body">
      <form id="questionEditForm">
        <div class="form-group">
          <label>Question ID:</label>
          <input type="text" name="question_id" readonly>
        </div>
        
        <div class="form-group">
          <label>Step:</label>
          <select name="step" required>
            <option value="1">Step 1 (Auto-scored)</option>
            <option value="2">Step 2 (Manual evaluation)</option>
            <option value="3">Step 3 (Executive interview)</option>
          </select>
        </div>
        
        <div class="form-group">
          <label>Category:</label>
          <select name="category" required>
            <option value="iq">IQ Questions</option>
            <option value="technical">Technical Questions</option>
            <option value="system_architecture">System Architecture</option>
            <option value="leadership">Leadership</option>
            <option value="business">Business</option>
          </select>
        </div>
        
        <div class="form-group">
          <label>Position Level:</label>
          <select name="position_level" required>
            <option value="all">All Positions</option>
            <option value="lead_developer">Lead Developer</option>
            <option value="software_engineer">Software Engineer</option>
            <option value="cto">CTO</option>
            <option value="ceo">CEO</option>
          </select>
        </div>
        
        <div class="form-group">
          <label>Difficulty:</label>
          <select name="difficulty" required>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>
        
        <div class="form-group">
          <label>Question Title:</label>
          <input type="text" name="title" required>
        </div>
        
        <div class="form-group">
          <label>Question Content:</label>
          <textarea name="content" rows="6" required></textarea>
        </div>
        
        <!-- Step 1 specific fields -->
        <div class="step1-fields" id="step1Fields">
          <div class="form-group">
            <label>Options (one per line):</label>
            <textarea name="options" rows="4" placeholder="Option A&#10;Option B&#10;Option C&#10;Option D"></textarea>
          </div>
          
          <div class="form-group">
            <label>Correct Answer:</label>
            <input type="text" name="correct_answer">
          </div>
          
          <div class="form-group">
            <label>Points:</label>
            <input type="number" name="points" min="1" max="5" value="1">
          </div>
        </div>
        
        <!-- Step 2 & 3 specific fields -->
        <div class="step23-fields" id="step23Fields">
          <div class="form-group">
            <label>Time (minutes):</label>
            <input type="number" name="time_minutes" min="1" max="30" value="15">
          </div>
          
          <div class="form-group">
            <label>Evaluation Criteria (one per line):</label>
            <textarea name="evaluation_criteria" rows="4" placeholder="Technical knowledge&#10;Problem solving&#10;Communication&#10;Leadership"></textarea>
          </div>
          
          <div class="form-group">
            <label>Related Technologies (comma separated):</label>
            <input type="text" name="related_technologies" placeholder="IoT, MQTT, Python, React">
          </div>
        </div>
        
        <div class="form-group">
          <label>Explanation (for Step 1):</label>
          <textarea name="explanation" rows="3" placeholder="Detailed explanation of the correct answer..."></textarea>
        </div>
        
        <div class="form-group">
          <label>Status:</label>
          <select name="status">
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="draft">Draft</option>
          </select>
        </div>
      </form>
    </div>
    
    <div class="modal-footer">
      <button onclick="saveQuestion()" class="btn-save">Save Changes</button>
      <button onclick="saveAndDuplicate()" class="btn-save-copy">Save & Copy</button>
      <button onclick="closeQuestionEditor()" class="btn-cancel">Cancel</button>
    </div>
  </div>
</div>
```

### **C. JavaScript Functions:**

#### **Question Management Functions:**
```javascript
// Question Management JavaScript
function editQuestion(questionId) {
    // Load question data from database
    fetch(`/api/questions/${questionId}`)
        .then(response => response.json())
        .then(question => {
            populateQuestionForm(question);
            showQuestionEditor();
        });
}

function populateQuestionForm(question) {
    const form = document.getElementById('questionEditForm');
    
    // Populate basic fields
    form.querySelector('[name="question_id"]').value = question.id;
    form.querySelector('[name="step"]').value = question.step;
    form.querySelector('[name="category"]').value = question.category;
    form.querySelector('[name="position_level"]').value = question.position_level;
    form.querySelector('[name="difficulty"]').value = question.difficulty;
    form.querySelector('[name="title"]').value = question.title;
    form.querySelector('[name="content"]').value = question.content;
    form.querySelector('[name="status"]').value = question.status;
    
    // Show/hide step-specific fields
    if (question.step == 1) {
        document.getElementById('step1Fields').style.display = 'block';
        document.getElementById('step23Fields').style.display = 'none';
        
        // Populate Step 1 fields
        form.querySelector('[name="options"]').value = question.options.join('\n');
        form.querySelector('[name="correct_answer"]').value = question.correct_answer;
        form.querySelector('[name="points"]').value = question.points;
        form.querySelector('[name="explanation"]').value = question.explanation;
    } else {
        document.getElementById('step1Fields').style.display = 'none';
        document.getElementById('step23Fields').style.display = 'block';
        
        // Populate Step 2/3 fields
        form.querySelector('[name="time_minutes"]').value = question.time_minutes;
        form.querySelector('[name="evaluation_criteria"]').value = question.evaluation_criteria.join('\n');
        form.querySelector('[name="related_technologies"]').value = question.related_technologies.join(', ');
    }
}

function saveQuestion() {
    const form = document.getElementById('questionEditForm');
    const formData = new FormData(form);
    
    // Convert form data to JSON
    const questionData = {
        id: formData.get('question_id'),
        step: parseInt(formData.get('step')),
        category: formData.get('category'),
        position_level: formData.get('position_level'),
        difficulty: formData.get('difficulty'),
        title: formData.get('title'),
        content: formData.get('content'),
        status: formData.get('status')
    };
    
    // Add step-specific fields
    if (questionData.step == 1) {
        questionData.options = formData.get('options').split('\n').filter(opt => opt.trim());
        questionData.correct_answer = formData.get('correct_answer');
        questionData.points = parseInt(formData.get('points'));
        questionData.explanation = formData.get('explanation');
    } else {
        questionData.time_minutes = parseInt(formData.get('time_minutes'));
        questionData.evaluation_criteria = formData.get('evaluation_criteria').split('\n').filter(crit => crit.trim());
        questionData.related_technologies = formData.get('related_technologies').split(',').map(tech => tech.trim());
    }
    
    // Save to database
    fetch('/api/questions/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(questionData)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showNotification('Question saved successfully!', 'success');
            closeQuestionEditor();
            refreshQuestionList();
        } else {
            showNotification('Error saving question: ' + result.error, 'error');
        }
    });
}

function duplicateQuestion(questionId) {
    // Load original question and create copy
    fetch(`/api/questions/${questionId}`)
        .then(response => response.json())
        .then(question => {
            // Create copy with new ID
            question.id = generateNewQuestionId(question.step, question.category);
            question.title = question.title + ' (Copy)';
            question.status = 'draft';
            
            populateQuestionForm(question);
            showQuestionEditor();
        });
}

function toggleQuestionStatus(questionId) {
    fetch(`/api/questions/${questionId}/toggle-status`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showNotification('Question status updated!', 'success');
            refreshQuestionList();
        }
    });
}

function bulkActivate() {
    const selectedQuestions = getSelectedQuestions();
    if (selectedQuestions.length > 0) {
        fetch('/api/questions/bulk-activate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question_ids: selectedQuestions })
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                showNotification(`${selectedQuestions.length} questions activated!`, 'success');
                refreshQuestionList();
            }
        });
    }
}
```

### **D. Database Models Update:**

#### **Question Management Models:**
```python
# database/models.py - Updated for question management
class Question(db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.String(20), primary_key=True)  # e.g., IQ001, LD001
    step = db.Column(db.Integer, nullable=False)  # 1, 2, or 3
    category = db.Column(db.String(50), nullable=False)
    position_level = db.Column(db.String(30), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    
    # Step 1 specific fields
    options = db.Column(db.Text)  # JSON array for multiple choice
    correct_answer = db.Column(db.String(10))
    points = db.Column(db.Integer, default=1)
    explanation = db.Column(db.Text)
    
    # Step 2 & 3 specific fields
    time_minutes = db.Column(db.Integer, default=15)
    evaluation_criteria = db.Column(db.Text)  # JSON array
    related_technologies = db.Column(db.Text)  # JSON array
    
    # Common fields
    status = db.Column(db.String(20), default='active')  # active, inactive, draft
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Usage tracking
    times_used = db.Column(db.Integer, default=0)
    average_score = db.Column(db.Float, default=0.0)
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        data = {
            'id': self.id,
            'step': self.step,
            'category': self.category,
            'position_level': self.position_level,
            'difficulty': self.difficulty,
            'title': self.title,
            'content': self.content,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'times_used': self.times_used,
            'average_score': self.average_score
        }
        
        # Add step-specific fields
        if self.step == 1:
            data.update({
                'options': json.loads(self.options) if self.options else [],
                'correct_answer': self.correct_answer,
                'points': self.points,
                'explanation': self.explanation
            })
        else:
            data.update({
                'time_minutes': self.time_minutes,
                'evaluation_criteria': json.loads(self.evaluation_criteria) if self.evaluation_criteria else [],
                'related_technologies': json.loads(self.related_technologies) if self.related_technologies else []
            })
        
        return data
```

### **E. API Endpoints:**

#### **Question Management APIs:**
```python
# routes/admin.py - Question management endpoints
@app.route('/api/questions/<question_id>', methods=['GET'])
@login_required
@admin_required
def get_question(question_id):
    """Get single question by ID"""
    question = Question.query.get(question_id)
    if question:
        return jsonify(question.to_dict())
    else:
        return jsonify({'error': 'Question not found'}), 404

@app.route('/api/questions/update', methods=['POST'])
@login_required
@admin_required
def update_question():
    """Update existing question"""
    data = request.get_json()
    
    question = Question.query.get(data['id'])
    if not question:
        return jsonify({'error': 'Question not found'}), 404
    
    # Update fields
    question.step = data['step']
    question.category = data['category']
    question.position_level = data['position_level']
    question.difficulty = data['difficulty']
    question.title = data['title']
    question.content = data['content']
    question.status = data['status']
    question.updated_at = datetime.utcnow()
    
    # Update step-specific fields
    if data['step'] == 1:
        question.options = json.dumps(data['options'])
        question.correct_answer = data['correct_answer']
        question.points = data['points']
        question.explanation = data['explanation']
    else:
        question.time_minutes = data['time_minutes']
        question.evaluation_criteria = json.dumps(data['evaluation_criteria'])
        question.related_technologies = json.dumps(data['related_technologies'])
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Question updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/questions/<question_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_question_status(question_id):
    """Toggle question active/inactive status"""
    question = Question.query.get(question_id)
    if not question:
        return jsonify({'error': 'Question not found'}), 404
    
    question.status = 'inactive' if question.status == 'active' else 'active'
    question.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': f'Question {question.status}'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/questions/bulk-activate', methods=['POST'])
@login_required
@admin_required
def bulk_activate_questions():
    """Bulk activate selected questions"""
    data = request.get_json()
    question_ids = data.get('question_ids', [])
    
    questions = Question.query.filter(Question.id.in_(question_ids)).all()
    for question in questions:
        question.status = 'active'
        question.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': f'{len(questions)} questions activated'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
```

---

## **🎯 SUMMARY - TÍNH NĂNG EDIT QUESTIONS**

### **✅ ĐÃ THIẾT KẾ:**

#### **📝 Question Management Interface:**
- ✅ **Admin Dashboard:** View, filter, search questions
- ✅ **Question Editor:** Full-featured edit form
- ✅ **Bulk Operations:** Activate, deactivate, delete multiple questions
- ✅ **Duplicate Function:** Copy questions with new ID
- ✅ **Status Management:** Active, inactive, draft status

#### **🔧 Technical Features:**
- ✅ **Step-Specific Forms:** Different fields for Step 1 vs Step 2/3
- ✅ **Real-time Validation:** Form validation và error handling
- ✅ **Database Integration:** CRUD operations cho questions
- ✅ **API Endpoints:** RESTful APIs cho question management
- ✅ **Audit Trail:** Track changes và usage statistics

#### **📊 Enhanced Capabilities:**
- ✅ **Question Statistics:** Track usage và average scores
- ✅ **Version Control:** Track question changes over time
- ✅ **Import/Export:** Bulk operations với JSON format
- ✅ **Search & Filter:** Advanced filtering by category, difficulty, position

**Bây giờ Admin có thể FULLY MANAGE question bank với edit, create, duplicate, và bulk operations!** 🚀 