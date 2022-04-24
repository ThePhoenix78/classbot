# coding: utf-8

from discord.ext import commands, tasks
from pdf2image import convert_from_path
from datetime import datetime, date
from discord_slash import SlashCommand
import discord_slash
from RoleManager import RoleManager
from itertools import cycle
from pathlib import Path
import asyncio
import requests
import discord
import os.path
import json
import time
import sys

# await asyncio.sleep(timera)
# client.guilds

bot_version = "3.7.1"
classbot_folder = "classbot_folder"
classbot_config_file = f"{classbot_folder}/classbot_config.json"
plante_verte = f"{classbot_folder}/team_plante_verte.png"
classbot_token = f"{classbot_folder}/classbot_token"
role_folder = f"{classbot_folder}/role_database.json"

edt_database_path = f"{classbot_folder}/edt_database.json"
edt_path = "edt"

programmer = os.path.basename(sys.argv[0])
role_db = RoleManager(role_folder)

vals = [classbot_folder, edt_path]

for name in vals:
    Path(name).mkdir(exist_ok=True)

launch_check_edt = True
bot_token = ""


def get_config():
    return {"edt": launch_check_edt}


try:
    with open(classbot_config_file, "rb") as f:
        bot_config = json.loads(f.read())
        launch_check_edt = bot_config["edt"]
        # launch_check_edt = True

except (FileNotFoundError, KeyError):
    with open(classbot_config_file, "w") as f:
        f.write(json.dumps(get_config(), indent=4))


try:
    with open(classbot_token, "r") as f:
        bot_token = f.readlines()[0].strip()
except FileNotFoundError:
    with open(classbot_token, "w") as f:
        f.write("TOKEN_HERE")
        input("please insert the bot token in the file classbot_token")
        sys.exit(0)


current_semester = "infoS1"
try:
    with open(edt_database_path, "rb") as f:
        liscInfo = json.loads(f.read())[current_semester]

except (FileNotFoundError, KeyError):
    pass


intents = discord.Intents.default()
intents.members = True

client = commands.Bot(intents=intents, command_prefix="?", help_command=None)
client.remove_command('help')
slash = SlashCommand(client, sync_commands=True)

status = cycle(['?edt pour emplois du temps', "Licence Info #1"])


welcome_message = """
Bienvenue {}, dans le serveur de la **Licence info!**
Je t'invite à choisir ta classe dans le salon {}

Si tu as la moindre question, n'hésite pas a demander de l'aide
"""


def get_help(ctx, is_slash: bool = False):
    embed = discord.Embed(title="EDT BOT Commands", description="Préfix : `?`", color=discord.Color.blue())
    embed.set_author(name='Liste des commandes')
    embed.add_field(name="**edt**", value="pour voir son emploi du temps")
    embed.add_field(name="**clear (nombre de massage à retirer)**", value="pour supprimer le dernier message")
    embed.add_field(name="**bin (nombre binaire)**", value="convertir en entier")

    if is_in_staff(ctx, is_slash):
        embed.add_field(name="**addrole (role) (emoji)**", value="à utiliser en réponse à un précédant message, créé un emote pour donner un role")
        embed.add_field(name="**help**", value="pour avoir ce message")
        embed.add_field(name="**reboot**", value="pour restart le bot")
        embed.add_field(name="**removeemote**", value="à utiliser en réponse à un message lié avec addrole pour retirer l'emote")
        embed.add_field(name="**removerole**", value="à utiliser en réponse à un message lié avec addrole pour desactiver")
        embed.add_field(name="**sedt**", value="desactive les notif de changement d'edt")
        embed.add_field(name="**stop**", value="stop le bot")
        embed.add_field(name="**update**", value="update le bot")
        embed.add_field(name="**uptedt (url) (classe)**", value="update l'emploi du temps")
        embed.add_field(name="**version**", value="donne la version du bot")
    # embed.set_image(url=attachment)

    return embed


def convert_time(value: int):
    val3, val2, val = 0, value//60, value % 60
    message = f"{val2}min {val}s."

    if val2 > 60:
        val3, val2 = val2//60, val2 % 60
        message = f"{val3}h {val2}min {val}s."

    return message


def update_edt_database(key, value):
    global liscInfo
    with open(edt_database_path, "rb") as f:
        database = json.loads(f.read())

    val = database[current_semester].get(key)

    if not val:
        return False

    try:
        database[current_semester][key] = value
    except Exception:
        return False

    with open(edt_database_path, "w") as f:
        f.write(json.dumps(database, indent=4))

    liscInfo = database[current_semester]
    return True


def convert_url(url: str = ""):
    if "edtweb2" not in url:
        return False

    current_date = date.isocalendar(datetime.now())
    num_semaine = current_date[1]

    if current_date[2] > 5:
        num_semaine += 1

    temp_url = url.split("edtweb2")[1:].pop(0)
    temp_url = temp_url.split("/")[1:]

    magic = temp_url.pop(0).split(".")
    magic2 = temp_url[0].replace("PDF_EDT_", "")
    magic2 = magic2.split(".pdf")[0].split("_")

    id0 = int(magic.pop(0))
    id1 = int(magic2.pop(0))
    chiffre_temporaire = int(magic2[0])

    temp = int(magic[0])

    if num_semaine - chiffre_temporaire < 0:
        return False

    id2 = chiffre_temporaire - temp

    value = [id0, id1, id2]

    infos = check_edt_info(value)
    try:
        size = infos["Content-Length"]
    except KeyError:
        size = 0
    status = infos["status"]

    if size < 500 or status != 200:
        return False

    return value


def is_dev(ctx):
    if ctx.author.id in (366055261930127360, 649532920599543828):
        return True

    member = ctx.message.author
    roles = [role.name for role in member.roles]
    admins = ["Bot Dev"]

    for role in roles:
        if role in admins:
            return True


def is_in_staff(ctx, direct_author=False):
    if ctx.author.id in (366055261930127360, 649532920599543828):
        return True
    if not direct_author:
        member = ctx.message.author
    else:
        member = ctx.author
    roles = [role.name for role in member.roles]
    admins = ["Admin", "Modo", "Bot Dev"]

    for role in roles:
        if role in admins:
            return True


def is_in_maintenance(ctx):
    if ctx.author.id in (366055261930127360, 649532920599543828):
        return True

    member = ctx.message.author
    roles = [role.name for role in member.roles]
    admins = ["Admin", "Modo", "Bot Dev"]

    for role in roles:
        if role in admins:
            return True

        if "maint." in role:
            return True


@client.event
async def on_ready():
    change_status.start()
    maintenance.start()

    check_edt_lisc.start()

    print("version : ", programmer, bot_version)
    print("Logged in as : ", client.user.name)
    print("ID : ", client.user.id)

    for commu in role_db.get_discords_id():
        try:
            guild = client.get_guild(int(commu))
        except Exception:
            continue
        for channels in role_db.get_channels_id(commu):
            try:
                channel = guild.get_channel(int(channels))
            except Exception:
                continue
            for mess in role_db.get_messages_id(commu, channels):
                try:
                    message = await channel.fetch_message(int(mess))
                except Exception:
                    continue

                for emote in role_db.get_emotes(commu, channels, mess):
                    try:
                        await message.add_reaction(emote)
                    except Exception:
                        continue


@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Please pass in all required arguments')

    elif isinstance(error, commands.CommandOnCooldown):
        value = int(f"{error.retry_after:.0f}")
        message = "Try again in "
        message += convert_time(value)

        em = discord.Embed(title="Slow it down bro!", description=message)
        await ctx.send(embed=em)


timer = time.time()


@client.command(aliases=["tests"])
@commands.check(is_in_staff)
async def test(ctx):
    await ctx.send(":pizza:")


@client.command(aliases=["ver", "ping"])
@commands.check(is_in_staff)
async def version(ctx):
    value = int(time.time()-timer)
    message = convert_time(value)
    final_message = f"version : {bot_version}\nping : {round(client.latency * 1000)}ms :ping_pong:\ntime up : {message}"
    await ctx.send(final_message)


@client.command()
@commands.cooldown(1, 300, commands.BucketType.user)
async def clear(ctx, amount=1):
    if is_in_staff(ctx):
        await ctx.channel.purge(limit=amount+1)
        clear.reset_cooldown(ctx)
    elif amount < 5:
        await ctx.channel.purge(limit=amount+1)
    else:
        await ctx.channel.purge(limit=6)


@client.command(aliases=["bin", "int", "entier"])
async def binaire(ctx, message):
    message = "Error!"
    try:
        message = f"Binaire : {bin(int(message))[2:]}\nEntier : {int(message, 2)}"
    except ValueError:
        message = f"Entier : {int(message, 2)}"

    await ctx.send(message)


@client.command()
@commands.check(is_in_staff)
async def sedt(ctx):
    global launch_check_edt

    val = True
    if launch_check_edt:
        val = False

    launch_check_edt = val

    with open(classbot_config_file, "w") as f:
        f.write(json.dumps(get_config(), indent=4))

    await ctx.channel.send(f"check edt set on : {val}")


@client.command()
@commands.check(is_in_maintenance)
async def uptedt(ctx, url: str, cle_dico: str = ""):
    gestion = "maint."
    val = convert_url(url)

    if not val:
        await ctx.send("`Error! Something went wrong with the url!`")
        return

    member = ctx.message.author
    roles = [role.name for role in member.roles]

    if "Admin" not in roles:
        for role in roles:
            if gestion not in role:
                continue

            role = role.lower().replace(gestion, "").replace(" ", "")

            if role in liscInfo.keys():
                cle_dico = role
                break

    if not cle_dico:
        await ctx.send("`Error! Something went wrong with the role!`")
        return

    check = update_edt_database(cle_dico, val)

    if not check:
        await ctx.send("`Error! Something went wrong with the role!`")
        return

    await ctx.send("`EDT database successfully updated!`")


@client.command()
async def edt(ctx, cle_dico="", plus=""):
    plus = plus.replace("+", "")

    if cle_dico not in liscInfo.keys():
        cle_dico = cle_dico.replace("+", "")
        plus = cle_dico
        cle_dico = ""

    if not cle_dico:
        member = ctx.message.author
        roles = [role.name for role in member.roles]
        for role in roles:
            role = role.lower().replace(" ", "")
            if role in liscInfo.keys():
                cle_dico = role
                break

    pdf_name = f"ask-{cle_dico}.pdf"

    try:
        plus = int(plus)
    except Exception:
        plus = 0

    corrupt = False
    infos = check_edt_info(liscInfo[cle_dico], plus)

    try:
        size = int(infos["Content-Length"])
    except KeyError:
        size = 0

    status = int(infos["status"])

    if (size < 500) or (status != 200):
        pdf_name = f"{cle_dico}.pdf"
        corrupt = True
    else:
        download_edt(pdf_name, liscInfo[cle_dico], plus)

    channel = ctx.channel

    message = f"EDT pour : {cle_dico.upper()}"
    if plus:
        message += f" (+{plus})"

    if corrupt:
        message += "\n`EDT Corrompu! Ceci est une ancienne version!`"

    await channel.send(message)
    await send_edt_to_chat(channel, pdf_name, liscInfo[cle_dico])


@client.command()
async def help(ctx):
    await ctx.send(embed=get_help(ctx, False))


@client.command(aliases=["addmention", "addemoji", "addemote"])
@commands.check(is_in_staff)
async def addrole(ctx, role_: discord.Role, emote):
    try:
        refId = ctx.message.reference.message_id
    except Exception:
        await ctx.channel.send("Erreur! Pas de message lié!")
        return

    try:
        role = role_.name
    except Exception:
        await ctx.channel.send("Erreur! Role inexistant")
        return

    emote = emote

    commu = ctx.guild.id
    chat = ctx.channel.id

    guild_info = client.get_guild(int(commu))
    channel = guild_info.get_channel(int(chat))
    role_message = await channel.fetch_message(int(refId))

    try:
        await role_message.add_reaction(emote)
    except Exception:
        await ctx.channel.send("Erreur! Mauvaise emote!")
        return

    await role_db.bind(commu, chat, refId, emote, role)
    role_db.save(role_db.role_database)

    channel = guild_info.get_channel(int(chat))
    role_message = await channel.fetch_message(ctx.message.id)
    await role_message.add_reaction("✅")
    await ctx.channel.purge(limit=1)


@client.command()
@commands.check(is_in_staff)
async def removerole(ctx, role: discord.Role):

    try:
        refId = ctx.message.reference.message_id
    except Exception:
        await ctx.channel.send("Erreur! Pas de message lié!")
        return

    role_name = role.name
    commu = ctx.guild.id
    chat = ctx.channel.id

    guild_info = client.get_guild(int(commu))

    try:
        role_db.remove_role(commu, chat, refId, role_name)
    except Exception:
        await ctx.channel.send("Erreur! Role inexistant")
        return

    role_db.save(role_db.role_database)

    channel = guild_info.get_channel(int(chat))
    role_message = await channel.fetch_message(ctx.message.id)
    await role_message.add_reaction("✅")
    await ctx.channel.purge(limit=1)


@client.command()
@commands.check(is_in_staff)
async def removeemote(ctx, emote):

    try:
        refId = ctx.message.reference.message_id
    except Exception:
        await ctx.channel.send("Erreur! Pas de message lié!")
        return

    role_name = emote
    commu = ctx.guild.id
    chat = ctx.channel.id

    guild_info = client.get_guild(int(commu))

    try:
        role_db.remove_emote(commu, chat, refId, role_name)
    except Exception:
        await ctx.channel.send("Erreur! Emote inexistant")
        return

    role_db.save(role_db.role_database)

    channel = guild_info.get_channel(int(chat))
    role_message = await channel.fetch_message(ctx.message.id)
    await role_message.add_reaction("✅")
    await ctx.channel.purge(limit=1)


# -------------------------------- SLASH COMMANDE -------------------------------


@slash.slash(name="help", description="liste des commande")
async def help_slash(ctx: discord_slash.SlashContext):
    await ctx.send(embed=get_help(ctx, True), hidden=True)


@slash.slash(name="clear", description="efface les messages")
async def clear_slash(ctx: discord_slash.SlashContext, amount: int = 1):
    if is_in_staff(ctx, True):
        await ctx.channel.purge(limit=amount)
        await ctx.send("Les messages ont bien été retiré.", hidden=True)


@slash.slash(name="addrole", description="liste des commande")
async def addrole_slash(ctx: discord_slash.SlashContext, role_: discord.Role, emote, message_id):
    if not is_in_staff(ctx, True):
        await ctx.send("Vous n'avez pas les permissions pour utiliser cette commande.", hidden=True)
        return

    refId = message_id
    role = role_.name
    commu = ctx.guild.id
    chat = ctx.channel.id

    guild_info = client.get_guild(int(commu))
    channel = guild_info.get_channel(int(chat))
    try:
        role_message = await channel.fetch_message(int(refId))
    except Exception:
        await ctx.send("Erreur! message_id invalide!", hidden=True)

    try:
        await role_message.add_reaction(emote)
    except Exception:
        await ctx.send("Erreur! Mauvaise emote!", hidden=True)
        return

    await role_db.bind(commu, chat, refId, emote, role)
    role_db.save(role_db.role_database)
    await ctx.send(f"{role_} à bien été créé avec l'emote {emote}.", hidden=True)


@slash.slash(name="removerole", description="retire le role")
async def removerole_slash(ctx: discord_slash.SlashContext, role: discord.Role, message_id):
    if not is_in_staff(ctx, True):
        await ctx.send("Vous n'avez pas les permissions pour utiliser cette commande.", hidden=True)
        return

    refId = message_id
    role_name = role.name
    commu = ctx.guild.id
    chat = ctx.channel.id
    guild_info = client.get_guild(int(commu))
    channel = guild_info.get_channel(int(chat))

    try:
        role_message = await channel.fetch_message(int(refId))
    except Exception:
        await ctx.send("Erreur! message_id invalide!", hidden=True)

    try:
        role_db.remove_role(commu, chat, refId, role_name)
    except Exception:
        await ctx.send("Erreur! Role inexistant", hidden=True)
        return

    role_db.save(role_db.role_database)
    await ctx.send(f"{role} à bien été retiré du message.", hidden=True)


@slash.slash(name="removeemote", description="retir l'emote")
async def removeemote_slash(ctx: discord_slash.SlashContext, emote, message_id):
    if not is_in_staff(ctx, True):
        await ctx.send("Vous n'avez pas les permissions pour utiliser cette commande.", hidden=True)
        return

    refId = message_id
    role_name = emote
    commu = ctx.guild.id
    chat = ctx.channel.id
    guild_info = client.get_guild(int(commu))
    channel = guild_info.get_channel(int(chat))

    try:
        role_message = await channel.fetch_message(int(refId))
    except Exception:
        await ctx.send("Erreur! message_id invalide!", hidden=True)

    try:
        await role_message.clear_reaction(emote)
        role_db.remove_emote(commu, chat, refId, role_name)
    except Exception:
        await ctx.send("Erreur! Emote inexistant", hidden=True)
        return

    role_db.save(role_db.role_database)
    await ctx.send(f"{emote} à bien été retiré du message.", hidden=True)


@client.command()
@commands.check(is_in_staff)
async def edtpush(ctx):
    if len(ctx.message.attachments) == 0:
        await ctx.send("Error! No file attached!")
        return

    attachment = ctx.message.attachments[0].url
    name = ctx.message.attachments[0].filename

    if name.lower() in ["liste_de_fichiers"]:
        await ctx.send("Error! Forbidden files!")
        return

    with requests.get(attachment, stream=True) as r:
        pat = f"{edt_path}/{name}"
        with open(pat, 'wb') as fd:
            for chunk in r.iter_content(1000):
                fd.write(chunk)

    await ctx.send(f"File installed at : {pat}")

# --------------------------------- BLOCKCHAIN ---------------------------------


"""
@client.command(aliases=["em"])
async def emb(ctx):
    embed = discord.Embed(title="Your title here", description="Your desc here") #,color=Hex code
    embed.add_field(name="Name", value="you can make as much as fields you like to")
    # embed.set_footer(name="footer") #if you like to
    embed.set_image(url="exampleVariable")  # throws error
    await ctx.send(embed=embed)
"""


# ---------------------------------- EVENTS ------------------------------------


@client.event
async def on_raw_reaction_add(ctx):
    if ctx.user_id == client.user.id:
        return

    message_id = str(ctx.message_id)
    chat_id = ctx.channel_id
    guild_id = ctx.guild_id
    # print(ctx.emoji.name)

    guild = discord.utils.find(lambda g: g.id == guild_id, client.guilds)
    user = await guild.fetch_member(ctx.user_id)

    val = role_db.is_binded_from_emote(guild_id, chat_id, message_id, ctx.emoji.name)

    if val:
        role = discord.utils.get(guild.roles, name=val)
        await user.add_roles(role)


@client.event
async def on_raw_reaction_remove(ctx):
    if ctx.user_id == client.user.id:
        return

    guild_id = ctx.guild_id

    # guild_id = 550450730192994306
    guild = discord.utils.find(lambda g: g.id == guild_id, client.guilds)
    user = await guild.fetch_member(ctx.user_id)

    val = role_db.is_binded_from_emote(guild_id, ctx.channel_id, ctx.message_id, ctx.emoji.name)

    if val:
        role = discord.utils.get(guild.roles, name=val)
        await user.remove_roles(role)


@client.event
async def on_member_join(ctx):
    if ctx.guild.id != 550450730192994306:
        return

    channel = ctx.guild.get_channel(724498186521280573)
    roles = ctx.guild.get_channel(812841349610471444)
    embed = discord.Embed(title="Bienvenu!", description=welcome_message.format(ctx.mention, roles.mention), color=discord.Color.blue())
    # embed.set_author(name='Bienvenu!')
    name = "team_plante_verte.png"
    file = discord.File(plante_verte, filename=name)
    embed.set_image(url=f"attachment://{name}")
    await channel.send(file=file, embed=embed)


@client.event
async def on_member_remove(ctx):
    if ctx.guild.id != 550450730192994306:
        return

    channel = ctx.guild.get_channel(724498186521280573)
    await channel.send(f"Oh non! {ctx.name} nous a quitté!")

# ----------------------------------- EDT ----------------------------------


def compare_edt(pdf_name, indices: list = None, plus: int = 0):
    path_to_pdf = f"{edt_path}/{pdf_name}"

    try:
        poid_old = os.path.getsize(path_to_pdf)
    except Exception:
        poid_old = 0

    infos = check_edt_info(indices, plus)
    try:
        poid_new = int(infos["Content-Length"])
    except KeyError:
        return 5

    # status = infos["status"]

    if poid_old == poid_new and poid_new < 500:
        # même taille et corrompu
        return 5

    elif poid_old == poid_new and poid_new < 2000:
        # même taille et erreur serveur
        return 6

    elif poid_old == poid_new:
        # même taille
        return 2

    elif poid_new < 500:
        # pdf corrompu
        return 3

    elif poid_new < 2000:
        # erreur serveur
        return 4

    return path_to_pdf


def download_edt(pdf_name: str, indices: list = None, plus: int = 0):
    # permet de transfomer la date en compteur du jour dans la semaine
    # et de la semaine dans l'année (retourne l'année, le numéro de semaine et le numéro du jour)
    # utilisé pour les ids du liens pour l'edt
    current_date = date.isocalendar(datetime.now())

    num_semaine = current_date[1]
    annee = current_date[0]

    if current_date[2] > 5:
        num_semaine += 1

    while num_semaine-indices[2] < 0:
        num_semaine += 1

    url_edt = "http://applis.univ-nc.nc/gedfs/edtweb2/{}.{}/PDF_EDT_{}_{}_{}.pdf"
    url = url_edt.format(indices[0], num_semaine - indices[2] + plus, indices[1], num_semaine + plus, annee)

    path_to_pdf = f"{edt_path}/{pdf_name}"
    with requests.get(url, stream=True) as r:
        with open(path_to_pdf, 'wb') as fd:
            for chunk in r.iter_content(1000):
                fd.write(chunk)
    return path_to_pdf


def check_edt_info(indices: list = None, plus: int = 0):
    # permet de transfomer la date en compteur du jour dans la semaine
    # et de la semaine dans l'année (retourne l'année, le numéro de semaine et le numéro du jour)
    # utilisé pour les ids du liens pour l'edt
    current_date = date.isocalendar(datetime.now())

    num_semaine = current_date[1]
    annee = current_date[0]

    if current_date[2] > 5:
        num_semaine += 1

    while num_semaine-indices[2] < 0:
        num_semaine += 1

    url_edt = "http://applis.univ-nc.nc/gedfs/edtweb2/{}.{}/PDF_EDT_{}_{}_{}.pdf"
    url = url_edt.format(indices[0], num_semaine - indices[2] + plus, indices[1], num_semaine + plus, annee)

    edt_info = {}

    val = requests.head(url)
    val.close()

    edt_info = dict(val.headers)
    edt_info["status"] = val.status_code

    return edt_info


async def send_edt_to_chat(channel, pdf_name: str, indices: list = None):
    path_to_pdf = f"{edt_path}/{pdf_name}"
    edt_id = indices[0]

    with open(path_to_pdf, 'rb') as fp:
        await channel.send(file=discord.File(fp, pdf_name))

    pages = convert_from_path(path_to_pdf, 150)

    i = 0
    for page in pages:
        file = f"{edt_path}/edt{edt_id}_{i}.jpg"
        page.save(file, 'JPEG')

        with open(file, 'rb') as fp:
            await channel.send(file=discord.File(fp, file))

        i += 1


async def check_edt_update(pdf_name: str, cle_dico: str, chat_name: str, dico_licence: dict = liscInfo):
    edt_name = compare_edt(pdf_name, dico_licence[cle_dico])
    corrupt = False

    if edt_name in (2, 5, 6):
        return

    elif edt_name in (3, 4):
        corrupt = True
        edt_name = pdf_name
        return
    else:
        download_edt(pdf_name, dico_licence[cle_dico])
    
    servers = client.guilds

    for server in servers:
        chat = server.text_channels
        for channel in chat:
            if chat_name == str(channel):
                formated_role = cle_dico.upper().replace("MIAGE", " miage")
                role = discord.utils.get(server.roles, name=formated_role)
                if corrupt:
                    await channel.send(f"changement d'edt pour : {role.mention} (pdf corrompu, voir sur le site)\n`Ceci est une ancienne version!`")
                else:
                    await channel.send(f"changement d'edt pour : {role.mention}")
                await asyncio.sleep(0.5)
                await send_edt_to_chat(channel, edt_name, dico_licence[cle_dico])
                break


# -------------------------------------- EDT UPDATE ------------------------------


@tasks.loop(seconds=1800)
async def check_edt_lisc():
    if not launch_check_edt:
        return

    this_time = datetime.now()
    role_liste = [
        ["l4t7.pdf", "l4t7", "edt-4"], ["l2t5.pdf", "l2t5", "edt-2"], ["l1t5.pdf", "l1t5", "edt-1"],
        ["l2t7.pdf", "l2t7", "edt-2"], ["l1t7.pdf", "l1t7", "edt-1"], ["l3t5.pdf", "l3t5", "edt-3"],
        ["l3t7.pdf", "l3t7", "edt-3"], ["l3t7miage.pdf", "l3t7miage", "edt-m"], ["l4t7miage.pdf", "l4t7miage", "edt-m"]
    ]

    if not (6 <= this_time.hour <= 22):
        return

    for i in range(len(role_liste)):
        try:
            await check_edt_update(*role_liste[i])
        except Exception:
            pass
        await asyncio.sleep(30)


# ----------------------------COMMANDE MAINTENANCE----------------------------------


@client.command()
@commands.check(is_in_staff)
async def reboot(ctx):
    await client.change_presence(activity=discord.Game("Restarting..."), status=discord.Status.dnd)

    await ctx.send("Restarting bot")
    os.execv(sys.executable, ["None", os.path.basename(sys.argv[0])])


@client.command()
@commands.check(is_in_staff)
async def stop(ctx):
    await ctx.send("Stopping")
    await client.change_presence(activity=discord.Game("Shutting down..."), status=discord.Status.dnd)
    exit(1)
    quit()


@client.command(aliases=["upt"])
@commands.check(is_dev)
async def update(ctx, *, ipe=programmer):
    await ctx.send("updating code")
    await client.change_presence(activity=discord.Game("Updating..."), status=discord.Status.idle)

    val = os.system(f"update.pyw {ipe} key=classbot")

    await client.change_presence(activity=discord.Game("Licence info go!"), status=discord.Status.online)

    if val:
        await ctx.send("Done")
        return

    await ctx.send("Error!")


# -------------------------------------- TASKS -----------------------------------


@tasks.loop(seconds=127)
async def change_status():
    await client.change_presence(activity=discord.Game(next(status)))


resetSystem = False


@tasks.loop(seconds=43201)
async def maintenance():
    global resetSystem
    if resetSystem:
        await client.change_presence(activity=discord.Game("Restarting..."), status=discord.Status.idle)
        os.execv(sys.executable, ["None", os.path.basename(sys.argv[0])])

    resetSystem = True

client.run(bot_token)
