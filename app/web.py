from flask import Flask, render_template, request, jsonify

from app.agent import CustomerAssistant


app = Flask(
    __name__,
    template_folder="../templates"
)

assistant = CustomerAssistant()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()

    message = data.get("message", "").strip()

    if not message:
        return jsonify({
            "error": "Please enter a message."
        }), 400

    result = assistant.handle(message)

    return jsonify({
        "message": result.get("message", ""),
        "type": result.get("type", ""),
        "sources": result.get("sources", []),
    })


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
    