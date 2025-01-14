from flask import Flask, request, make_response,session,abort,redirect,render_template, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.form.upload import FileUploadField
from wtforms.validators import ValidationError
import imghdr
from flask_login import login_user, current_user, logout_user, login_required  
from flask_login import UserMixin, LoginManager
from flask_bcrypt import Bcrypt 
from datetime import datetime 
from flask_mail import Mail,Message
from flask_admin import BaseView, expose
from flask_admin.menu import MenuLink

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db' 
app.config['SECRET_KEY'] = 'abababab'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)  
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

@login_manager.user_loader 
def load_user(user_id):
    return Manager.query.get(int(user_id))

### Database

class Manager(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(20), nullable=False)
    manager_name = db.Column(db.String(25))

class Venue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    venue_name = db.Column(db.String(50))
    capacity = db.Column(db.Integer) 
    From = db.Column(db.DateTime) 
    to = db.Column(db.DateTime)   
    url_pic = db.Column(db.String(20)) 
    cost = db.Column(db.Integer)

class Food(db.Model): 
    id = db.Column(db.Integer, primary_key=True)
    cuisine = db.Column(db.String(20))
    food_items = db.Column(db.String(50))
    beverages = db.Column(db.String(50))
    cost_per_head = db.Column(db.Integer) 

class Decoration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    theme_name = db.Column(db.String(50)) 
    url_pic = db.Column(db.String(50))
    cost = db.Column(db.Integer)

class Band(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    band_name = db.Column(db.String(25))
    genre = db.Column(db.String(20))
    cost = db.Column(db.Integer)

class Bookings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(25))
    venue_name = db.Column(db.String(50))
    attendees = db.Column(db.Integer)
    date = db.Column(db.Date)
    _from = db.Column(db.DateTime) 
    _to = db.Column(db.DateTime)   
    theme = db.Column(db.String(50))
    cuisine = db.Column(db.String(20))
    food_items = db.Column(db.String(50))
    food_type = db.Column(db.String(10))
    band_name = db.Column(db.String(25))
    status = db.Column(db.String(20), default='Pending')
    manager_id = db.Column(db.Integer, db.ForeignKey('manager.id'))
    cost = db.Column(db.Integer)

from forms import RegistrationForm, LoginForm 

### Admin Permissions

admin = Admin(app, template_mode='bootstrap4') 
class SecureModelView(ModelView):
    def is_accessible(self):
        if "logged_in" in session:
            return True
        else:
            abort(403)

admin.add_view(SecureModelView(Venue, db.session))
admin.add_view(SecureModelView(Food, db.session))
admin.add_view(SecureModelView(Band, db.session))
admin.add_view(SecureModelView(Bookings, db.session))
admin.add_view(SecureModelView(Manager, db.session))  
admin.add_view(SecureModelView(Decoration, db.session))

flag=0
@app.route("/alogin",methods=['GET','POST'])
def alogin():
    if request.method=='POST':
        if request.form.get('Username')== "Admin" and request.form.get('Password')=='Admin':
            session['logged_in']=True
            global flag
            if flag==0:
                admin.add_link(MenuLink(name='Logout', url=url_for('alogout')))
                flag=1
            return redirect("/admin")
        else:
            return render_template("/admin/alogin.html",failed=True)
    return render_template("/admin/alogin.html")

@app.route("/alogout")
def alogout():
    session.clear()
    return redirect("/alogin")


@app.route("/register", methods=['GET', 'POST'])  
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        manager = Manager(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(manager)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form) 


@app.route("/login", methods=['GET', 'POST']) 
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        manager = Manager.query.filter_by(email=form.email.data).first()
        if manager and bcrypt.check_password_hash(manager.password, form.password.data):
            login_user(manager, remember=form.remember.data)
            next_page = request.args.get('next')
            session['manager'] = current_user.get_id()
            print(session['manager'], '****')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout") 
def logout():
    logout_user()
    flash('You have been logged out!', 'success')
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def home():
     if 'manager' in session:
        venue=Venue.query.all()
        food=Food.query.all()
        band=Band.query.all()
        return render_template('home.html',venue=venue,food=food,band=band)

mail=Mail(app)

@app.route('/bookings')
@app.route('/theme')
def theme():
    dec = Decoration.query.all()
    return render_template('theme.html',dec=dec)

@app.route('/bookings/<name>',methods=['GET','POST'])
def bookings(name):
    
    if request.method == 'POST':
        event = request.form['event']
        venue = request.form['_venue_']
        attendees = request.form['attendees']
        date = request.form['date']
        time = request.form['time']
        totime = request.form['totime']
        cuisine = request.form['_cuisine_']
        fitems = request.form['fitems']
        ftype = request.form['ftype']
        band = request.form['_band_']
        db_date = datetime.strptime(date,'%Y-%m-%d')
        time = datetime.strptime(time,'%H:%M')
        totime = datetime.strptime(totime,'%H:%M')
        total_cost= request.form['total_cost_'] 
        print(total_cost)
        manager_id=current_user.get_id()
        print(cuisine, venue, band)
        theme_obj = Bookings(event_name=event,venue_name=venue,attendees=attendees, \
                                date=db_date,_from=time,_to=totime,theme=name,cuisine=cuisine,\
                                food_items=fitems,food_type=ftype,band_name=band,manager_id=manager_id, \
                                cost=total_cost, status="Confirmed")
        db.session.add(theme_obj)
        db.session.commit()
        return redirect('/home')
        print(manager_id)
        email=Manager.query.get(manager_id).email
        print(email)
        booking=Bookings.query.filter_by(id=manager_id).all()
        for booking in booking:
            msg="Booking successful!!\n\n\nBooking Details:\n"+ "Event: " + booking.event_name + "\nVenue: "+booking.venue_name + "\nDate: " + booking.date.strftime("%d/%m/%Y") \
            + "\nTime: " + booking._from.strftime("%H:%M") + "-" + booking._to.strftime("%H:%M") + "\nTheme: " + booking.theme + "\nCuisine: " + booking.cuisine \
            + "\nBand: " + booking.band_name + "\n\n\nThank You for using our service!"
        subject="Booking Info"
        message=Message(subject=subject,sender="event2381@gmail.com",recipients=[email])
        message.body=msg
        mail.send(message)
    venue_obj = Venue.query.with_entities(Venue.id, Venue.venue_name, Venue.cost).all()
    food_obj= Food.query.with_entities(Food.id, Food.cuisine, Food.cost_per_head, Food.food_items).all()
    band_obj = Band.query.with_entities(Band.id, Band.band_name, Band.cost).all()
    
    l=[]
    for x in food_obj:
        l.append(x.food_items)
    print(l)
    decoration_cost = Decoration.query.filter_by(theme_name=name).first().cost
    return render_template('bookings.html',venue=venue_obj,food=food_obj,band=band_obj,l=l, decoration=name, decoration_cost=decoration_cost)
    
@app.route('/viewbookings') 
def viewbookings():
    id = session['manager']
    bookings = Bookings.query.filter_by(manager_id=id).all()
    return render_template('viewbookings.html', bookings=bookings)

@app.route('/')
def default():
    return render_template('index.html')

if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)
    
