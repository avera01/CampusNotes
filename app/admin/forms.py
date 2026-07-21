from flask_wtf import FlaskForm


class EmptyForm(FlaskForm):
    """No visible fields -- just carries a CSRF token for one-click POST actions."""
    pass
