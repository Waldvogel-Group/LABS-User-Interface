from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, ValidationError, FieldList, FormField, SelectField, widgets, SelectMultipleField, IntegerField, Label, BooleanField
from wtforms.fields.simple import HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo


from .models import Plotter
