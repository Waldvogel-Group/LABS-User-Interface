import imp
from typing import ParamSpecKwargs
from flask import (
    Blueprint,
    render_template,
    url_for,
    redirect,
    flash,
    request,
    app,
    abort,
    Response,
)
import time
from flask_login import login_user, logout_user, login_required, current_user
from app.auth.models import User
from app.experiments.models import ExperimentalStation
import requests
from requests.auth import HTTPBasicAuth
from werkzeug.utils import secure_filename
import pathlib
from flask import jsonify
from .. import db
import json
from datetime import datetime
from werkzeug.exceptions import HTTPException
from requests.exceptions import HTTPError
import os.path, time


monitoring_blueprint = Blueprint("monitoring", __name__)


@monitoring_blueprint.route("/plots/<deviceID>/<plot>", methods=["GET", "POST"])
def getDevicePlotData(deviceID, plot):
    pass


@monitoring_blueprint.route("/device/chart-data/<int:deviceID>", methods=["GET"])
def chart_data(deviceID):
    ### Initial Timestamp is none, to get all updates from start of the experiment
    timestamp = None
    # build request url
    request_url = (
        f"http://{ExperimentalStation.get_address_address(deviceID)}/api/get_updates"
    )

    def get_updates(timestamp):
        while True:
            try:
                r = requests.post(
                    request_url,
                    data={"from_timestamp": timestamp},
                )

                json_data_stream = json.loads(r.content.decode())
                json_dump = json.dumps(json_data_stream)
                timestamp = json_data_stream["timestamp"]
                yield f"data:{json_dump}\n\n"
                time.sleep(1)
            except requests.exceptions.RequestException as e:
                break

    return Response(get_updates(timestamp), mimetype="text/event-stream")


@monitoring_blueprint.route("/device/experiment-tables/<int:deviceID>")
def experiment_table_data(deviceID):
    """returns generator for experiment tables and crawls for updates in the station"""

    request_url = f"http://{ExperimentalStation.get_address_address(deviceID)}/api/station_run_tables"

    def get_updates():
        while True:
            r = requests.post(request_url)
            json_data_stream = json.loads(r.content.decode())
            json_dump = json.dumps(json_data_stream)
            yield f"data:{json_dump}\n\n"
            time.sleep(10)

    return Response(get_updates(), mimetype="text/event-stream")


@monitoring_blueprint.route("/overview", methods=["GET", "POST"])
def deviceOverview():
    """Generates Device Overview, requests deviece list from API call. Uses experiments database information for list of devices and  adresses.

    Returns:
        render_template: renders a page for the user with Device information overview.
    """

    def _helper(station):
        request_url = (
            f"http://{station.get_address_address(station.id)}/api/station_overview"
        )

        try:
            r = requests.post(request_url)

            json_data = json.loads(r.content.decode())

            if json_data["status"].lower() == "idle":
                station_dict = {
                    "status": json_data["status"],
                    "running_experiment_name": json_data["running_experiment_name"],
                    "total_experiments_queued": json_data["total_experiments_queued"],
                    "current_run_number": json_data["current_run_number"],
                }
                return station_dict
            elif (
                json_data["current_run_number"] == 0
                and json_data["status"].lower() == "paused"
            ):
                station_dict = {
                    "status": f"{json_data['status']} - Not started",
                    "running_experiment_name": json_data["running_experiment_name"],
                    "total_experiments_queued": json_data["total_experiments_queued"],
                    "current_run_number": json_data["current_run_number"],
                }
            elif (
                json_data["current_run_number"] == ""
                and json_data["status"].lower() == "ready"
            ):
                station_dict = {
                    "status": f"{json_data['status']} - Queue finished",
                    "running_experiment_name": "all experiments finished",
                    "total_experiments_queued": json_data["total_experiments_queued"],
                    "current_run_number": json_data["total_experiments_queued"],
                }
            else:
                station_dict = {
                    "status": json_data["status"],
                    "running_experiment_name": json_data["running_experiment_name"],
                    "total_experiments_queued": json_data["total_experiments_queued"],
                    "current_run_number": json_data["current_run_number"],
                }
            return station_dict
        except requests.exceptions.RequestException as e:
            station_dict = {
                "status": "offline",
                "running_experiment_name": "offline",
                "total_experiments_queued": "offline",
                "current_run_number": "offline",
            }
            return station_dict

    device_details_list = []

    for station in ExperimentalStation.get_all_stations():
        station_info = station.__dict__
        # merge the additonal infos from the request call into station info
        station_info = station_info | _helper(station)

        device_details_list.append(station_info)

    return render_template("monitoring/overview.html", devices=device_details_list)


@monitoring_blueprint.route("/station/<int:station_id>", methods=["GET", "POST"])
def stationDetails(station_id):
    """Generates Device Detailview, calls an staion endpoint for the device details, renders the first DOM and neccessary js plot functions in the template.

    Returns:
        render_template: renders a page for the user with Device information.

    Args:
        station_id (_type_): station id from station_model db.

    Returns:
        _type_: _description_
    """

    ### Step 1: get the first bunch of data, use this package to construct the initial html DOM.
    ### TODO change to wrapper for api security
    # devices_in_experiment = requests.get("http://127.0.0.1:11123/api/get_updates")
    devices_in_experiment = get_station_information(
        station_id=station_id, endpoint="get_updates"
    )
    devices_in_experiment = devices_in_experiment.json()

    ## identify the last timestamp for the update caller
    ## TODO realy neccessary??
    last_timestamp = devices_in_experiment["timestamp"]

    ## store updates
    devices_data = devices_in_experiment["updates"]

    ## prepare a list of observable_Ids to be used in the Bootstrap Grid generation
    observable_ids = []
    for device in devices_data:
        for observable in devices_data[device]:
            observable_ids.append(f"{device}_{observable}")

    ## get device database record, if not present render 404 page.
    station = ExperimentalStation.query.get_or_404(station_id)

    return render_template(
        "monitoring/detail.html",
        station=station,
        devices_data=devices_data,
        observable_ids=observable_ids,
        last_timestamp=last_timestamp,
    )


@monitoring_blueprint.route(
    "/api/monitoring/run_tables/<int:station_id>", methods=["GET"]
)
def get_station_run_tables(station_id):
    ## defining allowed endpoints. If the request for status variable is not in the allowed_endpoints return error 400 - Bad Request.
    allowed_endpoints = ["finished", "running ", "queued"]

    requested_endpoint = str(request.args.get("status"))
    if requested_endpoint in allowed_endpoints:
        return "success", 200
    else:
        return abort(400)


@monitoring_blueprint.route(
    "/api/monitoring/get_active_experiment_parameters/<int:station_id>", methods=["GET"]
)
def get_active_experiment_parameters(station_id):
    """Returns the active experiment parameters for a station.

    Args:
        station_id (_type_): station id from station_model db.

    Returns:
        _type_: _description_
    """
    ## get device database record, if not present render 404 page.
    station = ExperimentalStation.query.get_or_404(station_id)

    ## get the active experiment parameters
    active_experiment_parameters = station.get_active_experiment_parameters()

    return active_experiment_parameters, 200


@monitoring_blueprint.route(
    "/api/monitoring/get_active_experiment_parameter_value/<int:station_id>",
    methods=["GET", "POST"],
)
def get_active_experiment_parameter_value(station_id):
    """Returns the active experiment parameters for a station.

    Args:
        station_id (str): station id from station_model db.
        parameter_name (_str_): parameter name from parameter_model db.

    Returns:
        _type_: _description_
    """
    ## get the parameter name from the request
    parameter_name = str(request.args.get("parameter_name"))
    ## get the active experiment parameters
    active_experiment_parameter_value = (
        ExperimentalStation.get_active_experiment_value_for_parameter(
            station_id, parameter_name
        )
    )
    return active_experiment_parameter_value, 200


@monitoring_blueprint.route(
    "/api/start/<string:station_address>", methods=["GET", "POST"]
)
def api_start(station_address):
    request_url = f"http://{station_address}/api/start"
    requests.post(request_url)
    return "", 204


@monitoring_blueprint.route(
    "/api/stop/<string:station_address>", methods=["GET", "POST"]
)
def api_stop(station_address):
    request_url = f"http://{station_address}/api/stop"
    requests.post(request_url)
    return "", 204


def call_station_api_stream(request_url, args, *kargs):
    """Yields the API Request for a server sent event stream. To be used in
            flask.Response(call_station_api_stream(), mimetype="text/event-stream")
    Args:
        request_url (_type_): request URL with endpoint
        args (_type_): args

    Returns:
        json: yields a JSON generator for endpoint request.
    """

    ## request api call
    # To-Do replace auth snippet
    auth = HTTPBasicAuth("apikey", "ljaskfhlkasfhlkasdjfhlksadjf")
    yield requests.get(request_url, auth=auth).json()


def get_station_list():
    """Frontend API helper function endpoint that returns a list of all stations that a user can observe.
    The datasource is the Stations Model from experiments blueprint."""

    stations = ExperimentalStation.query.all()
    return stations


def get_station_address(station_id):
    """returns the Adress corresponding to a station id

    Args:
        station_id (int): Database ID for the station

    Returns:
        str: Adress
    """

    station = ExperimentalStation.query.get_or_404(station_id)

    return station.address


def get_station_information(station_id, endpoint, *args, **kwargs):
    """Requests station information for different endtypes.

    Args:
        station_id (int): Database ID for the station.
        endpoint (string): Endpoint from staion API. Supported "station_overview", "station_details",

    Returns:
        dict: Dictonary from endpoint json response data.
    """

    # get corresponding  Adress for station_ID
    request_url_base = get_station_address(station_id)

    # add requested endpoint
    request_url = f"http://{request_url_base}/api/{endpoint}"
    try:
        r = requests.get(request_url)
        r.raise_for_status()
        return r
    except HTTPError as http_err:
        flash(
            f"There was an error during the call of {request_url}. \n Error Code: {http_err}",
            "danger",
        )
        abort(500)
    except requests.exceptions.RequestException as e:
        flash(
            f"There was an error during the call of {request_url}. \n Error Code: {e}",
            "danger",
        )
        abort(500)


@monitoring_blueprint.route("/api/monitoring/get_station_overview/<int:station_id>")
def api_get_station_overview(station_id):
    # add endpoint for overview
    endpoint = "station_overview"

    return get_station_information(station_id, endpoint)


@monitoring_blueprint.route("/api/monitoring/get_station_details/<int:station_id>")
def api_get_station_details(station_id):
    # get corresponding Adress for station_ID
    request_url_base = get_station_address(station_id)

    # add endpoint for overview
    endpoint = "station_details"

    return get_station_information(request_url_base, endpoint)
