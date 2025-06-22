import discord
import dotenv
import os
from openai import OpenAI
import csv
import base64

from server import server_thread

dotenv.load_dotenv()

TOKEN = os.environ.get("TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY2")
SERVER1 = os.environ.get("SERVER1")
SERVER2 = os.environ.get("SERVER2")
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
client = discord.Client(intents=intents)

gpt_channel_id = 1265916964258316288
server_list = [SERVER1, SERVER2]

models = [
        "gpt-4o",
        "gpt-4o-mini",
        "o1-preview",
        "o4-mini",
        "gpt-4.1-nano",
        "gpt-4.1"
    ]

def ebigpt(query, channel_id, authorid):
    gptclient = OpenAI(api_key=OPENAI_API_KEY)
    content = query.replace("?", "").replace("？", "")
    model = [m for m in models if query.endswith(m)]

    if model:
        selected_model = model[0]
    else:
        selected_model = "gpt-4.1-nano"

    completion = gptclient.chat.completions.create(
        model=selected_model,
        messages=[
            {"role": "user", "content": content}
            ]
    )
    response = completion.choices[0].message.content
    with open('gptchatlog.csv', 'a') as f:
        writer = csv.writer(f)
        writer.writerow([authorid, channel_id, query, response])
    return response

def ebigpt_thread(query, thread_id, authorid):
    gptclient = OpenAI(api_key=OPENAI_API_KEY)
    c_log = []

    # CSVファイルを開いて、thread_id が一致する行だけを収集
    with open("gptchatlog.csv", newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["thread_id"] == thread_id:
                c_log.append(row)

    content = ""

    if len(c_log) == 0:
        content = query
    elif len(c_log) > 14:
        ans = "一つのスレッドで質問できるのは15回までです！別スレッドでお願いします。"
        return ans
    else:
        content += "以下は一連の会話です。会話を踏まえて、最後の問いに答えてください。最後の問いの答えのみを出力してください。"
        for row in c_log:
            content += "Q:{}".format(row["prompt"])
            content += "A:{}".format(row["response"])
        content += "Q:{}".format(query)
        content += "A:"
        
        model = [m for m in models if query.endswith(m)]

        if model:
            selected_model = model[0]
        else:
            selected_model = "gpt-4.1-nano"

        completion = gptclient.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "user", "content": content}
                ]
        )
        response = completion.choices[0].message.content
        with open('gptchatlog.csv', 'a') as f:
            writer = csv.writer(f)
            writer.writerow([authorid, thread_id, query.replace(" " + selected_model, "").replace("　" + selected_model, ""), response])
        return response

def dalle(query):
    query = query.replace("$DALLE", "")
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.images.generate(
        model="dall-e-3",
        prompt="I NEED to test how the tool works with extremely simple prompts. DO NOT add any detail, just use it AS-IS:" + query,
        size="1024x1024",
        quality="standard",
        n=1,
        response_format="b64_json"
    )
    with open("file.txt", "a") as f:
        print(response, file = f)
    # 画像データを取得
    image_data = response.data[0].b64_json
    img_data = base64.b64decode(image_data)
    
    # 画像を保存
    with open("image.png", "wb") as f:
        f.write(img_data)
    return

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    # サーバー外（DM）なら無視
    if message.guild is None:
        return

    # サーバーID チェック
    if message.guild.id not in server_list:
        await message.channel.send(str(message.guild.id))
        return  # 指定のサーバーID でなければ無視

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

    #gpt
    if message.content.startswith('?') or message.content.startswith('？'):
        ans = ebigpt(message.content, gpt_channel_id, message.author.id)
        await message.reply(ans)
        return
    
    if type(message.channel) is discord.Thread:
        if message.channel.parent.id == gpt_channel_id:
            ans = ebigpt_thread(message.content, message.channel.id, message.author.id)
            await message.reply(ans)

    if message.content.startswith('$DALLE'):
        dalle(message.content)
        await message.reply(file=discord.File('./image.png', filename='image.png'))
        os.remove("image.png")
        os.remove("file.txt")
        return

# Koyeb用 サーバー立ち上げ
server_thread()
client.run(TOKEN)