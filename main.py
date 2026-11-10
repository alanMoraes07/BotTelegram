import os
import requests
from dotenv import load_dotenv

load_dotenv(".env")
TOKEN = os.getenv("TELEGRAM_TOKEN")

HEADERS = {"User-Agent": "TelegramSteamDealsBot/1.0"}

REMOVE_REPLY_KEYBOARD = {
    "remove_keyboard": True
}

def setup_bot_menu():
    url = f"https://api.telegram.org/bot{TOKEN}/setMyCommands"
    commands = {
        "commands": [
            {"command": "ofertas", "description": "Mostra os jogos destaques em oferta"},
            {"command": "busca", "description": "Procura o preço de um jogo específico (ex: /busca Half Life)"}
        ]
    }
    try:
        requests.post(url, json=commands, timeout=5)
    except Exception as e:
        print(f"Erro ao configurar o menu de comandos: {e}")


def get_ofertas_deals(page=0):
    url = "https://www.cheapshark.com/api/1.0/deals"
    params = {"storeID": "1", "onSale": "1", "sortBy": "Reviews", "AAA": "1"}

    return fetch_and_format_deals(url, params, "⭐ **Jogos destaques em Oferta:**", action_prefix="ofertas", page=page, ascending=False)


def search_game(title, page=0):
    url = "https://www.cheapshark.com/api/1.0/deals"
    params = {"storeID": "1", "title": title, "sortBy": "ReviewCount", "desc": "1"}

    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            deals = response.json()
            if not deals:
                return f'Nenhum jogo encontrado com o nome "{title}".', None

            per_page = 5
            start = page * per_page
            end = start + per_page
            current_deals = deals[start:end]

            if not current_deals and page > 0:
                return search_game(title, page - 1)

            text_res = f'🔍 **Resultados para "{title}" - Pág. {page + 1}:**\n\n'
            for deal in current_deals:
                game_title = deal.get("title")
                normal_price = deal.get("normalPrice", "0.00")
                sale_price = deal.get("salePrice", "0.00")
                savings = float(deal.get("savings", 0))
                deal_id = deal.get("dealID")

                text_res += f"🎮 **{game_title}**\n"
                
                if savings > 0:
                    text_res += f"💰 De: ${normal_price} | Por: **${sale_price}** (-{savings:.0f}%)\n"
                else:
                    text_res += f"💰 Preço: **${sale_price}** (Não há desconto no momento)\n"

                if deal_id:
                    text_res += f"🔗 [Ver Oferta na Steam](https://www.cheapshark.com/redirect?dealID={deal_id})\n\n"
                else:
                    text_res += "\n"

            keyboard = []
            row = []
            if page > 0:
                row.append({"text": "⬅️ Anterior", "callback_data": f"busca:{title}:{page - 1}"})
            if end < len(deals):
                row.append({"text": "Próxima ➡️", "callback_data": f"busca:{title}:{page + 1}"})
            if row:
                keyboard.append(row)

            reply_markup = {"inline_keyboard": keyboard} if keyboard else None
            return text_res, reply_markup
        else:
            return f"⚠️ Erro na API de busca (Código HTTP: {response.status_code})", None
    except Exception as e:
        return f"⚠️ Erro de conexão ao buscar o jogo: {str(e)}", None


def fetch_and_format_deals(url, params, header_title, action_prefix, page=0, ascending=False):
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            deals = response.json()
            
            if not deals:
                return "Nenhuma oferta encontrada com esses critérios.", None

            deals = sorted(deals, key=lambda x: float(x.get("savings", 0)), reverse=not ascending)

            per_page = 7
            start = page * per_page
            end = start + per_page
            current_deals = deals[start:end]

            if not current_deals and page > 0:
                return "Fim das ofertas disponíveis.", None

            text_res = f"{header_title} (Pág. {page + 1})\n\n"
            for deal in current_deals:
                title = deal.get("title")
                normal_price = deal.get("normalPrice", "0.00")
                sale_price = deal.get("salePrice", "0.00")
                savings = float(deal.get("savings", 0))
                deal_id = deal.get("dealID")

                text_res += f"🎮 **{title}**\n"
                
                if savings > 0:
                    text_res += f"💰 De: ${normal_price} | Por: **${sale_price}** (-{savings:.0f}%)\n"
                else:
                    text_res += f"💰 Preço: **${sale_price}** (Não há desconto atualmente)\n"

                text_res += f"🔗 [Ver Oferta](https://www.cheapshark.com/redirect?dealID={deal_id})\n\n"

            keyboard = []
            row = []
            if page > 0:
                row.append({"text": "⬅️ Anterior", "callback_data": f"{action_prefix}:{page - 1}"})
            
            if end < len(deals):
                row.append({"text": "Próxima ➡️", "callback_data": f"{action_prefix}:{page + 1}"})
            
            if row:
                keyboard.append(row)

            reply_markup = {"inline_keyboard": keyboard} if keyboard else None
            return text_res, reply_markup
        else:
            return f"⚠️ Erro na API (Código HTTP: {response.status_code})", None
    except Exception as e:
        return f"⚠️ Erro de conexão ao buscar ofertas: {str(e)}", None


def process_message(text):
    text = text.strip()

    if text in ["/ofertas", "/start"]:
        return get_ofertas_deals(page=0)
    elif text.startswith("/busca"):
        query = text.replace("/busca", "").strip()
        if query:
            return search_game(query, page=0)
        return "⚠️ Uso correto: `/busca (Half Life)` (substitua pelo nome do jogo).", None
    else:
        return search_game(text, page=0)


def process_callback(data):
    parts = data.split(":")
    action = parts[0]

    if action == "ofertas":
        page = int(parts[1])
        return get_ofertas_deals(page=page)
    elif action == "busca":
        query = parts[1]
        page = int(parts[2])
        return search_game(query, page=page)
    
    return "Ação desconhecida.", None


def get_latest_update(offset):
    try:
        res = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={offset}&timeout=10", timeout=15
        )
        data = res.json()
        if data.get("result"):
            return data["result"][-1]
    except Exception as e:
        print(f"Erro ao buscar updates: {e}")
    return None


setup_bot_menu()

last_update_id = 0
print("Bot inicializado!")

while True:
    try:
        update = get_latest_update(last_update_id + 1)
        if update:
            update_id = update["update_id"]
            last_update_id = update_id

            chat_id = None
            response_text = ""
            inline_markup = None

            if "message" in update and "text" in update["message"]:
                chat_id = update["message"]["chat"]["id"]
                msg_text = update["message"]["text"]
                
                res = process_message(msg_text)
                if isinstance(res, tuple):
                    response_text, inline_markup = res
                else:
                    response_text = res
                    inline_markup = None

                markup_to_send = inline_markup if inline_markup else REMOVE_REPLY_KEYBOARD

                requests.post(
                    url=f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": response_text,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True,
                        "reply_markup": markup_to_send,
                    },
                    timeout=10,
                )

            elif "callback_query" in update:
                cb = update["callback_query"]
                cb_id = cb["id"]
                chat_id = cb["message"]["chat"]["id"]
                message_id = cb["message"]["message_id"]
                data = cb["data"]

                requests.post(
                    url=f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery",
                    json={"callback_query_id": cb_id},
                    timeout=5,
                )

                response_text, inline_markup = process_callback(data)

                requests.post(
                    url=f"https://api.telegram.org/bot{TOKEN}/editMessageText",
                    json={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "text": response_text,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True,
                        "reply_markup": inline_markup,
                    },
                    timeout=10,
                )
    except Exception as e:
        print(f"Erro no loop principal: {e}")