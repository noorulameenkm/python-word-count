from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy 
import os
import requests
import operator
import re
import nltk
# from stop_words import st
from collections import Counter
from bs4 import BeautifulSoup
from nltk.corpus import stopwords


app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


from models import * 


@app.route('/', methods=['GET', 'POST'])
def index():
    errors = []
    results = {}
    r = None
    # nltk.download()
    stops = set(stopwords.words('english'))
    if request.method == 'POST':
        try:
            url = request.form['url']
            print(f"URL is {url}")
            r = requests.get(url)
            print(r.text)
        except:
            errors.append(
                "Unable to get URl. Please make sure its valid andtry again"
            )

        if r:
            # text processing
            raw = BeautifulSoup(r.text, 'html.parser').get_text()
            nltk.data.path.append('./nltk_data/') # set the path
            # nltk.download()
            tokens = nltk.word_tokenize(raw)
            text = nltk.Text(tokens)
            # remove punctuations, count raw words
            nonPunct = re.compile('.*[A-Za-z].*')
            raw_words = [w for w in text if nonPunct.match(w)]
            raw_word_count = Counter(raw_words)
            # stop words
            no_stop_words = [w for w in raw_words if w.lower() not in stops]
            no_stop_word_count = Counter(no_stop_words)
            # save the results
            results = sorted(
                no_stop_word_count.items(),
                key=operator.itemgetter(1),
                reverse=True
            )[:10]
            try:
                result = Result(
                    url=url,
                    result_all=raw_word_count,
                    result_no_stop_words=no_stop_word_count
                )
                # print(f"{result.url}")
                db.session.add(result)
                db.session.commit()
            except Exception as e:
                print(e)
                errors.append("Unable to add item to database.")
    return render_template('index.html', errors=errors, results=results)

@app.route('/<name>')
def hello_name(name):
    return f"Hello {name}!"


if __name__ == '__main__':
    app.run()
