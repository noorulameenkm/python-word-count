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
from rq import Queue
from rq.job import Job
from worker import conn


app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
q = Queue(connection=conn)

from models import * 


def count_and_save_words(url):
    errors = []
    r = None
    # nltk.download()
    stops = set(stopwords.words('english'))
    try:
        url = request.form['url']
        print(f"URL is {url}")
        r = requests.get(url)
    except:
        errors.append(
            "Unable to get URl. Please make sure its valid andtry again"
        )
        return {'errors': errors}

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
            return result.id
        except Exception as e:
            print(e)
            errors.append("Unable to add item to database.")
            return { 'errors': errors }


@app.route('/', methods=['GET', 'POST'])
def index():
    
    results = {}
    if request.method == 'POST':
        from app import count_and_save_words
        url = request.form['url']
        if not url[:8].startswith(('https://', 'http://')):
            url = 'http://' + url
        job = q.enqueue_call(
                    func=count_and_save_words, 
                    args=(url,), 
                    result_ttl=5000
                )
        print(job.get_id())
    return render_template('index.html', results=results)


@app.route('/results/<job_key>')
def get_results(job_key):
    job = Job.fetch(job_key, connection=conn)
    if job.is_finished:
        return str(job.result), 200
    elif job.is_failed:
        return "Failed"
    else:
        return "Nay!", 200



if __name__ == '__main__':
    app.run()
