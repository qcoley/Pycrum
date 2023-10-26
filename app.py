import geopandas as gpd
import folium
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from geoalchemy2 import Geometry

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://pycrum_user:pOCwAVVMw3YDbjPfMKkHSyZpK9JGicR3@dpg-ckrvo87d47qs73f05310-a/pycrum'
db = SQLAlchemy(app)


# ----------------------------------------------------------------------------------------------------------------------
class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    geolocation = db.Column(Geometry('POINT'))
    name = db.Column(db.String(80), unique=True)
    address = db.Column(db.String(120), unique=True)
    account_number = db.Column(db.Integer, unique=True)
    premise_number = db.Column(db.Integer, unique=True)
    component_id = db.Column(db.String(80), unique=True)
    component_type = db.Column(db.String(120), unique=True)
    number_accounted = db.Column(db.Integer, unique=True)
    number_off = db.Column(db.Integer, unique=True)
    area = db.Column(db.String(80), unique=True)
    job_set = db.Column(db.String(120), unique=True)

    def __init__(self, geolocation, name, address, account_number, premise_number, component_id, component_type, number_accounted,
                 number_off, area, job_set):

        self.geolocation = geolocation
        self.name = name
        self.address = address
        self.account_number = account_number
        self.premise_number = premise_number
        self.component_id = component_id
        self.component_type = component_type
        self.number_accounted = number_accounted
        self.number_off = number_off
        self.area = area
        self.job_set = job_set

    def __repr__(self):
        return f'<Customer {self.name}>'


# ----------------------------------------------------------------------------------------------------------------------
@app.route('/')
def root():

    
    # db.create_all()

    '''
    # insert a new record
    new_customer = Customer(geolocation='POINT(-85.34 33.64)', name="customer2", address="address2", account_number=2, premise_number=2, component_id="",
                            component_type="", number_accounted=2, number_off=2, area="", job_set="")
    db.session.add(new_customer)
    db.session.commit()

    # query all records
    customers = Customer.query.all()
    print(customers)
    '''
    

    return render_template('home_page.html')


@app.route('/map_page')
def map_page():
    return render_template('map_page.html')


@app.route('/record_page')
def record_page():
    return render_template('record_page.html')


@app.route('/upload_page', methods=['POST'])
def upload_page():
    file = request.files.get('file')
    generate_shape_map(None, None)
    generate_records()

    return redirect('/')


@app.route('/info_page')
def info_page():
    customer = request.args.getlist('customer')
    return render_template('info_page.html', data=customer)


@app.route('/edit_page', methods=['POST'])
def edit_page():
    new_name = request.form.get('name')
    new_address = request.form.get('address')

    # generate_shape_map('billing.shp', new_name, new_address)

    return render_template('mapped.html', data='map.html')


# Create a route that returns the locations as JSON
@app.route('/api/locations')
def get_locations():
    # Query the database
    locations = db.session.query(Location).all()
    # Convert the results to a list of dictionaries
    data = []
    for location in locations:
        data.append({
            'id': location.id,
            'name': location.name,
            'latitude': location.geolocation.y,
            'longitude': location.geolocation.x
        })
    # Return the JSON response
    return jsonify(data)
