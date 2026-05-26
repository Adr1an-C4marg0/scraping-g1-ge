from flask import Flask, jsonify, make_response, request

from utils import scrape_security_articles

G1_URL = "https://g1.globo.com/"
ESTADAO_URL = "https://www.estadao.com.br/"
TERRA_URL = "https://www.terra.com.br/noticias/brasil/"
CNNBRASIL_URL = "https://www.cnnbrasil.com.br/"
UOL_URL = "https://noticias.uol.com.br/cotidiano/"


app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


def only_with_neighborhood():
    value = (request.args.get("somente_com_bairro") or "").strip().lower()
    return value in {"1", "true", "sim", "yes"}


def render_articles_response(articles):
    if not articles:
        return make_response("Não há notícias válidas para mostrar", 200)
    return jsonify(articles)


@app.route("/")
def index():
    return (
        r"<h1>Hello! App is running</h1>"
        r"<h2>Allowed routes:</h2>"
        r"<p><a href='http://localhost:5000/noticiais/g1'>/noticiais/g1</a></p>"
        r"<p><a href='http://localhost:5000/noticiais/estadao'>/noticiais/estadao</a></p>"
        r"<p><a href='http://localhost:5000/noticiais/terra'>/noticiais/terra</a></p>"
        r"<p><a href='http://localhost:5000/noticiais/cnnbrasil'>/noticiais/cnnbrasil</a></p>"
        r"<p><a href='http://localhost:5000/noticiais/uol'>/noticiais/uol</a></p>"
    )



@app.route("/noticiais/g1")
def get_g1_news():
    return render_articles_response(
        scrape_security_articles(
            G1_URL,
            pages_feed=5,
            require_neighborhood=only_with_neighborhood(),
        )
    )




@app.route("/noticiais/gerais")
def get_g1_news_alias():
    return render_articles_response(
        scrape_security_articles(
            G1_URL,
            pages_feed=5,
            require_neighborhood=only_with_neighborhood(),
        )
    )


@app.route("/noticiais/estadao")
def get_estadao_news():
    return render_articles_response(
        scrape_security_articles(
            ESTADAO_URL,
            pages_feed=5,
            require_neighborhood=only_with_neighborhood(),
        )
    )


@app.route("/noticiais/terra")
def get_terra_news():
    return render_articles_response(
        scrape_security_articles(
            TERRA_URL,
            pages_feed=5,
            require_neighborhood=only_with_neighborhood(),
        )
    )

@app.route("/noticiais/cnnbrasil")
def get_cnnbrasil_news():
    return render_articles_response(
        scrape_security_articles(
            CNNBRASIL_URL,
            pages_feed=5,
            require_neighborhood=only_with_neighborhood(),
        )
    )


@app.route("/noticiais/uol")
def get_uol_news():
    return render_articles_response(
        scrape_security_articles(
            UOL_URL,
            pages_feed=5,
            require_neighborhood=only_with_neighborhood(),
        )
    )


