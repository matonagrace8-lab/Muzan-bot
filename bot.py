```python
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
# CONFIG
# ============================================================

TOKEN = os.getenv("8675798865:AAG2JDi5_zdEeceZobsGIHy9BC4iKw25YqQ")

DB_FILE = "domains.db"
MAX_ENERGY = 100
ATTACK_COOLDOWN = 5

# ============================================================
# DOMAINES
# ============================================================

DOMAINS = [
    {
        "name": "Sanctuaire Démoniaque",
        "character": "Sukuna",
        "emoji": "🔥",
        "power": (15, 27),
        "cost": (8, 16),
        "speech": (
            "Audi me, caeli et terra. "
            "Fines mundi nunc frangantur. "
            "Nulla via effugiendi maneat. "
            "Imperium meum supra omnes terminos surgat. "
            "Silentium cadat, et territorium meum aperiatur."
        ),
    },
    {
        "name": "Sphère de l'Infini",
        "character": "Gojo",
        "emoji": "♾️",
        "power": (17, 29),
        "cost": (10, 18),
        "speech": (
            "Inter finitum et infinitum spatium aperitur. "
            "Omnis motus lente subsistit. "
            "Quod appropinquat, terminum suum amittit. "
            "Quod fugit, ad infinitum redit. "
            "Nunc territorium infinitum aperiatur."
        ),
    },
    {
        "name": "Perfection de Soi",
        "character": "Mahito",
        "emoji": "👁️",
        "power": (14, 25),
        "cost": (8, 15),
        "speech": (
            "Forma mutatur et anima movetur. "
            "Nihil sub sole perpetuum est. "
            "Corpus suam veritatem ostendat. "
            "Forma antiqua cadat, nova forma surgat. "
            "Territorium meum nunc aperiatur."
        ),
    },
    {
        "name": "Cercueil de la Montagne de Fer",
        "character": "Jogo",
        "emoji": "🌋",
        "power": (15, 26),
        "cost": (9, 17),
        "speech": (
            "Ignis ex profundo terrae surgat. "
            "Montes ardeant et caelum rubescat. "
            "Calor meus omnes limites superet. "
            "Sub potestate ignis, terra contremiscat. "
            "Territorium flammarum aperiatur."
        ),
    },
    {
        "name": "Horizon du Captif",
        "character": "Dagon",
        "emoji": "🌊",
        "power": (14, 25),
        "cost": (8, 16),
        "speech": (
            "Oceanus antiquus me vocat. "
            "Undae surgant et caelum tegant. "
            "Profundum sine fine aperiatur. "
            "Terra humana sub undis taceat. "
            "Regnum maris nunc nascatur."
        ),
    },
]

# ============================================================
# DATABASE
# ============================================================

def connect_db():
    return sqlite3.connect(DB_FILE)


def init_db():
    con = connect_db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            energy INTEGER DEFAULT 100,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            xp INTEGER DEFAULT 0,
            last_attack REAL DEFAULT 0,
            PRIMARY KEY(chat_id, user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS battles (
            chat_id INTEGER PRIMARY KEY,
            player1 INTEGER NOT NULL,
            player2 INTEGER NOT NULL DEFAULT 0,
            hp1 INTEGER DEFAULT 100,
            hp2 INTEGER DEFAULT 100,
            turn_user INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1
        )
    """)

    con.commit()
    con.close()


def register_player(chat_id, user):
    con = connect_db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO players
        (chat_id, user_id, name)
        VALUES (?, ?, ?)
        ON CONFLICT(chat_id, user_id)
        DO UPDATE SET name=excluded.name
    """, (chat_id, user.id, user.full_name))

    con.commit()
    con.close()


def get_player(chat_id, user_id):
    con = connect_db()
    cur = con.cursor()

    cur.execute("""
        SELECT energy, wins, losses, likes, xp, last_attack, name
        FROM players
        WHERE chat_id=? AND user_id=?
    """, (chat_id, user_id))

    result = cur.fetchone()
    con.close()

    return result


def change_energy(chat_id, user_id, amount):
    con = connect_db()
    cur = con.cursor()

    cur.execute("""
        UPDATE players
        SET energy=MAX(0, MIN(100, energy + ?))
        WHERE chat_id=? AND user_id=?
    """, (amount, chat_id, user_id))

    con.commit()
    con.close()


def add_result(chat_id, user_id, win=False, like=False, xp=0):
    con = connect_db()
    cur = con.cursor()

    if win:
        cur.execute("""
            UPDATE players
            SET wins=wins+1, xp=xp+?
            WHERE chat_id=? AND user_id=?
        """, (xp, chat_id, user_id))
    else:
        cur.execute("""
            UPDATE players
            SET losses=losses+1, xp=xp+?
            WHERE chat_id=? AND user_id=?
        """, (xp, chat_id, user_id))

    if like:
        cur.execute("""
            UPDATE players
            SET likes=likes+1
            WHERE chat_id=? AND user_id=?
        """, (chat_id, user_id))

    con.commit()
    con.close()


def set_last_attack(chat_id, user_id):
    con = connect_db()
    cur = con.cursor()

    cur.execute("""
        UPDATE players
        SET last_attack=?
        WHERE chat_id=? AND user_id=?
    """, (time.time(), chat_id, user_id))

    con.commit()
    con.close()


def cooldown_remaining(chat_id, user_id):
    data = get_player(chat_id, user_id)

    if not data:
        return 0

    remaining = ATTACK_COOLDOWN - (time.time() - data[5])

    return max(0, remaining)


def get_battle(chat_id):
    con = connect_db()
    cur = con.cursor()

    cur.execute("""
        SELECT player1, player2, hp1, hp2, turn_user, active
        FROM battles
        WHERE chat_id=?
    """, (chat_id,))

    result = cur.fetchone()
    con.close()

    return result


def create_battle(chat_id, player1):
    con = connect_db()
    cur = con.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO battles
        (chat_id, player1, player2, hp1, hp2, turn_user, active)
        VALUES (?, ?, 0, 100, 100, 0, 1)
    """, (chat_id, player1))

    con.commit()
    con.close()


def join_battle(chat_id, player2):
    con = connect_db()
    cur = con.cursor()

    cur.execute("""
        UPDATE battles
        SET player2=?, turn_user=player1
        WHERE chat_id=? AND active=1
    """, (player2, chat_id))

    con.commit()
    con.close()


def update_battle(chat_id, hp1, hp2, turn_user):
    con = connect_db()
    cur = con.cursor()

    cur.execute("""
        UPDATE battles
        SET hp1=?, hp2=?, turn_user=?
        WHERE chat_id=?
    """, (hp1, hp2, turn_user, chat_id))

    con.commit()
    con.close()


def end_battle(chat_id):
    con = connect_db()
    cur = con.cursor()

    cur.execute("""
        UPDATE battles
        SET active=0
        WHERE chat_id=?
    """, (chat_id,))

    con.commit()
    con.close()


# ============================================================
# OUTILS
# ============================================================

def health_bar(value):
    value = max(0, min(100, value))

    full = value // 10
    empty = 10 - full

    return "█" * full + "░" * empty


def energy_bar(value):
    value = max(0, min(100, value))

    full = value // 10
    empty = 10 - full

    return "⚡" * full + "▫️" * empty


def random_domain():
    return random.choice(DOMAINS)


async def get_profile_photo(bot, user_id):
    """
    Récupère la photo de profil accessible au bot.
    """

    try:
        photos = await bot.get_user_profile_photos(
            user_id=user_id,
            limit=1
        )

        if photos.total_count == 0:
            return None

        photo = photos.photos[0][-1]

        telegram_file = await bot.get_file(
            photo.file_id
        )

        path = Path(
            f"profile_{user_id}.jpg"
        )

        await telegram_file.download_to_drive(
            custom_path=path
        )

        return path

    except Exception as error:
        print("Photo non disponible:", error)
        return None


async def send_player_card(
    update,
    context,
    user,
    text
):
    """
    Envoie le message avec la photo du joueur.
    """

    photo = await get_profile_photo(
        context.bot,
        user.id
    )

    try:

        if photo and photo.exists():

            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=InputFile(str(photo)),
                caption=text
            )

            try:
                photo.unlink()
            except Exception:
                pass

        else:

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text
            )

    except Exception as error:

        print("Erreur envoi:", error)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text
        )


async def animate_message(
    message,
    lines,
    delay=0.8
):
    """
    Animation du même message.
    """

    for text in lines:

        try:
            await message.edit_text(text)
        except Exception:
            return

        await asyncio.sleep(delay)


# ============================================================
# START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "⚔️ BATTLE OF DOMAINS ⚔️\n\n"
        "Je suis l'arbitre du territoire.\n\n"
        "Commandes :\n"
        "🔥 /extension_du_territoire\n"
        "⚡ /contre_extension\n"
        "💥 /attaque\n"
        "🔋 /energie\n"
        "📊 /stats\n"
        "🏆 /classement\n"
        "🏳️ /abandonner\n\n"
        "Chaque joueur commence avec 100 énergie."
    )


# ============================================================
# EXTENSION
# ============================================================

async def extension(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in (
        ChatType.GROUP,
        ChatType.SUPERGROUP
    ):
        await update.message.reply_text(
            "⚠️ Cette commande doit être utilisée dans un groupe."
        )
        return

    register_player(chat.id, user)

    battle = get_battle(chat.id)

    if battle and battle[5] == 1:

        await update.message.reply_text(
            "⚔️ Un territoire est déjà ouvert !\n\n"
            "Un autre joueur doit utiliser "
            "/contre_extension"
        )
        return

    create_battle(
        chat.id,
        user.id
    )

    domain = random_domain()

    # Supprime la commande dans le groupe.
    try:
        await update.message.delete()
    except Exception:
        pass

    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ UNE PRÉSENCE APPARAÎT\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 {user.full_name}\n\n"
        f"{domain['emoji']} {domain['character']}\n\n"
        "「領域展開」\n\n"
        f"⚔️ {domain['name']}\n\n"
        "📜 INCANTATION\n\n"
        f"{domain['speech']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔥 TERRITOIRE OUVERT\n\n"
        "🔋 Énergie : 100/100\n"
        "⚔️ Jauge : 100%\n\n"
        "👥 Les autres membres sont spectateurs.\n"
        "⚡ Un adversaire peut utiliser /contre_extension"
    )

    await send_player_card(
        update,
        context,
        user,
        text
    )


# ============================================================
# CONTRE EXTENSION
# ============================================================

async def contre_extension(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in (
        ChatType.GROUP,
        ChatType.SUPERGROUP
    ):
        return

    register_player(chat.id, user)

    battle = get_battle(chat.id)

    if not battle or battle[5] != 1:

        await update.message.reply_text(
            "❌ Aucun territoire ouvert."
        )
        return

    player1, player2, hp1, hp2, turn, active = battle

    if user.id == player1:

        await update.message.reply_text(
            "⚠️ Tu es déjà dans ce territoire."
        )
        return

    if player2 != 0:

        await update.message.reply_text(
            "⚔️ Le territoire possède déjà un adversaire."
        )
        return

    join_battle(
        chat.id,
        user.id
    )

    domain = random_domain()

    try:
        await update.message.delete()
    except Exception:
        pass

    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ CONTRE-EXTENSION\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 {user.full_name}\n\n"
        f"{domain['emoji']} {domain['character']}\n\n"
        "「領域展開」\n\n"
        f"⚔️ {domain['name']}\n\n"
        "📜 INCANTATION\n\n"
        f"{domain['speech']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚔️ DEUX TERRITOIRES SE RENCONTRENT\n\n"
        "🔴 Joueur 1 : 100%\n"
        "🔵 Joueur 2 : 100%\n\n"
        "🔥 Le premier tour commence."
    )

    await send_player_card(
        update,
        context,
        user,
        text
    )


# ============================================================
# ATTAQUE
# ============================================================

async def attaque(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in (
        ChatType.GROUP,
        ChatType.SUPERGROUP
    ):
        return

    battle = get_battle(chat.id)

    if not battle or battle[5] != 1:

        await update.message.reply_text(
            "❌ Aucun combat actif."
        )
        return

    p1, p2, hp1, hp2, turn, active = battle

    if p2 == 0:

        await update.message.reply_text(
            "⏳ Attends qu'un adversaire rejoigne le territoire."
        )
        return

    if user.id not in (p1, p2):

        await update.message.reply_text(
            "👥 Tu es spectateur.\n"
            "Seuls les deux combattants peuvent attaquer."
        )
        return

    if user.id != turn:

        await update.message.reply_text(
            "⏳ Ce n'est pas ton tour."
        )
        return

    remaining = cooldown_remaining(
        chat.id,
        user.id
    )

    if remaining > 0:

        await update.message.reply_text(
            f"⏳ Attends {remaining:.1f} seconde(s)."
        )
        return

    data = get_player(
        chat.id,
        user.id
    )

    energy = data[0]

    if energy < 10:

        await update.message.reply_text(
            "🔋 Ton énergie est insuffisante !\n\n"
            f"{energy_bar(energy)}\n"
            f"{energy}/100"
        )
        return

    set_last_attack(
        chat.id,
        user.id
    )

    domain = random_domain()

    damage = random.randint(
        domain["power"][0],
        domain["power"][1]
    )

    cost = random.randint(
        domain["cost"][0],
        domain["cost"][1]
    )

    # Evite de consommer plus d'énergie que disponible.
    cost = min(cost, energy)

    change_energy(
        chat.id,
        user.id,
        -cost
    )

    # Détermination de la cible.
    if user.id == p1:

        hp2 = max(
            0,
            hp2 - damage
        )

        next_turn = p2

        target_hp = hp2

    else:

        hp1 = max(
            0,
            hp1 - damage
        )

        next_turn = p1

        target_hp = hp1

    update_battle(
        chat.id,
        hp1,
        hp2,
        next_turn
    )

    # Nouvelle énergie.
    new_data = get_player(
        chat.id,
        user.id
    )

    new_energy = new_data[0]

    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💥 ATTAQUE DE {user.full_name.upper()}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📸 {domain['emoji']} {domain['character']}\n"
        f"⚔️ {domain['name']}\n\n"
        "📜 INCANTATION\n\n"
        f"{domain['speech']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💥 PUISSANCE : -{damage}\n"
        f"🔋 ÉNERGIE : -{cost}\n\n"
        f"⚡ Énergie restante : {new_energy}/100\n\n"
        "⚔️ CONFRONTATION\n\n"
        f"🔴 Joueur 1\n"
        f"{health_bar(hp1)} {hp1}%\n\n"
        f"🔵 Joueur 2\n"
        f"{health_bar(hp2)} {hp2}%\n\n"
        f"🎯 Territoire touché : {target_hp}%"
    )

    await send_player_card(
        update,
        context,
        user,
        text
    )

    # ========================================================
    # VICTOIRE
    # ========================================================

    if hp1 <= 0 or hp2 <= 0:

        winner = p1 if hp2 <= 0 else p2
        loser = p2 if winner == p1 else p1

        winner_data = get_player(
            chat.id,
            winner
        )

        winner_name = winner_data[6]

        end_battle(chat.id)

        add_result(
            chat.id,
            winner,
            win=True,
            like=True,
            xp=100
        )

        add_result(
            chat.id,
            loser,
            win=False,
            like=False,
            xp=25
        )

        winner_energy = get_player(
            chat.id,
            winner
        )[0]

        # Récupération photo du gagnant.
        photo = await get_profile_photo(
            context.bot,
            winner
        )

        victory_text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🏆 TERRITOIRE VAINQUEUR\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👑 {winner_name}\n\n"
            "⚔️ SON TERRITOIRE DOMINE !\n\n"
            "💥 Le territoire adverse s'est effondré.\n\n"
            "❤️ LIKE DU BOT : +1\n"
            "⭐ XP : +100\n"
            "🏆 VICTOIRE : +1\n\n"
            f"🔋 Énergie restante : {winner_energy}/100\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🎉 FIN DE LA CONFRONTATION\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )

        if photo:

            try:

                await context.bot.send_photo(
                    chat_id=chat.id,
                    photo=InputFile(str(photo)),
                    caption=victory_text
                )

                photo.unlink()

            except Exception:

                await context.bot.send_message(
                    chat_id=chat.id,
                    text=victory_text
                )

        else:

            await context.bot.send_message(
                chat_id=chat.id,
                text=victory_text
            )


# ============================================================
# ENERGIE
# ============================================================

async def energie(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in (
        ChatType.GROUP,
        ChatType.SUPERGROUP
    ):
        return

    register_player(
        chat.id,
        user
    )

    data = get_player(
        chat.id,
        user.id
    )

    energy = data[0]

    await update.message.reply_text(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔋 ÉNERGIE DU TERRITOIRE\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 {user.full_name}\n\n"
        f"{energy_bar(energy)}\n\n"
        f"⚡ {energy}/100"
    )


# ============================================================
# STATS
# ============================================================

async def stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in (
        ChatType.GROUP,
        ChatType.SUPERGROUP
    ):
        return

    register_player(
        chat.id,
        user
    )

    data = get_player(
        chat.id,
        user.id
    )

    energy, wins, losses, likes, xp, last, name = data

    level = 1 + (xp // 500)

    await update.message.reply_text(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📊 PROFIL DU TERRITOIRE\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 {name}\n"
        f"⭐ Niveau : {level}\n"
        f"✨ XP : {xp}\n"
        f"⚡ Énergie : {energy}/100\n"
        f"🏆 Victoires : {wins}\n"
        f"💀 Défaites : {losses}\n"
        f"❤️ Likes : {likes}\n"
        f"⚔️ Combats : {wins + losses}"
    )


# ============================================================
# CLASSEMENT
# ============================================================

async def classement(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat = update.effective_chat

    if chat.type not in (
        ChatType.GROUP,
        ChatType.SUPERGROUP
    ):
        return

    con = connect_db()
    cur = con.cursor()

    cur.execute("""
        SELECT name, wins, likes, xp
        FROM players
        WHERE chat_id=?
        ORDER BY wins DESC, xp DESC
        LIMIT 10
    """, (chat.id,))

    rows = cur.fetchall()

    con.close()

    if not rows:

        await update.message.reply_text(
            "📊 Aucun joueur enregistré."
        )
        return

    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🏆 CLASSEMENT DU TERRITOIRE\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    medals = [
        "🥇",
        "🥈",
        "🥉",
    ]

    for i, row in enumerate(rows):

        medal = medals[i] if i < 3 else f"{i+1}."

        name, wins, likes, xp = row

        text += (
            f"{medal} {name}\n"
            f"   🏆 {wins} | ❤️ {likes} | ⭐ {xp} XP\n\n"
        )

    await update.message.reply_text(text)


# ============================================================
# ABANDON
# ============================================================

async def abandonner(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat = update.effective_chat
    user = update.effective_user

    battle = get_battle(chat.id)

    if not battle or battle[5] != 1:

        await update.message.reply_text(
            "❌ Aucun combat actif."
        )
        return

    p1, p2, hp1, hp2, turn, active = battle

    if user.id not in (p1, p2):

        await update.message.reply_text(
            "👥 Tu es spectateur."
        )
        return

    opponent = p2 if user.id == p1 else p1

    end_battle(chat.id)

    add_result(
        chat.id,
        user.id,
        win=False,
        xp=0
    )

    if opponent != 0:

        add_result(
            chat.id,
            opponent,
            win=True,
            like=True,
            xp=100
        )

    await update.message.reply_text(
        "🏳️ ABANDON DU TERRITOIRE\n\n"
        f"👤 {user.full_name} quitte le combat.\n\n"
        "🏆 Le territoire adverse remporte la confrontation.\n"
        "❤️ Like du bot : +1 au vainqueur."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if not TOKEN:

        raise RuntimeError(
            "La variable BOT_TOKEN n'est pas configurée."
        )

    init_db()

    application = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler(
            "extension_du_territoire",
            extension
        )
    )

    application.add_handler(
        CommandHandler(
            "contre_extension",
            contre_extension
        )
    )

    application.add_handler(
        CommandHandler(
            "attaque",
            attaque
        )
    )

    application.add_handler(
        CommandHandler(
            "energie",
            energie
        )
    )

    application.add_handler(
        CommandHandler(
            "stats",
            stats
        )
    )

    application.add_handler(
        CommandHandler(
            "classement",
            classement
        )
    )

    application.add_handler(
        CommandHandler(
            "abandonner",
            abandonner
        )
    )

    print("⚔️ BATTLE OF DOMAINS — BOT ONLINE")

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
```
