from flask import Flask, jsonify, request

from utils import scrape_security_articles

UOL_URL = "https://www.uol.com.br/"
G1_URL = "https://g1.globo.com/"
FOLHA_URL = "https://www.folha.uol.com.br/"


app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


def only_with_neighborhood():
    value = (request.args.get("somente_com_bairro") or "").strip().lower()
    return value in {"1", "true", "sim", "yes"}


@app.route("/")
def index():
    return (
        r"<h1>Hello! App is running</h1>"
        r"<h2>Allowed routes:</h2>"
        r"<p><a href='http://localhost:5000/noticiais/uol'>/noticiais/uol</a></p>"
        r"<p><a href='http://localhost:5000/noticiais/g1'>/noticiais/g1</a></p>"
        r"<p><a href='http://localhost:5000/noticiais/folha'>/noticiais/folha</a></p>"
    )


@app.route("/noticiais/uol")
def get_uol_news():
    return jsonify(
        scrape_security_articles(
            UOL_URL,
            pages_feed=5,
            require_neighborhood=only_with_neighborhood(),
        )
    )


@app.route("/noticiais/g1")
def get_g1_news():
    return jsonify(
        scrape_security_articles(
            G1_URL,
            pages_feed=5,
            require_neighborhood=only_with_neighborhood(),
        )
    )


@app.route("/noticiais/folha")
def get_folha_security():
    return jsonify(
        scrape_security_articles(
            FOLHA_URL,
            pages_feed=5,
            require_neighborhood=only_with_neighborhood(),
        )
    )


@app.route("/noticiais/gerais")
def get_g1_news_alias():
    return jsonify(
        scrape_security_articles(
            G1_URL,
            pages_feed=5,
            require_neighborhood=only_with_neighborhood(),
        )
    )


@app.route("/noticiais/seguranca")
def get_folha_security_alias():
    return jsonify(
        scrape_security_articles(
            FOLHA_URL,
            pages_feed=5,
            require_neighborhood=only_with_neighborhood(),
        )
    )
