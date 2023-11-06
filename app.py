import geopandas as gpd
import folium
import os
import secrets

from flask import Flask, render_template, request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry
from sqlalchemy import text
from werkzeug.utils import secure_filename
from shapely import wkb

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
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
    number_accounted = db.Column(db.Integer)
    number_off = db.Column(db.Integer)
    area = db.Column(db.String(80))
    job_set = db.Column(db.String(120))

    def __init__(self, geolocation, name, address, account_number, premise_number, number_accounted, number_off, area,
                 job_set):
        self.geolocation = geolocation
        self.name = name
        self.address = address
        self.account_number = account_number
        self.premise_number = premise_number
        self.number_accounted = number_accounted
        self.number_off = number_off
        self.area = area
        self.job_set = job_set

    def __repr__(self):
        return f'<Customer {self.name}>'


class Light(db.Model):
    __tablename__ = 'lights'
    id = db.Column(db.Integer, primary_key=True)
    customer = db.relationship('Customer', backref=db.backref('lights'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    geolocation = db.Column(Geometry('POINT'))
    title = db.Column(db.String(120))
    address = db.Column(db.String(120))
    ptag = db.Column(db.Integer)
    lr_number = db.Column(db.String(120))
    area = db.Column(db.String(80))
    job_set = db.Column(db.String(120))
    status = db.Column(db.String(120))

    def __init__(self, geolocation, customer_id, title, address, ptag, lr_number, area, job_set, status):
        self.geolocation = geolocation
        self.customer_id = customer_id
        self.title = title
        self.address = address
        self.ptag = ptag
        self.lr_number = lr_number
        self.area = area
        self.job_set = job_set
        self.status = status

    def __repr__(self):
        return f'<Light {self.title}>'


# ----------------------------------------------------------------------------------------------------------------------
def generate_shape_map():
    # use sql and database connection to query customer data and create a geo data frame
    gdf_customers = gpd.GeoDataFrame.from_postgis("select * from customers", db.engine, geom_col='geolocation')
    gdf_customers = gdf_customers.set_crs("EPSG:4326")

    # use sql and database connection to query light data and create a geo data frame
    gdf_lights = gpd.GeoDataFrame.from_postgis("select * from lights", db.engine, geom_col='geolocation')
    gdf_lights = gdf_lights.set_crs("EPSG:4326")

    # create map
    m = folium.Map(location=[33.45, -86.75], zoom_start=10)

    # create a folium geojson objects from same dataset
    geo_customers = folium.GeoJson(data=gdf_customers,
                                   marker=folium.CircleMarker(radius=10, weight=1, color='black', fill_color='red',
                                                              fill_opacity=1),
                                   popup=folium.GeoJsonPopup(fields=['name', 'address', 'premise_number', 'link'],
                                                             aliases=['Name', 'Address', 'Premise', 'Link'],
                                                             style=("font-size: 12px; background-color: #fff; "
                                                                    "border: 2px solid black; border-radius: 3px; "
                                                                    "box-shadow: 3px")))
    geo_lights = folium.GeoJson(data=gdf_lights,
                                marker=folium.CircleMarker(radius=10, weight=1, color='black', fill_color='yellow',
                                                           fill_opacity=1),
                                popup=folium.GeoJsonPopup(fields=['title', 'address', 'status', 'link'],
                                                          aliases=['Title', 'Address', 'Status', 'Link'],
                                                          style=("font-size: 12px; background-color: #fff; "
                                                                 "border: 2px solid black; border-radius: 3px; "
                                                                 "box-shadow: 3px")))

    # loop through geojson features and add a link to update customer info
    for feature in geo_customers.data["features"]:
        # create list of customer info to pass to link
        record_list = ['customer', feature["properties"]["id"], feature["properties"]["name"],
                       feature["properties"]["address"], feature["properties"]["account_number"],
                       feature["properties"]["premise_number"]]

        # generate a reference link to customer
        link = f"<a href='{url_for('update_record_page', record=record_list)}' target='_top'>Update Record</a>"
        # add link as new field to generate in map popup
        feature["properties"]["link"] = link

    # loop through geojson features and add a link to update light info
    for feature in geo_lights.data["features"]:
        # create list of customer info to pass to link
        record_list = ['light', feature["properties"]["id"], feature["properties"]["title"],
                       feature["properties"]["address"], feature["properties"]["ptag"],
                       feature["properties"]["status"]]

        # generate a reference link to customer
        link = f"<a href='{url_for('update_record_page', record=record_list)}' target='_top'>Update Record</a>"
        # add link as new field to generate in map popup
        feature["properties"]["link"] = link

    geo_customers.add_to(m)
    geo_lights.add_to(m)

    # save map to be displayed
    m.save("templates/map.html")


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
@app.route('/')
def root():
    # for when database needs to be created from Models
    db.create_all()

    # to clear any previously uploaded files
    for remove_file in os.listdir(os.path.join(app.config["UPLOAD_FOLDER"])):
        file_path = os.path.join(os.path.join(app.config["UPLOAD_FOLDER"]), remove_file)
        if os.path.isfile(file_path):
            os.remove(file_path)

    return render_template('home_page.html')


# uploads files to server from local storage via stream form and previews content for confirmation
@app.route('/upload', methods=['POST'])
def upload():
    shapefile = ""
    files = request.files.getlist('file[]')
    file_type = request.form.get("file_type")

    if len(files) >= 7:
        for file in files:
            filename = secure_filename(file.filename)
            if ".shp" in filename and ".xml" not in filename:
                shapefile = filename
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        if shapefile != "":
            gdf = gpd.read_file("uploads/" + shapefile)
            try:
                if file_type == "Customer":
                    gdf_subset = gdf.loc[:9, ["Customer_N", "Service_Ad", "Account_Nu", "Premise_Nu"]]
                    table = gdf_subset.to_html(classes="table table-striped")
                    return render_template('upload_page.html', data=[table, "customer"])
                if file_type == "Light":
                    gdf_subset = gdf.loc[:9, ["Status", "Title", "PTAG", "LR_NUMBER"]]
                    table = gdf_subset.to_html(classes="table table-striped")
                    return render_template('upload_page.html', data=[table, "light"])
            except KeyError:
                return redirect(url_for('root'))

        # there was not a shape file in the uploaded files
        else:
            return redirect(url_for('root'))

    # files did not contain enough information for the shape file to build the data set
    else:
        return redirect(url_for('root'))


# handles confirmation on the upload page if user decides to save records to database.
# creates new records from uploaded shape file, and then removes the files from database
@app.route('/upload_page', methods=['GET', 'POST'])
def upload_page():
    # get shapefile from uploaded folder
    shapefile = ""
    for file in os.listdir(os.path.join(app.config["UPLOAD_FOLDER"])):
        filename = os.path.join(os.path.join(app.config["UPLOAD_FOLDER"]), file)
        if ".shp" in str(filename) and ".xml" not in str(filename):
            shapefile = filename

    # if there is a shapefile
    if shapefile != "":
        gdf = gpd.read_file(shapefile)
        file_type = request.form.get("file_type")

        if file_type == "customer":
            # default values
            location = 0
            name = ""
            address = ""
            account = 0
            premise = 0
            num_acc = 0
            num_ina = 0
            area = ""
            job_set = ""

            # replace default values with values from shape file if they exist
            for index, row in gdf.iterrows():
                if row["geometry"]:
                    location = row["geometry"]
                if row["Customer_N"]:
                    name = row["Customer_N"]
                if row["Service_Ad"]:
                    address = row["Service_Ad"]
                if row["Account_Nu"]:
                    account = row["Account_Nu"]
                if row["Premise_Nu"]:
                    premise = row["Premise_Nu"]
                if row["Number_Act"]:
                    num_acc = row["Number_Act"]
                if row["Number_Ina"]:
                    num_ina = row["Number_Ina"]
                if row["AREA"]:
                    area = row["AREA"]
                if row["JOBSET"]:
                    job_set = row["JOBSET"]

                new_record = Customer(geolocation='POINT(' + str(location.x) + ' ' + str(location.y) + ')', name=name,
                                      address=address, account_number=account, premise_number=premise,
                                      number_accounted=num_acc, number_off=num_ina, area=area,
                                      job_set=job_set)

                db.session.add(new_record)
                db.session.commit()

        if file_type == "light":
            # default values
            location = 0
            title = ""
            address = ""
            ptag = 0
            lr_number = 0
            area = ""
            job_set = ""
            status = ""

            # replace default values with values from shape file if they exist
            for index, row in gdf.iterrows():
                if row["geometry"]:
                    location = row["geometry"]
                if row["Customer_N"]:
                    title = row["Title"]
                if row["Service_Ad"]:
                    ptag = row["PTAG"]
                if row["Account_Nu"]:
                    lr_number = row["LR_NUMBER"]
                if row["AREA"]:
                    area = row["AREA"]
                if row["JOBSET"]:
                    job_set = row["JOBSET"]
                if row["Status"]:
                    status = row["Status"]

                new_record = Light(geolocation='POINT(' + str(location.x) + ' ' + str(location.y) + ')',
                                   customer_id=1, title=title, address=address, ptag=ptag,
                                   lr_number=lr_number, area=area, job_set=job_set, status=status, )

                db.session.add(new_record)
                db.session.commit()

        # remove files once complete
        for remove_file in os.listdir(os.path.join(app.config["UPLOAD_FOLDER"])):
            file_path = os.path.join(os.path.join(app.config["UPLOAD_FOLDER"]), remove_file)
            if os.path.isfile(file_path):
                os.remove(file_path)

        flash("Shapefile saved to database.", "success")

        return redirect(url_for('root'))


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
    if request.form.get("update_type") == 'customer':
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

    if request.form.get("update_type") == 'light':
        u_l_id = request.form.get("update_l_id")
        u_title = request.form.get("update_title")
        u_l_address = request.form.get('update_l_address')
        u_ptag = request.form.get('update_ptag')
        u_status = request.form.get('update_status')

        updated_record = db.session.query(Light).filter(Light.id == u_l_id).first()

        if updated_record:
            if u_title != "":
                updated_record.title = u_title
            if u_l_address != "":
                updated_record.address = u_l_address
            if u_ptag != "":
                updated_record.ptag = int(u_ptag)
            if u_status != "":
                updated_record.status = u_status

            db.session.commit()
            generate_shape_map()

            return render_template('map_page.html')

        else:
            return render_template('map_page.html')
    else:
        return render_template('map_page.html')


# app routes below correlate to record view
# ----------------------------------------------------------------------------------------------------------------------
# record page that shows all record information from a database query
@app.route('/record_page')
def record_page():
    data_cust = db.session.execute(text("SELECT * FROM customers ORDER BY id"))
    data_light = db.session.execute(text("SELECT * FROM lights ORDER BY id"))
    data = [data_cust, data_light]
    return render_template('record_page.html', data=data)


# add record from the records page
@app.route('/add_record_page', methods=['GET', 'POST'])
def add_record_page():
    if request.method == 'GET':
        picked = request.args.get('pick')
        return render_template('add_record_page.html', choices=["Customer", "Light"], pick=picked)

    return render_template('add_record_page.html', choices=["Customer", "Light"])


# route that handles adding the record by getting form data and inserting into database
@app.route('/add_record', methods=['GET', 'POST'])
def add_record():
    if request.method == 'POST':
        add = request.args.get('add')

        if add == "customer":
            name = request.form.get("Name")
            address = request.form.get('Address')
            account = request.form.get('Account')
            premise = request.form.get('Premise')
            number_accounted = request.form.get('Number_Accounted')
            number_off = request.form.get('Number_Off')
            area = request.form.get('Area')
            job_set = request.form.get('Job_Set')
            latitude = request.form.get('Latitude')
            longitude = request.form.get('Longitude')

            new_record = Customer(geolocation='POINT(' + str(latitude) + ' ' + str(longitude) + ')', name=name,
                                  address=address, account_number=account, premise_number=premise,
                                  number_accounted=number_accounted, number_off=number_off, area=area,
                                  job_set=job_set)
            db.session.add(new_record)
            db.session.commit()

            data_cust = db.session.execute(text("SELECT * FROM customers ORDER BY id"))
            data_light = db.session.execute(text("SELECT * FROM lights ORDER BY id"))
            data = [data_cust, data_light]
            return render_template('record_page.html', data=data)

        if add == "light":
            customer_id = request.form.get("Customer_ID")
            title = request.form.get("Title")
            address = request.form.get('L_Address')
            ptag = request.form.get('PTAG')
            status = request.form.get('Status')
            lr_number = request.form.get('LR_Number')
            area = request.form.get('L_Area')
            job_set = request.form.get('L_Job_Set')
            latitude = request.form.get('L_Latitude')
            longitude = request.form.get('L_Longitude')

            new_record = Light(geolocation='POINT(' + str(latitude) + ' ' + str(longitude) + ')',
                               customer_id=customer_id, title=title, address=address, ptag=ptag,
                               lr_number=lr_number, area=area, job_set=job_set, status=status, )
            db.session.add(new_record)
            db.session.commit()

            data_cust = db.session.execute(text("SELECT * FROM customers ORDER BY id"))
            data_light = db.session.execute(text("SELECT * FROM lights ORDER BY id"))
            data = [data_cust, data_light]
            return render_template('record_page.html', data=data)

        data_cust = db.session.execute(text("SELECT * FROM customers ORDER BY id"))
        data_light = db.session.execute(text("SELECT * FROM lights ORDER BY id"))
        data = [data_cust, data_light]
        return render_template('record_page.html', data=data)

    else:
        data_cust = db.session.execute(text("SELECT * FROM customers ORDER BY id"))
        data_light = db.session.execute(text("SELECT * FROM lights ORDER BY id"))
        data = [data_cust, data_light]
        return render_template('record_page.html', data=data)


# route that shows the edit record page from the records page
@app.route('/edit_record_page', methods=['POST'])
def edit_record_page():
    if request.form.get("editing_customer") == "yes":
        e_id = request.form.get("edit_id")
        e_location = request.form.get("edit_location")
        shapely_point = wkb.loads(e_location)
        e_lat = shapely_point.x
        e_lon = shapely_point.y
        e_name = request.form.get("edit_name")
        e_address = request.form.get('edit_address')
        e_account = request.form.get('edit_account')
        e_premise = request.form.get('edit_premise')
        e_num_acc = request.form.get('edit_num_acc')
        e_num_off = request.form.get('edit_num_off')
        e_area = request.form.get('edit_area')
        e_job_set = request.form.get('edit_job_set')
        editing_record = ["customer", e_id, e_lat, e_lon, e_name, e_address, e_account, e_premise, e_num_acc,
                          e_num_off, e_area, e_job_set]

        return render_template('edit_record_page.html', data=editing_record)

    if request.form.get("editing_light") == "yes":
        e_l_id = request.form.get("edit_l_id")
        e_c_id = request.form.get("edit_customer_id")
        e_l_location = request.form.get("edit_l_location")
        shapely_point = wkb.loads(e_l_location)
        e_l_lat = shapely_point.x
        e_l_lon = shapely_point.y
        e_title = request.form.get("edit_title")
        e_l_address = request.form.get('edit_l_address')
        e_ptag = request.form.get('edit_ptag')
        e_lr_number = request.form.get('edit_lr_number')
        e_l_area = request.form.get('edit_l_area')
        e_l_job_set = request.form.get('edit_l_job_set')
        e_status = request.form.get('edit_status')
        editing_record = ["light", e_l_id, e_c_id, e_l_lat, e_l_lon, e_title, e_l_address, e_ptag, e_lr_number,
                          e_l_area, e_l_job_set, e_status]

        return render_template('edit_record_page.html', data=editing_record)


# route that handles editing record data by getting the info from the edit page
@app.route('/edit_record', methods=['POST'])
def edit_record():
    if request.form.get("new_edit_type") == "customer":
        new_e_id = request.form.get("new_edit_id")
        new_e_latitude = request.form.get("new_edit_latitude")
        new_e_longitude = request.form.get("new_edit_longitude")
        new_e_name = request.form.get("new_edit_name")
        new_e_address = request.form.get('new_edit_address')
        new_e_account = request.form.get('new_edit_account')
        new_e_premise = request.form.get('new_edit_premise')
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
            if new_e_num_acc != "":
                edited_record.number_accounted = new_e_num_acc
            if new_e_num_off != "":
                edited_record.number_off = new_e_num_off
            if new_e_area != "":
                edited_record.area = new_e_area
            if new_e_job_set != "":
                edited_record.job_set = new_e_job_set

            db.session.commit()

            data_cust = db.session.execute(text("SELECT * FROM customers ORDER BY id"))
            data_light = db.session.execute(text("SELECT * FROM lights ORDER BY id"))
            data = [data_cust, data_light]
            return render_template('record_page.html', data=data)

    if request.form.get("new_edit_type") == "light":
        new_e_l_id = request.form.get("new_edit_l_id")
        new_e_l_latitude = request.form.get("new_edit_l_latitude")
        new_e_l_longitude = request.form.get("new_edit_l_longitude")
        new_e_title = request.form.get("new_edit_title")
        new_e_l_address = request.form.get('new_edit_l_address')
        new_e_ptag = request.form.get('new_edit_ptag')
        new_e_lr_number = request.form.get('new_edit_lr_number')
        new_e_l_area = request.form.get('new_edit_l_area')
        new_e_l_job_set = request.form.get('new_edit_l_job_set')
        new_e_status = request.form.get('new_edit_status')

        edited_record = db.session.query(Light).filter(Light.id == new_e_l_id).first()

        if edited_record:
            if new_e_l_latitude != "" and new_e_l_longitude != "":
                edited_record.geolocation = 'POINT(' + str(new_e_l_latitude) + ' ' + str(new_e_l_longitude) + ')'
            if new_e_title != "":
                edited_record.title = new_e_title
            if new_e_l_address != "":
                edited_record.address = new_e_l_address
            if new_e_ptag != "":
                edited_record.ptag = int(new_e_ptag)
            if new_e_lr_number != "":
                edited_record.lr_number = new_e_lr_number
            if new_e_l_area != "":
                edited_record.area = new_e_l_area
            if new_e_l_job_set != "":
                edited_record.job_set = new_e_l_job_set
            if new_e_status != "":
                edited_record.status = new_e_status

            db.session.commit()

            data_cust = db.session.execute(text("SELECT * FROM customers ORDER BY id"))
            data_light = db.session.execute(text("SELECT * FROM lights ORDER BY id"))
            data = [data_cust, data_light]
            return render_template('record_page.html', data=data)


# route that shows the delete record page for confirming deletion of a record
@app.route('/delete_record_page', methods=['POST'])
def delete_record_page():
    if request.form.get("deleting_customer") == "yes":
        d_id = request.form.get("delete_id")
        d_name = request.form.get("delete_name")
        d_address = request.form.get('delete_address')
        d_account = request.form.get('delete_account')
        d_premise = request.form.get('delete_premise')
        deleting_record = ["customer", d_id, d_name, d_address, d_account, d_premise]

        return render_template('delete_record_page.html', data=deleting_record)

    if request.form.get("deleting_light") == "yes":
        d_l_id = request.form.get("delete_l_id")
        d_title = request.form.get("delete_title")
        d_l_address = request.form.get('delete_l_address')
        d_ptag = request.form.get('delete_ptag')
        d_lr_number = request.form.get('delete_lr_number')
        deleting_record = ["light", d_l_id, d_title, d_l_address, d_ptag, d_lr_number]

        return render_template('delete_record_page.html', data=deleting_record)


# route that handles deleting record by getting id from confirmation page
@app.route('/delete_record', methods=['POST'])
def delete_record():
    if request.form.get("delete_type") == "customer":
        delete_id = request.form.get("delete_confirm_id")
        deleting_record = db.session.query(Customer).filter(Customer.id == delete_id).first()

        if deleting_record:
            db.session.delete(deleting_record)
            db.session.commit()
            data_cust = db.session.execute(text("SELECT * FROM customers ORDER BY id"))
            data_light = db.session.execute(text("SELECT * FROM lights ORDER BY id"))
            data = [data_cust, data_light]
            return render_template('record_page.html', data=data)

    if request.form.get("delete_type") == "light":
        delete_id = request.form.get("delete_confirm_id")
        deleting_record = db.session.query(Light).filter(Light.id == delete_id).first()

        if deleting_record:
            db.session.delete(deleting_record)
            db.session.commit()
            data_cust = db.session.execute(text("SELECT * FROM customers ORDER BY id"))
            data_light = db.session.execute(text("SELECT * FROM lights ORDER BY id"))
            data = [data_cust, data_light]
            return render_template('record_page.html', data=data)


# route that handles deleting record by getting id from confirmation page
@app.route('/search_record', methods=['POST'])
def search_record():
    search_this = request.form.get("search_this")

    if search_this.split(":")[0].lower().strip() == "c id":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"id='{search_this.split(':')[1].strip()}' ORDER BY id"))
        data = [data, None]
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "name":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"name='{search_this.split(':')[1].strip()}' ORDER BY id"))
        data = [data, None]
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "c address":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"address='{search_this.split(':')[1].strip()}' ORDER BY id"))
        data = [data, None]
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "account":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"account_number='{search_this.split(':')[1].strip()}' ORDER BY id"))
        data = [data, None]
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "premise":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"premise_number='{search_this.split(':')[1].strip()}' ORDER BY id"))
        data = [data, None]
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "number accounted":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"number_accounted='{search_this.split(':')[1].strip()}' ORDER BY id"))
        data = [data, None]
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "number off":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"number_off='{search_this.split(':')[1].strip()}' ORDER BY id"))
        data = [data, None]
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "c area":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"area='{search_this.split(':')[1].strip()}' ORDER BY id"))
        data = [data, None]
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "c job set":
        data = db.session.execute(text(f"SELECT * FROM customers WHERE "
                                       f"job_set='{search_this.split(':')[1].strip()}' ORDER BY id"))
        data = [data, None]
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "l id":
        data = db.session.execute(text(f"SELECT * FROM lights WHERE "
                                       f"id='{search_this.split(':')[1].strip()}' ORDER BY id"))
        data = [None, data]
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "title":
        data = db.session.execute(text(f"SELECT * FROM lights WHERE "
                                       f"title='{search_this.split(':')[1].strip()}' ORDER BY id"))
        data = [None, data]
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "l address":
        data = db.session.execute(text(f"SELECT * FROM lights WHERE "
                                       f"address='{search_this.split(':')[1].strip()}' ORDER BY id"))
        data = [None, data]
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "ptag":
        data = db.session.execute(text(f"SELECT * FROM lights WHERE "
                                       f"ptag='{search_this.split(':')[1].strip()}' ORDER BY id"))
        data = [None, data]
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "lr number":
        data = db.session.execute(text(f"SELECT * FROM lights WHERE "
                                       f"lr_number='{search_this.split(':')[1].strip()}' ORDER BY id"))
        data = [None, data]
        return render_template('record_page.html', data=data)

    elif search_this.split(":")[0].lower().strip() == "status":
        data = db.session.execute(text(f"SELECT * FROM lights WHERE "
                                       f"status='{search_this.split(':')[1].strip()}' ORDER BY id"))
        data = [None, data]
        return render_template('record_page.html', data=data)

    else:
        data_cust = db.session.execute(text("SELECT * FROM customers ORDER BY id"))
        data_light = db.session.execute(text("SELECT * FROM lights ORDER BY id"))
        data = [data_cust, data_light]
        return render_template('record_page.html', data=data)


# route that handles deleting record by getting id from confirmation page
@app.route('/show_customer', methods=['POST'])
def show_customer():
    show_customer_id = request.form.get("show_customer_id")
    showing_record = db.session.query(Customer).filter(Customer.id == show_customer_id).first()

    if showing_record:
        s_id = show_customer_id
        s_name = showing_record.name
        s_address = showing_record.address
        s_account = showing_record.account_number
        s_premise = showing_record.premise_number
        s_lights = showing_record.lights
        show_record = [s_id, s_name, s_address, s_account, s_premise, s_lights]

        return render_template('show_customer_page.html', data=show_record)

    else:
        data_cust = db.session.execute(text("SELECT * FROM customers ORDER BY id"))
        data_light = db.session.execute(text("SELECT * FROM lights ORDER BY id"))
        data = [data_cust, data_light]
        return render_template('record_page.html', data=data)


if __name__ == "__main__":
    app.run()

