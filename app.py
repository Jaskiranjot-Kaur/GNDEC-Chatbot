from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from chatbot.parser import parse_query
from chatbot.request_engine import (
    admin_update_request,
    build_request_response,
    get_admin_requests,
    get_request_history,
    update_request_status,
)
from chatbot.response_engine import generate_response

app = Flask(__name__)
CORS(app)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/admin-panel")
def admin_panel():
    return render_template("admin_panel.html")


@app.route("/chat", methods=["POST"])
def chat():
    try:
        payload = request.get_json(force=True)
        message = (payload.get("message") or "").strip()
        language = payload.get("language", "auto")

        if not message:
            return jsonify({
                "reply": "Please type a message.",
                "type": "text",
                "meta": None
            }), 400

        print("USER MESSAGE:", message)
        print("LANGUAGE:", language)

        parsed = parse_query(message, language)

        result = generate_response(parsed)

        if not isinstance(result, dict):
            result = {
                "reply": "Sorry, I could not process your request.",
                "type": "text",
                "meta": None
            }

        if "type" not in result:
            result["type"] = "text"

        if "meta" not in result:
            result["meta"] = None

        return jsonify(result)

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({
            "reply": "Internal Server Error occurred.",
            "type": "text",
            "meta": None
        }), 500


@app.route("/request-support", methods=["POST"])
def request_support():
    try:
        payload = request.get_json(force=True) or {}
        result = build_request_response(payload)
        return jsonify(result)
    except Exception as e:
        print(f"Request Support Error: {e}")
        return jsonify({
            "reply": "Request section could not process the submission.",
            "type": "request",
            "meta": None
        }), 500


@app.route("/request-support/history", methods=["GET"])
def request_support_history():
    try:
        return jsonify({"requests": get_request_history()})
    except Exception as e:
        print(f"Request History Error: {e}")
        return jsonify({"requests": []}), 500


@app.route("/request-support/status", methods=["POST"])
def request_support_status():
    try:
        payload = request.get_json(force=True) or {}
        result = update_request_status(payload.get("request_id"))
        return jsonify(result)
    except ValueError as e:
        return jsonify({
            "reply": str(e),
            "type": "request",
            "meta": None
        }), 400
    except Exception as e:
        print(f"Request Status Error: {e}")
        return jsonify({
            "reply": "Request status could not be updated right now.",
            "type": "request",
            "meta": None
        }), 500


@app.route("/admin/requests", methods=["GET"])
def admin_requests():
    try:
        return jsonify(get_admin_requests())
    except Exception as e:
        print(f"Admin Request Load Error: {e}")
        return jsonify({"requests": [], "stats": {}}), 500


@app.route("/admin/requests/update", methods=["POST"])
def admin_requests_update():
    try:
        payload = request.get_json(force=True) or {}
        result = admin_update_request(
            payload.get("request_id"),
            payload.get("status"),
            payload.get("admin_note"),
        )
        return jsonify(result)
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        print(f"Admin Request Update Error: {e}")
        return jsonify({"message": "Admin update failed."}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
