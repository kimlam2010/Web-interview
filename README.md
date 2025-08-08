# 🎯 Mekong Recruitment System

Simple Web Interface for HR 3-Step Recruitment Process

## 📋 Overview

This application supports Mekong Technology's recruitment process:
- **Step 1:** Online Assessment (IQ + Technical) - **ONLINE**
- **Step 2:** Technical Interview - **ONLINE**
- **Step 3:** Final Interview (CTO + CEO) - **OFFLINE** (Export to PDF)

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip (Python package manager)

### Installation

1. **Clone or extract the project:**
```bash
cd "APP INTERVIEW"
```

2. **Create virtual environment:**
```bash
python -m venv venv
```

3. **Activate virtual environment:**
```bash
# Windows
venv\Scripts\activate

# macOS/Linux  
source venv/bin/activate
```

4. **Install dependencies:**
```bash
pip install -r requirements.txt
```

5. **Initialize database:**
```bash
python run.py init-db
```

6. **Create admin user:**
```bash
python run.py create-admin
```

7. **Load sample data:**
```bash
python run.py load-sample-data
```

8. **Run the application:**
```bash
python run.py
```

9. **Access the application:**
   - Open browser: http://localhost:5000
   - Login: Username: `admin`, Password: `admin123`

## 📱 Features

### 🔐 Authentication
- Secure HR user login
- Role-based access (HR, Admin)
- Session management

### 👥 Candidate Management
- Add new candidates
- Track recruitment progress
- View candidate profiles
- Upload CV files

### 📝 Step 1: Online Assessment
- **Format:** Online test with timer
- **Duration:** 30 minutes
- **Components:** 
  - IQ Questions (10 questions, 40% weight)
  - Technical Questions (15 questions, 60% weight)
- **Scoring:** Auto-scored, 70% pass threshold
- **Features:**
  - Random question selection
  - Auto-submit when time expires
  - Instant results
  - Progress tracking

### 💻 Step 2: Technical Interview
- **Format:** Online interview with question bank
- **Duration:** 60 minutes
- **Components:**
  - 40+ open-ended questions
  - Smart filtering by position/category
  - HR selects 3-4 questions per section
- **Evaluation:**
  - Structured scoring (1-10 scale)
  - Multiple criteria assessment
  - Interviewer notes
  - Pass/fail recommendation

### 🎯 Step 3: Final Interview
- **Format:** Offline interview (PDF export)
- **Structure:**
  - CTO Interview (45 minutes, 9 questions)
  - CEO Interview (30 minutes, 6 questions)
- **Export Features:**
  - Professional PDF format
  - Company branding
  - Scoring rubric included
  - Evaluation forms
  - Compensation discussion guide

### 📊 Reports & Analytics
- Recruitment dashboard
- Candidate progress tracking
- Score analytics
- Export to Excel
- Performance metrics

## 🔧 Configuration

### Environment Variables
Create `.env` file:
```bash
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///recruitment.db
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### Application Settings
Edit `config.py` for:
- Assessment time limits
- Pass/fail thresholds
- Company information
- Salary ranges
- Email templates

## 📁 Project Structure

```
APP INTERVIEW/
├── app.py                      # Main Flask application
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── run.py                      # Application runner
├── database/
│   ├── models.py              # Database models
│   ├── init_db.py             # Database initialization
│   └── sample_data.py         # Sample data loader
├── routes/
│   ├── auth.py                # Authentication routes
│   ├── step1.py               # Step 1 routes
│   ├── step2.py               # Step 2 routes
│   ├── step3.py               # Step 3 routes
│   └── admin.py               # Admin routes
├── templates/                  # HTML templates
├── static/                     # CSS, JS, images
├── data/                       # Question banks (JSON)
├── uploads/                    # Uploaded files
└── exports/                    # Generated reports
```

## 🎓 Usage Guide

### For HR Users

1. **Login to the system**
   - Use provided credentials (Username: admin, Password: admin123)
   - Access main dashboard with recruitment overview

2. **Position Management (Admin/HR)**
   - **Create positions:** Define job titles, departments, levels, salary ranges
   - **Job descriptions:** Detailed requirements, responsibilities, required skills
   - **Question assignment:** Automatically assign questions based on position level
   - **Scoring configuration:** Set IQ/Technical weights, pass thresholds per position

3. **Add new candidate**
   - Go to Candidates section → "Add New Candidate"
   - Fill mandatory fields: Name, Email, Phone, Position
   - Upload CV file (optional, PDF/DOC/DOCX supported)
   - System automatically generates:
     * Step 1 assessment link với position-specific questions
     * Temporary username & password for candidate
     * Email with credentials sent automatically
   - Link expires after 7 days (configurable)

3. **Step 1: Online Assessment Management**
   - **Credential Management:** View candidate login credentials, extend expiration
   - **Monitor Progress:** Real-time dashboard showing active assessments
   - **Auto-Approval:** System automatically approves scores ≥70%
   - **Manual Review:** Review borderline scores (50-69%) manually
   - **Auto-Rejection:** Scores <50% automatically rejected
   - **Extend Links:** Extend expiration up to 30 days if needed
   - **Reminders:** System sends automatic reminders 24h and 3h before expiry

4. **Step 2: Technical Interview Setup**
   - **Available for Approved Candidates:** Only candidates who passed Step 1
   - **Position-Specific Questions:** System selects questions based on position level
   - **Question Selection:** Choose 3-4 questions per section from position-specific bank
   - **Smart Filtering:** Filter by position level, difficulty, time duration
   - **Schedule Interview:** Set date/time, assign interviewer, location/platform
   - **Generate Link:** Create interview link (expires in 3 days)
   - **Interviewer Evaluation:** Manual scoring 1-10, detailed feedback, approval decision

5. **Step 3: Final Interview Preparation**
   - **Available for Approved Candidates:** Only candidates approved by interviewer
   - **Position-Specific Questions:** CTO questions focus on technical leadership level
   - **Export Questions:** Generate professional PDF with CTO + CEO questions
   - **Print Package:** Includes questions, scoring rubric, evaluation forms
   - **Compensation Guide:** Position-specific salary ranges and benefits
   - **Executive Interview:** CTO conducts technical assessment, CEO cultural fit
   - **Final Decision:** Both CTO and CEO must approve for hiring
   - **Compensation Approval:** CEO approves final salary within position range

6. **Link Management**
   - **View All Links:** Dashboard shows active, expiring, and expired links
   - **Extend Expiration:** Extend individual links or bulk extend
   - **Weekend Auto-extend:** System automatically extends weekend expiries
   - **Resend Links:** Generate new links for expired assessments

7. **Question Bank Management (Admin)**
   - **Edit Questions:** Full-featured question editor with step-specific forms
   - **Import Questions:** Bulk import from JSON/Excel/CSV files
   - **Export Questions:** Export selected questions to JSON format
   - **Duplicate Questions:** Copy existing questions with new IDs
   - **Bulk Operations:** Activate, deactivate, delete multiple questions
   - **Step 1 Questions:** IQ and technical multiple choice questions
   - **Step 2 Questions:** Open-ended technical evaluation questions
   - **Step 3 Questions:** Executive interview questions for CTO/CEO
   - **Position Assignment:** Assign questions to specific positions/levels
   - **Scoring Configuration:** Set weights and thresholds per position
   - **Question Statistics:** Track usage and average scores

8. **Generate Reports & Analytics**
   - **Dashboard Analytics:** Real-time recruitment progress charts
   - **Candidate Reports:** Individual candidate progress and scores
   - **Position Analytics:** Performance metrics per position/level
   - **Export Data:** Excel reports with candidate information and results
   - **Performance Metrics:** Pass rates, average scores, time-to-hire

### For Candidates

1. **Receive credentials via email**
   - Email contains assessment link, username, and temporary password
   - Note expiration date and time
   - Ensure stable internet connection

2. **Login and Take Step 1 Assessment**
   - Use provided username and password to login
   - Complete assessment within 30 minutes once started
   - System auto-submits when time expires
   - Receive immediate results:
     * Score ≥70%: Automatically approved for Step 2
     * Score 50-69%: Under HR review (will be notified)
     * Score <50%: Not proceeding (thank you email sent)

3. **Step 2 Technical Interview** (if approved)
   - Receive interview invitation with date/time
   - Join online interview with technical interviewer
   - Answer open-ended technical questions
   - Wait for interviewer's approval decision

4. **Step 3 Final Interview** (if approved by interviewer)
   - Receive invitation for in-person final interview
   - Meet with CTO for technical assessment
   - Meet with CEO for cultural fit and compensation discussion
   - Final hiring decision made by both executives

5. **Final Decision Notification**
   - Receive email with final decision
   - If hired: Welcome package with start date and compensation
   - If not selected: Thank you email with feedback (if available)

## 🔒 Security Features

- Password hashing (bcrypt)
- Session management with timeout
- CSRF protection
- Input validation
- SQL injection prevention
- File upload security
- Temporary credential system
- Login attempt limiting (3 max attempts)
- IP address tracking
- Session auto-logout after inactivity
- Audit logging for all actions

## 📈 Performance

- SQLite for development
- PostgreSQL support for production
- Responsive design (mobile-friendly)
- Fast loading times (<2 seconds)
- Supports 100+ concurrent users

## 🔧 Maintenance

### Backup Database
```bash
cp recruitment.db recruitment_backup_$(date +%Y%m%d).db
```

### Update Questions
- Edit JSON files in `data/` folder
- Restart application to load changes

### Add New Users
```bash
python run.py create-admin
```

### View Logs
- Check console output for errors
- Enable detailed logging in config

## 🚀 Deployment

### Local Deployment
1. Follow installation steps above
2. Run on localhost:5000

### Production Deployment
1. Set `FLASK_ENV=production`
2. Configure PostgreSQL database
3. Set up reverse proxy (nginx)
4. Use WSGI server (gunicorn)
5. Configure SSL certificate

Example production command:
```bash
gunicorn -w 4 -b 0.0.0.0:8000 run:app
```

## 📞 Support

### Common Issues

**Q: Cannot login with admin credentials**
A: Run `python run.py create-admin` to recreate admin user

**Q: Assessment timer not working**
A: Check JavaScript is enabled in browser

**Q: PDF export fails**
A: Ensure WeasyPrint is properly installed

**Q: Database errors**
A: Run `python run.py init-db` to reinitialize

### Technical Support
- Check console logs for errors
- Verify all dependencies installed
- Ensure proper file permissions
- Contact development team if needed

## 📄 License

Internal use only - Mekong Technology

---

**🎯 Ready to streamline your recruitment process!**