import sys
import configparser
import time

# Azure Translatiopip install azure-ai-translation-textpip install azure-ai-translation-textn
from azure.ai.translation.text import TextTranslationClient
# Azure Text Analytics
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient
# Azure Speech
import os
import azure.cognitiveservices.speech as speechsdk
import librosa
# from azure.ai.translation.text.models import InputTextItem
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

from flask import Flask, request, abort

# Config Parser
config = configparser.ConfigParser()
config.read("config.ini")
# Config Azure Analytics
credential =AzureKeyCredential(config['AzureLanguage']['API_KEY'])
# Azure Speech Settings
speech_config = speechsdk.SpeechConfig(subscription=config['AzureSpeech']['SPEECH_KEY'], 
                                       region=config['AzureSpeech']['SPEECH_REGION'])
audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
UPLOAD_FOLDER = 'static'

# Translator Setup
text_translator = TextTranslationClient(
    credential=AzureKeyCredential(config["AzureTranslator"]["Key"]),
    endpoint=config["AzureTranslator"]["EndPoint"],
    region=config["AzureTranslator"]["Region"],
)

def azure_speech(user_input):
    # The language of the voice that speaks.
    speech_config.speech_synthesis_voice_name = "zh-CN-XiaoxiaoMultilingualNeural"
    file_name = "outputaudio.wav"
    file_config = speechsdk.audio.AudioOutputConfig(filename="static/" + file_name)
    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=file_config
    )

    # Set the style of the voice to excited
    style = "excited"

    # Receives a text from console input and synthesizes it to wave file.
    ssml_user_input = f'''
    <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="zh-CN">
        <voice name="zh-CN-XiaoxiaoMultilingualNeural">
            <mstts:express-as style="{style}" styledegree="2">
                {user_input}
            </mstts:express-as>
        </voice>
    </speak>'''
    
    result = speech_synthesizer.speak_ssml_async(ssml_user_input).get()
    # Check result
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(
            "Speech synthesized for text [{}], and the audio was saved to [{}]".format(
                user_input, file_name
            )
        )
        audio_duration = round(
            librosa.get_duration(path="static/outputaudio.wav") * 1000
        )
        print(audio_duration)
        # wait for the audio file to be created
        time.sleep( 3 )  

        return audio_duration
    
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print("Speech synthesis canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))
    

# if __name__ == "__main__":
    # azure_speech("很高興認識你，我是小小，你可以叫我小小。我是一個聊天機器人，我可以陪你聊天，也可以幫你解決問題。")
    # azure_speech("Nice to meet you, I am Xiaoxiao, you can call me Xiaoxiao. I am a chatbot, I can chat with you, and I can help you solve problems.")
    # azure_speech("こんにちは、私はシャオバです。あなたとチャットできてとても嬉しいです。私はチャットボットで、あなたとチャットすることができます。")