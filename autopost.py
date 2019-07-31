import praw
import prawcore
import arrow
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
import os
import traceback
import logging

import prodconf
from pytz import utc

logger = logging.getLogger("sgp-bot.main")
formatStr='%(process)d - %(asctime)s - %(name)s - %(levelname)s - %(message)s'


tz = 'America/Los_Angeles'

class Sidebar():
    def __init__(self):
        self.contents = {}

    def add(self, title, url):
        self.contents[title] = url

    def make(self):
        parts = ["Weekly and monthly posts"]
        for title in sorted(self.contents.keys()):
            parts.append("[%s](%s)"%(title, self.contents[title]))

        return parts

sidebar = Sidebar()

class Helper():

    def __init__(self, debug=False):
        self.reddit = praw.Reddit(**prodconf.BOT_CONF)
        self.sub = self.reddit.subreddit("SuperGreatParents")
        self.debug = debug

        if self.debug:

            if not os.path.exists("logs"):
                os.makedirs("logs")
            
            logger.setLevel(logging.DEBUG)
            logging.basicConfig(filename="logs/out.log", format=formatStr)

        else:
            logPath = os.path.join(prodconf.DIR_PATH, "logs")
            if not os.path.exists(logPath):
                os.makedirs(logPath)

            logger.setLevel(logging.INFO)
            logging.basicConfig(filename=os.path.join(logPath, "out.log"), format=formatStr)

    def submit(self, title, text):
        if self.debug:
            logger.debug("Would submit %s here"%title)
            class Mock():
                pass
            mock = Mock()
            mock.url = "FAKEURL"
            return mock
        else:
            logger.info("Submitting post with title %s"%title)
            return self.sub.submit(title, selftext=text, send_replies=False)

    def updateSidebar(self, bar):
        if self.debug:
            logger.debug("Would change sidebar here")
        else:
            self.sub.mod.update(description="\n\n".join(bar.make()))


    def postDaily(self):
        try:
            now = arrow.now(tz)


            which = "First" if now.hour < 12 else "Second"

            title = "{} general discussion for {}".format(which, arrow.now().format("MMMM D, YYYY"))
            text = "Talk about whatever you want here, baby related or not. Anything goes as long as you don't break the rules!"

            self.submit(title, text)
        except Exception as ex:
            logging.exception("Couldn't submit a daily post")

    def postWeekly(self, params):
        try:
            sub = self.submit(params.title, params.text)

            if sub:
                sidebar.add(params.title, sub.url)
                self.updateSidebar(sidebar)

        except Exception as ex:
            logging.exception("Couldn't submit a weekly post")

def beginJobService(rHelper):
    logger.info("Starting up")

    if rHelper.debug:
        dbName = 'jobs.sqlite'
    else:
        dbName = os.path.join(prodconf.DIR_PATH, "jobs.sqlite")

    logger.debug("DBPATH: %s"%dbName)

    jobstores = {
        'default': SQLAlchemyJobStore(url='sqlite:///%s'%dbName)
    }

    firstTrigger = CronTrigger(hour=22, minute=5)
    secondTrigger = CronTrigger(hour=10, minute=5)

    sched = BlockingScheduler(jobstores=jobstores)
    sched.add_job(rHelper.postDaily, trigger=firstTrigger)
    sched.add_job(rHelper.postDaily, trigger=secondTrigger)

    for w in weeklies:
        sched.add_job(rHelper.postWeekly, trigger=w.trigger, args=[w])

    try:
        logger.info("Starting blocking scheduler")
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Removing all jobs in end exception")
        sched.remove_all_jobs()
    finally:
        logger.info("Removing all jobs")
        sched.remove_all_jobs()

class Weekly():
    def __init__(self, title, text, day_of_week=None, day_of_month=None, time=0):
        if not day_of_week and not day_of_month:
            logger.warning("Couldn't schedule %s. No days specified."%title)
            return

        self.dow = day_of_week
        self.dom = day_of_month
        self.title = title
        self.text = text
        self.time = time


        if self.dow:
            if self.dow == "TEST":
                self.trigger = CronTrigger(second=(30 + self.time))
            else:
                self.trigger = CronTrigger(day_of_week=self.dow, hour=self.time, jitter=60, minute=5)
        else:
            self.trigger = CronTrigger(day=self.dom, hour=self.time, jitter=60, minute=5)

weeklies = [
    Weekly("Recipe Share", "Offer and request recipes for ourselves and for children. Also brag about things you've cooked!", day_of_month=10),
    Weekly("Anxiety, Depression, and other Mental Health", """Freely discuss mental health issues, whether it's related to childbirth and parenting or preexisting. May include triggering content, so read at your own discretion. Absolutely no criticizing or shaming is allowed, not that it's allowed in the rest of the sub. If you just need to get something off your chest, end your comment with No Advice Wanted or NAW. Even though we'll never meet in person, we still care about you.""", "wed", time=16),
    Weekly("Feed the Children", """Anything interesting happening with feeding your children? Do they eat everything or nothing. Brag and gripe as you need. Anything related to getting food in your kid's (and your family's) mouths can go here""", "wed"),
    Weekly("Post your Pictures", "Show off your silly, cute kiddos or any other pictures you want", "fri"),
    Weekly("Playing around", "Anything about your children playing. Ideas for activites and games. Places to go. Complaining about gifted toys. Anything goes!", "tue"),
    Weekly("SLEEEEEEP", "If it has to do with sleep, talk about it here. Good sleep, bad sleep, nonexistent sleep. Naps or night sleeps.", "mon", 16),
    Weekly("Development and Milestones", """What has your child been up to lately? What have they learned, what are they doing new? Have they reached a new milestone? Celebrate your children's accomplishments!""", "sun", 12),
    Weekly("Health and Wellness", """We all know this is a code term for weight. So talk about your weight if you need. But also how is your body feeling? Have you started anything new? Have you impressed yourself lately?""", "sat", 12),    
    Weekly("Show off your Stuff", """Have you made anything cool, physical, digital, or otherwise? House decorating or really anything that you've been working towards goes here!""", day_of_month=15),
    Weekly("Tips, Tricks, and Brags", """Have you figured out anything that makes life with your kid easier lately? Want to share, or just brag?""", day_of_month=1),
    Weekly("Book Discussion", """What have you and/or your kids been reading lately? Anything loved or hated? Anything you want to read?""", day_of_month=15),
]

if __name__ == "__main__":
    try:
        beginJobService(Helper())
    except Exception:
        logger.exception("Failed outside of main loop")

