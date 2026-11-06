from flask import Flask
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

app = Flask(__name__)
analyzer = SentimentIntensityAnalyzer()


@app.get('/analyze/<path:text>')
def analyze(text):
    score = analyzer.polarity_scores(text)['compound']
    sentiment = 'positive' if score >= 0.05 else 'negative' if score <= -0.05 else 'neutral'
    return {'sentiment': sentiment, 'score': score}
