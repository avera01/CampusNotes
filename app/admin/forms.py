from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class EmptyForm(FlaskForm):
    """No visible fields -- just carries a CSRF token for one-click POST actions."""
    pass


class UniversityForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=150)])
    code = StringField("Code (short, unique)", validators=[DataRequired(), Length(max=20)])
    location = StringField("Location", validators=[Optional(), Length(max=150)])
    submit = SubmitField("Add university")


class CourseForm(FlaskForm):
    university_id = SelectField("University", coerce=int, validators=[DataRequired()])
    name = StringField("Name (e.g. BCA)", validators=[DataRequired(), Length(max=50)])
    full_name = StringField("Full name (optional)", validators=[Optional(), Length(max=150)])
    total_semesters = IntegerField("Total semesters", default=6, validators=[DataRequired(), NumberRange(min=1, max=12)])
    submit = SubmitField("Add course")


class SemesterForm(FlaskForm):
    course_id = SelectField("Course", coerce=int, validators=[DataRequired()])
    number = IntegerField("Semester number", validators=[DataRequired(), NumberRange(min=1, max=12)])
    submit = SubmitField("Add semester")


class SubjectForm(FlaskForm):
    semester_id = SelectField("Semester", coerce=int, validators=[DataRequired()])
    name = StringField("Name (e.g. Data Structures)", validators=[DataRequired(), Length(max=150)])
    code = StringField("Code (optional)", validators=[Optional(), Length(max=20)])
    submit = SubmitField("Add subject")
