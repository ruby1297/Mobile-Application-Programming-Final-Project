const chatBox = document.getElementById('chat-box');
        const messageInput = document.getElementById('message-input');
        const imageInput = document.getElementById('image-input');
        let mediaRecorder;
        let audioChunks = [];

        // 發送訊息
        function sendMessage() {
            const messageText = messageInput.value.trim();

            if (messageText) {
                appendMessage('user', messageText);

                // 向 Flask 後端傳送訊息
                $.post("/call_llm", { message: messageText }, function (response) {
                    appendMessage('ai', response);
                }).fail(function () {
                    appendMessage('ai', "伺服器發生錯誤，請稍後再試！");
                });

                messageInput.value = '';
            }

            if (imageInput.files.length > 0) {
                const file = imageInput.files[0];
                const reader = new FileReader();
                reader.onload = () => {
                    appendImage(reader.result);
                    aiReplyWithQRCode();
                };
                reader.readAsDataURL(file);
                imageInput.value = '';
                document.getElementById('file-name').textContent = "";
                document.getElementById('image-input').value = "";
            }
        }

        // 新增文字訊息
        function appendMessage(sender, text) {
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message');
            if (sender === 'user') messageDiv.classList.add('user-message');
            else if (sender === 'ai') messageDiv.classList.add('ai-message');
            messageDiv.textContent = text;
            chatBox.appendChild(messageDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        // 新增圖片訊息
        function appendImage(src) {
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message', 'user-message');
            const img = document.createElement('img');
            img.src = src;
            messageDiv.appendChild(img);
            chatBox.appendChild(messageDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        // 錄音功能
        async function startRecording() {
            const recordBtn = document.getElementById('record-btn');

            if (!mediaRecorder || mediaRecorder.state === 'inactive') {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);

                mediaRecorder.ondataavailable = (event) => {
                    audioChunks.push(event.data);
                };

                mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/mpeg' });
                    const audioUrl = URL.createObjectURL(audioBlob);
                    appendAudio(audioUrl);
                    audioChunks = [];
                    recordBtn.textContent = '開始錄音';
                    // aiReply('audio');
                    aiReplyWithQRCode();
                };

                mediaRecorder.start();
                recordBtn.textContent = '停止錄音';
            } else {
                mediaRecorder.stop();
            }
        }

        // 新增語音訊息
        function appendAudio(src) {
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message', 'user-message');
            const audio = document.createElement('audio');
            audio.controls = true;
            audio.src = src;
            messageDiv.appendChild(audio);
            chatBox.appendChild(messageDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }


        // QR Code
        function aiReplyWithQRCode() {
            appendMessage('ai', "想體驗更完整內容嗎？\n歡迎加入我們的官方帳號！");

            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message', 'ai-message');
            const img = document.createElement('img');
            img.src = '/static/QR_code.png';
            img.style.height = '200px';
            img.style.objectFit = 'contain';
            img.alt = 'QR Code';
            messageDiv.appendChild(img);
            chatBox.appendChild(messageDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        messageInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                sendMessage();
            }
        });

        function updateFileName(input) {
            const fileName = input.files[0] ? input.files[0].name : "未選擇檔案";
            document.getElementById('file-name').textContent = fileName;
        }