####################################################################################################
# dbcal.py
#    This file defines the tables used for storing event information,
#    and functions for CRUD operations relating to event information.
#
#    Questions:
#        Should we include the ability to show relevant holidays?
#        Do we need/want a table for "event type" for filtering? Eg: assignment, seminar, etc.
#            I'd say no. An event is an event. It's up to the
#            object type - assigment, etc. - to give context.
#
####################################################################################################
from datetime import datetime, date, timedelta

# Define some useful constants.
NE = IS_NOT_EMPTY()
DEBUG = True
OUTPUT_DATE_FORMAT = '%Y-%m-%d'
INPUT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

#########################
# Table definitions
#########################

################################################################################
# event_visibility
#    Defines who can see which events. This allows filtering
#    of events in the calendar.
#
################################################################################
db.define_table(
    'event_visibility',
    Field('visibility', unique=True, requires=NE),
    format='%(visibility)s')
# db.event_visibility.id.readable = db.event_visibility.id.writable = False

################################################################################
# cal_event
#    requirements
#      An event must have a start date.
#      An event has an optional end date.
#
#    FC = FullCalendar in the comments below.
#
#   Proposed changes:
#      Convention: If an event has a start date, but not an end date,
#                  then the event is a task.
#
################################################################################
db.define_table(
    'cal_event',                                                         ## (id) FC Event field
    Field('owner_id', 'reference auth_user', default=auth.user_id),
    Field('title', requires=NE),                                         ## FC Event field
    Field('details', 'text'),
    Field('start_date', 'datetime', requires=NE),                        ## FC Event field
    Field('end_date', 'datetime'),                                       ## FC Event field
    Field('all_day', 'boolean', default=False),                          ## FC Event field
    Field('url', requires=IS_EMPTY_OR(IS_URL())),                        ## FC Event field
    Field('visibility', 'reference event_visibility'),
    Field('course_id', 'reference course', required=False, requires=IS_EMPTY_OR(IS_IN_DB(db, 'course.id', '%(name)s - %(code)s'))),
    auth.signature,
    format='%(title)s')
db.cal_event.id.readable = db.cal_event.id.writable = False
db.cal_event.owner_id.readable = db.cal_event.owner_id.writable = False

################################################################################
## A "constant" class, the purpose of which is to give a readable way
## to declare which default date - first day of the month or
## last day of the month - should be used.
################################################################################
class DATE_DEFAULT(object):
    start = 0
    end = 1

################################################################################
## This is a collection of queries that are commonly used
## to retrieve event information. These should be used in functions to make
## the code more readable and maintainable.
################################################################################
## Constants
PERSONAL_EVENTS = (db.cal_event.owner_id == auth.user_id)
PUBLIC_EVENTS = (db.event_visibility.visibility=='public')
ALL_MY_EVENTS = (PERSONAL_EVENTS | PUBLIC_EVENTS)
NO_END_DATE = (db.cal_event.end_date == None)
if auth.user_id:
    IS_TEACHER = db((db.auth_user.id == auth.user_id)).select(db.auth_user.is_teacher).first().is_teacher
    IS_ADMINISTRATOR = db((db.auth_user.id == auth.user_id)).select(db.auth_user.is_administrator).first().is_administrator
    CAN_CREATE_EVENTS = (IS_TEACHER | IS_ADMINISTRATOR)

## Functions
def STARTS_AFTER_DATE(date):
    '''Returns a query that selects events that start after the specified date.'''
    return (db.cal_event.start_date >= date)

def ENDS_BEFORE_DATE(date):
    '''Returns a query that selects events that end before the specified date.'''
    return (db.cal_event.end_date <= date)

def NO_END_DATE_OR_ENDS_BEFORE_DATE(date):
    '''Returns a query that selects events that either have no end date or end before the specified date.'''
    return (NO_END_DATE | ENDS_BEFORE_DATE(date))

def IS_IN_DATE_RANGE(start_date, end_date=None):
    '''Returns a query that selects events that either start after or end before the specified date.'''
    return (STARTS_AFTER_DATE(start_date) | NO_END_DATE_OR_ENDS_BEFORE_DATE(end_date))

def EVENTS_FOR_COURSE(course_id):
    '''Returns a query that selects events that are associated with the specified course.'''
    return (db.cal_event.course_id == course_id)

################################################################################
## A list of event fields to be used in queries for event information.
## These should be used to make code more readable and maintainable.
################################################################################
EVENT_FIELDS = [db.cal_event.id,
                db.cal_event.owner_id,
                db.cal_event.title,
                db.cal_event.details,
                db.cal_event.start_date,
                db.cal_event.end_date,
                db.cal_event.all_day,
                db.cal_event.url,
                db.event_visibility.visibility,
                db.cal_event.visibility,
                db.cal_event.course_id]

#########################
# Function definitions
#########################

def add_event(title, visibility, owner=auth.user_id, details='',
              start_date=date.today(), end_date=None, all_day=False, url=None, course_id=None):
    """Add a new event to the table."""
    from datetime import datetime
    start = _convert_string_to_date(start_date, default=DATE_DEFAULT.start)
    end = _convert_string_to_date(end_date, default=DATE_DEFAULT.end)
    db.cal_event.insert(owner_id=owner,
                        title=title,
                        details=details,
                        start_date=start,
                        end_date=end,
                        all_day=all_day,
                        url=url,
                        visibility=visibility,
                        course_id=course_id)

def update_event(event_id, title, details, start_date, end_date, all_day, url, visibility, course_id):
    """Update the given event."""
    event = db(db.cal_event.id == event_id).select(db.cal_event.id, db.cal_event.owner_id).first()
    if event:
        if auth.user_id != event.owner_id:
            raise Exception('You do not own the event "%s".' % title)
        start = _convert_string_to_date(start_date, fmt=INPUT_DATE_FORMAT, default=DATE_DEFAULT.start)
        end = _convert_string_to_date(end_date, fmt=INPUT_DATE_FORMAT, default=DATE_DEFAULT.end)
        start, end = _sort_dates(start, end)
        db(db.cal_event.id == event_id).update(title=title,
                                               details=details,
                                               start_date=start,
                                               end_date=end,
                                               all_day=all_day,
                                               url=url,
                                               visibility=visibility,
                                               course_id=course_id)
    else:
        raise Exception('Could not find event')

def delete_event(event_id, user_id=auth.user_id):
    """Delete the given event."""
    # Check if the user is the owner of the event.
    # If not, don't allow them to delete it.
    pass

def my_events(start_date, end_date, json=False):
    """Events for the logged-in user."""
    start = _convert_string_to_date(start_date, fmt=OUTPUT_DATE_FORMAT, default=DATE_DEFAULT.start)
    end = _convert_string_to_date(end_date, fmt=OUTPUT_DATE_FORMAT, default=DATE_DEFAULT.end)
    try:
        query = (ALL_MY_EVENTS & IS_IN_DATE_RANGE(start, end) &
                 (db.cal_event.visibility == db.event_visibility.id))
    except:
        return
    if json:
        return _get_events_json(query, EVENT_FIELDS) # , db.cal_event.id)
    else:
        return _get_events(query, EVENT_FIELDS) # , db.cal_event.id)

def course_events(start_date, end_date, course_id):
    '''
    Events for the selected-course-in user.
    '''
    from datetime import datetime
    start = _convert_string_to_date(start_date, default=DATE_DEFAULT.start)
    end = _convert_string_to_date(end_date, default=DATE_DEFAULT.end)
    try:
        query = (EVENTS_FOR_COURSE(course_id) &
                 IS_IN_DATE_RANGE(start, end) &
                 (db.cal_event.visibility == db.event_visibility.id))
    except:
        return
    return _get_events_json(query, EVENT_FIELDS)

def _get_events(query, fields, groupby=None):
    '''
    Executes the query against the database, returning the given fields.
    Results are grouped by the given field.
    '''
    return db(query).select(*fields, groupby=groupby)

def _get_events_json(query, fields, groupby=None):
    '''
    Executes the query against the database, returning the given fields in json format.
    Results are grouped by the given field.
    '''
    ############## Refactor this ##############
    # To do:
    # This needs error handling
    #
    # Possible enhancements:
    #     Choose date format based on whether the event is associated with a specific time.
    #     I'm not 100% comfortable with the groupby, but it gets rid of duplicates.
    #        We'll need to keep an eye on it.
    events = _get_events(query, fields, groupby)
    cal = []
    for evt in events:
        c = {'id': evt.cal_event.id,
             'title': evt.cal_event.title,
             'details': evt.cal_event.details,
             'start': evt.cal_event.start_date.strftime(OUTPUT_DATE_FORMAT),
             'allDay': evt.cal_event.all_day,
             'url': evt.cal_event.url,
             'visibility': evt.event_visibility.visibility,
             'vis_code': evt.event_visibility.visibility,
             'course_id': evt.cal_event.course_id}
        if evt.cal_event.end_date:
            c['end'] = evt.cal_event.end_date.strftime(OUTPUT_DATE_FORMAT)
        cal.append(c)
    return cal

def _first_of_month():
    '''
    Returns the first day of the current month.
    '''
    from datetime import datetime
    first = datetime.today()
    first = datetime(first.year, first.month, 1)
    return first

def _last_of_month():
    '''
    Returns the last day of the current month.
    '''
    from datetime import datetime
    last = datetime.today()
    last = datetime(last.year, last.month + 1, 1)
    last = last + timedelta(days=-1)
    return last

def _convert_string_to_date(date, fmt=INPUT_DATE_FORMAT, default=DATE_DEFAULT.start):
    '''
    Converts a date string to a datetime object.
    If date is already a datetime object, it just gets returned.
    If date is neither a datetime object or a string, a default date is returned.
    '''
    from datetime import datetime
    from types import StringType
    if type(date) is StringType:
        return datetime.strptime(date, fmt)
    elif isinstance(date, datetime):
        return date
    else:
        if default == DATE_DEFAULT.start:
            return _first_of_month()
        elif default == DATE_DEFAULT.end:
            return _last_of_month()
        else:
            return _first_of_month()

def _sort_dates(start, end):
    '''Ensures that start is earlier than end.'''
    if end < start:
        tmp = start
        start = end
        end = tmp
    return (start, end)

#########################
# Load defaults
#########################

################################################################################
# Default visiibility levels for events:
#    public: Anyone visiting the site can see, regardless of
#            whether they are logged in.
#    school: Any user logged into the system can see "school" events.
#    class : Only students entrolled in the class and the teacher of the class
#            can see these events when they are logged into the system.
#    staff : Only teachers and adminstrators can see these events
#            when they are logged into the system.
#    admin : Only members of the administrator group can see these events.
#
################################################################################
if db(db.event_visibility).isempty():
    db.event_visibility.bulk_insert([{'visibility':'admin'},
                                     {'visibility':'public'},
                                     {'visibility':'school'},
                                     {'visibility':'class'},
                                     {'visibility':'staff'}])
# if DEBUG:
#     from gluon.contrib.populate import populate
#     if db(db.auth_user).count() == 1:
#         # auth.get_or_create_user(first_name='Bryan',
#         #                         last_name='Patzke',
#         #                         email='bryan.patzke@insignis.com',
#         #                         password=CRYPT('bobbob'))
#         populate(db.auth_user, 5)
#     if db(db.cal_event).isempty():
#         populate(db.cal_event, 10)

