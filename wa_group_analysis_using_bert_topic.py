# -*- coding: utf-8 -*-
"""WA Group Analysis using Bert Topic.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/18RBa8omChGSeCc84t99P16XNxCH-WUK7

# Project Set-Up
"""

!pip install chart_studio
!pip install emoji
!pip install emot
!pip install os
!pip install re
!pip install stylecloud
!pip install bertopic
!pip install emosent-py
!pip install whatstk

import chart_studio, emoji, emot, os, re, stylecloud

import chart_studio.plotly as py
import pandas as pd
import plotly.graph_objs as go
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
from wordcloud import WordCloud, STOPWORDS
import urllib.request

from bertopic import BERTopic
from collections import Counter
from datetime import timedelta
from emosent import get_emoji_sentiment_rank
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from plotly.subplots import make_subplots
from umap import UMAP
from whatstk import WhatsAppChat, FigureBuilder

"""# Data Preparation"""

# URL of the raw file on GitHub
github_raw_url = ["https://raw.githubusercontent.com/Phaqh/files/main/WhatsApp%20Chat%20with%20CS%20UGM%2022%20Survivor.txt",
                  "https://raw.githubusercontent.com/nasalsabila/kamus-alay/master/colloquial-indonesian-lexicon.csv",
                  "https://raw.githubusercontent.com/masdevid/ID-Stopwords/d5e6774a7562d314495017af0064fdb9c7b7a5bb/id.stopwords.02.01.2016.txt"]

# Destination file path where you want to save the downloaded file
destination_path = ["wagcs22.txt",
                    "lcolloquial-indonesian-lexicon.csv",
                    "id.stopwords.02.01.2016.txt"]

# Download the file from GitHub
for i in range(len(github_raw_url)):
  urllib.request.urlretrieve(github_raw_url[i], destination_path[i])

chat = WhatsAppChat.from_source(filepath='/content/wagcs22.txt', hformat='%d.%m.%y, %H:%M - %name:').df

"""# Data Cleaning
- menghapus "< media omitted >"
- menghapus "this message was deleted"
- menghapus baris kosong
- menghapus link http
- menghapus sequence angka-angka
- spasi berulang
- menghapus non-alphanumeric
- menghapus karakter berulang seperti "mauuu" menjadi "mau"
- merubah menjadi huruf lowercase
"""

# def clean_text(text):
#     text = text.replace('<Media omitted>', '').replace('This message was deleted', '').replace('<Media tidak disertakan>', '').replace('\n', ' ').strip()
#     text = re.sub(r'http\S+', '', text)
#     text = re.sub(r'[0-9]+','', text)
#     text = re.sub(r'\s+',' ', text)
#     text = re.sub(r'[^\w\s]|_', '', text)
#     text = re.sub(r'([a-zA-Z])\1\1','\\1', text)
#     return text.lower()

def clean_text(text):
    # Remove emojis
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002500-\U00002BEF"  # chinese char
                               u"\U00002702-\U000027B0"
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               u"\U0001f926-\U0001f937"
                               u"\U00010000-\U0010ffff"
                               u"\u2640-\u2642"
                               u"\u2600-\u2B55"
                               u"\u200d"
                               u"\u23cf"
                               u"\u23e9"
                               u"\u231a"
                               u"\ufe0f"  # dingbats
                               u"\u3030"
                               "]+", flags=re.UNICODE)
    text = emoji_pattern.sub(r'', text)

    # Remove emoticons
    text = re.sub(r'(?::|;|=)(?:-)?(?:\)|\(|D|P)', '', text)

    # Remove other unwanted characters and normalize spaces
    text = text.replace('<Media omitted>', '').replace('This message was deleted', '').replace('\n', ' ').strip()
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'[0-9]+','', text)
    text = re.sub(r'\s+',' ', text)
    text = re.sub(r'[^\w\s]|_', '', text)
    text = re.sub(r'([a-zA-Z])\1\1','\\1', text)

    return text.lower()

chat['clean_msg'] = chat['message'].apply(clean_text)

# replace slang words with their formal equivalents
lexicon_df = pd.read_csv('/content/lcolloquial-indonesian-lexicon.csv')
lexicon_dict = dict(zip(lexicon_df.slang, lexicon_df.formal))
chat['clean_msg'] = chat['clean_msg'].apply(lambda x: ' '.join([lexicon_dict.get(word, word) for word in x.split()]))

# remove stop words
with open('/content/id.stopwords.02.01.2016.txt', 'r') as f:
    stop_words = f.read().splitlines()
chat['clean_msg'] = chat['clean_msg'].apply(lambda x: ' '.join([word for word in x.split() if word not in stop_words]))




chat.sample(10)

"""# Exploratory Data Analysis
Kami akan melakukan EDA mengenai User Teraktif, Waktu Aktif, Bulan Aktif, dan Kata yang sering dipakai dalam chat WhatsApp grup CS.

# User teraktif
"""

chat_cleaned = chat[['date', 'username', 'clean_msg']]
chat_cleaned = chat_cleaned[chat_cleaned['clean_msg'] != '']

# Orang yang chat terbanyak
most_user = chat_cleaned.groupby('username').size().sort_values(ascending=False).reset_index(name='Number_of_messages')

# Creating the bar chart
plt.figure(figsize=(10, 6))
plt.bar(most_user['username'].head(5), most_user['Number_of_messages'].head(5), color='skyblue')
plt.xlabel('Usernames')
plt.ylabel('Number of Messages')
plt.title('Number of Messages per User (Top 5)')
plt.xticks(rotation=45, ha='right')  # Rotate x-axis labels for better readability
plt.tight_layout()  # Adjust layout to prevent clipping of labels
plt.show()

"""# Waktu Aktif"""

wa_hours = chat_cleaned
wa_hours['number_of_message'] = [1] * wa_hours.shape[0]
wa_hours['hours'] = wa_hours['date'].apply(lambda x: x.hour)
wa_hours = wa_hours.groupby('hours').count().reset_index().sort_values(by = 'hours')
wa_hours

#Create the formatting of the graph
matplotlib.rcParams['font.size'] = 20
matplotlib.rcParams['figure.figsize'] = (20, 8)


# Using the seaborn style
sns.set_style("darkgrid")

plt.title('Most active hour in whatsapps');
sns.barplot(x = wa_hours.hours, y = wa_hours.number_of_message,data = wa_hours,dodge=False)

"""# Bulan Aktif"""

months_active = chat_cleaned
months_active['number_of_message'] = [1] * months_active.shape[0]
months_active['month'] = months_active['date'].apply(lambda x: x.month)

months_active = months_active.groupby('month').count().reset_index().sort_values(by = 'month')
months_active[['month', 'number_of_message']]

matplotlib.rcParams['font.size'] = 12
matplotlib.rcParams['figure.figsize'] = (12, 9)
matplotlib.rcParams['figure.facecolor'] = '#00000000'
fig, ax = plt.subplots()

#Creating a bar chart
sns.barplot(x=months_active.month,y=months_active.number_of_message ,hue='month',data=months_active,dodge=False,palette="pastel")
plt.title("Month that have the highest messages and the busiest month?")

"""# Kata yang Sering dipakai"""

#stop words
stopwords_id = pd.read_csv('id.stopwords.02.01.2016.txt', sep=" ", header=None)
stopwords_id.head()

word = " ".join(review for review in chat_cleaned.clean_msg)
stopwords = set(STOPWORDS)
stopwords = stopwords.union(stopwords_id[0])
wordcloud = WordCloud(width = 500, height =500 ,stopwords=stopwords, background_color="black",min_font_size = 10).generate(word)
wordcloud.to_image()

"""# Topic Modelling
Bert Topic
"""

model = BERTopic(umap_model=UMAP(n_neighbors=15,
                                 n_components=5,
                                 min_dist=0.0,
                                 metric='cosine',
                                 random_state=13),
                 language='multilingual',
                 calculate_probabilities=True,
                 nr_topics='auto')

topics, probabilities = model.fit_transform(
    list(chat[chat.clean_msg != ''].assign(
    message=chat.message.str.replace(re.compile(r'http\S+'), ''))['message'].values))

model.get_topic_info()

fig = model.visualize_barchart(top_n_topics=12, title='')
fig.show()

fig = model.visualize_term_rank(title='')
fig.show()

fig = model.visualize_topics(title='')
fig.show()

fig = model.visualize_hierarchy(title='')
fig.show()

sample = chat[(chat.message != '<Media omitted>') & (chat.clean_msg != '')].assign(
    message=chat.message.str.replace(re.compile(r'http\S+'), '')).reset_index().sample()
print('Sample message:', (sample['message'].iloc[0]))

fig = model.visualize_distribution(probabilities[sample['message'].index[0]], title='')
fig.show()

