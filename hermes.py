import flask as fk
from flask_sqlalchemy import SQLAlchemy
import flask_login as fk_lg
import datetime as dt
import bcrypt
import requests
import json


app = fk.Flask(__name__)
try:
    app.config.from_pyfile('config.py')
except FileNotFoundError:
    # For Heroku, use environment variables
    print('No configuration file present, trying environment variables')
    import os

    app.config['ENV'] = os.environ['ENV']
    app.config['SECRET_KEY'] = os.environ['FLASK_KEY']
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)
log_man = fk_lg.LoginManager(app)
log_man.login_view = 'login'

# Models ######################################################################


class User(fk_lg.UserMixin, db.Model):
    __tablename__ = 'users'
    uid = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128))
    email = db.Column(db.String(128))
    password = db.Column(db.Binary(60), nullable=False)
    time_created = db.Column(db.DateTime(timezone=True),
                             server_default=db.func.now())
    time_modified = db.Column(db.DateTime(timezone=True),
                              onupdate=db.func.now())

    def get_id(self):
        return self.uid

    def set_pw(self, pw):
        self.password = bcrypt.hashpw(pw.encode('utf8'), bcrypt.gensalt())

    def check_pw(self, pw):
        return bcrypt.checkpw(pw.encode('utf8'), self.password)


class Client(db.Model):
    __tablename__ = 'clients'
    cid = db.Column(db.Integer, primary_key=True)
    order = db.relationship('Order')
    name = db.Column(db.String(128))
    description = db.Column(db.String(128))
    deleted = db.Column(db.Boolean)
    time_created = db.Column(db.DateTime(timezone=True),
                             server_default=db.func.now())
    time_modified = db.Column(db.DateTime(timezone=True),
                              onupdate=db.func.now())

    def __repr__(self):
        return '<{0}, {1}, {2}>'.format(self.cid, self.name, self.description)

    def to_dict(self):
        return {'cid': self.cid, 'name': self.name,
                'description': self.description, 'deleted': self.deleted}


class Site(db.Model):
    __tablename__ = 'sites'
    sid = db.Column(db.Integer, primary_key=True)
    order = db.relationship('Order')
    address = db.Column(db.String(128))
    lat = db.Column(db.Numeric(precision=5))
    lon = db.Column(db.Numeric(precision=5))
    deleted = db.Column(db.Boolean)
    time_created = db.Column(db.DateTime(timezone=True),
                             server_default=db.func.now())
    time_modified = db.Column(db.DateTime(timezone=True),
                              onupdate=db.func.now())

    def __repr__(self):
        return '<{0}, {1}>'.format(self.sid, self.address)

    def to_dict(self):
        return {'sid': self.sid, 'address': self.address,
                'deleted': self.deleted}


class Order(db.Model):
    __tablename__ = 'orders'
    oid = db.Column(db.Integer, primary_key=True)
    cid = db.Column(db.Integer, db.ForeignKey('clients.cid'))
    sid = db.Column(db.Integer, db.ForeignKey('sites.sid'))
    due = db.Column(db.String(128))
    status = db.Column(db.String(128))
    deleted = db.Column(db.Boolean)
    order_to_part = db.relationship('OrderToPart')
    time_created = db.Column(db.DateTime(timezone=True),
                             server_default=db.func.now())
    time_modified = db.Column(db.DateTime(timezone=True),
                              onupdate=db.func.now())

    def __repr__(self):
        return '<{0}, {1}, {2}, {3}, {4}>'.format(self.oid,
                                                  self.cid,
                                                  self.sid,
                                                  self.due,
                                                  self.status)

    def to_dict(self):
        c = ''
        s = ''
        if Client.query.get(self.cid):
            c = Client.query.filter_by(cid=self.cid).first().name
        if Site.query.get(self.sid):
            s = Site.query.filter_by(sid=self.sid).first().address
        return {'oid': self.oid, 'cid': self.cid, 'client': c,
                'sid': self.sid, 'site': s, 'due': self.due,
                'status': self.status, 'deleted': self.deleted}


class Part(db.Model):
    __tablename__ = 'parts'
    pid = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    description = db.Column(db.String(128))
    units = db.Column(db.String(128))
    stock = db.Column(db.Integer)
    deleted = db.Column(db.Boolean)
    order_to_part = db.relationship('OrderToPart')
    time_created = db.Column(db.DateTime(timezone=True),
                             server_default=db.func.now())
    time_modified = db.Column(db.DateTime(timezone=True),
                              onupdate=db.func.now())

    def __repr__(self):
        return '<{0}, {1}>'.format(self.pid, self.name)

    def to_dict(self):
        return {'pid': self.pid, 'name': self.name,
                'description': self.description, 'units': self.units,
                'stock': self.stock, 'deleted': self.deleted}


class OrderToPart(db.Model):
    __tablename__ = 'order_to_part'
    otpid = db.Column(db.Integer, primary_key=True)
    oid = db.Column(db.Integer, db.ForeignKey('orders.oid'))
    pid = db.Column(db.Integer, db.ForeignKey('parts.pid'))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Numeric(precision=2))
    deleted = db.Column(db.Boolean)
    time_created = db.Column(db.DateTime(timezone=True),
                             server_default=db.func.now())
    time_modified = db.Column(db.DateTime(timezone=True),
                              onupdate=db.func.now())

    def __repr__(self):
        return '<{0}, {1}, {2}, {3}, {4}>'.format(self.otpid,
                                                  self.oid,
                                                  self.pid,
                                                  self.quantity,
                                                  self.price)
###############################################################################

# Routes ######################################################################


@app.route('/')
@app.route('/index/')
@fk_lg.login_required
def index():
    order_types = {'placed': len(Order.query.filter_by(deleted=False,
                                                       status='Order placed').all()),
                   'scheduled': len(Order.query.filter_by(deleted=False,
                                                          status='Delivery scheduled').all()),
                   'dispatched': len(Order.query.filter_by(deleted=False,
                                                           status='Driver dispatched').all()),
                   'completed': len(Order.query.filter_by(deleted=False,
                                                          status='Order completed').all())}
    restock = []
    for part in Part.query.filter_by(deleted=False).all():
        q = sum([o.quantity
                 for o in OrderToPart.query.filter_by(deleted=False,
                                                      pid=part.pid).all()])
        curr = part.stock
        if q > curr:
            restock.append({'name': part.name, 'number': q - curr})
    # restock = [{'name': 'Part A', 'number': 2},
    #            {'name': 'Part B', 'number': 4}]
    return fk.render_template('index.html', summary=order_types,
                              restock=restock)


@log_man.user_loader
def load_user(uid):
    return User.query.get(uid)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if fk_lg.current_user.is_authenticated:
        return fk.redirect(fk.url_for('index'))
    if fk.request.method == 'POST':
        u = User.query.filter_by(username=fk.request.form['username']).first()
        if not u or not u.check_pw(fk.request.form['password']):
            return fk.redirect(fk.url_for('login'))
        fk_lg.login_user(u)
        return fk.redirect(fk.url_for('index'))
    return fk.render_template('login.html')


@app.route('/logout')
def logout():
    fk_lg.logout_user()
    return fk.redirect(fk.url_for('index'))


@app.route('/clients/')
@fk_lg.login_required
def clients():
    res = [c.to_dict() for c in Client.query.filter_by(deleted=False).all()]
    return fk.render_template('clients.html', clients=res)


@app.route('/client/<cid>', methods=['GET', 'POST'])
@fk_lg.login_required
def client(cid):
    if fk.request.method == 'GET':
        if cid == 'new':
            # Get the max ID in the database
            max_cid = Client.query.order_by(Client.cid.desc()).first().cid
            res = Client(cid=max_cid + 1,
                         name='',
                         description='',
                         deleted=False).to_dict()
        else:
            res = Client.query.get(cid).to_dict()
        return fk.render_template('client.html', client=res)
    else:
        id_val = int(fk.request.form['cid'])
        new_name = fk.request.form['name']
        new_description = fk.request.form['description']
        # If CID is already in the database, update record, o.w. create new
        existing = Client.query.get(id_val)
        if existing is not None:
            existing.name = new_name
            existing.description = new_description
        else:
            new_client = Client(cid=id_val,
                                name=new_name,
                                description=new_description,
                                deleted=False)
            db.session.add(new_client)
        db.session.commit()
        return fk.redirect(fk.url_for('clients'))


@app.route('/delete_clients/', methods=['POST'])
@fk_lg.login_required
def delete_clients():
    ids_to_delete = [int(k.split('_')[1]) for k in fk.request.form.keys()]
    for c in Client.query.filter(Client.cid.in_(ids_to_delete)).all():
        c.deleted = True
    db.session.commit()
    return fk.redirect(fk.url_for('clients'))


@app.route('/sites/')
@fk_lg.login_required
def sites():
    res = [s.to_dict() for s in Site.query.filter_by(deleted=False).all()]
    return fk.render_template('sites.html', sites=res)


@app.route('/site/<sid>', methods=['GET', 'POST'])
@fk_lg.login_required
def site(sid):
    if fk.request.method == 'GET':
        if sid == 'new':
            # Get the max ID in the database
            max_sid = Site.query.order_by(Site.sid.desc()).first().sid
            res = Site(sid=max_sid + 1,
                       address='',
                       lat=0,
                       lon=0,
                       deleted=False).to_dict()
        else:
            res = Site.query.get(sid).to_dict()
        return fk.render_template('site.html', site=res)
    else:
        id_val = int(fk.request.form['sid'])
        new_address = fk.request.form['address']
        # If SID is already in the database, update record, o.w. create new
        existing = Site.query.get(id_val)
        if existing is not None:
            existing.address = new_address
        else:
            lat, lon = get_lat_lon(new_address)
            new_site = Site(sid=id_val,
                            address=new_address,
                            lat=lat,
                            lon=lon,
                            deleted=False)
            db.session.add(new_site)
        db.session.commit()
        return fk.redirect(fk.url_for('sites'))


@app.route('/delete_sites/', methods=['POST'])
@fk_lg.login_required
def delete_sites():
    ids_to_delete = [int(k.split('_')[1]) for k in fk.request.form.keys()]
    for s in Site.query.filter(Site.sid.in_(ids_to_delete)).all():
        s.deleted = True
    db.session.commit()
    return fk.redirect(fk.url_for('sites'))


@app.route('/parts/')
@fk_lg.login_required
def parts():
    res = [p.to_dict() for p in Part.query.filter_by(deleted=False).all()]
    return fk.render_template('parts.html', parts=res)


@app.route('/part/<pid>', methods=['GET', 'POST'])
@fk_lg.login_required
def part(pid):
    if fk.request.method == 'GET':
        if pid == 'new':
            # Get the max ID in the database
            max_pid = Part.query.order_by(Part.pid.desc()).first().pid
            res = Part(pid=max_pid + 1,
                       name='',
                       description='',
                       units='',
                       stock=0,
                       deleted=False).to_dict()
        else:
            res = Part.query.get(pid).to_dict()
        return fk.render_template('part.html', part=res)
    else:
        id_val = int(fk.request.form['pid'])
        new_name = fk.request.form['name']
        new_description = fk.request.form['description']
        new_units = fk.request.form['units']
        new_stock = fk.request.form['stock']
        # If PID is already in the database, update record, o.w. create new
        existing = Part.query.get(id_val)
        if existing is not None:
            existing.name = new_name
            existing.description = new_description
            existing.units = new_units
            existing.stock = new_stock
        else:
            new_part = Part(pid=id_val,
                            name=new_name,
                            description=new_description,
                            units=new_units,
                            stock=new_stock,
                            deleted=False)
            db.session.add(new_part)
        db.session.commit()
        return fk.redirect(fk.url_for('parts'))


@app.route('/delete_parts/', methods=['POST'])
@fk_lg.login_required
def delete_parts():
    ids_to_delete = [int(k.split('_')[1]) for k in fk.request.form.keys()]
    for p in Part.query.filter(Part.pid.in_(ids_to_delete)).all():
        p.deleted = True
    db.session.commit()
    return fk.redirect(fk.url_for('parts'))


@app.route('/orders/')
@fk_lg.login_required
def orders():
    res = [o.to_dict() for o in Order.query.filter_by(deleted=False).all()]
    return fk.render_template('orders.html', orders=res)


@app.route('/order/<oid>', methods=['GET', 'POST'])
@fk_lg.login_required
def order(oid):
    if fk.request.method == 'GET':
        if oid == 'new':
            # Get the max ID in the database
            latest = Order.query.order_by(Order.oid.desc()).first()
            if latest:
                max_oid = latest.oid
            else:
                max_oid = 0
            # Set default CID and SID to most recent, max values
            latest = Client.query.order_by(Client.cid.desc()).first()
            if latest:
                max_cid = latest.cid
            else:
                max_cid = 0
            latest = Site.query.order_by(Site.sid.desc()).first()
            if latest:
                max_sid = latest.sid
            else:
                max_sid = 0
            res = Order(oid=max_oid + 1,
                        cid=max_cid,
                        sid=max_sid,
                        due=str(dt.datetime.utcnow()).split()[0],
                        status='Order placed',
                        deleted=False).to_dict()
        else:
            res = Order.query.get(oid).to_dict()
        c_opts = [{'cid': c.cid, 'name': c.name}
                  for c in Client.query.filter_by(deleted=False).all()]
        s_opts = [{'sid': s.sid, 'address': s.address}
                  for s in Site.query.filter_by(deleted=False).all()]
        # Loop twice here, the first time to allocate blank values
        # TODO: This is certainly inefficient, improve it somehow
        p_opts = [{'pid': p.pid, 'name': p.name, 'stock': p.stock,
                   'current': 0, 'price': 0.00}
                  for p in Part.query.filter_by(deleted=False).all()]
        for p in p_opts:
            for otp in OrderToPart.query.filter_by(deleted=False,
                                                   pid=p['pid'],
                                                   oid=res['oid']).all():
                p['current'] = otp.quantity
                p['price'] = otp.price
        return fk.render_template('order.html', order=res,
                                  clients=c_opts, sites=s_opts, parts=p_opts)
    else:
        oid_val = int(fk.request.form['oid'])
        new_cid = int(fk.request.form['client'])
        new_sid = int(fk.request.form['site'])
        new_due = fk.request.form['due']
        new_status = fk.request.form['status']
        new_mapping = None
        for p in Part.query.filter_by(deleted=False).all():
            if OrderToPart.query.order_by(OrderToPart.otpid.desc()).first():
                max_otpid = OrderToPart.query.order_by(
                    OrderToPart.otpid.desc()).first().otpid
            else:
                max_otpid = 0
            new_quantity = int(fk.request.form['{0}_current'.format(p.pid)])
            new_price = float(fk.request.form['{0}_price'.format(p.pid)])
            existing = OrderToPart.query.filter_by(deleted=False,
                                                   pid=p.pid,
                                                   oid=oid_val).first()
            if existing is not None:
                record = OrderToPart.query.get(existing.otpid)
                record.quantity = new_quantity
                record.price = new_price
            elif new_quantity == 0:
                continue
            else:
                new_mapping = OrderToPart(otpid=max_otpid + 1,
                                          oid=oid_val,
                                          pid=p.pid,
                                          quantity=new_quantity,
                                          price=new_price,
                                          deleted=False)

        # If OID is already in the database, update record, o.w. create new
        existing = Order.query.get(oid_val)
        if existing is not None:
            existing.cid = new_cid
            existing.sid = new_sid
            existing.due = new_due
            existing.status = new_status
        else:
            new_order = Order(oid=oid_val,
                              cid=new_cid,
                              sid=new_sid,
                              due=new_due,
                              status=new_status,
                              deleted=False)
            db.session.add(new_order)
        if new_mapping:
            db.session.add(new_mapping)
        db.session.commit()
        return fk.redirect(fk.url_for('orders'))


@app.route('/delete_orders/', methods=['POST'])
@fk_lg.login_required
def delete_orders():
    ids_to_delete = [int(k.split('_')[1]) for k in fk.request.form.keys()]
    for o in Order.query.filter(Order.oid.in_(ids_to_delete)).all():
        o.deleted = True
    for o in OrderToPart.query.filter(OrderToPart.oid.in_(ids_to_delete)).all():
        o.deleted = True
    db.session.commit()
    return fk.redirect(fk.url_for('orders'))
###############################################################################

# Helper Functions ############################################################


def get_lat_lon(address):
    url = 'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?'
    params = ['address=' + '+'.join(address.split()),
              'benchmark=9',
              'format=json']
    url += '&'.join(params)
    response = requests.get(url=url)
    if not response.ok or not json.loads(response.text):
        print('failed request', response.reason, response.text)
    else:
        matches = json.loads(response.text)['result']['addressMatches']
        if len(matches) > 0:
            xy = matches[0]['coordinates']
            lat = xy['x']
            lon = xy['y']
            return lat, lon
        else:
            print('no matches for address!')
    return 0, 0


def reinitialize_demo_db():
    db.drop_all()
    db.create_all()
    demo_clients = [['Jan Levinson', 'White Pages'],
                    ['John Rammel', 'Prestige Postal Company'],
                    ['Gina Rogers', 'Apex Technology']]
    for client in demo_clients:
        name, description = client
        new_client = Client(name=name,
                            description=description,
                            deleted=False)
        db.session.add(new_client)
    demo_sites = ['811 S Washington Ave, Scranton, PA 18505',
                  '100 The Mall At Steamtown, Scranton, PA 18503',
                  '100 Adams Ave, Scranton, PA 18503',
                  '800 Linden St, Scranton, PA 18510',
                  '601 Jefferson Ave, Scranton, PA 18510']
    for address in demo_sites:
        lat, lon = get_lat_lon(address)
        new_site = Site(address=address,
                        lat=lat,
                        lon=lon,
                        deleted=False)
        db.session.add(new_site)
    demo_parts = [['100# cast coated',
                   '100 lb basis weight thick and shiny paper',
                   'reams', 10],
                  ['20# cast coated',
                   '20 lb basis weight thin and shiny paper',
                   'reams', 10],
                  ['50# smooth offset uncoated',
                   '50 lb basis weight smooth lightweight paper',
                   'reams', 10],
                  ['60# smooth offset uncoated',
                   '60 lb basis weight smooth lightweight paper',
                   'reams', 10],
                  ['70# smooth offset uncoated',
                   '70 lb basis weight smooth lightweight paper',
                   'reams', 10],
                  ['80# smooth offset uncoated',
                   '80 lb basis weight smooth lightweight paper',
                   'reams', 10],
                  ['50# vellum offset uncoated',
                   '50 lb basis weight rough vellum finish lightweight paper',
                   'reams', 10],
                  ['60# vellum offset uncoated',
                   '60 lb basis weight rough vellum finish lightweight paper',
                   'reams', 10],
                  ['70# vellum offset uncoated',
                   '70 lb basis weight rough vellum finish lightweight paper',
                   'reams', 10],
                  ['80# vellum offset uncoated',
                   '80 lb basis weight rough vellum finish lightweight paper',
                   'reams', 10]]
    for part in demo_parts:
        name, description, units, stock = part
        new_part = Part(name=name,
                        description=description,
                        units=units,
                        stock=stock,
                        deleted=False)
        db.session.add(new_part)
    demo_orders = [[1, 1, '2018-05-08', 'Order placed'],
                   [2, 2, '2018-12-25', 'Driver dispatched'],
                   [2, 2, '2018-12-26', 'Delivery scheduled'],
                   [1, 3, '2018-04-15', 'Order completed']]
    for order in demo_orders:
        cid, sid, due, status = order
        new_order = Order(cid=cid,
                          sid=sid,
                          due=due,
                          status=status,
                          deleted=False)
        db.session.add(new_order)

    demo_orders_to_parts = [[1, 1, 1, 5.99],
                            [1, 5, 10, 0.99],
                            [2, 2, 3, 19],
                            [2, 3, 2, 10.5],
                            [3, 4, 1, 29.99]]
    for order_to_part in demo_orders_to_parts:
        oid, pid, quantity, price = order_to_part
        new_order_to_part = OrderToPart(oid=oid,
                                        pid=pid,
                                        quantity=quantity,
                                        price=price,
                                        deleted=False)
        db.session.add(new_order_to_part)

    pw = 'password'.encode('utf8')
    demo_user = User(username='mscott',
                     email='mscott@dundermifflin.com',
                     password=bcrypt.hashpw(pw, bcrypt.gensalt()))
    db.session.add(demo_user)
    db.session.commit()
###############################################################################


if __name__ == '__main__':
    print('Environment type:', app.config['ENV'])
    if app.config['ENV'] == 'development':
        app.run(debug=True)
    else:
        app.run(debug=False)
    # To test on other devices, use: http://10.0.0.124:5000
    # app.run(host='0.0.0.0', port=5000)
