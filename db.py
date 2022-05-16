from sqlalchemy import create_engine
from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from constant import DB_URL

db = create_engine(DB_URL)
base = declarative_base()

# define all table models
class CollectorTask(base):
    __tablename__ = 'collectortask'

    collectortask_id = Column(Integer, primary_key=True)
    timestamp = Column(String)
    collectortype_id = Column(Integer)

class CollectorType(base):
    __tablename__ = 'collectortype'

    collectortype_id = Column(Integer, primary_key=True)
    name = Column(String)

class CollectorStatus(base):
    __tablename__ = 'collectorstatus'

    collectorstatus_id = Column(Integer, primary_key=True)
    collectortask_id = Column(Integer)
    status = Column(String)
    created_at = Column(String)

class CollectorTaskFiles(base):
    __tablename__ = 'collectortaskfiles'

    collectortaskfiles_id = Column(Integer, primary_key=True)
    collectortask_id = Column(Integer)
    filename = Column(String)
    filepath = Column(String)

class Connections(base):
    __tablename__ = 'connections'

    connections_id = Column(Integer, primary_key=True)
    name = Column(String)
    occupation = Column(String)
    connected_at = Column(String, nullable=True)
    connected_with_user_id = Column(Integer)
    profile_link = Column(String)
    circle_level = Column(String)

class User(base):
    __tablename__ = 'user'

    user_id = Column(Integer, primary_key=True)    
    email = Column(String)

if __name__ == '__main__':
    # DB COMMAND TEST
    Session = sessionmaker(db)
    session = Session()
    
    # user = User(email='fahri.lafa@gmail.com')
    # session.add(user)
    # session.commit()
    conns = session.query(User)
    for c in conns.all():
        print(c.email)