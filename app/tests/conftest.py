"""
Pytest configuration for Mekong Recruitment System tests
"""
import pytest
import tempfile
import os
from app import create_app
from app.models import db as _db
from app.models import User, Candidate, Position, Step1Question, Step2Question, Step3Question, AssessmentResult


@pytest.fixture(scope='session')
def app():
    """Create application for the tests."""
    _app = create_app('testing')
    
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp()
    _app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    _app.config['TESTING'] = True
    _app.config['WTF_CSRF_ENABLED'] = False
    
    with _app.app_context():
        _db.create_all()
        yield _app
        _db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope='session')
def db(app):
    """Create database for the tests."""
    with app.app_context():
        yield _db


@pytest.fixture(scope='function')
def session(db):
    """Create a new database session for a test."""
    connection = db.engine.connect()
    transaction = connection.begin()
    
    session = db.create_scoped_session(
        options={"bind": connection, "binds": {}}
    )
    
    db.session = session
    
    yield session
    
    transaction.rollback()
    connection.close()
    session.remove()


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def admin_user(session):
    """Create an admin user for testing."""
    user = User(
        username='admin',
        email='admin@mekong.com',
        role='admin',
        password_hash='hashed_password'
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def hr_user(session):
    """Create an HR user for testing."""
    user = User(
        username='hr_user',
        email='hr@mekong.com',
        role='hr',
        password_hash='hashed_password'
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def test_position(session):
    """Create a test position."""
    position = Position(
        title='Software Engineer',
        department='Engineering',
        level='Mid',
        salary_range='2000-3000 USD'
    )
    session.add(position)
    session.commit()
    return position


@pytest.fixture
def test_candidate(session, test_position):
    """Create a test candidate."""
    candidate = Candidate(
        name='John Doe',
        email='john.doe@example.com',
        phone='+1234567890',
        position_id=test_position.id,
        status='pending'
    )
    session.add(candidate)
    session.commit()
    return candidate


@pytest.fixture
def test_questions(session):
    """Create test questions."""
    questions = [
        Step1Question(
            step=1,
            category='IQ',
            content='What comes next in the sequence: 2, 4, 8, 16, ?',
            options='["20", "24", "32", "30"]',
            correct_answer='32'
        ),
        Step1Question(
            step=1,
            category='Technical',
            content='What is the time complexity of binary search?',
            options='["O(1)", "O(log n)", "O(n)", "O(n²)"]',
            correct_answer='O(log n)'
        )
    ]
    
    for question in questions:
        session.add(question)
    session.commit()
    return questions


@pytest.fixture
def test_assessment_result(session, test_candidate, test_questions):
    """Create a test assessment result."""
    result = AssessmentResult(
        candidate_id=test_candidate.id,
        step=1,
        score=75.0,
        status='passed',
        answers='{"answer_1": "32", "answer_2": "O(log n)"}',
        time_taken=1800
    )
    session.add(result)
    session.commit()
    return result 