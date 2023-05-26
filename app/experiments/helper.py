from functools import wraps

from flask import abort
from flask_login import current_user


def get_if_xlsx_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ["xlsx"]


def roles_required(*role_names):
    """| This function was copied from flask_user decorators.py, since flask user is no longer developed. also _is_logged_in_with_confirmed_email() was copied from the same file.:
    This decorator ensures that the current user is logged in,
    | and has *all* of the specified roles (AND operation).

    Example::

        @route('/escape')
        @roles_required('Special', 'Agent')
        def escape_capture():  # User must be 'Special' AND 'Agent'
            ...

    | Calls unauthenticated_view() when the user is not logged in
        or when user has not confirmed their email address.
    | Calls unauthorized_view() when the user does not have the required roles.
    | Calls the decorated view otherwise.
    """

    def wrapper(view_function):
        @wraps(view_function)  # Tells debuggers that is is a function wrapper
        def decorator(*args, **kwargs):
            # User must be logged in with a confirmed email address

            if not current_user.is_authenticated:
                # Redirect to unauthenticated page
                return abort(401)

            # User must have the required roles
            if not current_user.has_roles(*role_names):
                # Redirect to the unauthorized page
                return abort(401)

            # It's OK to call the view
            return view_function(*args, **kwargs)

        return decorator

    return wrapper
