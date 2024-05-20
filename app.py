from flask import Flask, jsonify, request
#Flask - gives us all the tools we need to run a flask app by creating an instance of this class
from flask_sqlalchemy import SQLAlchemy
#SQLAlchemy = ORM to connect and relate python classes to SQL tables
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
#DeclarativeBase - gives us the base model functionality to create the Classes as Model Classes for our DB Tables
#Mapped- Maps a Class attribute to a table column or relationship
#mapped_column - sets out Column and allows us to add any constraints we need (unique, nullable, primary_key)
from flask_marshmallow import Marshmallow
#Marshmallow allows us to create a schema to validate, serialize and de-serialize JSON data
from datetime import date, timedelta
#date - use to create date type objects
from typing import List
#List - is used to create a relationship that will return a list of objects
from marshmallow import fields, ValidationError
#Fields - lets us set a schema field which includes and constraints
from sqlalchemy import select, delete, func
#selects - acts as our SELECT FROM query
#delete - acts as our DELETE query


app = Flask(__name__) #creating an instance of our flask app
app.config['SQLALCHEMY_DATABASE_URI'] =  'mysql+mysqlconnector://root:sqlpassword@localhost/ecomm_db'

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(app,model_class=Base)
ma = Marshmallow(app)

class Customer(Base):
    __tablename__ = "Customer" #MAke your class name the same as your table name

    #mapping class attributes to database table columns
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(db.String(75), nullable = False)
    email: Mapped[str] = mapped_column(db.String(300))
    phone: Mapped[str] = mapped_column(db.String(16))

    #Creating one to many relationship to Orders table
    orders: Mapped[List["Orders"]] = db.relationship(back_populates = 'customer') #back_populates insures that both ends of the relationship have access to the other


order_products = db.Table(
    "Order_Products",
    Base.metadata, #Allows this table to locate the foreign keys from other base classes
    db.Column("order_id", db.ForeignKey("Orders.id"), primary_key = True),
    db.Column("product_id", db.ForeignKey("Products.id"), primary_key = True)
)


class Orders(Base):
    __tablename__ = "Orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_date: Mapped[date] = mapped_column(db.Date, nullable=False)
    customer_id: Mapped[int] = mapped_column(db.ForeignKey("Customer.id")) #This is Foreign Key which is referencing customer table
    expected_delivery_date: Mapped[date] = mapped_column(db.Date, nullable=True)

    #creating a many to one relationship to Customer table
    customer: Mapped["Customer"] = db.relationship(back_populates = "orders")

    #creating a many to many relationship to Products through our association table order_products
    products: Mapped[List["Products"]] = db.relationship(secondary=order_products)


class Products(Base):
    __tablename__ = "Products"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(db.String(255), nullable = False)
    price: Mapped[float] = mapped_column(db.Float, nullable=False)






#Initialize the database and create tables

with app.app_context():
    # db.drop_all() #IT will drop all the database stuff
    db.create_all() #First check which tables already exists and then create any tables it couldnt find
                    #However if it finds a table with the same name, it doesnt contruct or modify



#========================== CRUD OPERATIONS=====================================

#Define Customer Schema
class CustomerSchema(ma.Schema):
    id = fields.Integer(required = False)
    customer_name = fields.String(required = True)
    email = fields.String(required = True)
    phone = fields.String(required = True)

    class Meta:
        fields = ('id', "customer_name", "email", "phone")

class ProductSchema(ma.Schema):
    id = fields.Integer(required = False)
    product_name = fields.String(required = True)
    price = fields.Float(required = True)

    class Meta:
        fields = ("id", "product_name", "price")

class ProductSchema1(ma.Schema):
    id = fields.Integer(required = False)
    product_name = fields.String(required = True)
    price = fields.Float(required = True)
    order_date = fields.Date(required = True)

    class Meta:
        fields = ("id", "product_name", "price", "order_date")

class ProductTrackSchema(ma.Schema):
    id = fields.Integer(required = False)
    product_name = fields.String(required = True)
    price = fields.Float(required = True)
    expected_delivery_date = fields.Date(required = True)

    class Meta:
        fields = ("id", "product_name", "price", "expected_delivery_date")

customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many = True)

product_schema = ProductSchema()
products_schema = ProductSchema(many = True)

products_schema2 = ProductSchema1(many = True)

track_schema = ProductTrackSchema()

@app.route('/')
def home():
    return "Welcome to Ecomm"

#==================Customer Interactions========================

#Get all customers using a GET mathod
@app.route("/customers", methods=["GET"])
def get_customers():
    query = select(Customer)
    result = db.session.execute(query).scalars() #Execute query and convert row objects into scaler objects (python usable)
    customerz = result.all()
    return customers_schema.jsonify(customerz)


#Get Specific Customer using GET method and dynamic route
@app.route("/customers/<int:id>", methods = ['GET'])
def get_customer(id):

    query = select(Customer).filter(Customer.id == id)
    result = db.session.execute(query).scalars().first()

    if result is None:
        return jsonify({"Error":"Customer not found"}), 404

    return customer_schema.jsonify(result)


#Creating customers with POST request
@app.route("/customers", methods = ["POST"])
def add_customer():

    try:
        customer_data = customer_schema.load(request.json)
        print(customer_data)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    new_customer = Customer(customer_name = customer_data["customer_name"], email = customer_data["email"], phone = customer_data["phone"])
    print(new_customer)
    db.session.add(new_customer)
    db.session.commit()

    return jsonify({"Message":"New Customer Added Successfully"}), 201


#Update a user with PUT request
@app.route("/customers/<int:id>", methods = ["PUT"])
def update_customer(id):

    query = select(Customer).where(Customer.id == id)
    result = db.session.execute(query).scalars().first()
    # print(result)
    if result is None:
        return jsonify({"Error":"Customer not Found"}), 404
    
    customer = result
    
    try:
        customer_data = customer_schema.load(request.json)
        print(customer_data)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    for field, value in customer_data.items():
        setattr(customer, field, value)

    db.session.commit()
    return jsonify({"MEssage" : "Customer details have been updated"})


#Delete a user with Delete request
@app.route("/customers/<int:id>", methods = ["DELETE"])
def delete_customer(id):
    query = delete(Customer).filter(Customer.id == id)

    result = db.session.execute(query)

    if result.rowcount == 0:
        return jsonify({"Error":"Customer not found"}), 404
    
    db.session.commit()
    return jsonify({"Message":"Successfully removed Customer!!!"})


#=====================Products Interactions===================


#Create Product


@app.route("/products", methods=["POST"])
def add_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as E:
        return jsonify(e.messages), 400
    
    new_product = Products(product_name = product_data["product_name"], price=product_data["price"])
    db.session.add(new_product)
    db.session.commit()
    return jsonify({"Message":"Product Successfully Added!!!"})


#Read Products
#Get all products using a GET mathod
@app.route("/products", methods=["GET"])
def get_products():
    query = select(Products)
    result = db.session.execute(query).scalars() #Execute query and convert row objects into scaler objects (python usable)
    productz = result.all()
    return products_schema.jsonify(productz)


#Read 1 Product
@app.route("/products/<int:id>", methods = ['GET'])
def get_product(id):

    query = select(Products).filter(Products.id == id)
    result = db.session.execute(query).scalars().first()

    if result is None:
        return jsonify({"Error":"Product not found"}), 404

    return product_schema.jsonify(result)

#Update a Product with PUT request


@app.route("/products/<int:id>", methods = ["PUT"])
def update_product(id):

    query = select(Products).where(Products.id == id)
    result = db.session.execute(query).scalars().first()
    # print(result)
    if result is None:
        return jsonify({"Error":"Product not Found"}), 404
    
    product = result
    
    try:
        product_data = product_schema.load(request.json)
        print(product_data)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    for field, value in product_data.items():
        setattr(product, field, value)

    db.session.commit()
    return jsonify({"MEssage" : "Product details have been updated"})


#Delete a Product with Delete request
@app.route("/products/<int:id>", methods = ["DELETE"])
def delete_product(id):
    query = delete(Products).filter(Products.id == id)

    result = db.session.execute(query)

    if result.rowcount == 0:
        return jsonify({"Error":"Customer not found"}), 404
    
    db.session.commit()
    return jsonify({"Message":"Successfully removed Product!!!"})

#==============================Order Operations==========================

class OrderSchema(ma.Schema):
    id = fields.Integer(required=False)
    order_date = fields.Date(required=False)
    customer_id = fields.Integer(required=True)
    expected_delivery_date = fields.Date(required=False)

    class Meta:
        fields = ("id", "order_Date", "customer_id", "expected_delivery_date", "items") #Items will be a list of product_ids

order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)

#Add New Order

@app.route("/order", methods=["POST"])
def add_order():
    try:
        order_data = order_schema.load(request.json)

    except ValidationError as e:
        return jsonify(e.messages), 400
    
    
    future_date = date.today() + timedelta(days = 3)
    
    new_order = Orders(order_date = date.today(), customer_id = order_data["customer_id"], expected_delivery_date = future_date)

    for item_id in order_data['items']:
        query = select(Products).filter(Products.id == item_id)
        item = db.session.execute(query).scalar()
        # print(items)
        new_order.products.append(item)

    db.session.add(new_order)
    db.session.commit()
    new_order_id = new_order.id
    # print ("ORder ID is ", new_order.id)
    return jsonify({f"Message":"New Order Placed", "Order ID":new_order_id}),201

#Display all items for a particular Order ID #Retreive Order

@app.route("/orderdetails/<int:id>", methods=["GET"])
def order_items(id):
    query = select(Orders).filter(Orders.id == id)

    order = db.session.execute(query).scalar()
    try:
        return products_schema.jsonify(order.products)
    except AttributeError as e:
        return jsonify({"Error":"Order Doesnot Exist"}), 400

#Tracking a Order

@app.route("/ordertracking/<int:id>", methods=["GET"])
def order_tracking(id):
    query = select(Orders).filter(Orders.id == id)
    order = db.session.execute(query).scalar()
    try:
        # print ("Order Details" , order.id, order.order_date, order.expected_delivery_date)
        # # return order_schema.jsonify(order)
        return jsonify({"Order ID":order.id,"Customer ID":order.customer_id ,"Order Date":order.order_date, "Expected Delivery Date":order.expected_delivery_date})
    except AttributeError as e:
        return jsonify({"Error":"Order Doesnot Exist"}), 400






if __name__ == "__main__":
    app.run(debug = True)