from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:kali@localhost:3306/exchange'
CORS(app)
db = SQLAlchemy(app)


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
    return jsonify(serialize_transaction(new_transaction))


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