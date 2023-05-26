from flask import (
    Blueprint,
    render_template,
    url_for,
    redirect,
    flash,
    request,
    abort,
    session,
)
from flask_login import login_required, current_user
from .helper import get_if_xlsx_file

# from datetime import datetime
from flask import jsonify
from .. import db
import json
from .forms import (
    NewStationForm,
    NewExperimentalDesign,
    NewExperimentalStage,
)
from .models import (
    ExperimentalStation,
    Stage,
    ExperimentalDesign,
    ExperimentalRoutines,
    Parameters,
    ExperimentalRuns,
    Values,
)
import requests
from sqlalchemy import (
    MetaData,
)
from sqlalchemy.orm import sessionmaker
from app.auth.models import Group, User
from .helper import roles_required


experiments_blueprint = Blueprint("experiments", __name__)


@experiments_blueprint.route("/experiments")
@login_required
def experimentsOverview():
    return render_template("experiments/overview.html")


@experiments_blueprint.route("/new_station", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def add_new_station():
    form = NewStationForm(request.form)
    if form.validate_on_submit():
        station = ExperimentalStation(
            name=form.station_name.data,
            address_name=form.address.data,
            location=form.station_location.data,
            api_key=form.station_api_key.data,
        )
        station.save()
        flash("Successfuly added new experimental station.", "success")
        return redirect(url_for("experiments.list_station"))
    elif form.is_submitted():
        flash("The given data was invalid.", "danger")
    return render_template("experiments/newStation.html", form=form)


@experiments_blueprint.route("/list_stations", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def list_station():
    stations = ExperimentalStation.get_all_stations()
    return render_template(
        "experiments/station_list.html", title="Station List", rows=stations
    )


@experiments_blueprint.route("/edit_station/<int:station_id>", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def update_station(station_id):
    form = NewStationForm()
    station_to_update = ExperimentalStation.get_station_by_id(station_id)
    station_former_name = station_to_update.name
    if request.method == "POST":
        try:
            station_to_update.update(
                name=request.form["station_name"],
                address_name=request.form["address"],
                api_key=request.form["station_api_key"],
                location=request.form["station_location"],
            )
            flash(
                f"Successfuly updated existing experimental station {station_former_name}.",
                "success",
            )
            return render_template(
                "experiments/station_update.html",
                form=form,
                station_to_update=station_to_update,
            )
        except:
            flash(
                f"Error during update of existing experimental station {station_former_name}.",
                "warning",
            )
            return render_template(
                "experiments/station_update.html",
                form=form,
                station_to_update=station_to_update,
            )
    else:
        return render_template(
            "experiments/station_update.html",
            form=form,
            station_to_update=station_to_update,
        )


@experiments_blueprint.route("/delete_station/<int:station_id>")
@login_required
@roles_required("admin")
def delete_station(station_id):
    station_to_delete = ExperimentalStation.query.get_or_404(station_id)
    try:
        station_to_delete.delete()
        flash(
            f"Successfuly deleted existing experimental station {station_to_delete.name}.",
            "success",
        )
        return redirect(url_for("experiments.list_station"))
    except:
        flash(
            f"Error during delete existing experimental station {station_to_delete.name}.",
            "warning",
        )
        return redirect(url_for("experiments.list_station"))


@experiments_blueprint.route(
    "/get_available_experiments/<int:station_id>", methods=["GET", "POST"]
)
@login_required
@roles_required("admin")
def get_available_experiments_for_station(station_id):
    station_to_configure = ExperimentalStation.get_station_by_id(station_id)
    routines_already_available = (
        ExperimentalStation.get_all_routine_names_by_station_id(station_id)
    )

    request_url = f"http://{station_to_configure.address_name}/api/get_experiment_types"

    response = requests.get(request_url)

    data = json.loads(response.text)

    if type(data) == dict:
        for new_routine_name, routine_data in data.items():
            if new_routine_name not in routines_already_available:
                new_routine = ExperimentalRoutines.add_routine(new_routine_name)
                station_to_configure.register_routine_in_station(new_routine)
                if routine_data["parameters"] is not None:
                    for name, param in routine_data["parameters"].items():
                        new_param = Parameters(
                            name=name,
                            unit=param[1],
                            note=None,
                            data_type=param[0],
                            static_param=False,
                            default_value=0.0,
                        )
                        new_param.save()
                        new_routine.add_parameter(new_param)
            else:
                flash(f"Routine {new_routine_name} already exists.", "warning")

    return redirect(url_for("experiments.routines_administration"))


@experiments_blueprint.route("/new_experimental_design", methods=["GET", "POST"])
@login_required
# @experiments_blueprint.route("/configure_station/<int:station_id>")
def new_experimental_design():
    availableStations = ExperimentalStation.query.all()

    ## check if stations are available, if no station is configured, redirect to staion list page
    ## TODO: If user is admin -> station list, if not -> send to home
    if len(availableStations) == 0:
        flash("No stations available. Create a station in station list.", "warning")
        return redirect(url_for("experiments.list_station"))
    else:
        station_list = [(station.id, station.name) for station in availableStations]
    form = NewExperimentalDesign(request.form)
    form.station.choices = station_list

    if form.validate_on_submit():
        design = form.design_name.data
        new_design = ExperimentalDesign.add_experimental_design(
            name=form.design_name.data,
            user_id=current_user.id,
            station_id=form.station.data,
        )

        return redirect(url_for("experiments.list_experimental_designs"))
    elif form.is_submitted():
        flash("The given data was invalid.", "danger")
    return render_template("experiments/newExperimentalDesign.html", form=form)


@experiments_blueprint.route(
    "/new_experimental_stage/<int:design_id>", methods=["GET", "POST"]
)
@login_required
def new_experimental_stage(design_id):
    pass


@experiments_blueprint.route("/list_designs")
@login_required
def list_design():
    designs = ExperimentalDesign.query.all()
    return render_template(
        "experiments/design_list.html", title="Design List", rows=designs
    )


@experiments_blueprint.route("/add_run/<int:stage_id>", methods=["GET", "POST"])
@login_required
def add_experimental_run(stage_id):
    try:
        new_run = ExperimentalRuns(stage_id=stage_id)
        new_run.save()
        for sent_value in request.form.items():
            value = sent_value[1].replace(",", ".")
            new_value = Values(
                parameter_id=sent_value[0],
                value_as_str=value,
                experimental_runs_id=new_run.id,
            )
            new_value.save()
    except ValueError:
        flash("At least one value coult not be converted to float.", "warning")
        new_run.delete()
        redirect(url_for("experiments.edit_stage", stage_id=stage_id))

    return redirect(url_for("experiments.edit_stage", stage_id=stage_id))


@experiments_blueprint.route("/delete_run/<int:stage_id>", methods=["GET", "POST"])
@login_required
def delete_experimental_run(stage_id):
    ### get the run id to be deleted from post data
    run_id_to_deleted = int(request.args.get("run_id"))
    ### get all run ids for the stage to check if the run id to be deleted included
    run_ids_in_stage = [
        run.id for run in Stage.query.get_or_404(stage_id).experimental_runs
    ]
    if run_id_to_deleted in run_ids_in_stage:
        run_to_delete = ExperimentalRuns.query.get_or_404(run_id_to_deleted)
        run_to_delete.delete()
    return redirect(url_for("experiments.edit_stage", stage_id=stage_id))


@experiments_blueprint.route("/edit_design/<int:design_id>", methods=["GET", "POST"])
def edit_design(design_id):
    design = ExperimentalDesign.get_experimental_design_by_id(design_id)

    station = design.get_experimental_station()

    availableRoutines = station.experiments_available

    ## check if routines are available, if no routines is configured, redirect to staion list page
    ## TODO: If user is admin -> station list, if not -> send to home
    if len(availableRoutines) == 0:
        flash("No experimental routines were downloaded from the station.", "warning")
        return redirect(url_for("experiments.list_station"))
    else:
        routines_list = [(routine.id, routine.name) for routine in availableRoutines]

    new_routine_form = NewExperimentalStage()
    new_routine_form.experimental_routine.choices = routines_list

    if new_routine_form.validate_on_submit() and request.method == "POST":
        Stage.add_stage(
            name=new_routine_form.stage_name.data,
            user_id=current_user.id,
            experimental_Routine_id=new_routine_form.experimental_routine.data,
            experimental_design_id=design_id,
        )

        return redirect(url_for("experiments.edit_design", design_id=design_id))

    return render_template(
        "experiments/design_stages_overview.html",
        form=new_routine_form,
        design=design,
    )


@experiments_blueprint.route("/edit_stage/<int:stage_id>", methods=["GET", "POST"])
@login_required
def edit_stage(stage_id):
    stage = Stage.query.get_or_404(stage_id)
    routine = ExperimentalRoutines.query.get_or_404(stage.experimental_Routine_id)
    session["stage_id"] = stage_id
    ## grab list of parameters
    parameters = routine.get_parameters_in_routine()
    ## 2. Grab experimental runs, if any
    runs = stage.experimental_runs
    ## 3. Grab all values for run and all parameters for values
    table_rows = []
    for run in runs:
        run_vals = []
        for value in run.run_values:
            val = {"value_id": value.id, "value": value.value}
            run_vals.append(val)
        run_value_dict = {"run_id": run.id, "run_values": run_vals}
        table_rows.append(run_value_dict)

    return render_template(
        "experiments/stage_detail.html",
        stage=stage,
        parameters=parameters,
        table_rows=table_rows,
    )


@experiments_blueprint.route("/delete_stage/<int:stage_id>", methods=["GET", "POST"])
@login_required
def delete_stage(stage_id):
    stage_to_delete = Stage.query.get_or_404(stage_id)
    design_id = stage_to_delete.experimental_design_id
    try:
        stage_to_delete.delete()
        flash(
            f"Successfuly deleted existing experimental station {stage_to_delete.name}.",
            "success",
        )
        return redirect(url_for("experiments.edit_design", design_id=design_id))
    except:
        flash(
            f"Error during delete existing experimental station {stage_to_delete.name}.",
            "warning",
        )
        return redirect(url_for("experiments.edit_design", design_id=design_id))


@experiments_blueprint.route("/delete_design/<int:design_id>", methods=["GET", "POST"])
@login_required
def delete_design(design_id):
    design_to_delete = ExperimentalDesign.query.get_or_404(design_id)
    design_id = design_to_delete.id
    try:
        design_to_delete.delete()
        flash(
            f"Successfuly deleted existing experimental station {design_to_delete.name}.",
            "success",
        )
        return redirect(
            url_for("experiments.list_experimental_designs", design_id=design_id)
        )
    except:
        flash(
            f"Error during delete existing experimental station {design_to_delete.name}.",
            "warning",
        )
        return redirect(
            url_for("experiments.list_experimental_designs", design_id=design_id)
        )


@experiments_blueprint.route("/list_experimental_designs", methods=["GET", "POST"])
@login_required
def list_experimental_designs():
    desings = ExperimentalDesign.get_all_designs_for_user(current_user.id)

    return render_template(
        "experiments/experimental_designs_list.html",
        title="Experimental Designs-List",
        rows=desings,
    )


@experiments_blueprint.route("/dl_design/<int:stage_id>", methods=["POST"])
@login_required
def design_data_download(stage_id):
    """This function grabs all runs for a given stage_id and builds a row<->run wise dataframe, which gets converted to an excel spreadsheet. The spreadsheat is returnd as a file download.

    Args:
        stage_id (int): Database ID for the stage

    Returns:
        type: Response: Returns a Excel Sheet for with header information that is downloaded by the users browser.
    """

    if request.form["select_dl_mode"] == "dynamic_only":
        dynamic_only = True
    elif request.form["select_dl_mode"] == "full":
        dynamic_only = False

    return Stage.get_stage_by_id(stage_id).get_excel_file_for_stage_dl(dynamic_only)


@experiments_blueprint.route("/api/sent_design/<int:stage_id>", methods=["GET", "POST"])
@login_required
def api_sent_design(stage_id):
    stage = Stage.get_stage_by_id(stage_id)

    stage.sent_all_runs_to_station()

    return redirect(url_for("experiments.edit_stage", stage_id=stage_id))


@experiments_blueprint.route("/upload_stage/<int:stage_id>", methods=["POST"])
@login_required
def upload_stage(stage_id):
    if request.form["select_ul_mode"] == "dynamic_only":
        dynamic_only = True
    elif request.form["select_ul_mode"] == "full":
        dynamic_only = False
    design_data_upload(
        stage_id=stage_id, file=request.files["ul_file"], dynamic_only=dynamic_only
    )
    return redirect(url_for("experiments.edit_stage", stage_id=stage_id))


def design_data_upload(stage_id, file, dynamic_only):
    if request.method == "POST":
        # check if the post request has the file part
        if "ul_file" not in request.files:
            flash(
                f"File not found. Please select a file and try again.",
            )
            return redirect(url_for("experiments.edit_stage", stage_id=stage_id))
        else:
            file = request.files["ul_file"]

        # If the user does not select a file, the browser submits an empty file without a filename.
        if file.filename == "":
            flash("Please select a file with an valid filename.", "warning")
            return redirect(url_for("experiments.edit_stage", stage_id=stage_id))

        # if the file extentions is not allowed, abort
        if not get_if_xlsx_file(file.filename):
            flash(
                f"The file typ is not supported. Please use .xlsx files.",
                "warning",
            )
            return redirect(url_for("experiments.edit_stage", stage_id=stage_id))

        stage = Stage.get_stage_by_id(stage_id)
        stage.add_or_update_runs_from_excel_upload(file, dynamic_only)
        return redirect(url_for("experiments.edit_stage", stage_id=stage.id))


@experiments_blueprint.route("/send_multiple_stages/<int:design_id>", methods=["POST"])
@login_required
def send_multiple_stages(design_id):
    ## check the stage ids for the submitted design id.
    design = ExperimentalDesign.query.get_or_404(design_id)
    allowed_stages_ids = [design.id for design in design.stages]
    if request.method == "POST":
        ## get list of submitted design ids
        id_list = [int(id) for id in request.form.getlist("stages_to_be_sent")]
        ## compare both list to check for manipulated design ids in the web form
        checked_ids = [id for id in id_list if id in allowed_stages_ids]
        for id in checked_ids:
            api_sent_design(id)
        flash(
            message=f"{len(checked_ids)} Stages were submitted to the station.",
            category="success",
        )

        return redirect(url_for("experiments.edit_design", design_id=design_id))


@experiments_blueprint.route("/routines_administration", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def routines_administration():
    routines = ExperimentalRoutines.get_routines()
    stations = ExperimentalStation.get_all_stations()
    return render_template(
        "experiments/routines_administration.html", routines=routines, stations=stations
    )


@experiments_blueprint.route(
    "/routine_administration/<int:routine_id>", methods=["GET", "POST"]
)
@login_required
@roles_required("admin")
def routine_administration(routine_id):
    routine = ExperimentalRoutines.get_routine(routine_id)

    return render_template("experiments/routine_administration.html", routine=routine)


@experiments_blueprint.route(
    "/update_routine/<int:routine_id>", methods=["GET", "POST"]
)
def update_routine(routine_id):
    pass


@experiments_blueprint.route(
    "/delete_routine/<int:routine_id>", methods=["GET", "POST"]
)
@login_required
@roles_required("admin")
def delete_routine(routine_id):
    routine = ExperimentalRoutines.get_routine(routine_id)
    routine.delete()
    return redirect(url_for("experiments.routines_administration"))


@experiments_blueprint.route(
    "/toggle_static_parameter/<int:parameter_id>", methods=["GET", "POST"]
)
@login_required
@roles_required("admin")
def toggle_static_parameter(parameter_id):
    parameter = Parameters.get_parameter(parameter_id)
    parameter.toggle_static_parameter()
    response = jsonify(success=True)
    return response


@experiments_blueprint.route(
    "/set_default_value/<int:parameter_id>", methods=["GET", "POST"]
)
@login_required
@roles_required("admin")
def set_parameter_default_value(parameter_id):
    default_value = request.json.get("default_value")
    parameter = Parameters.get_parameter(parameter_id)
    parameter.set_default_value(default_value)
    response = jsonify(success=True)
    return response


@experiments_blueprint.route("/design/<int:design_id>/share/user", methods=["POST"])
@login_required
def share_design_with_user(design_id):
    user_id = request.form.get("user_id")
    user = User.get_user_by_token(user_id)
    design = ExperimentalDesign.get_experimental_design_by_id(design_id)

    if design.user_id != current_user.id:
        flash("You are not allowed to share this design.", "warning")
        return 403

    if user and design:
        design.share_with_user(user)
        flash("Design shared with group successfully!", "success")
        return 200
    else:
        flash("User or design not found.", "warning")
        return 404


@experiments_blueprint.route("/design/<int:design_id>/share/group", methods=["POST"])
def share_design_with_group(design_id):
    group_id = request.form.get("group_id")
    group = Group.get_group(group_id)
    design = ExperimentalDesign.get_experimental_design_by_id(design_id)
    if design.user_id != current_user.id:
        flash("You are not allowed to share this design.", "warning")
        return 403

    if group and design:
        design.share_with_group(group)
        flash("Design shared with group successfully!", "success")
        return 200
    else:
        flash("Group or design not found.", "warning")
        return 404


@experiments_blueprint.route("/design/<int:design_id>/unshare/user", methods=["POST"])
def unshare_design_with_user(design_id):
    user_id = request.form.get("user_id")
    user = User.get_user_by_token(user_id)
    design = ExperimentalDesign.get_experimental_design_by_id(design_id)

    if design.user_id != current_user.id:
        flash("You are not allowed to share this design.", "warning")
        return 403

    if user and design:
        design.remove_user_share(user)
        flash("Design unshared with user successfully!", "success")
        return 200
    else:
        flash("User or design not found.", "warning")
        return 404


@experiments_blueprint.route("/design/<int:design_id>/unshare/group", methods=["POST"])
def unshare_design_with_group(design_id):
    group_id = request.form.get("group_id")
    group = Group.query.get(group_id)
    design = ExperimentalDesign.query.get(design_id)

    if design.user_id != current_user.id:
        flash("You are not allowed to share this design.", "warning")
        return 403

    if group and design:
        design.remove_group_share(group)
        flash("Design unshared with group successfully!", "success")
        return 200
    else:
        flash("Group or design not found.", "warning")
        return 404
