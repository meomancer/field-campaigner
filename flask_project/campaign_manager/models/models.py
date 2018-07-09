#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import ast
import hashlib
import shutil
import requests
from geoalchemy2.shape import from_shape
from shapely.geometry import asShape

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Table,
    Text,
    ForeignKey,
    Date,
    DateTime,
    BOOLEAN
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import and_, or_
from sqlalchemy.sql.expression import true
from geoalchemy2 import Geometry

from app_config import Config


db_location = os.environ['DATABASE_URL']
engine = create_engine(db_location, echo=True)


Base = declarative_base()

Session = sessionmaker(bind=engine)
Session.configure(bind=engine)
session = Session()


adminAssociations = Table(
    'adminAssociations',
    Base.metadata,
    Column(
        'user_id',
        Integer,
        ForeignKey('user.id'),
        primary_key=True),
    Column(
        'campaign_id',
        Integer,
        ForeignKey('campaign.id'),
        primary_key=True))

typeCampaignAssociations = Table(
    'typeCampaignAssociations',
    Base.metadata,
    Column(
        'campaign_id',
        Integer,
        ForeignKey('campaign.id'),
        primary_key=True),
    Column(
        'type_id',
        Integer,
        ForeignKey('featureType.id'),
        primary_key=True))

featureTypeAssociations = Table(
    'featureTypeAssociations',
    Base.metadata,
    Column(
        'feature_id',
        Integer,
        ForeignKey('attribute.id'),
        primary_key=True),
    Column(
        'type_id',
        Integer,
        ForeignKey('featureType.id'),
        primary_key=True))

teamUserAssociations = Table(
    'teamUserAssociations',
    Base.metadata,
    Column(
        'user_id',
        Integer,
        ForeignKey('user.id'),
        primary_key=True),
    Column(
        'team_id',
        Integer,
        ForeignKey('team.id'),
        primary_key=True))

functionCampaignAssociations = Table(
    'functionCampaignAssociations',
    Base.metadata,
    Column(
        'campaign_id',
        Integer,
        ForeignKey('campaign.id')),
    Column(
        'function_id',
        Integer,
        ForeignKey('function.id')))


class User(Base):

    __tablename__ = 'user'

    id = Column(
        'id',
        Integer,
        primary_key=True,
        autoincrement=True)
    osm_user_id = Column(
        String(20),
        unique=True,
        nullable=False)
    email = Column(String(40))
    campaign_creator = relationship(
        'Campaign',
        back_populates='creator',
        lazy=True,
        uselist=False)
    chat_sender = relationship(
        'Chat',
        foreign_keys='Chat.sender_id',
        back_populates='sender',
        lazy=True,
        uselist=False)
    chat_receiver = relationship(
        'Chat',
        foreign_keys='Chat.receiver_id',
        back_populates='reciever',
        lazy=True,
        uselist=False)
    notification_sender = relationship(
        'Notification',
        back_populates='sender',
        lazy=True,
        uselist=False)
    campaigns = relationship(
        'Campaign',
        secondary=adminAssociations,
        lazy='subquery',
        back_populates='users')
    teams = relationship(
        'Team',
        secondary=teamUserAssociations,
        lazy='subquery',
        back_populates='users')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)

    def create(self):
        """ Creates and Saves the current model the DB. """
        session.add(self)
        session.commit()

    def save(self):
        session.commit()

    def get_by_osm_id(self, osm_id):
        """ Returns the user with the specified osm user id. """
        return session.query(User).filter(
            User.osm_user_id == osm_id).first()

    def get_all(self):
        """ Returns all the users registered with field-campaigner. """
        return session.query(User).all()

    def update(self, updated_user_dict):
        """ Updates the user's details """
        if 'osm_user_id' in updated_user_dict:
            self.osm_user_id = updated_user_dict['osm_user_id']
        if 'email' in updated_user_dict:
            self.email = updated_user_dict['email']
        session.commit()

    def delete(self):
        """ Deletes the campaign from the database. """
        session.delete(self)
        session.commit()


class Campaign(Base):

    __tablename__ = 'campaign'

    id = Column(
        'id',
        Integer,
        primary_key=True,
        autoincrement=True)
    creator_id = Column(
        Integer,
        ForeignKey('user.id'),
        nullable=False)
    creator = relationship(
        'User',
        back_populates='campaign_creator')
    users = relationship(
        'User',
        secondary=adminAssociations,
        lazy='subquery',
        back_populates='campaigns')
    feature_types = relationship(
        'FeatureType',
        secondary=typeCampaignAssociations,
        lazy='subquery',
        back_populates='campaigns')
    functions = relationship(
        'Function',
        secondary=functionCampaignAssociations,
        lazy='subquery',
        back_populates='campaigns')
    chat = relationship(
        'Chat',
        back_populates='campaign',
        lazy=True)
    notification = relationship(
        'Notification',
        back_populates='campaign',
        lazy=True)
    geometry = Column(Geometry('POLYGON'))
    task_boundaries = relationship(
        'TaskBoundary',
        back_populates='campaign',
        lazy=True)
    name = Column(
        String(20),
        unique=True,
        nullable=False)
    description = Column(String(200))
    start_date = Column(
        Date(),
        nullable=False)
    end_date = Column(
        Date(),
        nullable=False)
    create_on = Column(
        DateTime(),
        nullable=False)
    link_to_OpenMapKit = Column(
        BOOLEAN(),
        default=False)
    version = Column(Integer)
    uuid = Column(String(100))
    remote_projects = Column(String(30))
    map_type = Column(String(20))
    thumbnail = Column(String(100))

    def __init__(self, **kwargs):
        super(Campaign, self).__init__(**kwargs)

    def create(self):
        """ Creates and saves the current model to DB. """
        session.add(self)
        session.commit()

    def save(self):
        session.commit()

    def get_by_uuid(self, uuid):
        """ Returns the campaign object based on the uuid. """
        return session.query(Campaign).filter(Campaign.uuid == uuid).first()

    def get_all(self):
        """ Returns all the campaigns in the DB. """
        return session.query(Campaign).all()

    def get_all_active(self):
        """ Returns all the active campaigns. """
        from datetime import datetime
        date = datetime.now()
        return session.query(Campaign).filter(
            and_(
                Campaign.start_date <= date,
                date <= Campaign.end_date)).all()

    def get_active_count(self):
        """ Returns the count of all active campaigns. """
        from datetime import datetime
        date = datetime.now()
        return session.query(Campaign).filter(
            and_(
                Campaign.start_date <= date,
                date <= Campaign.end_date)).count()

    def get_all_inactive(self):
        """ Returns all the inactive campaigns. """
        from datetime import datetime
        date = datetime.now()
        return session.query(Campaign).filter(
            or_(Campaign.start_date >= date,
                date >= Campaign.end_date)).all()

    def get_participants(self):
        """ Returns the total number of particpants in the
        campaign."""
        return len(self.users)

    def get_task_boundary(self):
        """ Returns the task_boundary of the campaign. """
        return session.query(TaskBoundary).filter(
            TaskBoundary.campaign_id == self.id).first()

    def get_task_boundary_as_geoJSON(self):
        """ Returns the task boundary in GeoJSON format. """
        return session.query(
            TaskBoundary.coordinates.ST_AsGeoJSON()).filter(
            TaskBoundary.campaign_id == self.id).first()

    def update(self, updated_campaign_dict):
        """ Updates and saves the model object. """
        from datetime import datetime
        if 'name' in updated_campaign_dict:
            self.name = updated_campaign_dict['name']
        if 'description' in updated_campaign_dict:
            self.description = updated_campaign_dict['description']
        if 'start_date' in updated_campaign_dict:
            self.start_date = updated_campaign_dict['start_date']
        if 'end_date' in updated_campaign_dict:
            self.end_date = updated_campaign_dict['end_date']
        session.commit()

    def save_feature_types(self, data):
        """ Creates a new feature type and assigns it to campaign object.
        """
        # pre-processing featureTypes and feature-attributes
        data_types = ast.literal_eval(data['types'])
        for _type in data_types:
            type_dict = data_types[_type]
            name = type_dict['type']
            feature = type_dict['feature']
            featureType = FeatureType(
                feature=feature,
                name=name)
            featureType.create()
            # commit attributes for the feature to the database
            for _tag in type_dict['tags']:
                attribute = Attribute(
                    attribute_name=_tag)
                attribute.create()
                featureType.attributes.append(attribute)
            session.commit()
            self.feature_types.append(featureType)
        session.commit()

    def delete_feature_types(self):
        """ Delete the campaign features from the DB. """
        feature_types = self.feature_types
        for feature_type in feature_types:
            feature_type.delete()
        session.commit()

    def save_geometry(self, data):
        """ Creates a new geomtery object and assigns it to campaign.
        """
        # pre-processing geometry to obtain campaign geometry and taskboundary
        data_geometry = ast.literal_eval(data['geometry'])
        geom = data_geometry['features'][0]['geometry']
        geom_obj = from_shape(asShape(geom), srid=4326)
        area = data_geometry['features'][0]['properties']['area']
        status = data_geometry['features'][0]['properties']['status']
        taskboundary_type = data_geometry['type']
        taskboundary = TaskBoundary(
            coordinates=geom_obj,
            campaign_id=self.id,
            name=area,
            status=status,
            type_boundary=taskboundary_type)
        taskboundary.create()

        self.task_boundaries.append(taskboundary)
        session.commit()

        team = data_geometry['features'][0]['properties']['team']
        team_obj = Team(
            name=team,
            boundary_id=taskboundary.id)
        team_obj.create()

    def delete_taskboundaries(self):
        """ Deletes the geometry from the DB. """
        task_boundaries = self.task_boundaries
        for taskboundary in task_boundaries:
            team = taskboundary.team
            team.delete()
            taskboundary.delete()

    def save_insight_functions(self, data):
        """ Creates a new insight function for the campaign.
        """
        # pre-processing selected_function to obtain functions for the campaign
        data_function_selected = ast.literal_eval(data['selected_functions'])
        for function in data_function_selected:
            name = data_function_selected[function]['function']
            feature = data_function_selected[function]['feature']
            selected_type = data_function_selected[function]['type']
            feature_type = FeatureType()
            _type = feature_type.get_feature_type_by_name(selected_type)
            selected_function = Function(
                name=name,
                feature=feature,
                type_id=_type.id)
            selected_function.create()
            self.functions.append(selected_function)
        session.commit()

    def delete_insight_functions(self):
        """ Deletes the insight function for the campaign. """
        functions = self.functions
        for function in functions:
            function.delete()

    def save_managers(self, data):
        """ Assign users as campaign managers. """
        # pre-processing managers to obtain campaign managers
        user = User()
        managers = self.get_managers()
        for manager in data['campaign_managers']:
            if user.get_by_osm_id(manager):
                manager = user.get_by_osm_id(manager)
            else:
                manager = User(
                    osm_user_id=manager,
                    email=None)
                manager.create()
            if manager not in managers:
                self.users.append(manager)
        session.commit()

    def get_managers(self):
        """ Returns list od managers for the campaign. """
        managers = self.users
        managers = [x.osm_user_id for x in managers]
        return managers

    def create_thumbnail_image(self):
        """ Creates a new thumbnail image for the campaign. """
        try:
            from secret import MAPBOX_TOKEN
            url = 'https://api.mapbox.com/styles/v1/hot/' \
                  'cj7hdldfv4d2e2qp37cm09tl8/static/geojson({overlay})/' \
                  'auto/{width}x{height}?' \
                  'access_token=' + MAPBOX_TOKEN
            geometry = {}
            campaign_geometry = self.get_task_boundary_as_geoJSON()
            geom_obj = ast.literal_eval(campaign_geometry[0])
            geometry['geometry'] = geom_obj
            geometry['type'] = "Feature"
            geometry['properties'] = {}
            geometry = json.dumps(geometry)
            url = url.format(
                    overlay=geometry,
                    width=512,
                    height=300)
        except ImportError:
            from sqlalchemy import func
            url = 'http://staticmap.openstreetmap.de/staticmap.php?'\
                  'center=0.0,0.0&zoom=1&size=512x512&maptype=mapnik'
            polygon = session.query(func.ST_AsGeoJSON(
                TaskBoundary.coordinates.ST_Centroid()
                )).filter(TaskBoundary.campaign_id == self.id).first()
            polygon = ast.literal_eval(polygon[0])
            marker_url = '&markers=%s,%s,lightblue' % (
                    polygon['coordinates'][1],
                    polygon['coordinates'][0])
            url = url + marker_url
        safe_name = hashlib.md5(url.encode('utf-8')).hexdigest() + '.png'
        data_folder = os.path.join(
            Config.campaigner_data_folder,
            'campaign')
        thumbnail_dir = os.path.join(
            data_folder,
            'thumbnail')

        if not os.path.exists(thumbnail_dir):
            os.makedirs(thumbnail_dir)
        image_path = os.path.join(
            thumbnail_dir, safe_name
            )
        if not os.path.exists(image_path):
            request = requests.get(url, stream=True)
            if request.status_code == 200:
                with open(image_path, 'wb') as f:
                    request.raw.decode_content = True
                    shutil.copyfileobj(request.raw, f)
        self.thumbnail = image_path

        session.commit()

    def delete(self):
        """ Deletes the campaign from the database. """
        session.delete(self)
        session.commit()


class Chat(Base):

    __tablename__ = 'chat'

    id = Column(
        'id',
        Integer,
        primary_key=True,
        autoincrement=True)
    campaign_id = Column(
        Integer,
        ForeignKey('campaign.id'),
        nullable=False)
    campaign = relationship(
        'Campaign',
        back_populates='chat')
    sender_id = Column(
        Integer,
        ForeignKey('user.id'),
        nullable=False)
    sender = relationship(
        'User',
        foreign_keys=[sender_id],
        back_populates='chat_sender')
    receiver_id = Column(
        Integer,
        ForeignKey('user.id'),
        nullable=False)
    reciever = relationship(
        'User',
        foreign_keys=[receiver_id],
        back_populates='chat_receiver')
    message = Column(String(200))
    send_time = Column(DateTime())
    delivered = Column(
        BOOLEAN(),
        default=False)

    def __init__(self, **kwargs):
        super(Chat, self).__init__(**kwargs)


class Notification(Base):

    __tablename__ = 'notification'

    id = Column(
        'id',
        Integer,
        primary_key=True,
        autoincrement=True)
    campaign_id = Column(
        Integer,
        ForeignKey('campaign.id'),
        nullable=False)
    campaign = relationship(
        'Campaign',
        back_populates='notification')
    sender_id = Column(
        Integer,
        ForeignKey('user.id'),
        nullable=False)
    sender = relationship(
        'User',
        back_populates='notification_sender')
    notification_message = Column(String(100))
    time = Column(DateTime())
    delivered = Column(
        BOOLEAN(),
        default=False)

    def __init__(self, **kwargs):
        super(Notification, self).__init__(**kwargs)


class FeatureTemplate(Base):

    __tablename__ = 'featureTemplate'

    id = Column(
        'id',
        Integer,
        primary_key=True,
        autoincrement=True)
    name = Column(
        String(20),
        nullable=False)
    description = Column(String(200))
    featureType_id = Column(
        Integer,
        ForeignKey('featureType.id'))
    feature_type = relationship(
        'FeatureType',
        back_populates='feature_template')

    def __init__(self, **kwargs):
        super(FeatureTemplate, self).__init__(**kwargs)


class FeatureType(Base):

    __tablename__ = 'featureType'

    id = Column(
        'id',
        Integer,
        primary_key=True,
        autoincrement=True)
    feature = Column(
        String(20),
        nullable=False)
    name = Column(String(20))
    is_template = Column(
        BOOLEAN(),
        default=False)
    feature_template = relationship(
        'FeatureTemplate',
        back_populates='feature_type')
    function = relationship(
        'Function',
        back_populates='types',
        lazy=True)
    campaigns = relationship(
        'Campaign',
        secondary=typeCampaignAssociations,
        lazy='subquery',
        back_populates='feature_types')
    attributes = relationship(
        'Attribute',
        secondary=featureTypeAssociations,
        lazy='subquery',
        back_populates='feature_types')

    def __init__(self, **kwargs):
        super(FeatureType, self).__init__(**kwargs)

    def get_templates(self):
        """ Returns the templates feature types. """
        return session.query(FeatureType).filter(
            FeatureType.is_template == true()).all()

    def create(self):
        """ Creates and saves the current model to DB. """
        session.add(self)
        session.commit()

    def get_feature_type_by_name(self, name):
        """ Returns the latest feature type of the specified name. """
        return session.query(FeatureType).filter(
            FeatureType.name == name
            ).order_by(FeatureType.id.desc()).first()

    def delete(self):
        """ Adds the object in the delete queue. """
        session.delete(self)


class Attribute(Base):

    __tablename__ = 'attribute'

    id = Column(
        'id',
        Integer,
        primary_key=True,
        autoincrement=True)
    attribute_name = Column(String(20))
    feature_types = relationship(
        'FeatureType',
        secondary=featureTypeAssociations,
        lazy='subquery',
        back_populates='attributes')

    def __init__(self, **kwargs):
        super(Attribute, self).__init__(**kwargs)

    def create(self):
        """ Creates and saves the current model to DB. """
        session.add(self)
        session.commit()


class TaskBoundary(Base):

    __tablename__ = 'taskBoundary'

    id = Column(
        'id',
        Integer,
        primary_key=True,
        autoincrement=True)
    coordinates = Column(Geometry('POLYGON'))
    name = Column(String(100))
    status = Column(String(100))
    type_boundary = Column(String(100))
    team = relationship(
        'Team',
        back_populates='boundary',
        lazy=True,
        uselist=False)
    campaign_id = Column(
        Integer,
        ForeignKey('campaign.id'),
        nullable=False)
    campaign = relationship(
        'Campaign',
        back_populates='task_boundaries',
        lazy=True)

    def __init__(self, **kwargs):
        super(TaskBoundary, self).__init__(**kwargs)

    def create(self):
        """ Creates and saves the current model to DB. """
        session.add(self)
        session.commit()

    def delete(self):
        """ Adds the object in the delete queue. """
        session.delete(self)


class Team(Base):

    __tablename__ = 'team'

    id = Column(
        'id',
        Integer,
        primary_key=True,
        autoincrement=True)
    name = Column(
        String(20),
        nullable=False)
    boundary_id = Column(
        Integer,
        ForeignKey('taskBoundary.id'),
        nullable=False)
    boundary = relationship(
        'TaskBoundary',
        back_populates='team')
    users = relationship(
        'User',
        secondary=teamUserAssociations,
        lazy='subquery',
        back_populates='teams')

    def __init__(self, **kwargs):
        super(Team, self).__init__(**kwargs)

    def create(self):
        """ Creates and saves the current model to DB. """
        session.add(self)
        session.commit()

    def get_all(self):
        """ Returns all the teams registered in field campaigner. """
        return session.query(Team).all()

    def delete(self):
        """ Adds the object in the delete queue. """
        session.delete(self)


class Function(Base):

    __tablename__ = 'function'

    id = Column(
        'id',
        Integer,
        primary_key=True,
        autoincrement=True)
    name = Column(
        String(100),
        nullable=False)
    feature = Column(String(100))
    type_id = Column(
        Integer,
        ForeignKey('featureType.id'),
        nullable=False)
    types = relationship(
        'FeatureType',
        back_populates='function')
    campaigns = relationship(
        'Campaign',
        secondary=functionCampaignAssociations,
        lazy='subquery',
        back_populates='functions')

    def __init__(self, **kwargs):
        super(Function, self).__init__(**kwargs)

    def create(self):
        """ Creates and saves the current model to DB. """
        session.add(self)
        session.commit()

    def delete(self):
        """ Adds the object in the delete queue. """
        session.delete(self)