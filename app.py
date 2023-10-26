import geopandas as gpd
import folium
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, jsonify
from geoalchemy2 import Geometry

app = Flask(__name__)
con = psycopg2.connect(database="pycrum", user="pycrum_user", password="pOCwAVVMw3YDbjPfMKkHSyZpK9JGicR3", host="dpg-ckrvo87d47qs73f05310-a.ohio-postgres.render.com")


# ----------------------------------------------------------------------------------------------------------------------
def generate_shape_map(edit_name, edit_address):
    gdf = gpd.GeoDataFrame.from_postgis("select * from customers", con, geom_col='geolocation' )

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
    generate_shape_map(None, None)
    return render_template('map_page.html', data='map.html')


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
    
