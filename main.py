from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from functools import wraps
from http import HTTPStatus

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
bootstrap = Bootstrap5(app)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static/product_img')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


login_manager = LoginManager()
login_manager.init_app(app)



#Upload file checker
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy()
db.init_app(app)




# CONFIGURE TABLES
class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    role = db.Column(db.String(100),nullable=True)


# CONFIGURE TABLE FOR PRODUCTS
class Product(db.Model, UserMixin):
    __tablename__ = "product"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100),unique=True)
    img = db.Column(db.String(300))
    desc = db.Column(db.String(400))
    price = db.Column(db.Integer)
    quantity = db.Column(db.Integer)


def staff(func):
    @wraps(func)
    def  wrapper():
      if current_user.role in ['admin','staff']:
          return func()
      else:
          return redirect(url_for('home'))
    return wrapper

# Create a user_loader callback
@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

@login_manager.unauthorized_handler
def unauthorized():
    if request.blueprint == 'api':
        abort(HTTPStatus.UNAUTHORIZED)
    flash('login / signup is required')
    return redirect(url_for('login'))


with app.app_context():
    db.create_all()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        genpassword = generate_password_hash(request.form["password"], method='pbkdf2:sha256', salt_length=8)
        email = request.form.get('email')
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        if user:
            flash('Email already exists.Try logging in instead. ')
            return redirect(url_for('login'))
        new_user = User(
            email=request.form.get('email'),
            name=request.form.get('name'),
            password=genpassword,
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)

        return redirect(url_for("products"))
    return render_template("register.html")


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        if not user:
            flash('Invalid email provided')
            return render_template("login.html")
        if check_password_hash(user.password, password):
            login_user(user)

            return redirect(url_for('products'))
        else:
            flash('Password incorrect, please try again')
            return render_template("login.html")
    return render_template("login.html")


@app.route('/products')
def products():
    result = db.session.execute(db.select(Product))
    pro = result.scalars()


    return render_template("product.html",pro = pro,i=0)

@app.route('/add_pro', methods=["GET", "POST"])
@login_required
@staff
def add_pro():
    if request.method == 'POST':
        # check if the post request has the file part
        print(request.form['name'])
        # print(request.form['file'])
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            filename = 'blank.png'
        elif file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash('success')


        new_pro = Product(
            name=request.form.get('name'),
            img='static/product_img/'+filename,
            desc=request.form.get('desc'),
            price=request.form.get('price'),
            quantity=request.form.get('quantity')
        )
        db.session.add(new_pro)
        db.session.commit()
        return redirect(url_for("products"))

    return render_template("add_pro.html")


@app.route("/delete")
@login_required
@staff
def delete():
    num = request.args.get('id')
    p = db.session.execute(db.select(Product).where(Product.id == num)).scalar()
    db.session.delete(p)
    db.session.commit()
    return redirect('/view')

@app.route("/modify", methods=["GET", "POST"])
@login_required
@staff
def modify():
    num = request.args.get('id')
    print(num)
    if request.method == 'POST':
        # check if the post request has the file part
        # print(request.form['file'])
        if 'file' not in request.files:
            return redirect(url_for(view))
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        p = db.session.execute(db.select(Product).where(Product.id == num)).scalar()
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            p.img = 'static/product_img/' + filename

        p.name = request.form.get('name')
        p.desc = request.form.get('desc')
        p.price = request.form.get('price')
        p.quantity = request.form.get('quantity')
        db.session.commit()
        return redirect('/view')

    p = db.session.execute(db.select(Product).where(Product.id == num)).scalar()
    name=p.name
    img = p.img
    desc = p.desc
    price = p.price
    quantity = p.quantity

    return render_template("modify.html",id=num,name=name,i=img,desc=desc,price=price,quantity=quantity)

@app.route('/view', methods=["GET", "POST"])
@login_required
@staff
def view():
        result = db.session.execute(db.select(Product))
        pro = result.scalars()
        return render_template("view.html",p=pro)

@app.route('/viewitem', methods=["GET", "POST"])
def view_item():
    num = request.args.get('id')
    p = db.session.execute(db.select(Product).where(Product.id == num)).scalar()
    return render_template("view.html",p=pro)
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=True)
