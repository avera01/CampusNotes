"""WTForms for signup/login. Flask-WTF gives us CSRF protection for free."""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed, FileSize
from wtforms import StringField, PasswordField, SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange

AVATAR_ALLOWED_EXTENSIONS = ["png", "jpg", "jpeg", "webp"]
AVATAR_MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5MB

USER_TYPE_CHOICES = [("student", "Student"), ("faculty", "Faculty")]


class SignupForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=150)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm password", validators=[DataRequired(), EqualTo("password", message="Passwords must match")]
    )
    user_type = SelectField("I am a", choices=USER_TYPE_CHOICES, validators=[DataRequired()])
    university_id = SelectField("University", coerce=int, validators=[Optional()])
    course_id = SelectField("Course", coerce=int, validators=[Optional()])
    current_semester = IntegerField("Current semester", validators=[Optional(), NumberRange(min=1, max=12)])
    submit = SubmitField("Sign up")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")


class ProfileForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(max=100)])
    user_type = SelectField("I am a", choices=USER_TYPE_CHOICES, validators=[DataRequired()])
    university_id = SelectField("University", coerce=int, validators=[Optional()])
    course_id = SelectField("Course", coerce=int, validators=[Optional()])
    current_semester = IntegerField("Current semester", validators=[Optional(), NumberRange(min=1, max=12)])
    submit = SubmitField("Save profile")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField("New password", validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField(
        "Confirm new password", validators=[DataRequired(), EqualTo("new_password", message="Passwords must match")]
    )
    submit = SubmitField("Change password")


class AvatarForm(FlaskForm):
    avatar = FileField(
        "Profile picture",
        validators=[
            FileRequired(),
            FileAllowed(AVATAR_ALLOWED_EXTENSIONS, "Unsupported image type -- use JPG, PNG, or WEBP."),
            FileSize(max_size=AVATAR_MAX_SIZE_BYTES, message="Image must be 5MB or smaller."),
        ],
    )
    submit = SubmitField("Upload picture")


class EmptyForm(FlaskForm):
    """No visible fields -- just carries a CSRF token for one-click POST actions."""
    pass
