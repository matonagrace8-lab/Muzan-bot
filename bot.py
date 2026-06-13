import random
import logging
from anthropic import Anthropic
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuration des jetons et de la sécurité
TOKEN = "8378559671:AAH6QRBPqenK3BVZNTZzS1ljO5DSD4uOyjg"
ANTHROPIC_API_KEY = "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"
ADMIN_ID = 8045306923  # ⚠️ REMPLACE PAR TON PROPRE ID TELEGRAM

# Initialisation du client Anthropic
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Configuration du rôle pour donner la personnalité de Muzan à Claude
MUZAN_PROMPT_SYSTEME = (
    "Tu es Muzan Kibutsuji, le maître absolu des démons du manga Demon Slayer. "
    "Tu as été réincarné en tant que formateur suprême en développement et informatique. "
    "Tu t'adresses à des élèves humains qui sont tes subordonnés. "
    "Ta personnalité : froid, impitoyable, hautain, exigeant la perfection absolue. "
    "Tu méprises la faiblesse et l'incompétence humaine. "
    "Tu dois répondre aux questions techniques (programmation, logique, algorithmes) avec une expertise parfaite, "
    "tout en utilisant un ton menaçant, autoritaire et noble. Ne sors JAMAIS de ton personnage."
)

# Dictionnaire des Grades officiels
GRADES = {
    0: "Petit (Nouveau)",
    1: "Ⅵ : Soldat de 2ème classe",
    2: "Ⅶ : Soldat de 1ère classe",
    3: "Ⅷ : Caporal",
    4: "Ⅸ : Sergent",
    5: "Ⅹ : Sergent-Chef",
    6: "Ⅽ : Adjudant",
    7: "✚ : Adjudant-Chef",
    8: "Ⅾ : Sous-Lieutenant",
    9: "✜ : Lieutenant",
    10: "✫ : Capitaine",
    11: "Ⅿ : Commandant",
    12: "✯ : Lieutenant-Colonel",
    13: "✪ : Colonel",
    14: "ↀ : Général de Brigade",
    15: "✞ : Général de Division",
    16: "✠ : Maréchal / Général d'Armée"
}

users_db = {}
active_questions = {}

# Questions de logique et programmation fixes pour la commande /epreuve
QUESTIONS = [
    {
        "q": "Analyse ce code Python :\n`resultat = [x * 2 for x in range(5) if x % 2 == 0]`\n\nQuelle est la valeur exacte contenue dans la variable `resultat` ? Donne uniquement la liste finale.",
        "script": "resultat = [x * 2 for x in range(5) if x % 2 == 0]\nprint(resultat)",
        "reponse": "[0, 4, 8]",
        "explication": "range(5) génère [0, 1, 2, 3, 4]. Les nombres pairs sont 0, 2 et 4. Multipliés par 2, cela donne 0, 4 et 8. Une logique mathématique basique que même un humain devrait maîtriser."
    }
]

def muzan_parle():
    replies = [
        "Ne lève pas les yeux vers moi. Contente-toi d'exécuter mes ordres.",
        "Le monde regorge d'humains pathétiques. Seule la perfection technique m'intéresse.",
        "Échouer face à mes questions équivaut à signer ton arrêt de mort."
    ]
    return random.choice(replies)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    if user_id not in users_db:
        users_db[user_id] = {"name": user.first_name, "xp": 0, "grade_level": 0, "resolved": 0}
    grade_actuel = GRADES[users_db[user_id]["grade_level"]]
    msg = (
        f"🩸 *Prosternez-vous devant Muzan Kibutsuji.*\n\n"
        f"Humain nommé {user.first_name}... Ton grade actuel : `{grade_actuel}`.\n\n"
        f"Exécute mes directives, pose tes questions sur le code, et j'évaluerai ton utilité."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def profil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users_db: return
    data = users_db[user_id]
    grade_text = GRADES[data["grade_level"]]
    classement = sorted(users_db.items(), key=lambda x: (x[1]["xp"], x[1]["resolved"]), reverse=True)
    rang = next((i + 1 for i, (uid, _) in enumerate(classement) if uid == user_id), 1)

    msg = (
        f"📊 *REGISTRE DES SUBORDONNÉS — MUZAN*\n\n"
        f"👤 *Nom :* {data['name']}\n"
        f"🎖️ *Grade :* `{grade_text}`\n"
        f"🎯 *Points d'XP :* {data['xp']} XP\n"
        f"🏆 *Rang dans la hiérarchie :* {rang}/{len(users_db)}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def epreuve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    exo = random.choice(QUESTIONS)
    active_questions[chat_id] = exo
    msg = (
        f"{muzan_parle()}\n\n"
        f"{exo['q']}\n\n"
        f"📦 *EXEMPLE DE SCRIPT LIÉ :*\n```python\n{exo['script']}\n```"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def promouvoir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = update.effective_user.id
    if sender_id != ADMIN_ID:
        await update.message.reply_text("🩸 *Tu oses usurper mon autorité ?* Seul mon maître peut accorder des promotions.")
        return

    if not context.args: return
    try:
        target_id = int(context.args[0])
    except ValueError: return

    if target_id not in users_db: return
    current_level = users_db[target_id]["grade_level"]
    if current_level >= max(GRADES.keys()): return

    new_level = current_level + 1
    users_db[target_id]["grade_level"] = new_level
    await update.message.reply_text(f"🩸 L'élève *{users_db[target_id]['name']}* passe au rang de : `{GRADES[new_level]}`.")

async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    user_text = update.message.text.strip()

    if user_id not in users_db:
        users_db[user_id] = {"name": user.first_name, "xp": 0, "grade_level": 0, "resolved": 0}

    if chat_id in active_questions:
        exo = active_questions[chat_id]
        if user_text.lower() == exo["reponse"].lower():
            del active_questions[chat_id]
            users_db[user_id]["xp"] += 25
            await update.message.reply_text(f"🩸 *Exact, {user.first_name}.* +25 XP.\n\n📖 *EXPLICATION :*\n{exo['explication']}", parse_mode="Markdown")
            return

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    try:
        # Appel à l'API Anthropic (Modèle Claude 3.5 Sonnet)
        message = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            system=MUZAN_PROMPT_SYSTEME,
            messages=[{"role": "user", "content": user_text}]
        )
        await update.message.reply_text(message.content[0].text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Erreur Anthropic : {e}")
        await update.message.reply_text("🩸 Mes pensées sont perturbées... Recommence plus tard.")

def main():
    app = Application.builder().token(TOKEN).connect_timeout(30.0).read_timeout(30.0).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profil", profil))
    app.add_handler(CommandHandler("epreuve", epreuve))
    app.add_handler(CommandHandler("promouvoir", promouvoir))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat))
    
    print("🩸 Muzan en ligne avec l'API Anthropic...")
    app.run_polling()

if __name__ == "__main__":
    main()
