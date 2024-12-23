import sys
import configparser

# Azure Text Analytics
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient

from flask import Flask, request, abort


# Config Parser
config = configparser.ConfigParser()
config.read('config.ini')

# Config Azure Analytics
credential = AzureKeyCredential(config['AzureLanguage']['API_KEY'])

def analyze_sentences(user_input):
    text_analytics_client = TextAnalyticsClient(
        endpoint=config['AzureLanguage']['END_POINT'], 
        credential=credential
    )

    # if input have "\n\n" ignore it
    user_input = user_input.replace("\n\n", "\n")

    # Use analyze_sentiment directly to split and analyze sentences
    response = text_analytics_client.analyze_sentiment(
        [user_input],
        show_opinion_mining=True,
        language="zh-hant"
    )

    # Store the analyzed sentences in a list
    analyzed_sentences = []
    analyzed_sentiment_count = [] # store the count of sentiment analysis (in order of positive, neutral, negative)
    for sentence in response[0].sentences:
        analyzed_sentences.append(sentence.text)

        # Store the analyzed data of count (positive, neutral, negative), setnece.sentiment is a enum
        if sentence.sentiment == "positive":
            analyzed_sentiment_count.append((1, 0, 0))
        elif sentence.sentiment == "neutral":
            analyzed_sentiment_count.append((0, 1, 0))
        elif sentence.sentiment == "negative":
            analyzed_sentiment_count.append((0, 0, 1))
        

        # Print the sentiment analysis results to the terminal
        print(
            f"句子: {sentence.text}\n" +
            f"情緒: {sentence.sentiment}\n" +
            f"信心分數: 正面 {sentence.confidence_scores.positive}, 中性 {sentence.confidence_scores.neutral}, 負面 {sentence.confidence_scores.negative}"
        )

    # sum up the sentiment analysis result
    analyzed_sentiment_count = tuple(map(sum, zip(*analyzed_sentiment_count)))

    # retrun the sentiment analysis results
    return analyzed_sentiment_count
    

# if __name__ == "__main__":
    # sentences = analyze_sentences("喔，聽到你因為午餐想吃的店沒開而感到難過，我理解你的感受。午餐沒吃到想吃的東西，的確會讓人有點沮喪，尤其當你已經期待很久的時候。\n\n可以跟我說說，那家店是什麼樣的店呢？  還有，你為什麼特別想吃那家店的食物呢？  了解這些或許能幫助我更好理解你的感受。")
    # sentences = analyze_sentences("hey, I am happy to see you. It is a good day. what do you want to eat? I am hungry. I was sad because the restaurant I wanted to eat was closed. I understand your feelings. It is a bit frustrating not to eat what you want for lunch, especially when you have been looking forward to it for a long time. Can you tell me, what kind of restaurant is that restaurant? Also, why do you want to eat the food from that restaurant? Understanding these may help me better understand your feelings.")
    # sentences = analyze_sentences("ああ、お昼に食べようと思っていたお店が開いていなくて悲しいそうです、そのお気持ちはわかります。ランチに欲しかったものが手に入らないと、特に長い間楽しみにしていた場合は少しイライラするかもしれません。 \n\nそのお店がどんなお店なのか教えてもらえますか？  また、なぜそのお店の料理を特に食べたいと思うのでしょうか？  これを知ることで、あなたの気持ちをより理解できるかもしれません。")
    # print(sentences)