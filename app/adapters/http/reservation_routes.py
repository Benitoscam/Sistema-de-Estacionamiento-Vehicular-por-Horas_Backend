from flask import Blueprint, jsonify

bp = Blueprint("reservation", __name__)


@bp.route("/reservations/ping", methods=["GET"])
def ping():
    return jsonify({"message": "reservation routes ready"}), 200