import os
from flask import Flask, render_template, request, flash, redirect, url_for
import requests

from message_push import load_webhook_urls, build_message, send_to_wechat, WEBHOOK_FILE_PATH

app = Flask(__name__)
app.secret_key = 'lightweight_secret_key_for_flash_messages'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        msg_type = request.form.get('type', 'markdown')
        content = request.form.get('content', '')
        mention_all = 'mention_all' in request.form

        if not content.strip():
            flash('消息内容不能为空 / Content cannot be empty.', 'error')
            return redirect(url_for('index'))

        try:
            webhook_urls = load_webhook_urls(str(WEBHOOK_FILE_PATH))
        except Exception as e:
            flash(f'加载 webhook 失败 / Failed to load webhooks: {e}', 'error')
            return redirect(url_for('index'))

        message = build_message(msg_type, content, mention_all)
        
        success_count = 0
        errors = []
        for index, url in enumerate(webhook_urls, start=1):
            try:
                send_to_wechat(message, url, timeout=10.0)
                success_count += 1
            except Exception as e:
                errors.append(f"Webhook {index}: {e}")
                
        if success_count == len(webhook_urls):
            flash(f'成功发送到 {success_count} 个群组 / Successfully sent to {success_count} webhook(s).', 'success')
        elif success_count > 0:
            flash(f'部分发送成功 ({success_count}/{len(webhook_urls)}). 失败原因 / Errors: {", ".join(errors)}', 'warning')
        else:
            flash(f'全部发送失败 / Failed to send. 失败原因 / Errors: {", ".join(errors)}', 'error')
            
        return redirect(url_for('index'))
        
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
