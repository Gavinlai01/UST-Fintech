from flask import Flask, render_template, request
import requests
import joblib
import pandas as pd
import requests
import talib
import json
app = Flask(__name__)

bearer_token = "AAAAAAAAAAAAAAAAAAAAAPYVWgEAAAAAidkkoJ72QjFjmNHwoWHb5rtwagE%3DVjHzdiYMqPcEMuCTWmURKcvf2lardEydnKd34QZMrMHtBFcy51"


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
    url = 'https://min-api.cryptocompare.com/data/v2/histominute?fsym=BTC&tsym=USD&limit=49&toTs=-1&api_key=375a206b8c4f0033b8e53cd69e94931844c8f621775dcfd04740d9bfeb3e0e59'
    resp = requests.get(url=url).json()
    data = pd.DataFrame.from_dict(resp["Data"]["Data"])
    data['datetime'] = pd.to_datetime(data['time'], unit='s')
    data.set_index('datetime', inplace=True)
    data = data.sort_values(by="datetime")
    data = data.drop(['conversionType','conversionSymbol'], 1)
    data['SMA20'] = talib.SMA(data['close'], timeperiod=20)
    data['SMA50'] = talib.SMA(data['close'], timeperiod=50)
    data['EMA20'] = talib.EMA(data['close'], timeperiod=20)
    data['EMA50'] = talib.EMA(data['close'], timeperiod=50)
    data['ADX'] = talib.ADX(data['high'], data['low'], data['close'], timeperiod=14)
    data['MACD'], data['Signal'], data['Hist'] = talib.MACD(data['close'], fastperiod=12, slowperiod=26, signalperiod=9)
    data['RSI'] = talib.RSI(data['close'], timeperiod=14)
    data['Upper'], data['Mid'], data['Lower'] = talib.BBANDS(data['close'], nbdevup=2, nbdevdn=2, timeperiod=20)
    data['K'], data['D'] = talib.STOCH(data['high'], data['low'], data['close'].values, fastk_period=9, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
    data['K'].fillna(0,inplace=True)
    data['D'].fillna(0,inplace=True)
    data['J']=3*data['K']-2*data['D']
    data['Willam R'] = talib.WILLR(data['high'], data['low'], data['close'], timeperiod=14)
    data['SAR'] = talib.SAR(data['close'], data['low'], acceleration=0, maximum=0)
    data = data.dropna()
    return data

def TreeModel(Data_np):
    tree_clf = joblib.load('model/Tree_classifier.pkl')
    Prediction = pd.DataFrame(tree_clf.predict(Data_np[:, 13:22]), columns = ['decision'])
    return Prediction

def ResultProcessing(Prediction,Data_np):
    Prediction['time'] = pd.DataFrame(Data_np[:,0:1], columns = ['time'])
    Prediction['close'] = pd.DataFrame(Data_np[:,7:8], columns = ['close'])
    Prediction['datetime'] = pd.to_datetime(Prediction['time'], unit='s')
    Prediction = Prediction.sort_values(by="datetime")
    def Tostr(row):
        if row['decision'] == 1:
            return 'buy' 
        elif row['decision'] == -1:
            return 'Sell'
        elif row['decision'] == 0:
            return 'No decision'
    Prediction['decision'] = Prediction.apply(lambda row: Tostr(row), axis=1)
    result = Prediction.astype(str).to_json(orient="records")
    return json.loads(result)

@app.route('/')
def main():
    Data = GetData()
    Data_np = Data.to_numpy()
    Prediction = TreeModel(Data_np)
    json_reulst = ResultProcessing(Prediction, Data_np)
    print(json_reulst)
    return render_template('crypto.html', data=json_reulst)

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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
