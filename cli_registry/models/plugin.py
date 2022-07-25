from pathlib import Path
from typing import Optional

from pydantic import BaseModel, constr
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship

from cli_registry.db import Base
from cli_registry.config import BASE_PATH
from cli_registry.models.maintainer import association_table
from cli_registry.utils import encode_file


class PluginOrm(Base):
    __tablename__ = 'plugins'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    versions = relationship('PluginVersionOrm', back_populates='plugin')
    maintainers = relationship(
        'MaintainerOrm', secondary=association_table,
        back_populates='plugins'
    )

    @property
    def latest_version(self) -> 'Optional[PluginVersionOrm]':
        latest_version = None
        for version in sorted(self.versions, reverse=True, key=lambda v: v.upload_date):
            latest_version = version
            break
        return latest_version

    def dict(self):
        if self.latest_version is None:
            latest = None
        else:
            latest = self.latest_version.version
        return {
            'id': self.id,
            'name': self.name,
            'latest_version': latest,
            'maintainers': [m.email for m in self.maintainers if m is not None],
        }


class PluginVersionOrm(Base):
    __tablename__ = 'versions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_date = Column(DateTime)
    version = Column(String(20), nullable=False)

    plugin_id = Column(Integer, ForeignKey('plugins.id'))
    plugin = relationship('PluginOrm', back_populates='versions')

    @property
    def file_path(self) -> Path:
        '''
        Returns the path to the tarball for that plugin's version
        '''
        return BASE_PATH / f'plugins/{self.plugin.name}/{self.version}.tar.gz'

    def dict(self, with_file=True):
        data = {
            'id': self.id,
            'plugin_id': self.plugin.id,
            'upload_date': self.upload_date.isoformat(),
            'version': self.version,
        }
        if not with_file:
            return data
        data['file'] = encode_file(self.file_path)
        return data


class PluginModel(BaseModel):
    class Config:
        orm_mode = True

    name: constr(to_lower=True, max_length=255, strip_whitespace=True)


class PluginVersionModel(BaseModel):
    class Config:
        orm_mode = True

    tarball: str
