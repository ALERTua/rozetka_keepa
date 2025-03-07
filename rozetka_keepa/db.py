from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from functools import cached_property
from typing import ClassVar
from collections.abc import Iterable

from global_logger import Log
from rozetka.entities.item import Item
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import EmailType, PasswordType, UUIDType

from rozetka_keepa import constants

LOG = Log.get_logger()


Base = declarative_base()  # https://leportella.com/sqlalchemy-tutorial/
engine_str = constants.DB_URL


class DBBase:
    @classmethod
    def instantiate(cls, session, **kwargs):
        candidate = session.query(cls).filter_by(**kwargs)
        if candidate.count() != 0:
            return candidate.first()

        # noinspection PyArgumentList
        session.add(cls(**kwargs))
        session.commit()
        return cls.instantiate(session, **kwargs)

    @classmethod
    def find(cls, session, **kwargs):
        return session.query(cls).filter_by(**kwargs).all()


class Keepa(Base, DBBase):
    __tablename__ = "keepa"
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    added = Column("added", DateTime, default=datetime.now(tz=constants.TZ))

    item_id = Column("item_id", Integer)
    user_id = Column("user_id", ForeignKey("users.id"))
    wanted_price = Column("wanted_price", Float)
    pause_until = Column("pause_until", DateTime, default=datetime.now(tz=constants.TZ))

    def __repr__(self):
        return f"{self.item_id}@{self.wanted_price}"

    @property
    def url(self):
        return f"https://rozetka.com.ua/ua/search/?text={self.item_id}"

    def pause(self):
        self.pause_until = datetime.now(tz=constants.TZ) + timedelta(days=1)

    def reset_pause(self):
        self.pause_until = datetime.now(tz=constants.TZ)

    @property
    def item(self):
        return self._item(parse=False)

    def _item(self, parse=False):  # noqa: FBT002
        output = Item.get(self.item_id)
        # noinspection PyProtectedMember
        if parse:
            output.parse()
        return output


class User(Base, DBBase):
    __tablename__ = "users"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    created = Column("created", DateTime, default=datetime.now(tz=constants.TZ))
    auth_token = Column(name="auth_token", type_=UUIDType(binary=False), default=uuid.uuid4)

    telegram_id = Column(name="telegram_id", type_=Integer, nullable=True)
    email = Column(name="email", type_=EmailType, nullable=True)
    username = Column(name="username", type_=String(32), nullable=True)
    password = Column(name="password", type_=PasswordType(max_length=64, schemes=["pbkdf2_sha512"]), nullable=True)

    def __repr__(self):
        return f"{self.id}"

    def auth_token_invalidate(self):
        self.auth_token = uuid.uuid4()


class DBController:
    cache = []

    def __init__(self, direct=True):  # noqa: FBT002
        assert not direct, "please use instantiate classmethod"
        self._db = None

    @cached_property
    def db_engine(self):
        db_engine = create_engine(engine_str, pool_pre_ping=True, pool_recycle=600)  # , echo=log.verbose)
        Base.metadata.create_all(db_engine)
        return db_engine

    @property
    def db(self):
        if self._db is None:
            self._db = sessionmaker(bind=self.db_engine)()
        else:
            try:
                self._db.scalar(select(1))
            except DBAPIError as err:
                LOG.red(f"DB connection error: {err}")
                self._db.close()

        return self._db

    @classmethod
    def instantiate(cls):
        if cls.cache:
            return cls.cache[0]

        output = cls(direct=False)
        cls.cache.append(output)
        return output

    def commit(self):
        if self.db.dirty:
            LOG.green("Saving database")
            self.db.commit()

    def close(self):
        LOG.green("Closing database")
        self.db.close()

    def add(self, obj):
        if not isinstance(obj, Iterable):
            obj = [obj]

        return self.db.add_all(obj)

    def get_user(self, **kwargs):
        return User.find(self.db, **kwargs)

    def create_user(self, **kwargs):
        LOG.green(f"Creating User with {kwargs}")
        output = User.instantiate(self.db, **kwargs)
        LOG.green(f"Created {output}")
        return output

    def delete_user(self, **kwargs):
        _user = User.instantiate(self.db, **kwargs)
        LOG.green(f"Deleting {_user}")
        self.db.delete(_user)
        self.db.commit()

    def get_user_items(self, user: User, **kwargs) -> list[Keepa]:
        return Keepa.find(self.db, user_id=user.id, **kwargs)

    def user_add_item(self, user: User, item_id: int, wanted_price: int):
        output = Keepa.instantiate(self.db, item_id=item_id, user_id=user.id, wanted_price=wanted_price)
        self.db.commit()
        return output

    def get_user_item_id(self, user: User, item_id: int, **kwargs):
        return self.get_user_items(user=user, item_id=item_id, **kwargs)

    def get_keepas(self) -> list[Keepa]:
        return Keepa.find(self.db)

    def remove_item(self, item: Keepa):
        self.db.delete(item)
        self.db.commit()


if __name__ == "__main__":
    pass
