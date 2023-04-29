from msilib.schema import Error
from . import db


class ModelMixin(object):
    def save(self):
        # Save this model to the database.
        try:
            db.session.add(self)
            db.session.commit()
        except:
            db.session.rollback()
        return self

    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return Error

        return self


# Add your own utility classes and functions here.
