import geopandas as gpd
import folium
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://pycrum_user:pOCwAVVMw3YDbjPfMKkHSyZpK9JGicR3@dpg-ckrvo87d47qs73f05310-a.ohio-postgres.render.com/pycrum'
db = SQLAlchemy(app)


# ----------------------------------------------------------------------------------------------------------------------
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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

    def __init__(self, name, address, account_number, premise_number, component_id, component_type, number_accounted,
                 number_off, area, job_set):
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
        return '<User %r>' % self.name


# ----------------------------------------------------------------------------------------------------------------------
def get_pos(lat, lng):
    return lat, lng


def generate_shape_map(shape_file, edit_name, edit_address):
    gdf = gpd.read_file("shapefiles/" + shape_file)

    if edit_name is not None:
        print(edit_name)

    if edit_address is not None:
        print(edit_address)

    geojson = gdf.to_crs(epsg='4326').to_json()

    m = folium.Map(location=[gdf.iloc[0].geometry.centroid.y, gdf.iloc[0].geometry.centroid.x], zoom_start=10)

    # Create a folium choropleth object and specify the geo_data, data, columns, key_on, and other arguments
    folium.Choropleth(geo_data=geojson, name='choropleth', data=gdf, columns=['Customer_N', 'Service_Ad'],
                      fill_color='YlGn', fill_opacity=0.7, line_opacity=0.2, legend_name='Customers').add_to(m)

    # Create a folium geojson object from the same geo_data as the choropleth object
    geo = folium.GeoJson(data=gdf, popup=folium.GeoJsonPopup(fields=['Customer_N', 'Service_Ad', "Link"], labels=True))

    # Add the geojson object to the map using the add_to method
    geo.add_to(m)

    # Loop through the geojson features and add a reference link to each country
    index = 0
    for feature in geo.data["features"]:
        customer_list = [index,
                         feature["properties"]["Customer_N"],
                         feature["properties"]["Service_Ad"],
                         feature["properties"]["Account_Nu"],
                         feature["properties"]["Premise_Nu"]]
        # Get the country name
        # Generate a reference link using Wikipedia
        link = f"<a href='{url_for('info', customer=customer_list)}'>Update Record</a>"
        # Add the link as a new property
        feature["properties"]["Link"] = link
        index += 1

    # Save or display the map
    m.save("templates/map.html")


def generate_records(shape_file):
    gdf = gpd.read_file("shapefiles/" + shape_file)
    gdf.to_html("templates/record.html")


# ----------------------------------------------------------------------------------------------------------------------
@app.route('/')
def root():
    # create the table
    db.create_all()


    return render_template('index_page.html')


@app.route('/map_page')
def map_view():
    return render_template('map_page.html', data='map.html')


@app.route('/record_page')
def record_view():
    return render_template('record_page.html', data='record.html')


@app.route('/upload', methods=['POST'])
def upload_files():
    file = request.files.get('file')
    generate_shape_map(file.filename, None, None)
    generate_records(file.filename)

    return redirect('/')


@app.route('/info_page')
def info():
    customer = request.args.getlist('customer')
    return render_template('info_page.html', data=customer)


@app.route('/edit_page', methods=['POST'])
def edit():
    new_name = request.form.get('name')
    new_address = request.form.get('address')

    # generate_shape_map('billing.shp', new_name, new_address)

    return render_template('mapped.html', data='map.html')
