import geopandas as gpd
import folium
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry
from sqlalchemy import text

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = ('postgresql+psycopg2://'
                                         'pycrum_user:'
                                         'pOCwAVVMw3YDbjPfMKkHSyZpK9JGicR3@'
                                         'dpg-ckrvo87d47qs73f05310-a.ohio-postgres.render.com/'
                                         'pycrum')
app.config['TEMPLATES_AUTO_RELOAD'] = True
db = SQLAlchemy(app)


# ----------------------------------------------------------------------------------------------------------------------
class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    geolocation = db.Column(Geometry('POINT'))
    name = db.Column(db.String(80))
    address = db.Column(db.String(120))
    account_number = db.Column(db.Integer)
    premise_number = db.Column(db.Integer)
    component_id = db.Column(db.String(80))
    component_type = db.Column(db.String(120))
    number_accounted = db.Column(db.Integer)
    number_off = db.Column(db.Integer)
    area = db.Column(db.String(80))
    job_set = db.Column(db.String(120))

    def __init__(self, geolocation, name, address, account_number, premise_number, component_id, component_type,
                 number_accounted, number_off, area, job_set):
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
def generate_shape_map():
    # use sql and database connection to query customer data and create a geo data frame
    gdf = gpd.GeoDataFrame.from_postgis("select * from customers", db.engine, geom_col='geolocation')
    # set location and convert to geojson for choropleth layer
    gdf = gdf.set_crs("EPSG:4326")
    geojson = gdf.to_crs(epsg='4326').to_json()

    m = folium.Map(location=[gdf.iloc[0].geolocation.centroid.y, gdf.iloc[0].geolocation.centroid.x], zoom_start=8)

    # create a folium choropleth object that shows markers for each billing customer
    folium.Choropleth(geo_data=geojson, name='choropleth', data=gdf, columns=['name', 'address'],
                      fill_color='YlGn', fill_opacity=0.7, line_opacity=0.2, legend_name='Customers').add_to(m)

    # create a folium geojson object from same dataset
    geo = folium.GeoJson(data=gdf, popup=folium.GeoJsonPopup(fields=['name', 'address', "link"], labels=True))

    geo.add_to(m)

    # loop through geojson features
    for feature in geo.data["features"]:
        # create list of customer info to pass to link
        customer_list = [feature["properties"]["id"],
                         feature["properties"]["name"],
                         feature["properties"]["address"],
                         feature["properties"]["account_number"],
                         feature["properties"]["premise_number"]]

        # generate a reference link to customer
        link = f"<a href='{url_for('info_page', customer=customer_list)}'>Update Record</a>"
        # add link as new field to generate in map popup
        feature["properties"]["link"] = link

    # save map to be displayed
    m.save("templates/map.html")


# ----------------------------------------------------------------------------------------------------------------------
@app.route('/')
def root():
    return render_template('home_page.html')


# map page that show the map rendered with map generation
@app.route('/map_page')
def map_page():
    return render_template('map_page.html')


# creates the map to be rendered into an iFrame on the map page
@app.route('/map_view')
def map_view():
    generate_shape_map()
    return render_template('map.html')


# record page that shows all customer information from a database query
@app.route('/record_page')
def record_page():
    data = db.session.execute(text("SELECT * FROM customers"))
    return render_template('record_page.html', data=data)


# for processing uploaded shape files
@app.route('/upload_page', methods=['POST'])
def upload_page():
    # file = request.files.get('file')
    generate_shape_map()
    # generate_records()

    return redirect('/')


# shows more information for customer when clicked on from map link
@app.route('/info_page')
def info_page():
    customer = request.args.getlist('customer')
    return render_template('info_page.html', data=customer)


# add record from the records page
@app.route('/add_record', methods=['POST'])
def add_record():
    return render_template('add_record.html')


# route that handles adding the customer by getting form data and inserting into database
@app.route('/add_customer', methods=['POST'])
def add_customer():

    name = request.form.get("Name")
    address = request.form.get('Address')
    account = request.form.get('Account')
    premise = request.form.get('Premise')
    component_id = request.form.get('Component_ID')
    component_type = request.form.get('Component_Type')
    number_accounted = request.form.get('Number_Accounted')
    number_off = request.form.get('Number_Off')
    area = request.form.get('Area')
    job_set = request.form.get('Job_Set')
    latitude = request.form.get('Latitude')
    longitude = request.form.get('Longitude')

    new_customer = Customer(geolocation='POINT('+str(latitude)+' '+str(longitude)+')', name=name, address=address,
                            account_number=account, premise_number=premise, component_id=component_id,
                            component_type=component_type, number_accounted=number_accounted, number_off=number_off,
                            area=area, job_set=job_set)
    db.session.add(new_customer)
    db.session.commit()

    data = db.session.execute(text("SELECT * FROM customers"))
    return render_template('record_page.html', data=data)


# route that handles updating the customer information in map view
@app.route('/update_customer', methods=['POST'])
def update_customer():

    u_id = request.form.get("update_id")
    u_name = request.form.get("update_name")
    u_address = request.form.get('update_address')
    u_account = request.form.get('update_account')
    u_premise = request.form.get('update_premise')

    updated_customer = db.session.query(Customer).filter(Customer.id == u_id).first()

    if updated_customer:
        if u_name != "":
            updated_customer.name = u_name
        if u_address != "":
            updated_customer.address = u_address
        if u_account != "":
            updated_customer.account_number = int(u_account)
        if u_premise != "":
            updated_customer.premise_number = int(u_premise)

        db.session.commit()
        generate_shape_map()

        return render_template('map.html')

    else:
        return render_template('map.html')


# route that shows the edit customer page from the records page
@app.route('/edit_customer_page', methods=['POST'])
def edit_customer_page():

    e_id = request.form.get("edit_id")
    e_location = request.form.get("edit_location")
    e_name = request.form.get("edit_name")
    e_address = request.form.get('edit_address')
    e_account = request.form.get('edit_account')
    e_premise = request.form.get('edit_premise')
    e_comp_id = request.form.get('edit_comp_id')
    e_comp_type = request.form.get('edit_comp_type')
    e_num_acc = request.form.get('edit_num_acc')
    e_num_off = request.form.get('edit_num_off')
    e_area = request.form.get('edit_area')
    e_job_set = request.form.get('edit_job_set')
    editing_customer = [e_id, e_location, e_name, e_address, e_account, e_premise, e_comp_id, e_comp_type, e_num_acc,
                        e_num_off, e_area, e_job_set]

    return render_template('edit_record.html', data=editing_customer)


# route that handles editing customer data by getting the info from the edit page
@app.route('/edit_customer', methods=['POST'])
def edit_customer():

    new_e_id = request.form.get("new_edit_id")
    new_e_latitude = request.form.get("new_edit_latitude")
    new_e_longitude = request.form.get("new_edit_longitude")
    new_e_name = request.form.get("new_edit_name")
    new_e_address = request.form.get('new_edit_address')
    new_e_account = request.form.get('new_edit_account')
    new_e_premise = request.form.get('new_edit_premise')
    new_e_comp_id = request.form.get('new_edit_comp_id')
    new_e_comp_type = request.form.get('new_edit_comp_type')
    new_e_num_acc = request.form.get('new_edit_num_acc')
    new_e_num_off = request.form.get('new_edit_num_off')
    new_e_area = request.form.get('new_edit_area')
    new_e_job_set = request.form.get('new_edit_job_set')

    edited_customer = db.session.query(Customer).filter(Customer.id == new_e_id).first()

    if edited_customer:
        if new_e_latitude != "" and new_e_longitude != "":
            edited_customer.geolocation = 'POINT(' + str(new_e_latitude) + ' ' + str(new_e_longitude) + ')'
        if new_e_name != "":
            edited_customer.name = new_e_name
        if new_e_address != "":
            edited_customer.address = new_e_address
        if new_e_account != "":
            edited_customer.account_number = int(new_e_account)
        if new_e_premise != "":
            edited_customer.premise_number = int(new_e_premise)
        if new_e_comp_id != "":
            edited_customer.component_id = new_e_comp_id
        if new_e_comp_type != "":
            edited_customer.component_type = new_e_comp_type
        if new_e_num_acc != "":
            edited_customer.number_accounted = new_e_num_acc
        if new_e_num_off != "":
            edited_customer.number_off = new_e_num_off
        if new_e_area != "":
            edited_customer.area = new_e_area
        if new_e_job_set != "":
            edited_customer.job_set = new_e_job_set

        db.session.commit()
        data = db.session.execute(text("SELECT * FROM customers"))
        return render_template('record_page.html', data=data)

    else:
        data = db.session.execute(text("SELECT * FROM customers"))
        return render_template('record_page.html', data=data)


# route that handles deleting customer by getting id from record page form
@app.route('/delete_customer', methods=['POST'])
def delete_customer():

    delete_id = request.form.get("delete_id")

    deleting_customer = db.session.query(Customer).filter(Customer.id == delete_id).first()

    if deleting_customer:
        db.session.delete(deleting_customer)
        db.session.commit()
        data = db.session.execute(text("SELECT * FROM customers"))
        return render_template('record_page.html', data=data)

    else:
        data = db.session.execute(text("SELECT * FROM customers"))
        return render_template('record_page.html', data=data)
