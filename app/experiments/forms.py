from ast import Str
from flask import Flask
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SubmitField,
    FieldList,
    FormField,
    SelectField,
    IntegerField,
    BooleanField,
)
from wtforms.validators import DataRequired, InputRequired


class NewStationForm(FlaskForm):
    station_name = StringField("Name of the new station", [DataRequired()])
    station_dns = StringField("DNS Name of the new station", [DataRequired()])
    station_location = StringField("Location of the new station", [DataRequired()])
    station_api_key = StringField("API-Key", [DataRequired()])
    submit = SubmitField("Create new")


class ParameterForm(FlaskForm):
    param_name = StringField("Parameter name")
    param_note = StringField("Note for the paramter")
    param_dtype = SelectField(
        "SQL datatype",
        coerce=Str,
        choices=["Float", "Integer", "String", "Boolean"],
        validate_choice=False,
    )
    param_unit = StringField("Parameter unit")


class StationConfigForm(FlaskForm):
    config_name = StringField("Name of the configuration", [DataRequired()])
    config_table_name = StringField("SQL table name", [DataRequired()])
    station_channels = IntegerField(
        "Number of possible channels (min = 1).", [DataRequired()]
    )
    doe_identifier_column = BooleanField(
        "Do you want to create identifier colums like block or DoE-pointtype?",
        default=True,
    )
    station_parameters = FieldList(FormField(ParameterForm))
    submit = SubmitField("Create Configuration")


class NewExperimentalDesign(FlaskForm):
    design_name = StringField("Name of the new experimental desing", [DataRequired()])
    station = SelectField("Select Station", coerce=int, validators=[InputRequired()])
    submit = SubmitField("Create Configuration")


class NewExperimentalStage(FlaskForm):
    stage_name = StringField(
        "Name of the new experimental stage",
        [DataRequired()],
        render_kw={"placeholder": "Name - New stage"},
    )
    experimental_routine = SelectField(
        "Select Routine",
        coerce=int,
        validators=[InputRequired()],
        render_kw={"placeholder": "Select Routine"},
    )
    submit = SubmitField("Create Stage")
