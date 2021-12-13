from flask import Flask, render_template, request
import requests
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

@app.route('/')
def home():
    if request.args.get('sentence'):
        text = request.args.get('sentence')
    else:
        text = "there is a shortage of capital, and we need extra financing"
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
        text = "there is a shortage of capital, and we need extra financing"
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
    app.run()