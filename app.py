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
    lights = db.relationship('Light', backref='customer', lazy='dynamic')
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
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    geolocation = db.Column(Geometry('POINT'))
    ptag = db.Column(db.Integer)
    status = db.Column(db.String(120))
    title = db.Column(db.String(120))
    lr_number = db.Column(db.String(120))
    address = db.Column(db.String(120))
    area = db.Column(db.String(80))
    job_set = db.Column(db.String(120))

    def __init__(self, geolocation, ptag, status, title, lr_number, address, area, job_set):
        self.geolocation = geolocation
        self.ptag = ptag
        self.status = status
        self.title = title
        self.lr_number = lr_number
        self.address = address
        self.area = area
        self.job_set = job_set

    def __repr__(self):
        return f'<Light {self.title}>'


# ----------------------------------------------------------------------------------------------------------------------
def generate_shape_map():
    # use sql and database connection to query customer data and create a geo data frame
    gdf_customers = gpd.GeoDataFrame.from_postgis("select * from customers", db.engine, geom_col='geolocation')
    # set location and convert to geojson for choropleth layer
    gdf_customers = gdf_customers.set_crs("EPSG:4326")
    geojson = gdf_customers.to_crs(epsg='4326').to_json()

    m = folium.Map(location=[33.45, -86.75], zoom_start=10)

    # create a folium choropleth object that shows markers for each billing customer
    folium.Choropleth(geo_data=geojson, name='choropleth', data=gdf_customers, columns=['name', 'address'],
                      fill_color='YlGn', fill_opacity=0.7, line_opacity=0.2, legend_name='Customers').add_to(m)

    # create a folium geojson object from same dataset
    geo = folium.GeoJson(data=gdf_customers, popup=folium.GeoJsonPopup(fields=['name', 'address', "link"], labels=True))

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

    if len(files) >= 7:
        for file in files:
            filename = secure_filename(file.filename)
            if ".shp" in filename and ".xml" not in filename:
                shapefile = filename
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        if shapefile != "":
            gdf = gpd.read_file("uploads/" + shapefile)
            gdf_subset = gdf.loc[:9, ["Customer_N", "Service_Ad", "Account_Nu", "Premise_Nu"]]
            table = gdf_subset.to_html(classes="table table-striped")
            return render_template('upload_page.html', data=table)

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

            # create the new record entry and save it to database
            new_record = Customer(geolocation='POINT(' + str(location.x) + ' ' + str(location.y) + ')', name=name,
                                  address=address, account_number=account, premise_number=premise,
                                  number_accounted=num_acc, number_off=num_ina, area=area, job_set=job_set)

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
        print(request.args.get('add'))

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
                                  number_accounted=number_accounted, number_off=number_off, area=area, job_set=job_set)
            db.session.add(new_record)
            db.session.commit()

            data = db.session.execute(text("SELECT * FROM customers"))
            return render_template('record_page.html', data=data)

        data = db.session.execute(text("SELECT * FROM customers"))
        return render_template('record_page.html', data=data)


# route that shows the edit record page from the records page
@app.route('/edit_record_page', methods=['POST'])
def edit_record_page():
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
    editing_record = [e_id, e_lat, e_lon, e_name, e_address, e_account, e_premise, e_num_acc, e_num_off, e_area,
                      e_job_set]

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


if __name__ == "__main__":
    app.run()
