"""Populate the database with sample data for local development/testing.

Usage (after the database has been created, see README):
    python seed.py

Safe to re-run: existing rows are looked up by their unique fields and left
untouched rather than duplicated.
"""
from app import create_app
from app.extensions import db
from app.models import University, Course, Semester, Subject, User

# NOTE: this is illustrative sample data for local testing, not a scraped or
# verified copy of Nagaland University's actual current course/subject
# catalog -- swap in real curriculum data before using this for real students.

BCA_SUBJECTS = {
    1: ["Programming in C", "Mathematics I", "Digital Electronics", "Communication Skills"],
    2: ["C++ Programming", "Data Structures", "Mathematics II", "Computer Organization"],
    3: ["DBMS", "Operating Systems", "Object Oriented Analysis and Design", "Java Programming"],
    4: ["Computer Networks", "Software Engineering", "Web Technologies", "Python Programming"],
    5: ["Advanced DBMS", "Artificial Intelligence", "Mobile Application Development", "Cloud Computing"],
    6: ["Machine Learning", "Project Work", "Elective: Cyber Security", "Elective: Data Analytics"],
}

BSC_SUBJECTS = {
    1: ["Mathematics I", "Physics I", "Chemistry I"],
    2: ["Mathematics II", "Physics II", "Chemistry II"],
    3: ["Mathematics III", "Statistics", "Environmental Science"],
    4: ["Numerical Methods", "Differential Equations", "Computer Applications"],
    5: ["Real Analysis", "Elective I", "Elective II"],
    6: ["Complex Analysis", "Project Work", "Elective III"],
}

BA_SUBJECTS = {
    1: ["English I", "Political Science I", "History I"],
    2: ["English II", "Political Science II", "History II"],
    3: ["Sociology I", "Economics I", "Public Administration I"],
    4: ["Sociology II", "Economics II", "Public Administration II"],
    5: ["Elective I", "Elective II"],
    6: ["Elective III", "Project Work"],
}

BCOM_SUBJECTS = {
    1: ["Financial Accounting I", "Business Organisation", "Business Communication"],
    2: ["Financial Accounting II", "Business Law", "Micro Economics"],
    3: ["Corporate Accounting", "Income Tax", "Macro Economics"],
    4: ["Cost Accounting", "Company Law", "Banking and Insurance"],
    5: ["Auditing", "Elective I", "Elective II"],
    6: ["Management Accounting", "Project Work", "Elective III"],
}

BBA_SUBJECTS = {
    1: ["Principles of Management", "Business Mathematics", "Financial Accounting"],
    2: ["Organisational Behaviour", "Business Statistics", "Marketing Management"],
    3: ["Human Resource Management", "Financial Management", "Business Environment"],
    4: ["Production Management", "Research Methodology", "Consumer Behaviour"],
    5: ["Strategic Management", "Elective I", "Elective II"],
    6: ["Entrepreneurship Development", "Project Work", "Elective III"],
}

MA_SUBJECTS = {
    1: ["Advanced English Studies", "Research Methodology"],
    2: ["Literary Criticism", "Elective I"],
    3: ["Dissertation Phase I", "Elective II"],
    4: ["Dissertation Phase II", "Elective III"],
}

MSC_SUBJECTS = {
    1: ["Advanced Mathematics", "Research Methodology"],
    2: ["Numerical Analysis", "Elective I"],
    3: ["Dissertation Phase I", "Elective II"],
    4: ["Dissertation Phase II", "Elective III"],
}

MCA_SUBJECTS = {
    1: ["Advanced Data Structures", "Advanced DBMS"],
    2: ["Software Engineering", "Computer Networks"],
    3: ["Cloud Computing", "Machine Learning"],
    4: ["Project Work", "Elective"],
}

MCOM_SUBJECTS = {
    1: ["Advanced Financial Accounting", "Managerial Economics"],
    2: ["Advanced Cost Accounting", "Elective I"],
    3: ["Corporate Tax Planning", "Elective II"],
    4: ["Dissertation", "Elective III"],
}

MBA_SUBJECTS = {
    1: ["Principles of Management", "Managerial Economics"],
    2: ["Financial Management", "Marketing Management"],
    3: ["Strategic Management", "Elective I"],
    4: ["Project Work", "Elective II"],
}


def get_or_create(model, defaults=None, **filters):
    instance = model.query.filter_by(**filters).first()
    if instance:
        return instance
    instance = model(**filters, **(defaults or {}))
    db.session.add(instance)
    db.session.flush()  # assigns instance.id so it can be used as a FK below
    return instance


def seed_course(university, name, full_name, subjects_by_semester, total_semesters=6):
    course = get_or_create(
        Course,
        name=name,
        university_id=university.id,
        defaults={"full_name": full_name, "total_semesters": total_semesters},
    )
    for number in range(1, total_semesters + 1):
        semester = get_or_create(Semester, course_id=course.id, number=number)
        for subject_name in subjects_by_semester.get(number, []):
            get_or_create(Subject, semester_id=semester.id, name=subject_name)
    return course


def seed_users():
    # NOTE: use a real-looking TLD here -- the Email() validator (via the
    # email-validator package) rejects .local/.test/.invalid as reserved
    # special-use domains, so seeded accounts using those would exist in the
    # DB but be unable to log in through the actual login form.
    if not User.query.filter_by(email="admin@campusnotes.edu").first():
        admin = User(name="CampusNotes Admin", email="admin@campusnotes.edu", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)

    if not User.query.filter_by(email="student@campusnotes.edu").first():
        student = User(name="Test Student", email="student@campusnotes.edu", role="student")
        student.set_password("student123")
        db.session.add(student)


def run():
    app = create_app()
    with app.app_context():
        db.create_all()

        university = get_or_create(
            University,
            code="NU",
            defaults={"name": "Nagaland University"},
        )

        # Undergraduate (3-year, 6 semesters)
        seed_course(university, "BCA", "Bachelor of Computer Applications", BCA_SUBJECTS)
        seed_course(university, "BSc", "Bachelor of Science", BSC_SUBJECTS)
        seed_course(university, "BA", "Bachelor of Arts", BA_SUBJECTS)
        seed_course(university, "BCom", "Bachelor of Commerce", BCOM_SUBJECTS)
        seed_course(university, "BBA", "Bachelor of Business Administration", BBA_SUBJECTS)

        # Postgraduate (2-year, 4 semesters)
        seed_course(university, "MA", "Master of Arts", MA_SUBJECTS, total_semesters=4)
        seed_course(university, "MSc", "Master of Science", MSC_SUBJECTS, total_semesters=4)
        seed_course(university, "MCA", "Master of Computer Applications", MCA_SUBJECTS, total_semesters=4)
        seed_course(university, "MCom", "Master of Commerce", MCOM_SUBJECTS, total_semesters=4)
        seed_course(university, "MBA", "Master of Business Administration", MBA_SUBJECTS, total_semesters=4)

        seed_users()

        db.session.commit()
        print("Seed complete.")
        print("  Admin login:   admin@campusnotes.edu / admin123")
        print("  Student login: student@campusnotes.edu / student123")


if __name__ == "__main__":
    run()
