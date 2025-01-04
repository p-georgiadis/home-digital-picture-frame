from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", "db.sqlite3")
Base = declarative_base()

class MediaItem(Base):
    __tablename__ = 'media_items'
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, unique=True, nullable=False)
    filetype = Column(String, nullable=False)   # 'image' or 'video'
    duration = Column(Float, nullable=True)      # duration in seconds for videos, None for images

engine = create_engine(f"sqlite:///{DB_PATH}")

# Use a sessionmaker and scoped_session for thread safety and easy cleanup
SessionLocal = sessionmaker(bind=engine)
Session = scoped_session(SessionLocal)

Base.metadata.create_all(engine)
