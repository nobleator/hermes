import flask as fk
from flask_sqlalchemy import SQLAlchemy
import flask_login as fk_lg
import datetime
import bcrypt


app = fk.Flask(__name__)
app.secret_key = 'this-is-a-terrible-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost:5432/hermes'
db = SQLAlchemy(app)
log_man = fk_lg.LoginManager(app)
log_man.login_view = 'login'

# Models ######################################################################
# TODO: Singular vs plural table names? 'Order' is an invalid name in Postgres.
# TODO: Non-sequential IDs


class User(fk_lg.UserMixin, db.Model):
    __tablename__ = 'users'
    uid = db.Column(db.String(128), primary_key=True)
    username = db.Column(db.String(128))
    email = db.Column(db.String(128))
    password = db.Column(db.Binary(60), nullable=False)
    created_on = db.Column(db.DateTime(), nullable=False)

    def get_id(self):
        return self.uid

    def set_pw(self, pw):
        self.password = bcrypt.hashpw(pw.encode('utf8'), bcrypt.gensalt())

    def check_pw(self, pw):
        return bcrypt.checkpw(pw.encode('utf8'), self.password)


class Client(db.Model):
    __tablename__ = 'clients'
    cid = db.Column(db.String(128), primary_key=True)
    order = db.relationship('Order')
    name = db.Column(db.String(128))
    description = db.Column(db.String(128))
    deleted = db.Column(db.Boolean)

    def __repr__(self):
        return '<{0}, {1}, {2}>'.format(self.cid, self.name, self.description)

    def to_dict(self):
        return {'cid': self.cid, 'name': self.name,
                'description': self.description, 'deleted': self.deleted}


class Site(db.Model):
    __tablename__ = 'sites'
    sid = db.Column(db.String(128), primary_key=True)
    order = db.relationship('Order')
    address = db.Column(db.String(128))
    deleted = db.Column(db.Boolean)

    def __repr__(self):
        return '<{0}, {1}>'.format(self.sid, self.address)

    def to_dict(self):
        return {'sid': self.sid, 'address': self.address,
                'deleted': self.deleted}


class Order(db.Model):
    __tablename__ = 'orders'
    oid = db.Column(db.String(128), primary_key=True)
    cid = db.Column(db.String(128), db.ForeignKey('clients.cid'))
    sid = db.Column(db.String(128), db.ForeignKey('sites.sid'))
    due = db.Column(db.String(128))
    status = db.Column(db.String(128))
    deleted = db.Column(db.Boolean)

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
###############################################################################

# Routes ######################################################################
# TODO: New user account creation


@app.route('/')
@app.route('/index')
@fk_lg.login_required
def index():
    return fk.render_template('index.html')


@log_man.user_loader
def load_user(uid):
    return User.query.get(uid)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if fk_lg.current_user.is_authenticated:
        return fk.redirect(fk.url_for('index'))
    if fk.request.method == 'POST':
        print(fk.request.form)
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
            max_cid = int(Client.query.order_by(Client.cid.desc()).first().cid)
            res = Client(cid=str(max_cid + 1),
                         name='',
                         description='',
                         deleted=False).to_dict()
        else:
            res = Client.query.get(cid).to_dict()
        return fk.render_template('client.html', client=res)
    else:
        id_val = fk.request.form['cid']
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
    ids_to_delete = [k.split('_')[1] for k in fk.request.form.keys()]
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
            max_sid = int(Site.query.order_by(Site.sid.desc()).first().sid)
            res = Site(sid=str(max_sid + 1),
                       address='',
                       deleted=False).to_dict()
        else:
            res = Site.query.get(sid).to_dict()
        return fk.render_template('site.html', site=res)
    else:
        id_val = fk.request.form['sid']
        new_address = fk.request.form['address']
        # If SID is already in the database, update record, o.w. create new
        existing = Site.query.get(id_val)
        if existing is not None:
            existing.address = new_address
        else:
            new_site = Site(sid=id_val,
                            address=new_address,
                            deleted=False)
            db.session.add(new_site)
        db.session.commit()
        return fk.redirect(fk.url_for('sites'))


@app.route('/delete_sites/', methods=['POST'])
@fk_lg.login_required
def delete_sites():
    ids_to_delete = [k.split('_')[1] for k in fk.request.form.keys()]
    for s in Site.query.filter(Site.sid.in_(ids_to_delete)).all():
        s.deleted = True
    db.session.commit()
    return fk.redirect(fk.url_for('sites'))


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
            max_oid = int(Order.query.order_by(Order.oid.desc()).first().oid)
            # Set defaul CID and SID to most recent, max values
            max_cid = Client.query.order_by(Client.cid.desc()).first().cid
            max_sid = Site.query.order_by(Site.sid.desc()).first().sid
            res = Order(oid=str(max_oid + 1),
                        cid=max_cid,
                        sid=max_sid,
                        due='No due date',
                        status='Order placed',
                        deleted=False).to_dict()
        else:
            res = Order.query.get(oid).to_dict()
        c_opts = [{'cid': c.cid, 'name': c.name}
                  for c in Client.query.filter_by(deleted=False).all()]
        s_opts = [{'sid': s.sid, 'address': s.address}
                  for s in Site.query.filter_by(deleted=False).all()]
        return fk.render_template('order.html', order=res,
                                  clients=c_opts, sites=s_opts)
    else:
        id_val = fk.request.form['oid']
        new_cid = fk.request.form['client']
        new_sid = fk.request.form['site']
        new_due = fk.request.form['due']
        new_status = fk.request.form['status']
        # If OID is already in the database, update record, o.w. create new
        existing = Order.query.get(id_val)
        if existing is not None:
            existing.cid = new_cid
            existing.sid = new_sid
            existing.due = new_due
            existing.status = new_status
        else:
            new_order = Order(oid=id_val,
                              cid=new_cid,
                              sid=new_sid,
                              due=new_due,
                              status=new_status,
                              deleted=False)
            db.session.add(new_order)
        db.session.commit()
        return fk.redirect(fk.url_for('orders'))


@app.route('/delete_orders/', methods=['POST'])
@fk_lg.login_required
def delete_orders():
    ids_to_delete = [k.split('_')[1] for k in fk.request.form.keys()]
    for o in Order.query.filter(Order.oid.in_(ids_to_delete)).all():
        o.deleted = True
    db.session.commit()
    return fk.redirect(fk.url_for('orders'))
###############################################################################

# Development Functions #######################################################


def reinitialize_demo_db():
    db.drop_all()
    db.create_all()
    demo_clients = [['1', 'Doug Dimmadome',
                     'Owner of the Dimmsdale Dimmadome'],
                    ['2', 'Bob Vance', 'Vance Refrigeration']]
    for client in demo_clients:
        cid, name, description = client
        new_client = Client(cid=cid,
                            name=name,
                            description=description,
                            deleted=False)
        db.session.add(new_client)
    demo_sites = [['1', '100 Maple Road'],
                  ['2', '7 Main Street'],
                  ['3', '1600 Pennsylvania Avenue']]
    for site in demo_sites:
        sid, address = site
        new_site = Site(sid=sid,
                        address=address,
                        deleted=False)
        db.session.add(new_site)
    demo_orders = [['1', '1', '1', '4 May 2018', 'Order placed'],
                   ['2', '2', '2', '25 December 2018', 'Delivery scheduled'],
                   ['3', '1', '3', '1 April 2018', 'Order completed']]
    for order in demo_orders:
        oid, cid, sid, due, status = order
        new_order = Order(oid=oid,
                          cid=cid,
                          sid=sid,
                          due=due,
                          status=status,
                          deleted=False)
        db.session.add(new_order)

    pw = 'p@ssw0rd'.encode('utf8')
    demo_user = User(uid='1',
                     username='Bugs Bunny',
                     email='thisisfake@gmail.com',
                     password=bcrypt.hashpw(pw, bcrypt.gensalt()),
                     created_on=str(datetime.datetime.utcnow()))
    db.session.add(demo_user)
    db.session.commit()
    return None
###############################################################################


if __name__ == '__main__':
    app.run(debug=True)
