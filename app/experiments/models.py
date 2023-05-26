from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from .. import db
from ..utils import ModelMixin
import builtins
import requests
import json
import io
from requests.exceptions import HTTPError
import pandas as pd
from flask import (
    url_for,
    redirect,
    flash,
    Response,
    abort,
)

from ..auth.models import User


### Association Tables ###

Parameters_in_Routines = db.Table(
    "association_Parameters_in_Routines",
    db.Model.metadata,
    db.Column(
        "experimental_routines_id",
        db.Integer,
        db.ForeignKey("experimental_routines.id"),
    ),
    db.Column("parameters_id", db.Integer, db.ForeignKey("parameters.id")),
)

Routines_in_Stations = db.Table(
    "association_Routines_in_Stations",
    db.Model.metadata,
    db.Column("Station_id", db.Integer, db.ForeignKey("stations.id")),
    db.Column(
        "experimental_routines_id",
        db.Integer,
        db.ForeignKey("experimental_routines.id"),
    ),
)


class ExperimentalRoutines(db.Model, ModelMixin):
    """This class is used to create experimental routines. Routines are not defined by the user but downloaded from a registred station. The user can then use the routines to create experiments."""

    __tablename__ = "experimental_routines"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=False, nullable=False)
    note = db.Column(db.String(60), unique=False, nullable=True)
    parameters = db.relationship(
        "Parameters",
        secondary=Parameters_in_Routines,
        lazy="subquery",
        backref=db.backref("parameters_in_routine", lazy=True),
    )

    @classmethod
    def add_routine(cls, name):
        """Add a new routine to the database.

        Args:
            name (str): The name of the routine.

        Returns:
            _type_: 'class'
        """
        routine = cls(name=name)
        db.session.add(routine)
        db.session.commit()
        return routine

    @classmethod
    def get_routine(cls, id):
        return cls.query.get_or_404(id)

    @classmethod
    def get_routines(cls):
        return cls.query.all()

    @classmethod
    def get_routine_name_by_id(cls, id):
        return cls.query.get_or_404(id).name

    @classmethod
    def get_parameter_names_in_routine_by_id(cls, id):
        return [parameter.name for parameter in cls.query.get_or_404(id).parameters]

    @classmethod
    def get_dynamic_parameter_names_in_routine_by_id(cls, id):
        return [
            parameter.name
            for parameter in cls.query.get_or_404(id).parameters
            if not parameter.static_param
        ]

    @classmethod
    def get_parameters_in_routine_by_id(cls, id):
        return cls.query.get_or_404(id).parameters

    @classmethod
    def get_static_parameters_in_routine_by_id(cls, id):
        return [
            parameter
            for parameter in cls.query.get_or_404(id).parameters
            if parameter.static_param
        ]

    @classmethod
    def get_dynamic_parameters_in_routine_by_id(cls, id):
        return [
            parameter
            for parameter in cls.query.get_or_404(id).parameters
            if not parameter.static_param
        ]

    @classmethod
    def get_dict_of_parameter_names_and_ids_in_routine_by_id(cls, id):
        return {
            parameter.name: parameter.id for parameter in cls.get_routine(id).parameters
        }

    @classmethod
    def get_routine_by_name(cls, name):
        return cls.query.filter_by(name=name).first()

    def get_sanitized_name(self):
        return self.name.replace("\t", "").replace("\n", "").replace("\r", "")

    def update_routine(self, id, name, note, parameters):
        routine = self.query.get(id)
        routine.name = name
        routine.note = note
        routine.parameters = parameters
        db.session.commit()

    def delete_routine(self, id):
        routine = self.query.get(id)
        db.session.delete(routine)
        db.session.commit()

    def set_parameters(self, parameters):
        self.parameters = parameters
        db.session.commit()

    def add_parameter(self, parameter):
        self.parameters.append(parameter)
        db.session.commit()

    def get_parameters_in_routine(self):
        return self.parameters

    def get_parameter_names_in_routine(self):
        return [parameter.name for parameter in self.parameters]

    def get_static_parameters_in_routine(self):
        return [parameter for parameter in self.parameters if parameter.static_param]

    def get_dynamic_parameter_names_in_routine(self):
        return [
            parameter.name
            for parameter in self.parameters
            if not parameter.static_param
        ]

    def get_parameter_ids_in_routine(self):
        return [parameter.id for parameter in self.parameters]

    @classmethod
    def get_list_of_routine_names(cls):
        return [routine.name for routine in cls.get_routines()]


class ExperimentalRuns(db.Model, ModelMixin):
    __tablename__ = "experimental_runs"

    id = db.Column(db.Integer, primary_key=True)
    stage_id = db.Column(db.Integer, db.ForeignKey("stage.id"), nullable=False)
    status = db.Column(db.Integer, default=0, unique=False, nullable=False)
    run_values = db.relationship(
        "Values", backref="experimental_runs", lazy=True, cascade="all,delete"
    )

    @classmethod
    def add_new_run(cls, stage_id, status=0):
        run = cls(stage_id=stage_id, status=status)
        db.session.add(run)
        db.session.commit()
        return run

    def set_status(self, status):
        self.status = status
        self.save()

    def add_values_to_run(self, run_values):
        self.run_values.append(run_values)
        self.save()

    @classmethod
    def get_run_by_id(cls, id):
        return cls.query.get_or_404(id)

    def get_parameter_value_pairs_in_run_dynamic_only(self):
        dynamic_parameters_in_routine = (
            Stage.get_stage_by_id(self.stage_id)
            .get_experimental_routine()
            .get_dynamic_parameter_names_in_routine()
        )
        parameter_value_pairs = [
            value.get_parameter_value_pair() for value in self.run_values
        ]

        # get only the dynamic parameters
        parameter_value_pairs = [
            pair
            for pair in parameter_value_pairs
            if pair[0] in dynamic_parameters_in_routine
        ]

        # sort the parameter_value_pairs by the order of parameters in the routine
        parameter_value_pairs.sort(  # sort by the first element of the tuple
            key=lambda x: dynamic_parameters_in_routine.index(x[0])
        )
        return parameter_value_pairs

    def get_parameter_value_pairs_in_run(self):
        parameters_in_routine = (
            Stage.get_stage_by_id(self.stage_id)
            .get_experimental_routine()
            .get_parameter_names_in_routine()
        )
        parameter_value_pairs = [
            value.get_parameter_value_pair() for value in self.run_values
        ]
        # sort the parameter_value_pairs by the order of parameters in the routine
        parameter_value_pairs.sort(  # sort by the first element of the tuple
            key=lambda x: parameters_in_routine.index(x[0])
        )
        return parameter_value_pairs


class Parameters(db.Model, ModelMixin):
    __tablename__ = "parameters"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=False, nullable=False)
    unit = db.Column(db.String(60), unique=False, nullable=False)
    note = db.Column(db.String(60), unique=False, nullable=True)
    data_type = db.Column(db.String(10), unique=False, nullable=False)
    static_param = db.Column(db.Boolean, default=False, unique=False, nullable=False)
    values = db.relationship("Values", backref="parameters", lazy=True)
    default_value = db.Column(db.Float, unique=False, nullable=False, default=0.0)

    @classmethod
    def get_parameter(cls, id):
        return cls.query.get_or_404(id)

    def get_parameters(self):
        return self.query.all()

    @classmethod
    def get_all_static_parameters(cls):
        return cls.query.filter_by(static_param=True).all()

    def update_parameter(self, id, name, unit, note, data_type, static_param):
        parameter = self.query.get(id)
        parameter.name = name
        parameter.unit = unit
        parameter.note = note
        parameter.data_type = data_type
        parameter.static_param = static_param
        db.session.commit()

    def toggle_static_parameter(self):
        self.static_param = not self.static_param
        db.session.commit()

    def delete_parameter(self, id):
        parameter = self.query.get(id)
        db.session.delete(parameter)
        db.session.commit()

    def set_default_value(self, value):
        def _cast_by_dtype_name(var):
            if type(var) == str:
                var = var.replace(",", ".")
            trusted_types = ["int", "float", "complex", "bool", "str"]
            if self.data_type in trusted_types:
                if self.data_type == "int":
                    return getattr(builtins, self.data_type)(float(round(var)))
                return getattr(builtins, self.data_type)(var)
            return var

        self.default_value = _cast_by_dtype_name(value)
        db.session.commit()

    def get_default_value(self):
        def _cast_by_dtype_name(var):
            trusted_types = ["int", "float", "complex", "bool", "str"]
            if self.data_type in trusted_types:
                if self.data_type == "int":
                    return getattr(builtins, self.data_type)(float(var))
                return getattr(builtins, self.data_type)(var)
            return var

        return _cast_by_dtype_name(self.default_value)

    def get_if_static_param(self):
        return self.static_param


class ExperimentalDesign(db.Model, ModelMixin):
    __tablename__ = "experimental_design"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey("stations.id"))
    stages = db.relationship(
        "Stage",
        backref="experimental_design",
        lazy=True,
        cascade="all, delete-orphan",
    )
    shared_users = db.relationship(
        "User",
        secondary="shared_designs",
        backref=db.backref("shared_designs", lazy="dynamic"),
    )

    @classmethod
    def add_experimental_design(cls, name, user_id, station_id):
        safe_name = (
            name.replace("\t", " ")
            .replace("\n", " ")
            .replace("\r", " ")
            .replace("  ", "")
        )
        design = cls(name=safe_name, user_id=user_id, station_id=station_id)
        design.save()
        flash("Successfuly added new experimental design.", "success")

    @classmethod
    def get_experimental_designs(cls):
        return cls.query.all()

    @classmethod
    def get_experimental_design_by_id(cls, id):
        return cls.query.get_or_404(id)

    @classmethod
    def get_station_id_by_design_id(cls, id):
        return cls.query.get_or_404(id).station_id

    @classmethod
    def get_designs_by_user(cls, user_id):
        return cls.query.filter_by(user_id=user_id).all()

    @classmethod
    def get_shared_designs(cls, user_id):
        return cls.query.filter(cls.shared_users.any(id=user_id)).all()

    @classmethod
    def get_all_designs_for_user(cls, user_id):
        return cls.get_designs_by_user(user_id) + cls.get_shared_designs(user_id)

    def get_experimental_stages(self):
        return self.stages

    def get_experimental_station(self):
        return ExperimentalStation.get_station_by_id(self.station_id)

    def get_owner_name(self):
        return User.get_user_by_token(self.user_id).username

    def share_with_user(self, user):
        if user not in self.shared_users:
            self.shared_users.append(user)
            db.session.commit()

    def remove_user_share(self, user):
        if user in self.shared_users:
            self.shared_users.remove(user)
            db.session.commit()

    def share_with_group(self, group):
        if group not in self.shared_groups:
            self.shared_groups.append(group)
            db.session.commit()

    def remove_group_share(self, group):
        if group in self.shared_groups:
            self.shared_groups.remove(group)
            db.session.commit()


class Stage(db.Model, ModelMixin):
    __tablename__ = "stage"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    experimental_runs = db.relationship(
        "ExperimentalRuns",
        backref="stage",
        cascade="all, delete-orphan",
        lazy=True,
    )
    experimental_Routine_id = db.Column(
        db.Integer, db.ForeignKey("experimental_routines.id"), nullable=False
    )
    status = db.Column(db.Integer, default=0)
    experimental_design_id = db.Column(
        db.Integer, db.ForeignKey("experimental_design.id"), nullable=False
    )

    @classmethod
    def get_stage_by_id(cls, id):
        return cls.query.get_or_404(id)

    @classmethod
    def get_design(cls, id):
        return cls.query.get_or_404(id)

    @classmethod
    def add_stage(cls, name, user_id, experimental_Routine_id, experimental_design_id):
        safe_name = (
            name.replace("\t", " ")
            .replace("\n", " ")
            .replace("\r", " ")
            .replace("  ", "")
        )
        stage = cls(
            name=safe_name,
            user_id=user_id,
            experimental_Routine_id=experimental_Routine_id,
            experimental_design_id=experimental_design_id,
        )
        stage.save()
        flash("Successfuly added new experimental stage.", "success")

    def get_designs(self):
        return self.query.all()

    def get_owner_name(self):
        return User.get_user_by_token(self.user_id).username

    def update_design(self, name):
        self.name = name
        self.save()

    def delete_design(self, id):
        design = self.query.get(id)
        design.delete()

    def set_status(self, status):
        self.status = status
        self.save()

    def get_status(self):
        return self.status

    def get_sanitized_name(self):
        return self.name.replace("\t", "").replace("\n", "").replace("\r", "")

    def get_design(
        self,
    ):
        return ExperimentalDesign.get_experimental_design_by_id(
            self.experimental_design_id
        )

    def get_experimental_station(self):
        design = self.get_design()
        station = design.get_experimental_station()
        return station

    def get_experimental_routine(self):
        return ExperimentalRoutines.get_routine(self.experimental_Routine_id)

    def get_experimental_routine_name(self):
        return ExperimentalRoutines.get_routine_name_by_id(self.experimental_Routine_id)

    def get_designs_by_user(self, user_id):
        return self.query.filter_by(user_id=user_id).all()

    def get_designs_by_station(self, station_id):
        return self.query.filter_by(station_id=station_id).all()

    def get_designs_by_user_and_station(self, user_id, station_id):
        return self.query.filter_by(user_id=user_id, station_id=station_id).all()

    def get_runs_in_stage(self):
        return self.experimental_runs

    def get_run_ids_in_stage(self):
        return [run.id for run in self.experimental_runs]

    def sent_all_runs_to_station(self):
        run_data_to_send = self.sent_runs_to_station_by_ids(self.get_run_ids_in_stage())

    def add_or_update_run(self, run_data, parameter_in_routine):
        if run_data.run_id == "" or pd.isna(run_data.run_id):
            new_run = ExperimentalRuns.add_new_run(stage_id=self.id)
            for parameter_name, value in run_data.items():
                if parameter_name == "run_id":
                    pass
                else:
                    parameter = [
                        parameter
                        for parameter in parameter_in_routine
                        if parameter.name == parameter_name
                    ][0]

                    new_value = Values.add_value(
                        value=value,
                        parameter_id=parameter.id,
                        experimental_run_id=new_run.id,
                    )
                    new_run.add_values_to_run(new_value)

        else:
            run_to_update = ExperimentalRuns.get_run_by_id(int(run_data.run_id))
            for parameter_name, value in run_data.items():
                if parameter_name == "run_id":
                    pass
                else:
                    parameter = [
                        parameter
                        for parameter in parameter_in_routine
                        if parameter.name == parameter_name
                    ][0]
                    value_to_update = Values.get_value_by_run_id_and_parameter_id(
                        run_to_update.id, parameter.id
                    )
                    value_to_update.update_value(value)

    def add_or_update_runs_from_excel_upload(self, excel_file, dynamic_only):
        """accepts an excel file and adds the data to the stage

        Args:
            excel_file (_type_): _description_
            dynamic_only (bool): switch to toggel between dynamic only and all parameters

        Returns:
            _type_: _description_
        """

        try:
            # read the excel file into a dataframe
            df = pd.read_excel(excel_file)

            # if no run_id column is present, add it with empty values
            if not "run_id" in df.columns:
                df["run_id"] = ""

            # check if the dataframe contails empty values (exept for run_id column)
            parameters_with_missing_values = (
                df.loc[:, df.columns != "run_id"].isna().any()
            )
            for parameter, missing in parameters_with_missing_values.iteritems():
                # this gets only the first occuring error #TODO: add all errors
                if missing:
                    flash(
                        f"The parameter {parameter} contains empty values. Please check the dataset and try again.",
                        "danger",
                    )
                    raise Exception(f"The parameter {parameter} contains empty values.")

            ### check if all parameters in the dataframe are present in the routine
            ### get the parameter names in the routine
            if dynamic_only:
                parameter_names_in_routine = (
                    ExperimentalRoutines.get_dynamic_parameter_names_in_routine_by_id(
                        self.experimental_Routine_id
                    )
                )
                parameters_in_routine = (
                    ExperimentalRoutines.get_dynamic_parameters_in_routine_by_id(
                        self.experimental_Routine_id
                    )
                )
            else:
                parameter_names_in_routine = (
                    ExperimentalRoutines.get_parameter_names_in_routine_by_id(
                        self.experimental_Routine_id
                    )
                )
                parameters_in_routine = (
                    ExperimentalRoutines.get_parameters_in_routine_by_id(
                        self.experimental_Routine_id
                    )
                )
            # add the run_id column to the list of parameter names
            parameter_names_in_routine.insert(0, "run_id")

            # check if all parameters in the dataframe are present in the routine
            if not all(
                item in parameter_names_in_routine for item in df.columns.tolist()
            ):
                flash(
                    "The dataset contains parameters that are not present in the routine. Please check the dataset and try again.",
                    "danger",
                )
                raise Exception(
                    "The dataset contains parameters that are not present in the routine."
                )

            # check if the number of parameters in the dataframe matches the number of parameters in the routine
            if (len(df.columns)) != len(parameter_names_in_routine):
                flash(
                    "The number of parameters in the dataset does not match the number of parameters in the routine. Please check the dataset and try again.",
                    "danger",
                )
                raise Exception(
                    "The number of parameters in the dataset does not match the number of parameters in the routine."
                )

            df.apply(
                self.add_or_update_run,
                parameter_in_routine=parameters_in_routine,
                axis=1,
            )

        except Exception as e:
            flash(
                f"There was an error during the call. \n Error Code: {e}",
                "danger",
            )
            return redirect(url_for("experiments.edit_stage", stage_id=self.id))

    def get_excel_file_for_stage_dl(self, dynamic_only):
        """_summary_

        Args:
            dynamic_only (bool): switch to toggel between dynamic only and all parameters

        Returns:
            _type_: _description_
        """
        ## if no runs present in stage, return a blank table with the correct headers
        if len(self.get_runs_in_stage()) == 0:
            if dynamic_only:
                parameter_list = (
                    ExperimentalRoutines.get_dynamic_parameter_names_in_routine_by_id(
                        self.experimental_Routine_id
                    )
                )
            else:
                parameter_list = (
                    ExperimentalRoutines.get_parameter_names_in_routine_by_id(
                        self.experimental_Routine_id
                    )
                )
            # add the run_id column to the list of parameters
            parameter_list.insert(0, "run_id")
            parameter_value_pairs_in_stage = [
                [(parameter, "")] for parameter in parameter_list
            ]
        # if runs present in stage, get the parameter value pairs for each run
        else:
            if dynamic_only:
                # nested list comprehension to get the parameter value pairs for each run in the stage,
                parameter_value_pairs_in_stage = [
                    [("run_id", run.id)]
                    + [
                        value
                        for value in run.get_parameter_value_pairs_in_run_dynamic_only()
                    ]
                    for run in self.get_runs_in_stage()
                ]
            else:
                parameter_value_pairs_in_stage = [
                    [("run_id", run.id)]
                    + [value for value in run.get_parameter_value_pairs_in_run()]
                    for run in self.get_runs_in_stage()
                ]

        data_list = []
        for lst in parameter_value_pairs_in_stage:
            run_dict = {}
            for tup in lst:
                run_dict[tup[0]] = tup[1]
            data_list.append(run_dict)

        # Create the dataframe
        df = pd.DataFrame(data_list)

        ## define a buffer to store dataframe excel output in
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)

        # alter the filename to inform about the dynamic_only parameter

        if dynamic_only:
            filename = f"{self.get_sanitized_name()}_dynamic_parameters.xlsx"
        else:
            filename = f"{self.get_sanitized_name()}_all_parameters.xlsx"

        ## prepare headers for the download file to return to the browser
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-type": "application/vnd.ms-excel",
        }
        ## return buffer and header informations
        return Response(
            buffer.getvalue(), mimetype="application/vnd.ms-excel", headers=headers
        )

    def get_dataframe_with_runs_in_stage(self):
        runs = self.get_runs_in_stage()
        df = pd.DataFrame()
        for run in runs:
            df = df.append(run.get_parameter_value_pairs_in_run(), ignore_index=True)
        return df

    def sent_runs_to_station_by_ids(self, runs_ids):
        for run_id in runs_ids:
            run = ExperimentalRuns.get_run_by_id(run_id)
            design = ExperimentalDesign.get_experimental_design_by_id(
                self.experimental_design_id
            )
            station = ExperimentalStation.get_station_by_id(design.station_id)

            ## build run id from design name - stage name - run id
            run_id = f"{design.name}-{self.get_sanitized_name()}-{run.id}"

            experiment_meta_data = {
                "experiment_id": run_id,
                "experiment_type": ExperimentalRoutines.get_routine_name_by_id(
                    self.experimental_Routine_id
                ),
            }

            experiment_data = dict(run.get_parameter_value_pairs_in_run())

            joined_data = experiment_meta_data | experiment_data

            try:
                request_url = f"http://{station.address}/api/add_experiment"
                r = requests.post(request_url, data=joined_data)
                r.raise_for_status()

            except HTTPError as http_err:
                flash(
                    f"There was an error during the call.\n Error message from the station: {r.text} \n Error Code HTTP: {http_err}",
                    "danger",
                )
                abort(500)
            except requests.exceptions.RequestException as e:
                flash(
                    f"There was an error during the call.\n Error message from the station: {r.text} \n Error Code: {e}",
                    "danger",
                )
                abort(500)
            else:
                flash(
                    f"Experiment {run.id} was sent to station {station.name} successfully.",
                    "success",
                )
                run.set_status(1)

        return experiment_meta_data | experiment_data


class ParameterAliases(db.Model):
    """deprecated in future"""

    __tablename__ = "parameterAliases"

    id = db.Column(db.Integer, primary_key=True)
    param_from_cfg = db.Column(db.String(60), unique=False, nullable=False)
    param_alias = db.Column(db.String(60), unique=False, nullable=True)


class Values(db.Model, ModelMixin):
    __tablename__ = "values"

    id = db.Column(db.Integer, primary_key=True)
    parameter_id = db.Column(db.Integer, db.ForeignKey("parameters.id"), nullable=False)
    value_as_str = db.Column(db.String(100), unique=False, nullable=False)
    experimental_runs_id = db.Column(
        db.Integer, db.ForeignKey("experimental_runs.id"), nullable=False
    )

    @hybrid_property
    def value(self):
        def _cast_by_dtype_name(data_type, var):
            trusted_types = ["int", "float", "complex", "bool", "str"]
            if data_type in trusted_types:
                if data_type == "int":
                    return getattr(builtins, data_type)(float(var))
                return getattr(builtins, data_type)(var)
            return var

        parameter = Parameters.get_parameter(self.parameter_id)

        return _cast_by_dtype_name(parameter.data_type, self.value_as_str)

    def get_parameter_value_pair(self):
        parameter = Parameters.get_parameter(self.parameter_id)
        if parameter.get_if_static_param():
            return parameter.name, parameter.get_default_value()
        else:
            return (parameter.name, self.value)

    def get_parameter_value_dict(self):
        parameter = Parameters.get_parameter(self.parameter_id)
        if parameter.get_if_static_param():
            return {parameter.name: parameter.get_default_value()}
        else:
            return {parameter.name: self.value}

    def update_value(self, value):
        self.value_as_str = str(value)
        self.save()

    @classmethod
    def add_value(cls, parameter_id, value, experimental_run_id):
        new_value = cls(
            parameter_id=parameter_id,
            value_as_str=str(value),
            experimental_runs_id=experimental_run_id,
        )
        new_value.save()
        return new_value

    @classmethod
    def get_value_by_run_id_and_parameter_id(cls, run_id, parameter_id):
        return cls.query.filter_by(
            experimental_runs_id=run_id, parameter_id=parameter_id
        ).first()


class ExperimentalStation(db.Model, ModelMixin):
    __tablename__ = "stations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=False, nullable=False)
    address = db.Column(db.String(60), unique=False, nullable=False)
    api_key = db.Column(db.String(60), unique=False, nullable=False)
    location = db.Column(db.String(60), unique=False, nullable=False)
    experiments_available = db.relationship(
        "ExperimentalRoutines",
        secondary=Routines_in_Stations,
        lazy="subquery",
        backref=db.backref("stations", lazy=True),
    )

    @classmethod
    def get_station_by_id(cls, station_id):
        return cls.query.get_or_404(station_id)

    @classmethod
    def get_address_address(cls, station_id):
        station = cls.query.get_or_404(station_id)
        return station.address

    @classmethod
    def get_all_stations(cls):
        return cls.query.all()

    def get_all_routines(self):
        return self.experiments_available

    @classmethod
    def get_all_routines_by_station_id(cls, station_id):
        station = cls.query.get_or_404(station_id)
        return station.get_all_routines()

    @classmethod
    def get_all_routine_names_by_station_id(cls, station_id):
        station = cls.query.get_or_404(station_id)
        return [routine.name for routine in station.get_all_routines()]

    def register_routine_in_station(self, routine):
        self.experiments_available.append(routine)
        db.session.commit()

    def unregister_routine_in_station(self, routine):
        self.experiments_available.remove(routine)
        db.session.commit()

    def update(self, name, address, api_key, location):
        self.name = name
        self.address = address
        self.api_key = api_key
        self.location = location
        self.save()

    @classmethod
    def get_active_experiment_parameters(cls, station_id):
        request_url = (
            f"http://{cls.get_address_address(station_id)}/api/station_run_tables"
        )
        r = requests.get(request_url)
        json_data_stream = json.loads(r.content.decode())
        for run in json_data_stream:
            if run["state"] == "Running":
                return run["parameters"]
        return None

    @classmethod
    def get_active_experiment_value_for_parameter(cls, station_id, parameter_name):
        request_url = (
            f"http://{cls.get_address_address(station_id)}/api/station_run_tables"
        )
        r = requests.get(request_url)
        json_data_stream = json.loads(r.content.decode())
        for run in json_data_stream:
            if run["state"] == "Running":
                for parameter in run["parameters"]:
                    if parameter == parameter_name:
                        return run["parameters"]
        return "None", 202


class ExperimentalResultTypes(db.Model, ModelMixin):
    __tablename__ = "experimental_result_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=False, nullable=False)
    unit = db.Column(db.String(60), unique=False, nullable=False)
    experimental_results = db.relationship(
        "ExperimentalResults",
        backref="experimental_result_types",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def get_result_names(self):
        result_names = []
        for result in self.experimental_results:
            result_names.append(result.experimental_result_types.name)
        return result_names


class ExperimentalResults(db.Model, ModelMixin):
    __tablename__ = "experimental_results"

    id = db.Column(db.Integer, primary_key=True)
    experimental_runs_id = db.Column(
        db.Integer, db.ForeignKey("experimental_runs.id"), nullable=False
    )
    value = db.Column(db.String(60), unique=False, nullable=False)
    experimental_result_types_id = db.Column(
        db.Integer, db.ForeignKey("experimental_result_types.id"), nullable=False
    )

    @classmethod
    def _set_ExperimentalResult(cls, experimentalResultTypes_id, result_value, run_id):
        result = ExperimentalResults(
            experimental_runs_id=run_id,
            value=result_value,
            experimental_result_types_id=experimentalResultTypes_id,
        )
        db.session.add(result)
        db.session.commit()
        return result
