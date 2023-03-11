from datetime import datetime
from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt
import jwt
import db_config

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = db_config.DB_CONFIG
CORS(app)
db = SQLAlchemy(app)
ma = Marshmallow(app)
bcrypt = Bcrypt(app)

SECRET_KEY = "b'|\xe7\xbfU3`\xc4\xec\xa7\xa9zf:}\xb5\xc7\xb9\x139^3@Dv'"

from .model.user import User, user_schema
from .model.transaction import Transaction, transaction_schema, transactions_schema

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

def extract_auth_token(authenticated_request):
    auth_header = authenticated_request.headers.get('Authorization')
    if auth_header:
        return auth_header.split(" ")[1]
    else:
        return None

def decode_token(token):
    payload = jwt.decode(token, SECRET_KEY, 'HS256')
    return payload['sub']


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


@app.route('/transaction', methods=['POST'])
def create_transaction():
    auth_token = extract_auth_token(request)
    if auth_token:
        try:
            user_id = decode_token(auth_token)
        except:
            abort(403)
    else:
        user_id = None

    body = request.get_json()
    new_transaction = Transaction(
        body['usd_amount'],
        body['lbp_amount'],
        body['usd_to_lbp'],
        user_id
    )

    db.session.add(new_transaction)
    db.session.commit()

    return jsonify(transaction_schema.dump(new_transaction))

@app.route("/exchangeRate", methods=['GET', 'POST'])
def exchange_rate():
    current_time = datetime.datetime.now()
    start_time = current_time - datetime.timedelta(hours=72) # 3 days ago
    filtered_transactions = db.session.query(Transaction).filter(
        Transaction.added_date.between(start_time, current_time),
        Transaction.usd_to_lbp == 0
    )
    filtered_transactions2 = db.session.query(Transaction).filter(
        Transaction.added_date.between(start_time, current_time),
        Transaction.usd_to_lbp == 1
    )

    total_lbp_amount = sum(t.lbp_amount for t in filtered_transactions)
    total_usd_amount = sum(t.usd_amount for t in filtered_transactions2)

    if filtered_transactions.count() > 0:
        average_lbp_amount = total_lbp_amount / filtered_transactions.count()
    else:
        average_lbp_amount = 0

    if filtered_transactions2.count() > 0:
        average_usd_amount = total_usd_amount / filtered_transactions2.count()
    else:
        average_usd_amount = 0

    response = {
        "usd_to_lbp": average_usd_amount,
        "lbp_to_usd": average_lbp_amount
    }

    return jsonify(response)


@app.route('/transaction', methods=['GET'])
def get_transactions():
    auth_token = extract_auth_token(request)
    if not auth_token:
        abort(403)
    try:
        user_id = decode_token(auth_token)
    except:
        abort(403)
    transactions = Transaction.query.filter_by(user_id=user_id).all()
    return jsonify(transaction_schema.dump(transactions)), 200
