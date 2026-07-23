from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, IntegerField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

ALLOWED_EXTENSIONS = ["pdf", "doc", "docx", "png", "jpg", "jpeg"]


class UploadForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])
    tags = StringField("Tags (comma-separated)", validators=[Optional(), Length(max=300)])
    resource_type = SelectField(
        "Type",
        choices=[("notes", "Notes"), ("pyq", "Previous Year Question Paper"), ("syllabus", "Syllabus")],
    )
    # University is the only admin-managed catalog level, so it's a real dropdown
    # of existing rows (choices populated in the route). Course, Semester, and
    # Subject are all free text: the user types a name/number instead of picking
    # from a dropdown, and the route looks up or creates matching Course/Semester/
    # Subject rows under the chosen University/Course/Semester.
    university_id = SelectField("University", coerce=int, validators=[DataRequired()])
    course_name = StringField("Course", validators=[DataRequired(), Length(max=50)])
    semester_number = IntegerField("Semester", validators=[DataRequired(), NumberRange(min=1, max=20)])
    subject_name = StringField("Subject", validators=[DataRequired(), Length(max=150)])
    is_premium = BooleanField("Mark as Premium (locked content, no payment yet)")
    file = FileField(
        "File",
        validators=[FileRequired(), FileAllowed(ALLOWED_EXTENSIONS, "Unsupported file type")],
    )
    submit = SubmitField("Upload")
