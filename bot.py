import asyncio
import os
import random
import sqlite3
import time
from pathlib import Path

from telegram import Update, InputFile
from telegram.constants import ChatType
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# ============================================================
# CONFIGURATION
# ============================================================

TOKEN = os.getenv("8675798865:AAG2JDi5_zdEeceZobsGIHy9BC4iKw25YqQ")

DB_FILE = "domains.db"
COOLDOWN = 5

# ============================================================
# DOMAINES
# ============================================================

DOMAINS = [
    {
        "name": "Sanctuaire Démoniaque",
        "character": "Sukuna",
        "emoji": "🔥",
        "power": 22,
        "energy": 20,
        "speech": (
            "Audite vocem meam, o caeli et terra. "
            "Termini mundi nunc franguntur. "
            "Nulla lex, nulla fuga, nulla spes remanet. "
            "Imperium meum super omnia surgit. "
            "Aperiantur portae territorii, "
            "et silentium cadat super eos qui resistunt."
        ),
    },
    {
        "name": "Sphère de l'Infini",
        "character": "Gojo",
        "emoji": "♾️",
        "power": 24,
        "energy": 24,
        "speech": (
            "Inter finitum et infinitum, "
            "spatium sine fine nascitur. "
            "Quod appropinquat, lente subsistit. "
            "Quod fugit, semper manet. "
            "Mens hominis ante infinitatem tremit. "
            "Nunc territorium meum aperitur."
        ),
    },
    {
        "name": "Perfection de Soi",
        "character": "Mahito",
        "emoji": "👁️",
        "power": 19,
        "energy": 18,
        "speech": (
            "Forma mutatur, anima movetur, "
            "et corpus veritatem suam revelat. "
            "Nihil stabile est sub hoc caelo. "
            "Omnis forma potest frangi et renasci. "
            "Territorium meum nunc aperiatur."
        ),
    },
    {
        "name": "Cercueil de la Montagne de Fer",
        "character": "Jogo",
        "emoji": "🌋",
        "power": 21,
        "energy": 21,
        "speech": (
            "Ignis antiquus e profundo terrae surgat. "
            "Montes ardeant et caelum rubescat. "
            "Calor meus omnia claustra superet. "
            "Sub potestate ignis, "
            "nullum refugium permaneat."
        ),
    },
    {
        "name": "Horizon du Captif",
        "character": "Dagon",
        "emoji": "🌊",
        "power": 20,
        "energy": 20,
        "speech": (
            "Oceanus infinitus vocat. "
            "Undae surgant ultra caelum. "
            "Profundum aperitur, "
            "et terra hominum evanescit. "
            "In hoc regno maris, "
            "ego dominor."
        ),
    },
]

# ============================================================
# BASE DE DONNÉES
# ============================================================

def db():
    return sqlite3.connect(DB_FILE)


def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            chat_id INTEGER,
            user_id INTEGER,
            name TEXT,
            energy INTEGER DEFAULT 100,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            PRIMARY KEY(chat_id, user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS battles (
            chat_id INTEGER PRIMARY KEY,
            player1 INTEGER,
            player2 INTEGER,
            hp1 INTEGER DEFAULT 100,
            hp2 INTEGER DEFAULT 100,
            active INTEGER DEFAULT 1,
            turn INTEGER DEFAULT 1
        )
    """)

    con.commit()
    con.close()


def register_player(chat_id, user):
    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO players
        (chat_id, user_id, name, energy)
        VALUES (?, ?, ?, 100)
    """, (
        chat_id,
        user.id,
        user.full_name,
    ))

    con.commit()
    con.close()


def get_player(chat_id, user_id):
    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT energy, wins, losses
        FROM players
        WHERE chat_id=? AND user_id=?
    """, (chat_id, user_id))

    result = cur.fetchone()
    con.close()

    return result


def change_energy(chat_id, user_id, amount):
    con = db()
    cur = con.cursor()

    cur.execute("""
        UPDATE players
        SET energy = MAX(0, MIN(100, energy + ?))
        WHERE chat_id=? AND user_id=?
    """, (amount, chat_id, user_id))

    con.commit()
    con.close()


# ============================================================
# PHOTO DE PROFIL
# ============================================================

async def get_profile_photo(bot, user_id):
    """
    Essaie de récupérer la photo de profil Telegram du joueur.
    Retourne le fichier Telegram ou None.
    """

    try:
        photos = await bot.get_user_profile_photos(
            user_id=user_id,
            limit=1
        )

        if photos.total_count == 0:
            return None

        photo = photos.photos[0][-1]

        file = await bot.get_file(photo.file_id)

        path = f"profile_{user_id}.jpg"

        await file.download_to_drive(path)

        return path

    except Exception as e:
        print("Erreur photo profil:", e)
        return None


# ============================================================
# OUTILS
# ============================================================

def bar(value):
    value = max(0, min(100, value))

    full = value // 10
    empty = 10 - full

    return "█" * full + "░" * empty


def random_domain():
    return random.choice(DOMAINS)


def get_battle(chat_id):
    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT player1, player2, hp1, hp2, active, turn
        FROM battles
        WHERE chat_id=?
    """, (chat_id,))

    result = cur.fetchone()
    con.close()

    return result


def create_battle(chat_id, p1, p2):
    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO battles
        (chat_id, player1, player2, hp1, hp2, active, turn)
        VALUES (?, ?, ?, 100, 100, 1, 1)
    """, (chat_id, p1, p2))

    con.commit()
    con.close()


def update_battle(chat_id, hp1, hp2, turn):
    con = db()
    cur = con.cursor()

    cur.execute("""
        UPDATE battles
        SET hp1=?, hp2=?, turn=?
        WHERE chat_id=?
    """, (hp1, hp2, turn, chat_id))

    con.commit()
    con.close()


def finish_battle(chat_id):
    con = db()
    cur = con.cursor()

    cur.execute("""
        UPDATE battles
        SET active=0
        WHERE chat_id=?
    """, (chat_id,))

    con.commit()
    con.close()


def add_win(chat_id, user_id):
    con = db()
    cur = con.cursor()

    cur.execute("""
        UPDATE players
        SET wins=wins+1
        WHERE chat_id=? AND user_id=?
    """, (chat_id, user_id))

    con.commit()
    con.close()


def add_loss(chat_id, user_id):
    con = db()
    cur = con.cursor()

    cur.execute("""
        UPDATE players
        SET losses=losses+1
        WHERE chat_id=? AND user_id=?
    """, (chat_id, user_id))

    con.commit()
    con.close()


# ============================================================
# COMMANDE /START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "⚔️ BATTLE OF DOMAINS ⚔️\n\n"
        "Bienvenue dans le système de confrontation.\n\n"
        "Commandes :\n"
        "/extension_du_territoire — lancer un domaine\n"
        "/contre_extension — répondre à un domaine\n"
        "/attaque — attaquer\n"
        "/energie — voir son énergie\n"
        "/stats — voir ses statistiques\n"
        "/abandonner — quitter le combat\n\n"
        "⚡ Énergie maximale : 100"
    )


# ============================================================
# EXTENSION DU TERRITOIRE
# ============================================================

async def extension(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.reply_text(
            "⚠️ Les territoires ne peuvent être ouverts que dans un groupe."
        )
        return

    register_player(chat.id, user)

    battle = get_battle(chat.id)

    if battle and battle[4] == 1:
        await message.reply_text(
            "⚔️ Un territoire est déjà actif !\n"
            "Utilise /contre_extension pour répondre."
        )
        return

    domain = random_domain()

    # On crée un combat avec un adversaire temporaire.
    # Le premier joueur devient le challenger.
    create_battle(
        chat.id,
        user.id,
        0
    )

    # Photo du joueur
    photo = await get_profile_photo(
        context.bot,
        user.id
    )

    text = (
        "⚠️ UNE PRÉSENCE ÉTRANGE SE MANIFESTE...\n\n"
        f"👤 {user.full_name}\n\n"
        f"{domain['emoji']} {domain['character']}\n\n"
        f"「領域展開」\n\n"
        f"⚔️ {domain['name']}\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📜 INCANTATION\n\n"
        f"{domain['speech']}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "⚡ TERRITOIRE OUVERT"
    )

    if photo:
        sent = await context.bot.send_photo(
            chat_id=chat.id,
            photo=InputFile(photo),
            caption=text
        )

        try:
            os.remove(photo)
        except:
            pass

    else:
        sent = await context.bot.send_message(
            chat_id=chat.id,
            text=text
        )

    # On rappelle aux spectateurs de ne pas interférer.
    await context.bot.send_message(
        chat_id=chat.id,
        text=(
            "👥 SPECTATEURS\n\n"
            "Le territoire est ouvert.\n"
            "Seul un autre joueur peut répondre avec :\n\n"
            "/contre_extension"
        )
    )


# ============================================================
# CONTRE-EXTENSION
# ============================================================

async def contre_extension(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return

    register_player(chat.id, user)

    battle = get_battle(chat.id)

    if not battle or battle[4] != 1:
        await message.reply_text(
            "❌ Aucun territoire actif."
        )
        return

    player1, player2, hp1, hp2, active, turn = battle

    if player1 == user.id:
        await message.reply_text(
            "⚠️ Tu ne peux pas contre-attaquer ton propre territoire."
        )
        return

    if player2 != 0:
        await message.reply_text(
            "⚔️ Un adversaire a déjà rejoint le combat."
        )
        return

    # Adversaire accepté
    create_battle(
        chat.id,
        player1,
        user.id
    )

    domain = random_domain()

    photo = await get_profile_photo(
        context.bot,
        user.id
    )

    text = (
        "⚡ CONTRE-EXTENSION !\n\n"
        f"👤 {user.full_name}\n\n"
        f"{domain['emoji']} {domain['character']}\n\n"
        "「領域展開」\n\n"
        f"⚔️ {domain['name']}\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📜 INCANTATION\n\n"
        f"{domain['speech']}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔥 DEUX TERRITOIRES S'AFFRONTENT !"
    )

    if photo:

        await context.bot.send_photo(
            chat_id=chat.id,
            photo=InputFile(photo),
            caption=text
        )

        try:
            os.remove(photo)
        except:
            pass

    else:
        await context.bot.send_message(
            chat_id=chat.id,
            text=text
        )

    await context.bot.send_message(
        chat_id=chat.id,
        text=(
            "⚔️ COMBAT COMMENCÉ !\n\n"
            "Les deux combattants peuvent maintenant utiliser :\n"
            "/attaque\n\n"
            "👥 Les autres membres sont spectateurs."
        )
    )


# ============================================================
# ATTAQUE
# ============================================================

async def attaque(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return

    battle = get_battle(chat.id)

    if not battle or battle[4] != 1:
        await message.reply_text(
            "❌ Aucun combat actif."
        )
        return

    p1, p2, hp1, hp2, active, turn = battle

    if user.id not in [p1, p2]:
        await message.reply_text(
            "👥 Tu es spectateur.\n"
            "Seuls les deux combattants peuvent attaquer."
        )
        return

    # Alternance des tours
    current_player = p1 if turn == 1 else p2

    if user.id != current_player:
        await message.reply_text(
            "⏳ Ce n'est pas ton tour."
        )
        return

    player = get_player(chat.id, user.id)

    if not player:
        return

    energy = player[0]

    if energy < 10:
        await message.reply_text(
            "🔋 Énergie insuffisante !\n\n"
            f"Énergie : {energy}/100"
        )
        return

    domain = random_domain()

    # puissance aléatoire
    damage = random.randint(
        max(8, domain["power"] - 7),
        domain["power"] + 5
    )

    energy_cost = random.randint(8, 15)

    change_energy(
        chat.id,
        user.id,
        -energy_cost
    )

    photo = await get_profile_photo(
        context.bot,
        user.id
    )

    if user.id == p1:
        hp2 = max(0, hp2 - damage)
        next_turn = 2
    else:
        hp1 = max(0, hp1 - damage)
        next_turn = 1

    update_battle(
        chat.id,
        hp1,
        hp2,
        next_turn
    )

    text = (
        f"💥 ATTAQUE DE {user.full_name.upper()} !\n\n"
        f"{domain['emoji']} {domain['name']}\n\n"
        "📜 INCANTATIO\n\n"
        f"{domain['speech']}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💥 PUISSANCE : -{damage}\n"
        f"🔋 COÛT : -{energy_cost} énergie\n\n"
        "⚔️ ÉTAT DU TERRITOIRE\n\n"
        f"🔴 Joueur 1\n"
        f"{bar(hp1)} {hp1}%\n\n"
        f"🔵 Joueur 2\n"
        f"{bar(hp2)} {hp2}%"
    )

    if photo:

        await context.bot.send_photo(
            chat_id=chat.id,
            photo=InputFile(photo),
            caption=text
        )

        try:
            os.remove(photo)
        except:
            pass

    else:
        await context.bot.send_message(
            chat_id=chat.id,
            text=text
        )

    # ========================================================
    # FIN DU COMBAT
    # ========================================================

    if hp1 <= 0 or hp2 <= 0:

        winner = p1 if hp2 <= 0 else p2
        loser = p2 if winner == p1 else p1

        add_win(chat.id, winner)
        add_loss(chat.id, loser)

        finish_battle(chat.id)

        winner_data = get_player(
            chat.id,
            winner
        )

        await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "━━━━━━━━━━━━━━━━━━\n"
                "🏆 TERRITOIRE DÉTRUIT\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"👑 VAINQUEUR : {winner_data and winner_data[0] and 'LE COMBATTANT'}\n\n"
                "⚔️ Le territoire adverse s'est effondré.\n"
                "🔥 La confrontation est terminée.\n\n"
                "Utilisez /extension_du_territoire\n"
                "pour commencer un nouveau combat."
            )
        )


# ============================================================
# ÉNERGIE
# ============================================================

async def energie(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return

    register_player(chat.id, user)

    data = get_player(
        chat.id,
        user.id
    )

    energy = data[0]

    await update.message.reply_text(
        f"🔋 ÉNERGIE DE TERRITOIRE\n\n"
        f"👤 {user.full_name}\n\n"
        f"{bar(energy)} {energy}/100"
    )


# ============================================================
# STATS
# ============================================================

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return

    register_player(chat.id, user)

    data = get_player(
        chat.id,
        user.id
    )

    energy, wins, losses = data

    await update.message.reply_text(
        "📊 TES STATISTIQUES\n\n"
        f"👤 {user.full_name}\n"
        f"🔋 Énergie : {energy}/100\n"
        f"🏆 Victoires : {wins}\n"
        f"💀 Défaites : {losses}\n"
        f"⚔️ Combats : {wins + losses}"
    )


# ============================================================
# ABANDON
# ============================================================

async def abandonner(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat = update.effective_chat
    user = update.effective_user

    battle = get_battle(chat.id)

    if not battle or battle[4] != 1:
        await update.message.reply_text(
            "❌ Aucun combat actif."
        )
        return

    p1, p2, hp1, hp2, active, turn = battle

    if user.id not in [p1, p2]:

        await update.message.reply_text(
            "👥 Tu es spectateur."
        )
        return

    opponent = p2 if user.id == p1 else p1

    finish_battle(chat.id)

    add_loss(chat.id, user.id)

    if opponent != 0:
        add_win(chat.id, opponent)

    await update.message.reply_text(
        f"🏳️ {user.full_name} abandonne le territoire.\n\n"
        "🏆 L'adversaire remporte la confrontation."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN n'est pas configuré."
        )

    init_db()

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "extension_du_territoire",
            extension
        )
    )

    app.add_handler(
        CommandHandler(
            "contre_extension",
            contre_extension
        )
    )

    app.add_handler(
        CommandHandler(
            "attaque",
            attaque
        )
    )

    app.add_handler(
        CommandHandler(
            "energie",
            energie
        )
    )

    app.add_handler(
        CommandHandler(
            "stats",
            stats
        )
    )

    app.add_handler(
        CommandHandler(
            "abandonner",
            abandonner
        )
    )

    print("⚔️ BATTLE OF DOMAINS démarré !")

    app.run_polling()


if __name__ == "__main__":
    main()
