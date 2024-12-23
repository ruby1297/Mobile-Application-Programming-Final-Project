import sys
import configparser
import json
import matplotlib.pyplot as plt

# Azure Text Analytics
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient

from flask import Flask, request, abort


#Config Parser
config = configparser.ConfigParser()
config.read('config.ini')

#Config Azure Analytics
credential = AzureKeyCredential(config['AzureLanguage']['API_KEY'])

def azure_sentiment(user_input):
    text_analytics_client = TextAnalyticsClient(
        endpoint=config['AzureLanguage']['END_POINT'], 
        credential=credential)
    documents = [user_input]
    response = text_analytics_client.analyze_sentiment(
        documents, 
        show_opinion_mining=True,
        language="zh-hant")
    
    docs = [doc for doc in response if not doc.is_error]
    reply = ""
    positive_count = 0
    negative_count = 0
    neutral_count = 0
    score = 0

    for idx, doc in enumerate(docs):
        for sentence in doc.sentences:
            reply += f"句子情緒 : {sentence.sentiment} \n"
            if sentence.sentiment == "positive":
                positive_count += 1
                score += 1
            elif sentence.sentiment == "negative":
                negative_count += 1
                score -= 1
            elif sentence.sentiment == "neutral":
                neutral_count += 1
                score += 0.2

            if sentence.mined_opinions:
                for opinion in sentence.mined_opinions:
                    reply += f"{opinion.target.text} => {sentence.sentiment}\n"
            else:
                reply += f"N/A => {sentence.sentiment}\n"

    # Clamp the score between -20 and 20
    score = max(min(score, 20), -20)
    
    # Round the score to avoid floating point precision issues
    score = round(score, 2)
    return_value = 1
    # Determine the return value based on the score
    if score < -4.0:
        return_value = -1
    elif score > 10.0:
        return_value = 1
    else:
        return_value = 0

    return reply, positive_count, negative_count, neutral_count, score, return_value

def create_pie_chart(positive_count, negative_count, neutral_count):
    labels = 'Positive', 'Negative', 'Neutral'
    sizes = [positive_count, negative_count, neutral_count]
    colors = ['#ff9999','#66b3ff','#99ff99']
    explode = (0.1, 0, 0)  # explode 1st slice

    fig1, ax1 = plt.subplots()
    ax1.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
            shadow=True, startangle=90)
    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

    plt.title('Sentiment Analysis Results')
    plt.savefig('static/sentiment_pie_chart.png')
    plt.close()

def analyze_chat_history():
    with open('chat_history.json', 'r', encoding='utf-8') as file:
        chat_history = json.load(file)

    user_texts = [part['text'] for entry in chat_history if entry['role'] == 'user' for part in entry['parts']]
    
    overall_reply = ""
    total_positive = 0
    total_negative = 0
    total_neutral = 0
    total_score = 0
    final_return_value = 0

    for text in user_texts:
        reply, positive_count, negative_count, neutral_count, score, return_value = azure_sentiment(text)
        overall_reply += reply
        total_positive += positive_count
        total_negative += negative_count
        total_neutral += neutral_count
        total_score += score
    
    if total_score < -5.0:
        final_return_value = -1
    elif total_score > 10.0:
        final_return_value = 1
    else:
        final_return_value = 0

    print("Overall Reply:\n", overall_reply)
    print("Positive Count:", total_positive)
    print("Negative Count:", total_negative)
    print("Neutral Count:", total_neutral)
    print("Total Score:", total_score)
    print("Return Value:", final_return_value)

    create_pie_chart(total_positive, total_negative, total_neutral)
    
    return final_return_value

if __name__ == "__main__":
    analyze_chat_history()