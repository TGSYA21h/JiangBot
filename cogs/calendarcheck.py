from icalendar import Calendar
from discord.ext import commands, tasks
from pathlib import Path
from datetime import datetime, timedelta
import discord, aiohttp, re



class CalendarCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.look_for_updates.start(self.bot)

    async def get_async(url):
        async with aiohttp.ClientSession() as session:
            retry_count = 0
            success = False
            while retry_count < 5 and not success:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    else:
                        retry_count += 1
                        time.sleep(60)
            if retry_count == 5:
                raise ValueError('To many failed connection attempts', retry_count)


    @commands.command()
    async def schema(self, ctx, *args):
        if len(args):
            try:
                number_of_days = int(args[0])
            except Exception as error:
                number_of_days = 1
        else:
            number_of_days = 1

        with open('calendar.ics', 'r', encoding='utf8') as calendar_file:
            old_calendar = Calendar.from_ical(calendar_file.read())

        now = datetime.now()
        last_sunday = []
        for weekday in range(7):
            if datetime(now.year, 3, 31-weekday).weekday() == 6:
                last_sunday.append(datetime(now.year, 3, 31-weekday))

        for weekday in range(7):
            if datetime(now.year, 10, 31-weekday).weekday() == 6:
                last_sunday.append(datetime(now.year, 10, 31-weekday))

        daylight_saving = 2 if last_sunday[0] < now < last_sunday[1] else 1
        time_limit = datetime.strptime(str(datetime.now())[:10], "%Y-%m-%d")
        event_data = []
        first_date = None

        for event in old_calendar.walk():
            if event.name == 'VEVENT':
                f_start = event.get('DTSTART').dt + timedelta(hours=daylight_saving)
                f_end = event.get('DTEND').dt + timedelta(hours=daylight_saving)

                if time_limit.timestamp() > f_start.timestamp():
                    continue
                elif first_date is None:
                    first_date = f_start
                    temp_date = f_start + timedelta(days=number_of_days)
                    last_date = datetime(temp_date.year, temp_date.month, temp_date.day)
                    while last_date.weekday() >= 5:
                        last_date = last_date + timedelta(days=1)
                elif f_start.timestamp() > last_date.timestamp():
                    break

                start = str(f_start)[11:16]
                end = str(f_end)[11:16]
                duration = str(f_end - f_start)[:-3]
                subject = re.search('(?<=^Kurs\.grp: ).*?(?=,)', event.get('SUMMARY'))
                moment = re.search('(?<=Moment: ).*(?= ? Program)', event.get('SUMMARY'))[0]
                location = event.get('LOCATION')

                if not subject:
                    subject = ''
                else:
                    subject = subject[0]

                if not location:
                    location = 'ok??nt'
                else:
                    location = location

                event_data.append({
                    "date":      str(f_start)[:10],
                    "starttime": start,
                    "endtime":   end,
                    "duration":  f'{duration[:-3]}h{duration[-3:]}m',
                    "subject":   subject,
                    "location":  location,
                    "moment":    moment
                })

        if len(event_data) > 0:
            prev_date = None
            embed = None
            saved = None

            for event in event_data:
                if prev_date is None:
                    prev_date = datetime.strptime(event["date"], "%Y-%m-%d")
                    embed=discord.Embed(title=f"Kommande h??ndelser {event['date']}", url="https://schema.mau.se/setup/jsp/Schema.jsp?startDatum=idag&intervallTyp=m&intervallAntal=6&sprak=SV&sokMedAND=true&forklaringar=true&resurser=p.TGSYA21h", color=0xe5032d)
                    embed.set_thumbnail(url="https://mau.se/siteassets/mau_sv_logotyp.svg")
                    if saved is not None:
                        embed.add_field(name=saved["name"], value=saved["value"], inline=False)
                        saved = None

                if prev_date != datetime.strptime(event["date"], "%Y-%m-%d"):
                    await ctx.author.send(embed=embed)
                    prev_date = None
                    embed = None
                    saved = {
                        'name': event['moment'],
                        'value': f'{event["starttime"]}-{event["endtime"]} ({event["duration"]})\n{event["subject"]} - Sal: {event["location"]}'
                    }
                else:
                    embed.add_field(name=f'{event["moment"]}', value=f'{event["starttime"]}-{event["endtime"]} ({event["duration"]})\n{event["subject"]} - Sal: {event["location"]}', inline=False)

            if saved is not None:
                embed=discord.Embed(title=f"Kommande h??ndelser {event['date']}", url="https://schema.mau.se/setup/jsp/Schema.jsp?startDatum=idag&intervallTyp=m&intervallAntal=6&sprak=SV&sokMedAND=true&forklaringar=true&resurser=p.TGSYA21h", color=0xe5032d)
                embed.set_thumbnail(url="https://mau.se/siteassets/mau_sv_logotyp.svg")
                embed.add_field(name=saved["name"], value=saved["value"], inline=False)

            if embed is not None:
                await ctx.author.send(embed=embed)
        else:
            await ctx.author.send("Det finns inget mer p?? schemat. Pinga en admin om detta ??r fel.")



    """
    Function that runs every 15 minutes, responsible for sending
    updates to the users with new updates.
    """
    @tasks.loop(minutes=15)
    async def look_for_updates(self, bot, *args):
        print(f'{datetime.now()}: ------------------------------------------------')
        print(f'{datetime.now()}: Looking for updates.')
        self.bot = bot
        self.url = 'https://schema.mau.se/setup/jsp/SchemaICAL.ics?startDatum=idag&intervallTyp=m&intervallAntal=6&sprak=SV&sokMedAND=true&forklaringar=true&resurser=p.TGSYA21h'
        # Riktiga kanalen
        self.channel = bot.get_channel(881799174763462657)
        # Testkanelen'
        #self.channel = bot.get_channel(882207091887046676)

        # Check if valid URL
        try:
            resp = await CalendarCheck.get_async(self.url)
        except ValueError:
            return print(f'{datetime.now()}: Kunde inte koppla upp')
        except aiohttp.ClientError as error:
            print(f'{datetime.now()}: error: ClientError')
            print(f'{datetime.now()}: {error}')
            return
        except Exception as error:
            print(f'{datetime.now()}: N??got fel n??r kalender skulle h??mtas:')
            print(f'{datetime.now()}: {error}')
            return

        new_calendar = Calendar.from_ical(resp)

        if not Path('calendar.ics').exists():
            with open('calendar.ics', 'wb') as calendar_file:
                calendar_file.write(new_calendar.to_ical())
                print(f'{datetime.now()}: calendar sparad till disk')


        with open('calendar.ics', 'r') as calendar_file:
            old_calendar = Calendar.from_ical(calendar_file.read())


        old_calendar_dict = {}
        for event in old_calendar.walk():
            if event.name == 'VEVENT':
                old_calendar_dict[event.get('UID')] = event


        embeds = []
        embed = None

        for event in new_calendar.walk():
            name = None

            if event.name == 'VEVENT':
                uid = event.get('UID')
                new_DTSTART = event.get('DTSTART')
                human_start = datetime.strptime(str(new_DTSTART.dt), '%Y-%m-%d %H:%M:%S+00:00')

                # Inte ta med saker +30 dagar fram??t
                if new_DTSTART.dt.timestamp() < (datetime.now() + timedelta(days=30)).timestamp():
                    try:
                        old_DTSTART = old_calendar_dict[uid].get('DTSTART')

                        if new_DTSTART.dt != old_DTSTART.dt:
                            print(f'{datetime.now()}: Ny starttid hittad.')
                            name = f"Ny starttid: {human_start}"
                    except KeyError:
                        print(f'{datetime.now()}: Ny h??ndelse hittad.')
                        name = f"Ny h??ndelse ({human_start})"


            if name is not None:
                if embed is None:
                    embed=discord.Embed(title="Schemat har ??ndrats", url="https://schema.mau.se/setup/jsp/Schema.jsp?startDatum=idag&intervallTyp=m&intervallAntal=6&sprak=SV&sokMedAND=true&forklaringar=true&resurser=p.TGSYA21h", description="H??r ??r de senaste ??ndringarna i schemat.", color=0xe5032d)
                    embed.set_thumbnail(url="https://mau.se/siteassets/mau_sv_logotyp.svg")

                course = re.search('(?<=Kurs.grp: ).+?(?=, \d\d?\.?\d hp)', event.get('SUMMARY'))[0]
                summary = re.search('(?<=Moment: ).*(?= ? Program)', event.get('SUMMARY'))[0]
                embed.add_field(name=name, value=f'{course}:\n{summary}', inline=False)


            if embed is not None and len(embed.fields) == 25:
                embeds.append(embed)
                embed = None

        if embed is not None:
            embeds.append(embed)



        if len(embeds) > 0:
            for embed in embeds:
                await self.channel.send(embed=embed)
            print(f'{datetime.now()}: Meddelat p?? discord.')

            with open('calendar.ics', 'wb') as calendar_file:
                calendar_file.write(new_calendar.to_ical())
                print(f'{datetime.now()}: Ny ical filen ??r sparad.')
        else:
            print(f'{datetime.now()}: Inget nytt.')



    # Do not start looking before the bot has connected to Discord nad is ready.
    @look_for_updates.before_loop
    async def before_looking(self):
        await self.bot.wait_until_ready()
        print("Start looking for updates.")


def setup(bot):
    bot.add_cog(CalendarCheck(bot))
