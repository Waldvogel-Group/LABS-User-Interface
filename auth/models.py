from datetime import datetime
from os import abort
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import UserMixin, AnonymousUserMixin, current_user
from sqlalchemy.ext.hybrid import hybrid_property
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship

from .. import db
from ..utils import ModelMixin


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

    @hybrid_property
    def password(self):
        return self.password_hash

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    @classmethod
    def authenticate(cls, user_id, password):
        user = cls.query.filter(
            db.or_(cls.username == user_id, cls.email == user_id)
        ).first()
        if user is not None and check_password_hash(user.password, password):
            return user

    def __str__(self):
        return "<User: %s>" % self.username


class AnonymousUser(AnonymousUserMixin):
    pass


class Controller(ModelView):
    def is_accessible(self):
        if current_user.is_admin:
            return current_user.is_authenticated
        else:
            return abort(404)
