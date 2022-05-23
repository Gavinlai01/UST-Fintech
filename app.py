from flask import Flask, render_template, request
import requests
import joblib
import pandas as pd
import requests
import talib
import json
import yfinance as yf
import numpy as np
from pypfopt import EfficientFrontier
from pypfopt import risk_models
from pypfopt import expected_returns
from pypfopt import DiscreteAllocation
from datetime import datetime
from dateutil.relativedelta import relativedelta

app = Flask(__name__)

tree_clf = joblib.load('model/tree_classifier.pkl')
#MLP_clf = joblib.load('model/MLP_classifier.pkl')
Logistic_clf = joblib.load('model/Logistic_classifier.pkl')
NB_clf = joblib.load('model/Naive Bayes.pkl')
bearer_token = "AAAAAAAAAAAAAAAAAAAAAPYVWgEAAAAAidkkoJ72QjFjmNHwoWHb5rtwagE%3DVjHzdiYMqPcEMuCTWmURKcvf2lardEydnKd34QZMrMHtBFcy51"
tickers = pd.read_csv('Portfolio/Stock_Shortlist.csv')
StartDate = datetime.today() - relativedelta(years=15) - relativedelta(days=1)
tickers.sort_values(by='score', ascending=False)
tickers = tickers.loc[tickers['score'] >= 7]
tickers = tickers.loc[pd.to_datetime(tickers['IPODate']) <= StartDate]
tickers =tickers['Symbol'].values.tolist()
stock = yf.download(tickers, period="max")['Adj Close']

# def Get_data(StartDate):
#   tickers = pd.read_csv('Stock_Shortlist.csv')
#   tickers.sort_values(by='score', ascending=False)
#   tickers = tickers.loc[tickers['score'] >= 7]
#   tickers = tickers.loc[pd.to_datetime(tickers['IPODate']) <= StartDate]
#   tickers =tickers['Symbol'].values.tolist()
#   df = yf.download(tickers, period="max")['Adj Close']
#   return df

def Portfolio_Optimization(df, upperWeight, lowerWeight):
  S = risk_models.CovarianceShrinkage(df).ledoit_wolf()
  mu = expected_returns.capm_return(df)
  ef = EfficientFrontier(mu, S, weight_bounds=(lowerWeight, upperWeight))
  raw_weights = ef.max_sharpe(risk_free_rate = 0.01)
  cleaned_weights = ef.clean_weights()
  return ef, cleaned_weights


def connect_to_endpoint_user(url):
    response = requests.request("GET", url, auth=bearer_oauth,)
    if response.status_code != 200:
        raise Exception(
            "Request returned an error: {} {}".format(
                response.status_code, response.text
            )
        ) 
    return response

def create_url_user(author):
    usernames = "usernames=" + author
    user_fields = "user.fields=description,created_at"
    url = "https://api.twitter.com/2/users/by?{}&{}".format(usernames, user_fields)
    return url

def create_url(id):
    user_id = id
    return "https://api.twitter.com/2/users/{}/tweets".format(user_id)

def get_params():
    return {"tweet.fields": "created_at"}

def bearer_oauth(r):
    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2UserTweetsPython"
    return r

def connect_to_endpoint(url, params):
    response = requests.request("GET", url, auth=bearer_oauth, params=params)
    print(response.status_code)
    if response.status_code != 200:
        return False
    return response.json()

def query(payload):
    API_URL = "https://api-inference.huggingface.co/models/ProsusAI/finbert"
    headers = {"Authorization": f"Bearer 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"}
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()

app = Flask(__name__)

def GetData():
    url = 'https://min-api.cryptocompare.com/data/v2/histominute?fsym=BTC&tsym=USD&limit=223&toTs=-1&api_key=375a206b8c4f0033b8e53cd69e94931844c8f621775dcfd04740d9bfeb3e0e59'
    resp = requests.get(url=url).json()
    data = pd.DataFrame.from_dict(resp["Data"]["Data"])
    data['datetime'] = pd.to_datetime(data['time'], unit='s')
    data.set_index('datetime', inplace=True)
    data = data.sort_values(by="datetime")
    data = data.drop(['conversionType','conversionSymbol'], 1)
    data['SMA20'] = talib.SMA(data['close'], timeperiod=20) #overlap
    data['SMA50'] = talib.SMA(data['close'], timeperiod=50) #overlap
    data['EMA20'] = talib.EMA(data['close'], timeperiod=20) #overlap
    data['EMA50'] = talib.EMA(data['close'], timeperiod=50) #overlap
    data['EMA200'] = talib.EMA(data['close'], timeperiod=200) #overlap
    data['Upper'], data['Mid'], data['Lower'] = talib.BBANDS(data['close'], nbdevup=2, nbdevdn=2, timeperiod=20) #overlap
    data['SAR'] = talib.SAR(data['close'], data['low'], acceleration=0, maximum=0) #overlap
    data['ADX'] = talib.ADX(data['high'], data['low'], data['close'], timeperiod=14) #Momentum
    data['MACD'], data['Signal'], data['Hist'] = talib.MACD(data['close'], fastperiod=12, slowperiod=26, signalperiod=9) #Momentum
    data['RSI'] = talib.RSI(data['close'], timeperiod=14) #Momentum
    data['K'], data['D'] = talib.STOCH(data['high'], data['low'], data['close'].values, fastk_period=9, slowk_period=3, #Momentum
                                slowk_matype=0, slowd_period=3, slowd_matype=0)
    data['K'].fillna(0,inplace=True)
    data['D'].fillna(0,inplace=True)
    data['J']=3*data['K']-2*data['D']
    data['Willam R'] = talib.WILLR(data['high'], data['low'], data['close'], timeperiod=14)  #Momentum
    data['slowk'], data['slowd'] = talib.STOCH(data['high'], data['low'],data['close']) #Momentum
    data['ADOSC'] = talib.ADOSC(data['high'], data['low'], data['close'], data['volumeto']) #Momentum
    data['MFI'] = talib.MFI(data['high'], data['low'], data['close'], data['volumeto']) #Momentum
    data['aroondown'], data['aroonup'] = talib.AROON(data['close'], data['low']) #Volume
    data = data.dropna()
    return data

def TreeModel(Data):
    Data_np = Data.to_numpy()
    Prediction = pd.DataFrame(tree_clf.predict(Data_np[:, 7:]), columns = ['decision'])
    return Prediction
"""
def MLPModel(Data):
    Data_np = Data.to_numpy()
    Prediction = pd.DataFrame(MLP_clf.predict(Data_np[:, 13:22]), columns = ['decision'])
    return Prediction
"""
def LogisticModel(Data):
    Data_np = Data.to_numpy()
    Prediction = pd.DataFrame(Logistic_clf.predict(Data_np[:, 7:]), columns = ['decision'])
    return Prediction

def NBModel(Data):
    Data_np = Data.to_numpy()
    Prediction = pd.DataFrame(NB_clf.predict(Data_np[:, 7:]), columns = ['decision'])
    return Prediction

def ResultProcessing(Prediction,Data_np, Data):
    Prediction['time'] = pd.DataFrame(Data_np[:,0:1], columns = ['time'])
    Prediction['close'] = pd.DataFrame(Data_np[:,7:8], columns = ['close'])
    Prediction['datetime'] = pd.to_datetime(Prediction['time'], unit='s')
    Prediction['Datetime'] = pd.to_datetime(Prediction['time'], unit='s')
    Prediction = Prediction.sort_values(by="datetime")
    Prediction.set_index('datetime', inplace=True)
    Prediction['close'] = Data['close']
    def Tostr(row):
        if row['decision'] == 1:
            return 'buy' 
        elif row['decision'] == -1:
            return 'Sell'
        elif row['decision'] == 0:
            return 'Hold'
    Prediction['decision'] = Prediction.apply(lambda row: Tostr(row), axis=1)
    def Upper(row):
        return round(row['close'] * (1+0.005),2)
    Prediction['Upper'] = Prediction.apply(lambda row: Upper(row), axis=1)
    def Lower(row):
        return round(row['close'] * (1-0.005),2)
    Prediction['Lower'] = Prediction.apply(lambda row: Lower(row), axis=1)
    result = Prediction.astype(str).to_json(orient="records")
    return json.loads(result)

@app.route('/')
def main():
    Data = GetData()
    Data_np = Data.to_numpy()
    Prediction = TreeModel(Data)
    json_reulst = ResultProcessing(Prediction, Data_np, Data)
    return render_template('tree.html', data=json_reulst)
"""
@app.route('/mlp')
def MLP():
    Data = GetData()
    Data_np = Data.to_numpy()
    Prediction = MLPModel(Data)
    json_reulst = ResultProcessing(Prediction, Data_np, Data)
    return render_template('mlp.html', data=json_reulst)
"""
@app.route('/logistic')
def Logistic():
    Data = GetData()
    Data_np = Data.to_numpy()
    Prediction = LogisticModel(Data)
    json_reulst = ResultProcessing(Prediction, Data_np, Data)
    return render_template('logistic.html', data=json_reulst)

@app.route('/naive-bayes')
def KNN():
    Data = GetData()
    Data_np = Data.to_numpy()
    Prediction = NBModel(Data)
    json_reulst = ResultProcessing(Prediction, Data_np, Data)
    return render_template('nb.html', data=json_reulst)

@app.route('/finbert')
def home():
    if request.args.get('sentence'):
        text = request.args.get('sentence')
    else:
        text = "Powell Declares Inflation Big Threat as Fed Signals Rate Hikes"
    output = query({"inputs": text})
    result = []
    output[0].append({'text': text})
    result.append(output[0])
    return render_template('home.html', data=result)

@app.route('/sentence')
def sentence():
    if request.args.get('sentence'):
        text = request.args.get('sentence')
    else:
        text = "Powell Declares Inflation Big Threat as Fed Signals Rate Hikes"
    output = query({"inputs": text})
    result = []
    output[0].append({'text': text})
    result.append(output[0])
    return render_template('sentence.html',title='One Sentence Analysis', data=result)

@app.route('/twitter')
def twitter():
    author = request.args.get('author')
    url = create_url_user(author)
    userid = connect_to_endpoint_user(url)
    if userid.status_code != 200:
        return render_template('InvalidUser.html',title='Error', id=author)
    else:
        json_response = userid.json()
        url = create_url(json_response["data"][0]['id'])
        params = get_params()
        json_response = connect_to_endpoint(url, params)
        result = []
        for tweet in json_response["data"]:
            text = tweet["text"]
            output = query({"inputs": text})
            output[0].append(tweet)
            result.append(output[0])
        return render_template('twitter.html',title='Tweet Analysis', data=result, author=author)

@app.route('/mannul')
def mannul():
    return render_template('mannul.html',title='User Mannul')

@app.route('/portfolio')
def Portfolio():
    StartDate = datetime.today() - relativedelta(years=15) - relativedelta(days=1)
    # stock = Get_data(StartDate)
    if request.args.get('totalvalue'):
        total_portfolio_value = float(request.args.get('totalvalue'))
    else:
        total_portfolio_value = 20000
    if request.args.get('upper'):
        upperWeight = float(request.args.get('upper'))
    else:
        upperWeight = 0.2
    if request.args.get('lower'):
        lowerWeight = float(request.args.get('lower'))
    else:
        lowerWeight = -0.1
    ef, cleaned_weights = Portfolio_Optimization(stock, upperWeight, lowerWeight)
    weight = list(cleaned_weights.values())
    tickers = list(cleaned_weights.keys())
    performance = ef.portfolio_performance(verbose=True, risk_free_rate = 0.01)
    latest_prices = stock.iloc[-1]  # prices as of the day you are allocating
    da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=total_portfolio_value, short_ratio=0.3)
    alloc, leftover = da.lp_portfolio()
    NoShare = list(alloc.values())
    NoTicker = list(alloc.keys())
    return render_template('portfolio.html',title='Portfolio', labels=tickers, values=weight, returns = performance[0], volatility = performance[1], ratio = performance[2], NoShare= NoShare, NoTicker = NoTicker, len=len(alloc))
    # return render_template('portfolio.html',title='Portfolio Allocation', labels=tickers, values=weight, returns = performance[0], volatility = performance[1], ratio = performance[2])

@app.route('/portfolio/Backtesting')
def BackTest():
    backTest = pd.read_csv('Portfolio/BackTest.csv')
    Duration = backTest['Duration'].tolist()
    Expectation = backTest['Expected Sharpe Ratio'].tolist()
    Actual = backTest['Actual Sharpe Ratio'].tolist()
    IWF = backTest['IWF'].tolist()
    NDAQ = backTest['NDAQ'].tolist()
    SPY = backTest['SPY'].tolist()
    return render_template('backtest.html',title='Back Testing', labels=Duration, Expectation = Expectation, Actual = Actual, IWF = IWF, NDAQ = NDAQ, SPY=SPY)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)