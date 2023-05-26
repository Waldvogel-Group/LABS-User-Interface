from flask import Blueprint, render_template, url_for, redirect, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from .. import db
from .models import Group, User
from .forms import AddGroupForm, LoginForm, RegistrationForm, PasswordChangeForm

auth_blueprint = Blueprint("auth", __name__)


@auth_blueprint.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm(request.form)
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            shortID=form.shortID.data,
        )
        user.save()
        login_user(user)
        flash("Registration successful. You are logged in.", "success")
        return redirect(url_for("main.index"))
    elif form.is_submitted():
        flash("The given data was invalid.", "danger")
    return render_template("auth/register.html", form=form)


@auth_blueprint.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if form.validate_on_submit():
        user = User.authenticate(form.user_id.data, form.password.data)
        if user is not None:
            login_user(user)
            flash("Login successful.", "success")
            return redirect(url_for("main.index"))
        flash("Wrong user ID or password.", "danger")
    return render_template("auth/login.html", form=form)


@auth_blueprint.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You were logged out.", "info")
    return redirect(url_for("main.index"))


@auth_blueprint.route("/password_change", methods=["GET", "POST"])
@login_required
def user_password_change():
    form = PasswordChangeForm(request.form)
    if request.method == "POST":
        if form.validate_on_submit():
            user = current_user
            user.password = form.password.data
            db.session.add(user)
            db.session.commit()
            flash("Password has been updated!", "success")
    return form


@auth_blueprint.route("/profile_update", methods=["GET", "POST"])
@login_required
def profile_update():
    pass


@auth_blueprint.route("/profile", methods=["GET", "POST"])
@login_required
def userProfile():
    return render_template("auth/userProfile.html", form=user_password_change())


@auth_blueprint.route("/groups", methods=["GET"])
@login_required
def groups():
    groups = current_user.get_groups()
    form = AddGroupForm(request.form)

    return render_template("auth/groups.html", groups=groups, form=form, User=User)


@auth_blueprint.route("/group/<int:group_id>/add_user/", methods=["POST", "GET"])
@login_required
def group_add_user(group_id):
    group = Group.query.get_or_404(group_id)
    user_id = request.form.get("add_user")
    group.add_user(user_id)
    return redirect(url_for("auth.groups", group_id=group_id))


@auth_blueprint.route("/group/<int:group_id>/remove_user", methods=["POST", "GET"])
@login_required
def group_remove_user(group_id):
    group = Group.query.get_or_404(group_id)
    user_id = request.form.get("remove_user")
    if not group.remove_user(user_id):
        flash("You are not the owner of this group.", "danger")
    return redirect(url_for("auth.groups", group_id=group_id))


@auth_blueprint.route("/group/add_group/", methods=["POST"])
@login_required
def add_group():
    form = AddGroupForm(request.form)
    if request.method == "POST" and form.validate_on_submit():
        current_user.create_group_and_join(request.form.get("name"))
        return redirect(url_for("auth.groups"))


@auth_blueprint.route("/group/<int:group_id>/delete_group", methods=["GET"])
@login_required
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)
    if group.owner == current_user.id:
        group.delete()
        flash("Group deleted.", "success")
    else:
        flash("You are not the owner of this group.", "danger")
    return redirect(url_for("auth.groups"))
