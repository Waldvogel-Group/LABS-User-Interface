from flask import (
    Blueprint,
    url_for,
    redirect,
    flash,
    request,
    app,
    Response,
    abort,
    current_app,
    session,
)


def get_if_xlsx_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ["xlsx"]
