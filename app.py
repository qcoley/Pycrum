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
    gdf = gpd.GeoDataFrame.from_postgis("select * from customers", db.engine, geom_col='geolocation')
    gdf = gdf.set_crs("EPSG:4326")
    geojson = gdf.to_crs(epsg='4326').to_json()

    m = folium.Map(location=[gdf.iloc[0].geolocation.centroid.y, gdf.iloc[0].geolocation.centroid.x], zoom_start=8)

    # Create a folium choropleth object and specify the geo_data, data, columns, key_on, and other arguments
    folium.Choropleth(geo_data=geojson, name='choropleth', data=gdf, columns=['name', 'address'],
                      fill_color='YlGn', fill_opacity=0.7, line_opacity=0.2, legend_name='Customers').add_to(m)

    # Create a folium geojson object from the same geo_data as the choropleth object
    geo = folium.GeoJson(data=gdf, popup=folium.GeoJsonPopup(fields=['name', 'address', "link"], labels=True))

    # Add the geojson object to the map using the add_to method
    geo.add_to(m)

    # Loop through the geojson features and add a reference link to each country
    index = 0
    for feature in geo.data["features"]:
        customer_list = [index,
                         feature["properties"]["name"],
                         feature["properties"]["address"],
                         feature["properties"]["account_number"],
                         feature["properties"]["premise_number"]]
        # Get the country name
        # Generate a reference link using Wikipedia
        link = f"<a href='{url_for('info_page', customer=customer_list)}'>Update Record</a>"
        # Add the link as a new property
        feature["properties"]["link"] = link
        index += 1

    # Save or display the map
    m.save("templates/map.html")


# ----------------------------------------------------------------------------------------------------------------------
@app.route('/')
def root():
    return render_template('home_page.html')


@app.route('/map_page')
def map_page():
    return render_template('map_page.html')


# creates the map to be rendered into an iFrame on the map page
@app.route('/map_view')
def map_view():
    generate_shape_map()
    return render_template('map.html')


@app.route('/record_page')
def record_page():
    data = db.session.execute(text("SELECT * FROM customers"))
    return render_template('record_page.html', data=data)


@app.route('/upload_page', methods=['POST'])
def upload_page():
    # file = request.files.get('file')
    generate_shape_map()
    # generate_records()

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


@app.route('/add_record', methods=['POST'])
def add_record():
    return render_template('add_record.html')


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

    return render_template('add_record.html')


if __name__ == "__main__":
    app.run()
