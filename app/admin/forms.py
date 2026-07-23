from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class EmptyForm(FlaskForm):
    """No visible fields -- just carries a CSRF token for one-click POST actions."""
    pass


class UniversityForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=150)])
    code = StringField("Code (short, unique)", validators=[DataRequired(), Length(max=20)])
    submit = SubmitField("Add university")
