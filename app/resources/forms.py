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
    # University/Course/Semester are plain (non-WTForms) selects on the page, used only to
    # narrow down the Subject dropdown via JS. Subject is the only value actually submitted,
    # and its options are populated client-side, so choice validation is done manually in the route.
    subject_id = SelectField("Subject", coerce=int, validate_choice=False)
    is_premium = BooleanField("Mark as Premium (locked content, no payment yet)")
    file = FileField(
        "File",
        validators=[FileRequired(), FileAllowed(ALLOWED_EXTENSIONS, "Unsupported file type")],
    )
    submit = SubmitField("Upload")
