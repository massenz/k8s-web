from flask_login import UserMixin

__author__ = 'M. Massenzio (massenz@adobe.com'


class User(UserMixin):
    def __init__(self, user_id, name):
        self.id = user_id
        self.name = name

    def __repr__(self):
        return f'User({self.id}, {self.name})'

    def __str__(self):
        return f'{self.name} [{self.id}]'
