from datetime import datetime
from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt
import jwt

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:kali@localhost:3306/exchange'
CORS(app)
db = SQLAlchemy(app)
ma = Marshmallow(app)
bcrypt = Bcrypt(app)

SECRET_KEY = "b'|\xe7\xbfU3`\xc4\xec\xa7\xa9zf:}\xb5\xc7\xb9\x139^3@Dv'"

class Transaction(db.Model):
    __tablename__ = 'Transaction'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    usd_amount = db.Column(db.Float, nullable=False)
    lbp_amount = db.Column(db.Float, nullable=False)
    usd_to_lbp = db.Column(db.Boolean, nullable=False)

    def __init__(self, usd_amount, lbp_amount, usd_to_lbp):
        self.usd_amount = usd_amount
        self.lbp_amount = lbp_amount
        self.usd_to_lbp = usd_to_lbp

class User(db.Model):
    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(30), unique=True)
    hashed_password = db.Column(db.String(128))

    def __init__(self, user_name, password):
        super(User, self).__init__(user_name=user_name)
        self.hashed_password = bcrypt.generate_password_hash(password)


class TransactionSchema(ma.Schema):
    class Meta:
        fields = ("id", "usd_amount", "lbp_amount", "usd_to_lbp")
        model = Transaction

transaction_schema = TransactionSchema()

class UserSchema(ma.Schema):
    class Meta:
        fields = ("id", "user_name")
        model = User

user_schema = UserSchema()

def create_token(user_id):
    payload = {
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=4),
        'iat': datetime.datetime.utcnow(),
        'sub': user_id
    }
    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm='HS256'
    )


@app.route('/user', methods=['POST'])
def create_user():
    user_name = request.json.get('user_name')
    password = request.json.get('password')

    if not user_name or not password:
        abort(400)

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    new_user = User(user_name=user_name, hashed_password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User created successfully'}), 201

@app.route('/auth', methods=['POST'])
def authenticate_user():
    user_name = request.json.get('user_name')
    password = request.json.get('password')

    if not user_name or not password:
        abort(400)

    user = User.query.filter_by(user_name=user_name).first()

    if not user or not bcrypt.checkpw(password.encode('utf-8'), user.hashed_password):
        abort(403)

    token = create_token(user.id)

    return jsonify({'token': token.decode('utf-8')}), 200



def serialize_transaction(transaction):
    return {
        'id': transaction.id,
        'usd_amount': transaction.usd_amount,
        'lbp_amount': transaction.lbp_amount,
        'usd_to_lbp': transaction.usd_to_lbp
    }


@app.route('/transaction', methods=['POST'])
def create_transaction():
    body = request.get_json()
    new_transaction = Transaction(body['usd_amount'], body['lbp_amount'], body['usd_to_lbp'])
    db.session.add(new_transaction)
    db.session.commit()
    return jsonify(transaction_schema.dump(new_transaction))


@app.route("/exchangeRate", methods=['GET', 'POST'])
def exchange_rate():
    filtered_transactions = db.session.query(Transaction).filter(Transaction.usd_to_lbp == 0)
    average_lbp_amount = sum(t.lbp_amount for t in filtered_transactions) / filtered_transactions.count()
    filtered_transactions2 = db.session.query(Transaction).filter(Transaction.usd_to_lbp == 1)
    average_usd_amount= sum(t.usd_amount for t in filtered_transactions2) / filtered_transactions.count()

    response = {
        "usd_to_lbp": average_usd_amount,
        "lbp_to_usd": average_lbp_amount
    }

    return jsonify(response)