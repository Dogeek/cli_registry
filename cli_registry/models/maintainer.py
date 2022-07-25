from pydantic import BaseModel, constr
from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from cli_registry.db import Base


association_table = Table(
    'plugins_maintainers_association',
    Base.metadata,
    Column("plugin_id", Integer, ForeignKey("plugins.id"), primary_key=True),
    Column("maintainer_id", Integer, ForeignKey("maintainers.id"), primary_key=True),
)


class MaintainerOrm(Base):
    __tablename__ = 'maintainers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=True)
    ssh_key = Column(String(400), nullable=False)

    plugins = relationship(
        'PluginOrm', secondary=association_table, back_populates='maintainers'
    )

    def dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'ssh_key': self.ssh_key,
        }


class MaintainerModel(BaseModel):
    class Config:
        orm_mode = True

    email: constr(max_length=255)
    ssh_key: constr(max_length=400)
