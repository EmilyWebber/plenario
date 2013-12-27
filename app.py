from flask import Flask, make_response, request, render_template
from flask.ext.sqlalchemy import SQLAlchemy
import os
from datetime import date
import json
from sqlalchemy import Table, func, distinct, Column
from sqlalchemy.exc import NoSuchTableError
from geoalchemy2 import Geometry

app = Flask(__name__)
CONN_STRING = os.environ['WOPR_CONN']
app.config['SQLALCHEMY_DATABASE_URI'] = CONN_STRING

db = SQLAlchemy(app)

dthandler = lambda obj: obj.isoformat() if isinstance(obj, date) else None

def make_query(table, raw_query_params):
    table_keys = table.columns.keys()
    args_keys = raw_query_params.keys()
    resp = {
        'meta': {
            'status': 'error',
            'message': '',
        },
        'objects': [],
    }
    status_code = 200
    query_clauses = []
    valid_query = True
    if 'offset' in args_keys:
        args_keys.remove('offset')
    if 'limit' in args_keys:
        args_keys.remove('limit')
    for query_param in args_keys:
        try:
            field, operator = query_param.split('__')
        except ValueError:
            field = query_param
            operator = 'eq'
        query_value = raw_query_params.get(query_param)
        column = table.columns.get(field)
        if field not in table_keys:
            resp['meta']['message'] = '"%s" is not a valid fieldname' % field
            status_code = 400
            valid_query = False
        elif operator == 'in':
            query = column.in_(query_value.split(','))
            query_clauses.append(query)
        elif operator == 'within':
            # TODO: Capture geospatial queries here and format like so:
            # .filter(table.c.geom.ST_Within(func.ST_GeomFromGeoJSON(geo)))
            # This should work because we are reflecting the table with 
            # a proper geometry column (see line 125)
            val = json.loads(query_value)['geometry']
            val['crs'] = {"type":"name","properties":{"name":"EPSG:4326"}}
            query = column.ST_Within(func.ST_GeomFromGeoJSON(json.dumps(val)))
            query_clauses.append(query)
        else:
            try:
                attr = filter(
                    lambda e: hasattr(column, e % operator),
                    ['%s', '%s_', '__%s__']
                )[0] % operator
            except IndexError:
                resp['meta']['message'] = '"%s" is not a valid query operator' % operator
                status_code = 400
                valid_query = False
                break
            if query_value == 'null':
                query_value = None
            query = getattr(column, attr)(query_value)
            query_clauses.append(query)
    return valid_query, query_clauses, resp, status_code

@app.route('/api/')
def meta():
    status_code = 200
    table = Table('dat_master', db.Model.metadata,
            autoload=True, autoload_with=db.engine)
    resp = []
    # TODO: Doing aggregate queries here is super slow. It would be nice to speed it up
    # This query only performs well after making an index on dataset_name
    values = db.session.query(
        distinct(table.columns.get('dataset_name'))).all()
    for value in values:
       #obs_to, obs_from = (value[1].strftime('%Y-%m-%d'), value[2].strftime('%Y-%m-%d'))
       #observed_range = '%s - %s' % (obs_from, obs_to)
       #s = select([func.ST_AsGeoJSON(func.ST_Estimated_Extent(
       #    'dat_%s' % value[0], 'geom'))])
       #bbox = json.loads(list(db.engine.execute(s))[0][0])
        d = {
            'machine_name': value[0],
            'human_name': ' '.join(value[0].split('_')).title(),
           #'observed_date_range': observed_range,
           #'bounding_box': bbox,
        }
        resp.append(d)
    resp = make_response(json.dumps(resp), status_code)
    resp.headers['Content-Type'] = 'application/json'
    return resp

@app.route('/api/<dataset>/')
def dataset(dataset):
    offset = request.args.get('offset')
    limit = request.args.get('limit')
    if not offset:
        offset = 0
    if not limit:
        limit = 100
    status_code = 200
    geo = False
    try:
        table = Table('dat_%s' % dataset, db.Model.metadata,
                autoload=True, autoload_with=db.engine)
        if hasattr(table.c, 'geom'):
            geo = True
            table = Table('dat_%s' % dataset, db.Model.metadata,
                    Column('geom', Geometry('POINT')),
                    autoload=True, autoload_with=db.engine,
                    extend_existing=True)
        table_keys = table.columns.keys()
        raw_query_params = request.args.copy()
        valid_query, query_clauses, resp, status_code = make_query(table,raw_query_params)
    except NoSuchTableError:
        valid_query = False
        resp = {
            'meta': {
                'status': 'error',
                'message': 'No dataset called "%s"' % dataset,
            },
            'objects': [],
        }
        status_code = 400
    if valid_query:
        resp['meta']['status'] = 'ok'
        resp['meta']['message'] = None
        base_query = db.session.query(table)
        if geo:
            base_query = db.session.query(table, func.ST_AsGeoJSON(table.c.geom))
        for clause in query_clauses:
            base_query = base_query.filter(clause)
        values = [r for r in base_query.offset(offset).limit(limit).all()]
        for value in values:
            d = {}
            for k,v in zip(table_keys, value):
                d[k] = v
            if geo:
                d['geom'] = json.loads(value[-1])
            resp['objects'].append(d)
    resp = make_response(json.dumps(resp, default=dthandler), status_code)
    resp.headers['Content-Type'] = 'application/json'
    return resp

@app.route('/')
def index():
    return render_app_template('index.html')

@app.route('/map/')
def map():
    return render_app_template('map.html')

# UTILITY
def render_app_template(template, **kwargs):
    '''Add some goodies to all templates.'''

    if 'config' not in kwargs:
        kwargs['config'] = app.config
    return render_template(template, **kwargs)

if __name__ == '__main__':
    app.run(debug=True)
