import sys
import configparser
import os, tempfile
import uuid
import shutil
import whisper
import json
import random

whisper_model = whisper.load_model("base")

# Gemini API SDK
import google.generativeai as genai

# import PIL
import PIL

# import my access_azure_storage
import access_azure_storage as aas
# import my sentiment_analysis
import sentiment_analysis as sa
# import my sentiment_score
import sentiment_score as ss
# import my azure_text_to_speech
import azure_text_to_speech as tts

from flask import Flask, request, abort,render_template
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    ImageMessageContent,
    AudioMessageContent,
    StickerMessageContent
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    MessagingApiBlob,
    ReplyMessageRequest,
    TextMessage,
    StickerMessage,
    ImageMessage,
    MessageAction,
    ConfirmTemplate,
    TemplateMessage,
    AudioMessage
)


#Config Parser
config = configparser.ConfigParser()
config.read('config.ini')

# Gemini API Settings
genai.configure(api_key=config["Gemini"]["API_KEY"])

llm_role_description = """
請根據輸入的語言進行對話。
你是一名心理諮商師，你的任務是幫助人們解決心理困擾，提供他們支持和建議。
你擁有豐富的心理學知識和經驗，並且擅長與人溝通。
你的目標是幫助人們找到解決問題的方法，讓他們能夠過上更健康、快樂的生活。
你將會用聊天的方式回答用戶的問題，並提供他們需要的支持和建議。
不要用條列式回答，而是用連貫的語言來回應用戶的問題。
你可以使用你的專業知識和經驗來幫助他們解決問題，並提供他們需要的支持和建議。

"""

# Use the model
from google.generativeai.types import HarmCategory, HarmBlockThreshold
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-latest",
    safety_settings={
        HarmCategory.HARM_CATEGORY_HARASSMENT:HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH:HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT:HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT:HarmBlockThreshold.BLOCK_NONE,
    },
    generation_config={
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
    },
    system_instruction="請根據輸入的語言進行對話。",
)

model_with_role = genai.GenerativeModel(
    model_name="gemini-1.5-flash-latest",
    safety_settings={
        HarmCategory.HARM_CATEGORY_HARASSMENT:HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH:HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT:HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT:HarmBlockThreshold.BLOCK_NONE,
    },
    generation_config={
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
    },
    system_instruction=llm_role_description,
)

chat = model.start_chat(history=[],enable_automatic_function_calling=True)
chat_with_role = model_with_role.start_chat(history=[],enable_automatic_function_calling=True)

chat_history = []
read_chat_history = False

UPLOAD_FOLDER = "static"

app = Flask(__name__)

channel_access_token = config['Line']['CHANNEL_ACCESS_TOKEN']
channel_secret = config['Line']['CHANNEL_SECRET']
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

handler = WebhookHandler(channel_secret)

configuration = Configuration(
    access_token=channel_access_token
)

is_image_uploaded = False
confirm_delete = False

user_repaly_mode = {}

def update_user_repaly_mode(user_id, mode):
    user_repaly_mode[user_id] = mode

def get_user_repaly_mode(user_id):
    if user_id in user_repaly_mode:
        return user_repaly_mode[user_id]
    else:
        user_repaly_mode[user_id] = 0
        return 0

current_mode = 2
score = -1

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/call_llm", methods=["POST"])
def call_llm():
    if request.method == "POST":
        # print("POST!")
        data = request.form
        # print(data)
        # to_llm = ""
        to_llm = data.get("message", "")
        if len(chat.history) == 0:
            to_llm = llm_role_description + to_llm
        try:
            result = chat.send_message(to_llm)
        except Exception as e:
            print(e)
            return "伺服器錯誤，請稍後再試"
        return result.text.replace("\n", "")

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 處理特殊指令 ("使用翻譯模式", "使用交談模式", "使用諮商師模式", "刪除對話紀錄")
def handle_special_command(event):
    global current_mode
    global chat_history
    global read_chat_history
    global confirm_delete
    command = event.message.text
    user_id = event.source.user_id

    if command == "使用翻譯模式":
        current_mode = 0
        return "已切換至翻譯模式，請輸入要翻譯的文字。"
    elif command == "使用一般聊天模式":
        current_mode = 1
        return "已切換至一般對話模式，請輸入要對話的文字。"
    elif command == "使用字療師模式":
        current_mode = 2
        return "已切換至字療師模式，請輸入要對話的文字。"
    elif confirm_delete :
        if command == "刪除對話紀錄":
            chat_history = []
            read_chat_history = False
            blob_name = aas.hash_username(user_id)
            aas.delete_blob(blob_name)
            confirm_delete = False
            return "已刪除對話紀錄。"
        else:
            confirm_delete = False
            return "已取消刪除對話紀錄。"
    
    elif command == "刪除對話紀錄":
        if not confirm_delete:
            confirm_delete = True
            return "確定要刪除對話紀錄嗎？請再輸入一次「刪除對話紀錄」確認刪除。"
    elif command == "執行對話分析":
        return "執行對話分析。"
    elif command == "對話分析&使用者":
        return "對話分析&使用者"
    elif command == "對話分析&諮商師":
        return "對話分析&諮商師"
    elif command == "使用文字模式":
        update_user_repaly_mode(user_id, 0)
        return "已切換至文字模式。"
    elif command == "使用語音模式":
        update_user_repaly_mode(user_id, 1)
        return "已切換至語音模式。"
    else:
        return None


@handler.add(MessageEvent, message=TextMessageContent)
def message_text(event):
    global current_mode
    # print event
    # print("event = \n" + json.dumps(event, default=lambda o: o.__dict__, indent=4))
    reply_message = handle_special_command(event)
    cancel_message = False
    if reply_message == "已取消刪除對話紀錄。" :
        cancel_message = True
        reply_message = None
    else:
        cancel_message = False

    used_gemini = False
    if reply_message is None:
        if current_mode == 1:
            # 對話模式 (不使用 llm_role_description)
            reply_message = gemini_llm_sdk(event.source.user_id, event.message.text)
        elif current_mode == 2:
            # 諮商師模式 (使用 llm_role_description)
            reply_message = gemini_llm_sdk(event.source.user_id, event.message.text, role_description = True)
        used_gemini = True
        
    # anaylis the sentiment of the response ， if the response is positive, add a sticker
    add_sticker = False
    if used_gemini:
        response_sentiment = sa.analyze_sentences(reply_message)
        if response_sentiment[0]*0.75 > response_sentiment[2]:
            add_sticker = True
    
    response_message = []

    # anaylis the senitment of chat history
    # ===心情分析=================================================================================
    if reply_message == "執行對話分析。":    
        confirm_template = ConfirmTemplate(
            text='我是誰!',
            actions=[
                MessageAction(label='我是使用者', text='對話分析&使用者'),
                MessageAction(label='我是諮商師', text='對話分析&諮商師')
            ]
        )
        template_message = TemplateMessage(
            alt_text='Confirm alt text',
            template=confirm_template
        )
        response_message.append(template_message)
        reply_message = "請選擇角色"
        

    if reply_message == "對話分析&使用者" or reply_message == "對話分析&諮商師":
        chosen_analyse_user = ""
        if reply_message == "對話分析&使用者":
            chosen_analyse_user = "user"
        elif reply_message == "對話分析&諮商師":
            chosen_analyse_user = "counselor"

        #  download chat history
        aas.download_blob(aas.hash_username(event.source.user_id))
        score = ss.analyze_chat_history()
        
        if(chosen_analyse_user == "user"):
            if score == -1:
                response_message.append(ImageMessage(original_content_url="https://stickershop.line-scdn.net/stickershop/v1/sticker/331531495/android/sticker.png?v=1", 
                                                            preview_image_url="https://stickershop.line-scdn.net/stickershop/v1/sticker/331531495/android/sticker.png?v=1"))
                reply_message = "你的對話紀錄心情分數較低，建議你尋求進一步的幫助!"
            elif score == 0:
                response_message.append(ImageMessage(original_content_url="https://stickershop.line-scdn.net/stickershop/v1/sticker/679140764/android/sticker.png?v=1",
                                                            preview_image_url="https://stickershop.line-scdn.net/stickershop/v1/sticker/679140764/android/sticker.png?v=1"))
                reply_message = "你的對話紀錄心情分數正常，繼續保持!"
            elif score == 1:
                response_message.append(ImageMessage(original_content_url="https://stickershop.line-scdn.net/stickershop/v1/sticker/461285078/android/sticker.png?v=1", 
                                                            preview_image_url="https://stickershop.line-scdn.net/stickershop/v1/sticker/461285078/android/sticker.png?v=1"))
                reply_message = "你的對話紀錄心情分數較高，祝你每天都可以保持好心情!"
            else:
                reply_message = "對話分析失敗。"
        elif(chosen_analyse_user == "counselor"):
            # send image of the sentiment analysis， static/sentiment_pie_chart.png (local)
            url = request.url_root + '/static/sentiment_pie_chart.png'
            url = url.replace("http", "https")
            app.logger.info("url=" + url)
            response_message.append(ImageMessage(originalContentUrl = url, previewImageUrl = url))
            reply_message = "以上是對話紀錄對話分析結果。"

        response_message.append(TextMessage(text=reply_message))

        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=response_message
                )
        )
        return 
    # ===心情分析=================================================================================

    # ===指令回覆訊息=================================================================================
    if used_gemini == False:
        response_message.append(TextMessage(text=reply_message))
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=response_message
                )
        )
        return
    # ===指令回覆訊息=================================================================================

    if get_user_repaly_mode(event.source.user_id) == 0:
        # 文字模式
        if "\n\n" in reply_message:
            # 如果 canlcel_message 為 True ，第一個訊息為"已取消刪除對話紀錄。"，後面的訊息若超過四條則將超出的訊息合併成到第五條中
            if cancel_message:
                response_message.append(TextMessage(text="已取消刪除對話紀錄。"))
                if len(reply_message.split("\n\n")) > 4:
                    response_message.append(TextMessage(text="\n\n".join(reply_message.split("\n\n")[1:4])))
                    add_sticker = False
                else:
                    response_message += [TextMessage(text=reply_message.split("\n\n")[i]) for i in range(1, len(reply_message.split("\n\n")))]
            # 如果分割後的訊息超過五條，則將後面的訊息合併成一條
            elif len(reply_message.split("\n\n")) > 5:
                response_message.append(TextMessage(text="\n\n".join(reply_message.split("\n\n")[1:5])))
                add_sticker = False
            else:
                response_message += [TextMessage(text=reply_message.split("\n\n")[i]) for i in range(1, len(reply_message.split("\n\n")))]
        else:
            if reply_message != "":
                response_message.append(TextMessage(text=reply_message))
    else:
        # 語音模式
        reply_message.replace("*", "")
        audio_duration = tts.azure_speech(reply_message)
        response_message.append(AudioMessage(original_content_url=config["Deploy"]["URL"]+"/static/outputaudio.wav", duration=audio_duration))

    if add_sticker: 
        stickers = [{"package_id":"11539", "sticker_id":"52114110"},
                    {"package_id":"11539", "sticker_id":"52114122"},
                    {"package_id":"11538", "sticker_id":"51626494"},
                    {"package_id":"11537", "sticker_id":"52002734"}]
        random_sticker = random.randint(1, 4)
        response_message.append(StickerMessage(package_id=stickers[random_sticker-1]["package_id"], sticker_id=stickers[random_sticker-1]["sticker_id"]))
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=response_message
                )
            )
        return

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=response_message
            )
        )

@handler.add(MessageEvent, message=ImageMessageContent)
def message_image(event):
    # 清空 static 資料夾中的舊圖片
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

    with ApiClient(configuration) as api_client:
        line_bot_blob_api = MessagingApiBlob(api_client)
        message_content = line_bot_blob_api.get_message_content(
            message_id=event.message.id
        )
        with tempfile.NamedTemporaryFile(
            dir=UPLOAD_FOLDER, prefix="", delete=False
        ) as tf:
            tf.write(message_content)
            tempfile_path = tf.name

    original_file_name = os.path.basename(tempfile_path)
    new_file_name = f"{uuid.uuid4()}.jpg"
    os.replace(
        UPLOAD_FOLDER + "/" + original_file_name,
        UPLOAD_FOLDER + "/" + new_file_name,
    )

    finish_message = "我看到圖片了! 你想要說什麼呢？"

    global is_image_uploaded
    is_image_uploaded = True

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=finish_message)],
            )
        )

@handler.add(MessageEvent, message=AudioMessageContent)
def message_voice(event):

    # 清空 static 資料夾中的舊語音檔
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

    with ApiClient(configuration) as api_client:
        line_bot_blob_api = MessagingApiBlob(api_client)
        message_content = line_bot_blob_api.get_message_content(
            message_id=event.message.id
        )
        with tempfile.NamedTemporaryFile(
            dir=UPLOAD_FOLDER, prefix="", delete=False, suffix=".wav"  # 語音檔案通常是 .m4a 格式
        ) as tf:
            tf.write(message_content)
            tempfile_path = tf.name

    original_file_name = os.path.basename(tempfile_path)
    new_file_name = "audio.wav"
    new_file_path = os.path.join(UPLOAD_FOLDER, new_file_name)
    os.replace(tempfile_path, new_file_path)

    # 等待文件存檔完成
    import time
    time.sleep(2) 

    # 確保文件已經完成存檔後再進行轉錄
    if os.path.exists(new_file_path):
        # 使用 whisper 將語音文件轉換為文本
        transcribed_text = transcribe_audio(new_file_path)
        # print the transcribed text
        print(f"Transcribed Text: {transcribed_text}")

        # 將轉換後的文本保存到 static 文件夾中
        text_file_path = os.path.join(UPLOAD_FOLDER, "transcribed_text.txt")
        with open(text_file_path, "w", encoding="utf-8") as text_file:
            text_file.write(transcribed_text)

    if current_mode == 1:
        # 對話模式 (不使用 llm_role_description)
        reply_message = gemini_llm_sdk(event.source.user_id, transcribed_text)
    elif current_mode == 2:
        # 諮商師模式 (使用 llm_role_description)
        reply_message = gemini_llm_sdk(event.source.user_id, transcribed_text, True)


    # anaylis the sentiment of the response ， if the response is positive, add a sticker
    add_sticker = False
    response_sentiment = sa.analyze_sentences(reply_message)
    if response_sentiment[0] > response_sentiment[2]:
        add_sticker = True
    
    response_message = []

    if get_user_repaly_mode(event.source.user_id) == 0:
        # 文字模式
        if "\n\n" in reply_message:
            # 如果分割後的訊息超過五條，則將後面的訊息合併成一條
            if len(reply_message.split("\n\n")) > 5:
                response_message.append(TextMessage(text="\n\n".join(reply_message.split("\n\n")[1:5])))
                add_sticker = False
            else:
                response_message += [TextMessage(text=reply_message.split("\n\n")[i]) for i in range(1, len(reply_message.split("\n\n")))]
        else:
            if reply_message != "":
                response_message.append(TextMessage(text=reply_message))
    else:
        # 語音模式
        reply_message.replace("*", "")
        audio_duration = tts.azure_speech(reply_message)
        response_message.append(AudioMessage(original_content_url=config["Deploy"]["URL"]+"/static/outputaudio.wav", duration=audio_duration))

    if add_sticker: 
        response_message.append(StickerMessage(package_id="11539", sticker_id="52114110"))
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=response_message
                )
            )
        return
    
        
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_message)]
            )
        )

def transcribe_audio(audio_file_path):
    try:
        # Check if the audio file exists
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        # Load the audio file
        audio = whisper.load_audio(audio_file_path)
        
        # Transcribe the audio file
        result = whisper_model.transcribe(audio, fp16=False)  # Use whisper_model here
        
        # Return the transcribed text
        return result['text']
    except Exception as e:
        print(f"Error transcribing audio file: {e}")
        return "NO TRANSCRIPTION"



def gemini_llm_sdk(user_id, user_input, role_description=False):
    global chat_history
    global read_chat_history
    global is_image_uploaded

    blob_name = aas.hash_username(user_id)
    
    # 下載對話紀錄
    chat_history = aas.get_blob_data(blob_name)
    # print("chat_history: \n" + json.dumps(chat_history, ensure_ascii=False, indent=4))

    try:
        if is_image_uploaded:
            # 如果有圖片則加入圖片進行回答
            image_files = [os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.jpg')]
            images = [PIL.Image.open(image_file) for image_file in image_files]

            if role_description:
                # 將用戶輸入加入對話紀錄
                chat_history.append({
                    'role': 'user',
                    'parts': [{'text': user_input}]
                })
                response = model_with_role.generate_content([user_input] + images)
            else:
                # response = model.generate_content([user_input] + images)
                response = chat.send_message([user_input] + images)

            is_image_uploaded = False
        else:
            # 如果有角色描述，則帶入；否則僅使用用戶輸入進行回答
            if role_description:
                # 將用戶輸入加入對話紀錄
                chat_history.append({
                    'role': 'user',
                    'parts': [{'text': user_input}]
                })
                # print("chat_history: \n" + json.dumps(chat_history, ensure_ascii=False, indent=4))
                response = model_with_role.generate_content(chat_history)
            else:
                # response = model.generate_content(user_input)
                response = chat.send_message(user_input)

        # 去除掉最後的換行符號
        response_text = response.candidates[0].content.parts[0].text.strip()

        if role_description:
            # 將模型的回應加入對話紀錄
            chat_history.append({
                'role': 'model',
                'parts': [{'text': response_text}]
            })
            
            # 將對話紀錄上傳至 Azure Blob Storage
            # 將 chat_history 從 json 轉換為 text 格式
            chat_history = json.dumps(chat_history, ensure_ascii=False, indent=4)
            aas.upload_blob(blob_name, chat_history)

        

        # print usage metadata
        print(f"prompt Token Count: {response.usage_metadata.prompt_token_count}")
        print(f"candidates Token Count: {response.usage_metadata.candidates_token_count}")
        print(f"total Token Count: {response.usage_metadata.total_token_count}")
      
        # print response
        print(f"Question: {user_input}")
        print(f"Answer: {response_text}")
        return response_text
    except Exception as e:
        print(e)
        return "探探故障中。"

if __name__ == "__main__":
    app.run()

