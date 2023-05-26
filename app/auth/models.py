from datetime import datetime
from os import abort
from random import random
import string
from flask import url_for
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import UserMixin, AnonymousUserMixin, current_user

from sqlalchemy.ext.hybrid import hybrid_property
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship

# from flask_user import roles_required

from .. import db
from ..utils import ModelMixin


class Group(db.Model, ModelMixin):
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)
    owner = db.Column(db.Integer, db.ForeignKey("users.id"))
    shared_designs = db.relationship(
        "ExperimentalDesign",
        secondary="group_shared_designs",
        backref=db.backref("shared_groups", lazy="dynamic"),
    )

    def __str__(self):
        return "<Group: %s>" % self.name

    @classmethod
    def add_group(cls, name):
        """creates new group and returns the group object if the group does not exist, otherwise returns False

        Args:
            name (str): name of the group

        Returns:
            _type_: Group object if the group does not exist, otherwise returns False
        """
        if cls.query.filter_by(name=name).first() is None:
            group = cls(name=name, owner=current_user.id)
            group.save()
            return group
        return False

    @classmethod
    def delete_group(cls, group_id):
        group = cls.query.filter_by(id=group_id).first()
        if group is not None and current_user.id == group.owner:
            group.delete()
            return True
        return False

    @classmethod
    def get_group(cls, group_id):
        group = cls.query.filter_by(id=group_id).first()
        if group is not None:
            return group
        return None

    @classmethod
    def get_all_groups(cls):
        return cls.query.all()

    @classmethod
    def get_group_by_name(cls, name):
        group = cls.query.filter_by(name=name).first()
        if group is not None:
            return group
        return None

    @classmethod
    def add_user_to_group(cls, user_id, group_id):
        user = User.get_user(user_id)
        group = cls.get_group(group_id)
        if user is not None and group is not None:
            user.groups.append(group)
            db.session.commit()
            return True
        return False

    def add_user(self, user_id):
        user = User.get_user(user_id)
        if user is not None:
            user.groups.append(self)
            db.session.commit()
            return True
        return False

    def remove_user(self, user_id):
        user = User.get_user(user_id)
        if user is not None and (current_user.id == self.owner or user == current_user):
            user.groups.remove(self)
            self.save()
            # if no more users in the group, delete the group
            if len(self.users()) == 0:
                self.delete()
            return True
        return False

    def get_delte_url(self):
        return url_for("auth.delete_group", group_id=self.id)

    def users(self):
        return (
            User.query.join(user_groups).filter(user_groups.c.group_id == self.id).all()
        )

    def get_users(self):
        return self.users()

    def get_owner(self):
        return User.get_user(self.owner)


user_groups = db.Table(
    "user_groups",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("group_id", db.Integer, db.ForeignKey("groups.id"), primary_key=True),
)


class User(db.Model, UserMixin, ModelMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    activated = db.Column(db.Boolean, default=False)
    firstName = db.Column(db.String(255), unique=False, nullable=True)
    lastName = db.Column(db.String(255), unique=False, nullable=True)
    shortID = db.Column(db.String(3), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_admin = db.Column(db.Boolean, default=False)
    roles = db.relationship("Role", secondary="user_roles")
    email_confirmed_at = db.Column("confirmed_at", db.DateTime())
    groups = db.relationship("Group", secondary=user_groups)

    @hybrid_property
    def password(self):
        return self.password_hash

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    @classmethod
    def get_user_by_token(cls, token):
        return cls.query.get(int(token))

    def has_roles(self, *args):
        return set(args).issubset({role.name for role in self.roles})

    @classmethod
    def authenticate(cls, user_id, password):
        user = cls.query.filter(
            db.or_(cls.username == user_id, cls.email == user_id)
        ).first()
        if user is not None and check_password_hash(user.password, password):
            return user

    def __str__(self):
        return "<User: %s>" % self.username

    def change_password(self, old_password, new_password1, new_password2):
        if (
            check_password_hash(self.password_hash, old_password)
            and new_password1 == new_password2
        ):
            self.password_hash = generate_password_hash(new_password1)
            db.session.commit()
            return True
        return False

    def change_email(self, new_email):
        self.email = new_email
        db.session.commit()
        return True

    def change_name(self, new_firstName, new_lastName):
        self.firstName = new_firstName
        self.lastName = new_lastName
        db.session.commit()
        return True

    def change_shortID(self, new_shortID):
        self.shortID = new_shortID
        db.session.commit()
        return True

    def is_active(self):
        return self.activated

    def is_administrator(self):
        return self.is_admin

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    def get_groups(self):
        return self.groups

    def get_groups_names(self):
        return [group.name for group in self.groups]

    def create_group_and_join(self, name):
        group = Group.add_group(name)
        if group is not False:
            self.groups.append(group)
            self.save()
        return True

    @classmethod
    def activate_user(cls, user_id):
        user = cls.query.filter_by(id=user_id).first()
        if user is not None:
            user.activated = True
            db.session.commit()
            return True
        return False

    @classmethod
    def deactivate_user(cls, user_id):
        user = cls.query.filter_by(id=user_id).first()
        if user is not None:
            user.activated = False
            db.session.commit()
            return True
        return False

    @classmethod
    def promote_user(cls, user_id):
        user = cls.query.filter_by(id=user_id).first()
        if user is not None:
            user.is_admin = True
            db.session.commit()
            return True
        return False

    @classmethod
    def demote_user(cls, user_id):
        user = cls.query.filter_by(id=user_id).first()
        if user is not None:
            user.is_admin = False
            db.session.commit()
            return True
        return False

    @classmethod
    def delete_user(cls, user_id):
        user = cls.query.filter_by(id=user_id).first()
        if user is not None:
            user.delete()
            return True
        return False

    @classmethod
    def get_user(cls, user_id):
        user = cls.query.filter_by(id=user_id).first()
        if user is not None:
            return user
        return None

    @classmethod
    def get_all_users(cls):
        return cls.query.all()

    @classmethod
    def add_admin_user(cls):
        from sqlalchemy import inspect

        # if user table is present in the database
        if inspect(db.engine).has_table("users"):
            if cls.query.filter_by(username="admin").first() is None:
                random_password = "".join(
                    random.choice(string.ascii_letters) for i in range(10)
                )
                admin_user = cls(
                    username="admin",
                    email="admin@admin",
                    password=random_password,
                    activated=True,
                    is_admin=True,
                )
                admin_user.roles = [Role.get_admin_role()]
                admin_user.save()
                print(
                    f"*** Admin user created. Name {admin_user.username}, password {random_password} ***"
                )
                return True


# Define the Role data-model
class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True)

    def __str__(self):
        return "<Role: %s>" % self.name

    def __repr__(self):
        return self.name

    @classmethod
    def add_admin_role(cls):
        if cls.query.filter_by(name="admin").first() is None:
            admin_role = cls(name="admin")
            db.session.add(admin_role)
            db.session.commit()
            return True
        return False

    @classmethod
    def get_admin_role(cls):
        cls.add_admin_role()
        return cls.query.filter_by(name="admin").first()


# Define the UserRoles association table
class UserRoles(db.Model):
    __tablename__ = "user_roles"
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey("users.id", ondelete="CASCADE"))
    role_id = db.Column(db.Integer(), db.ForeignKey("roles.id", ondelete="CASCADE"))


shared_designs = db.Table(
    "shared_designs",
    db.Column(
        "experimental_design_id",
        db.Integer,
        db.ForeignKey("experimental_design.id"),
        primary_key=True,
    ),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
)


group_shared_designs = db.Table(
    "group_shared_designs",
    db.Column(
        "experimental_design_id",
        db.Integer,
        db.ForeignKey("experimental_design.id"),
        primary_key=True,
    ),
    db.Column("group_id", db.Integer, db.ForeignKey("groups.id"), primary_key=True),
)


class AnonymousUser(AnonymousUserMixin):
    pass
