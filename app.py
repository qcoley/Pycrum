import geopandas as gpd
import folium
import os
from flask import Flask, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry
from sqlalchemy import text
from werkzeug.utils import secure_filename

os.makedirs('uploads', exist_ok=True)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = ('postgresql+psycopg2://'
                                         'pycrum_user:'
                                         'pOCwAVVMw3YDbjPfMKkHSyZpK9JGicR3@'
                                         'dpg-ckrvo87d47qs73f05310-a.ohio-postgres.render.com/'
                                         'pycrum')
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['UPLOAD_FOLDER'] = 'uploads'
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

    m = folium.Map(location=[gdf.iloc[0].geolocation.centroid.y, gdf.iloc[0].geolocation.centroid.x], zoom_start=10)

    # create a folium choropleth object that shows markers for each billing customer
    folium.Choropleth(geo_data=geojson, name='choropleth', data=gdf, columns=['name', 'address'],
                      fill_color='YlGn', fill_opacity=0.7, line_opacity=0.2, legend_name='Customers').add_to(m)

    # create a folium geojson object from same dataset
    geo = folium.GeoJson(data=gdf, popup=folium.GeoJsonPopup(fields=['name', 'address', "link"], labels=True))

    geo.add_to(m)

    # loop through geojson features
    for feature in geo.data["features"]:
        # create list of customer info to pass to link
        record_list = [feature["properties"]["id"],
                       feature["properties"]["name"],
                       feature["properties"]["address"],
                       feature["properties"]["account_number"],
                       feature["properties"]["premise_number"]]

        # generate a reference link to customer
        link = f"<a href='{url_for('update_record_page', record=record_list)}' target='_top'>Update Record</a>"
        # add link as new field to generate in map popup
        feature["properties"]["link"] = link

    # save map to be displayed
    m.save("templates/map.html")


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
@app.route('/')
def root():
    # for when database needs to be created from Models
    # db.create_all()
    return render_template('home_page.html')


@app.route('/upload', methods=['POST'])
def upload():
    if "file" in request.files:
        file = request.files["file"]
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    return render_template('home_page.html')


# app routes below correlate to map view
# ----------------------------------------------------------------------------------------------------------------------
# map page that show the map rendered with map generation
@app.route('/map_page')
def map_page():
    return render_template('map_page.html')


# creates the map to be rendered into an iFrame on the map page
@app.route('/map_view')
def map_view():
    generate_shape_map()
    return render_template('map.html')


# shows more information for record when clicked on from map link for updating
@app.route('/update_record_page')
def update_record_page():
    record = request.args.getlist('record')
    return render_template('update_record_page.html', data=record)


# route that handles updating the record information from map view record update
@app.route('/update_record', methods=['POST'])
def update_record():
    u_id = request.form.get("update_id")
    u_name = request.form.get("update_name")
    u_address = request.form.get('update_address')
    u_account = request.form.get('update_account')
    u_premise = request.form.get('update_premise')

    updated_record = db.session.query(Customer).filter(Customer.id == u_id).first()

    if updated_record:
        if u_name != "":
            updated_record.name = u_name
        if u_address != "":
            updated_record.address = u_address
        if u_account != "":
            updated_record.account_number = int(u_account)
        if u_premise != "":
            updated_record.premise_number = int(u_premise)

        db.session.commit()
        generate_shape_map()

        return render_template('map_page.html')

    else:
        return render_template('map_page.html')


# app routes below correlate to record view
# ----------------------------------------------------------------------------------------------------------------------
# record page that shows all record information from a database query
@app.route('/record_page')
def record_page():
    data = db.session.execute(text("SELECT * FROM customers"))
    return render_template('record_page.html', data=data)


# add record from the records page
@app.route('/add_record_page', methods=['POST'])
def add_record_page():
    return render_template('add_record_page.html')


# route that handles adding the record by getting form data and inserting into database
@app.route('/add_record', methods=['POST'])
def add_record():
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

    new_record = Customer(geolocation='POINT(' + str(latitude) + ' ' + str(longitude) + ')', name=name, address=address,
                          account_number=account, premise_number=premise, component_id=component_id,
                          component_type=component_type, number_accounted=number_accounted, number_off=number_off,
                          area=area, job_set=job_set)
    db.session.add(new_record)
    db.session.commit()

    data = db.session.execute(text("SELECT * FROM customers"))
    return render_template('record_page.html', data=data)


# route that shows the edit record page from the records page
@app.route('/edit_record_page', methods=['POST'])
def edit_record_page():
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
    editing_record = [e_id, e_location, e_name, e_address, e_account, e_premise, e_comp_id, e_comp_type, e_num_acc,
                      e_num_off, e_area, e_job_set]

    return render_template('edit_record_page.html', data=editing_record)


# route that handles editing record data by getting the info from the edit page
@app.route('/edit_record', methods=['POST'])
def edit_record():
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

    edited_record = db.session.query(Customer).filter(Customer.id == new_e_id).first()

    if edited_record:
        if new_e_latitude != "" and new_e_longitude != "":
            edited_record.geolocation = 'POINT(' + str(new_e_latitude) + ' ' + str(new_e_longitude) + ')'
        if new_e_name != "":
            edited_record.name = new_e_name
        if new_e_address != "":
            edited_record.address = new_e_address
        if new_e_account != "":
            edited_record.account_number = int(new_e_account)
        if new_e_premise != "":
            edited_record.premise_number = int(new_e_premise)
        if new_e_comp_id != "":
            edited_record.component_id = new_e_comp_id
        if new_e_comp_type != "":
            edited_record.component_type = new_e_comp_type
        if new_e_num_acc != "":
            edited_record.number_accounted = new_e_num_acc
        if new_e_num_off != "":
            edited_record.number_off = new_e_num_off
        if new_e_area != "":
            edited_record.area = new_e_area
        if new_e_job_set != "":
            edited_record.job_set = new_e_job_set

        db.session.commit()
        data = db.session.execute(text("SELECT * FROM customers"))
        return render_template('record_page.html', data=data)

    else:
        data = db.session.execute(text("SELECT * FROM customers"))
        return render_template('record_page.html', data=data)


# route that shows the delete record page for confirming deletion of a record
@app.route('/delete_record_page', methods=['POST'])
def delete_record_page():
    d_id = request.form.get("delete_id")
    d_name = request.form.get("delete_name")
    d_address = request.form.get('delete_address')
    d_account = request.form.get('delete_account')
    d_premise = request.form.get('delete_premise')
    deleting_record = [d_id, d_name, d_address, d_account, d_premise]

    return render_template('delete_record_page.html', data=deleting_record)


# route that handles deleting record by getting id from confirmation page
@app.route('/delete_record', methods=['POST'])
def delete_record():
    delete_id = request.form.get("delete_confirm_id")

    deleting_record = db.session.query(Customer).filter(Customer.id == delete_id).first()

    if deleting_record:
        db.session.delete(deleting_record)
        db.session.commit()
        data = db.session.execute(text("SELECT * FROM customers"))
        return render_template('record_page.html', data=data)

    else:
        data = db.session.execute(text("SELECT * FROM customers"))
        return render_template('record_page.html', data=data)


# route that handles deleting record by getting id from confirmation page
@app.route('/search_record', methods=['POST'])
def search_record():
    search_this = request.form.get("search_this")

    if search_this.split(":")[0].lower().strip() == "name":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"name='{search_this.split(':')[1].strip()}'"))
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "address":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"address='{search_this.split(':')[1].strip()}'"))
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "account":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"account_number='{search_this.split(':')[1].strip()}'"))
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "premise":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"premise_number='{search_this.split(':')[1].strip()}'"))
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "component id":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"component_id='{search_this.split(':')[1].strip()}'"))
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "component type":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"component_type='{search_this.split(':')[1].strip()}'"))
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "number accounted":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"number_accounted='{search_this.split(':')[1].strip()}'"))
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "number off":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"number_off='{search_this.split(':')[1].strip()}'"))
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "area":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"area='{search_this.split(':')[1].strip()}'"))
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "job set":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"job_set='{search_this.split(':')[1].strip()}'"))
        return render_template('record_page.html', data=data)

    else:
        data = db.session.execute(text("SELECT * FROM customers"))
        return render_template('record_page.html', data=data)


'''
if __name__ == "__main__":
    app.run()
'''
