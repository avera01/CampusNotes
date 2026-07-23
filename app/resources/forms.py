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
    # University is a plain (non-WTForms) select on the page, used only to narrow
    # down the Course dropdown via JS -- its value is never submitted. Course IS
    # submitted (its choices are populated client-side, so choice validation happens
    # manually in the route). Semester and Subject are free text: the user types a
    # semester number / subject name instead of picking from a dropdown, and the
    # route looks up or creates matching Semester/Subject rows under the chosen course.
    course_id = SelectField("Course", coerce=int, validate_choice=False)
    semester_number = IntegerField("Semester", validators=[DataRequired(), NumberRange(min=1, max=20)])
    subject_name = StringField("Subject", validators=[DataRequired(), Length(max=150)])
    is_premium = BooleanField("Mark as Premium (locked content, no payment yet)")
    file = FileField(
        "File",
        validators=[FileRequired(), FileAllowed(ALLOWED_EXTENSIONS, "Unsupported file type")],
    )
    submit = SubmitField("Upload")
