from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

ALLOWED_EXTENSIONS = ["pdf", "doc", "docx", "png", "jpg", "jpeg"]


class UploadForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])
    tags = StringField("Tags (comma-separated)", validators=[Optional(), Length(max=300)])
    resource_type = SelectField(
        "Type",
        choices=[("notes", "Notes"), ("pyq", "Previous Year Question Paper"), ("syllabus", "Syllabus")],
    )
    # University/Course are plain (non-WTForms) selects on the page, used only to narrow
    # down the Semester dropdown via JS -- their values are never submitted. Semester IS
    # submitted (its choices are populated client-side, so choice validation happens
    # manually in the route). Subject is free text: the user types a subject name instead
    # of picking from a dropdown, and the route looks up or creates a matching Subject
    # under the chosen semester.
    semester_id = SelectField("Semester", coerce=int, validate_choice=False)
    subject_name = StringField("Subject", validators=[DataRequired(), Length(max=150)])
    is_premium = BooleanField("Mark as Premium (locked content, no payment yet)")
    file = FileField(
        "File",
        validators=[FileRequired(), FileAllowed(ALLOWED_EXTENSIONS, "Unsupported file type")],
    )
    submit = SubmitField("Upload")
