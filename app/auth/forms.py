from tokenize import String
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, ValidationError
from wtforms.validators import DataRequired, Email, Length, EqualTo

from .models import User


class LoginForm(FlaskForm):
    user_id = StringField("Username or Email", [DataRequired()])
    password = PasswordField("Password", [DataRequired()])
    submit = SubmitField("Login")


class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(2, 30)])
    email = StringField("Email Address", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(6, 30)])
    password_confirmation = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Password do not match."),
        ],
    )
    shortID = StringField("Short ID (XYZ)", validators=[DataRequired(), Length(3, 3)])
    submit = SubmitField("Register")

    def validate_username(form, field):
        if User.query.filter_by(username=field.data).first() is not None:
            raise ValidationError("This username is taken.")

    def validate_email(form, field):
        if User.query.filter_by(email=field.data).first() is not None:
            raise ValidationError("This email is already registered.")


class PasswordForm(FlaskForm):
    password = PasswordField("Password", validators=[DataRequired()])


class PasswordChangeForm(FlaskForm):
    password = PasswordField("Old Password", validators=[DataRequired()])
    new_password = PasswordField(
        "New Password", validators=[DataRequired(), Length(6, 30)]
    )
    new_password_confirmation = PasswordField(
        "Confirm new Password",
        validators=[
            DataRequired(),
            EqualTo("new_password", message="Password do not match."),
        ],
    )
    submit = SubmitField("Update")


class ProfileUpdateForm(FlaskForm):
    short_ID = StringField("Your short ID", validators=[Length(2, 3)])
    email = StringField("Email Address", validators=[Email()])
    password = PasswordField("Password for verification", validators=[DataRequired()])


class AddGroupForm(FlaskForm):
    name = StringField(
        "Group name",
        validators=[DataRequired()],
        render_kw={
            "placeholder": "Name of the new group",
            "class": "form-control me-2",
        },
    )
    submit = SubmitField(
        "Add",
        render_kw={
            "class": "btn btn-primary",
        },
    )
