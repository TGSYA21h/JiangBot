from icalendar import Calendar
from discord.ext import commands, tasks
from pathlib import Path
import discord, aiohttp, datetime



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


    """
    Function that runs every 15 minutes, responsible for sending
    updates to the users with new updates.
    """
    @tasks.loop(hours=3)
    async def look_for_updates(self, bot, *args):
        self.bot = bot
        self.url = 'https://schema.mau.se/setup/jsp/SchemaICAL.ics?startDatum=idag&intervallTyp=m&intervallAntal=6&sprak=SV&sokMedAND=true&forklaringar=true&resurser=p.TGSYA21h'
        self.channel = bot.get_channel(881799174763462657)

        # Check if valid URL
        try:
            resp = await CalendarCheck.get_async(self.url)
        except ValueError as valerror:
            return print('Kunde inte koppla upp')
        except Exception as error:
            print('Något fel när kalender skulle hämtas:')
            print(error)

        new_calendar = Calendar.from_ical(resp)

        if not Path('calendar.ics').exists():
            with open('calendar.ics', 'wb') as calendar_file:
                calendar_file.write(new_calendar.to_ical())
                print('calendar sparad till disk')


        with open('calendar.ics', 'r') as calendar_file:
            old_calendar = Calendar.from_ical(calendar_file.read())


        old_calendar_dict = {}
        for event in old_calendar.walk():
            if event.name == 'VEVENT':
                old_calendar_dict[event.get('UID')] = event


        embed=discord.Embed(title="Schemat har ändrats", url="https://schema.mau.se/setup/jsp/Schema.jsp?startDatum=idag&intervallTyp=m&intervallAntal=6&sprak=SV&sokMedAND=true&forklaringar=true&resurser=p.TGSYA21h", description="Här är de senaste ändringarna i schemat.")
        embed.set_thumbnail(url="https://mau.se/siteassets/mau_sv_logotyp.svg")

        for event in new_calendar.walk():
            if event.name == 'VEVENT':

                uid = event.get('UID')
                event_summary = event.get('SUMMARY')

                try:
                    old_DTSTART = old_calendar_dict[uid].get('DTSTART')
                except KeyError:
                    embed.add_field(name="Ny händelse", value=event_summary, inline=False)
                    continue

                new_DTSTART = event.get('DTSTART')
                human_start = datetime.datetime.strptime(str(new_DTSTART.dt), '%Y-%m-%d %H:%M:%S+00:00')

                if new_DTSTART.dt != old_DTSTART.dt:
                    embed.add_field(name=f"Ny starttid: {human_start}", value=event_summary, inline=False)

        if len(embed.fields) > 0:
            await self.channel.send(embed=embed)
            with open('calendar.ics', 'wb') as calendar_file:
                calendar_file.write(new_calendar.to_ical())



    # Do not start looking before the bot has connected to Discord nad is ready.
    @look_for_updates.before_loop
    async def before_looking(self):
        await self.bot.wait_until_ready()
        print("Start looking for updates.")


def setup(bot):
    bot.add_cog(CalendarCheck(bot))
