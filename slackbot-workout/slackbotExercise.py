import csv
import datetime
import json
import os
import os.path
import pickle
import random
import signal
import sys
import time
from random import shuffle

import curl
import requests
from dotenv import load_dotenv

from User import User

load_dotenv()

# Environment variables must be set with your tokens
BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')

HASH = "%23"


# Configuration values to be set in setConfiguration
class Bot:

  def __init__(self):
    self.setConfiguration()

    self.csv_filename = "log" + time.strftime("%Y%m%d-%H%M") + ".csv"
    self.first_run = True

    # local cache of usernames
    # maps userIds to usernames
    self.user_cache = self.loadUserCache()

    # round robin store
    self.user_queue = []

  def loadUserCache(self):
    if os.path.isfile('user_cache.save'):
      with open('user_cache.save', 'rb') as f:
        self.user_cache = pickle.load(f)
        print("Loading " + str(len(self.user_cache)) + " users from cache.")
        return self.user_cache

    return {}

  '''
    Sets the configuration file.

    Runs after every callout so that settings can be changed realtime
    '''

  def setConfiguration(self):
    # Read variables fromt the configuration file
    with open('config.json') as f:
      settings = json.load(f)

      self.team_domain = settings["teamDomain"]
      self.channel_name = settings["channelName"]
      self.channel_id = settings["channelId"]
      self.elite_group_id = settings["eliteGroupId"]
      self.min_countdown = settings["callouts"]["timeBetween"]["minTime"]
      self.max_countdown = settings["callouts"]["timeBetween"]["maxTime"]
      self.num_people_per_callout = settings["callouts"]["numPeople"]
      self.sliding_window_size = settings["callouts"]["slidingWindowSize"]
      self.group_callout_chance = settings["callouts"]["groupCalloutChance"]
      self.elite_callout_chance = settings["callouts"]["eliteCalloutChance"]
      self.exercises = settings["exercises"]
      self.office_hours_on = settings["officeHours"]["on"]
      self.office_hours_begin = settings["officeHours"]["begin"]
      self.office_hours_end = settings["officeHours"]["end"]
      self.exclude_users = settings["excludeUsers"]

      self.debug = settings["debug"]
      self.auth_header = {'Authorization': 'Bearer {}'.format(BOT_TOKEN)}


##########################################################################
'''
Selects an active user from a list of users
'''


def postSlackMessage(bot, text="", blocks=None):
  return requests.post('https://slack.com/api/chat.postMessage', {
    'channel': bot.channel_name,
    'text': text,
    'link_names': True,
  }, headers=bot.auth_header)


def selectUser(bot, exercise):
  active_users = fetchActiveUsers(bot)

  # Add all active users not already in the user queue
  # Shuffles to randomly add new active users
  shuffle(active_users)
  bothArrays = set(active_users).intersection(bot.user_queue)
  for user in active_users:
    if user not in bothArrays:
      bot.user_queue.append(user)

  # The max number of users we are willing to look forward
  # to try and find a good match
  sliding_window = bot.sliding_window_size

  # find a user to draw, priority going to first in
  for i in range(len(bot.user_queue)):
    user = bot.user_queue[i]

    # User should be active and not have done exercise yet
    if user in active_users and not user.hasDoneExercise(exercise):
      bot.user_queue.remove(user)
      return user
    elif user in active_users:
      # Decrease sliding window by one. Basically, we don't want to jump
      # too far ahead in our queue
      sliding_window -= 1
      if sliding_window <= 0:
        break

  # If everybody has done exercises or we didn't find a person within our
  # sliding window,
  for user in bot.user_queue:
    if user in active_users:
      bot.user_queue.remove(user)
      return user

  if len(active_users) > 0:
    # If we weren't able to select one, just pick a random
    print("Selecting user at random (queue length was " + str(len(bot.user_queue)) + ")")
    return active_users[random.randrange(0, len(active_users))]
  else:
    print("no active users ")
    return []


'''
Fetches a list of all active users in the channel
'''


def fetchActiveUsers(bot):
  # Check for new members
  params = {"channel": bot.channel_id}
  response = requests.get("https://slack.com/api/conversations.members", headers=bot.auth_header, params=params)

  print(curl.parse(response))
  print(response.text)

  user_ids = json.loads(response.text)["members"]

  active_users = []

  for user_id in user_ids:

    # exclude certain users from the final active user list.
    # should mostly be used for bots
    if user_id in bot.exclude_users:
      continue

    # Add user to the cache if not already
    if user_id not in bot.user_cache:
      bot.user_cache[user_id] = User(user_id)
      if not bot.first_run:
        # Push our new users near the front of the queue!
        bot.user_queue.insert(2, bot.user_cache[user_id])

    if bot.user_cache[user_id].isActive():
      active_users.append(bot.user_cache[user_id])

  if bot.first_run:
    bot.first_run = False

  return active_users


'''
Fetches a list of all elite fitness members
'''


def fetchEliteUsers(bot):
  # Check for group members
  params = {"usergroup": bot.elite_group_id}
  response = requests.get(
    "https://slack.com/api/usergroups.users.list", headers=bot.auth_header, params=params)
  print(curl.parse(response))
  print(response.text)
  elite_ids = json.loads(response.text)["users"]

  return elite_ids


'''
Selects an exercise and start time, and sleeps until the time
period has past.
'''


def selectExerciseAndStartTime(bot):
  next_time_interval = selectNextTimeInterval(bot)
  minute_interval = int(next_time_interval / 60)
  exercise = selectExercise(bot)

  # Announcement String of next lottery time
  lottery_announcement = "_next lottery for " + exercise["name"] + " is in " + str(
    minute_interval) + (" minutes_" if minute_interval != 1 else " minute_")

  # Announce the exercise to the thread
  if not bot.debug:
    response = postSlackMessage(bot, lottery_announcement)
    print(curl.parse(response))
    print(response.text)
  print(lottery_announcement)

  # Sleep the script until time is up
  if not bot.debug:
    time.sleep(next_time_interval)
  else:
    # If debugging, once every 5 seconds
    time.sleep(5)

  return exercise


'''
Selects the next exercise
'''


def selectExercise(bot):
  idx = random.randrange(0, len(bot.exercises))
  return bot.exercises[idx]


'''
Selects the next time interval
'''


def selectNextTimeInterval(bot):
  return random.randrange(bot.min_countdown * 60, bot.max_countdown * 60)


'''
Selects a person to do the already-selected exercise
'''


def assignExercise(bot, exercise):
  # Select number of reps
  exercise_reps = random.randrange(
    exercise["minReps"], exercise["maxReps"] + 1)

  winner_announcement = str(exercise_reps) + " " + \
                        str(exercise["units"]) + " " + exercise["name"] + " RIGHT NOW "

  # EVERYBODY
  if random.random() < bot.group_callout_chance:
    winner_announcement += "@here!"

    for user_id in bot.user_cache:
      user = bot.user_cache[user_id]
      user.addExercise(exercise, exercise_reps)

    logExercise(bot, "@here", exercise[
      "name"], exercise_reps, exercise["units"])

  else:
    winners = [selectUser(bot, exercise)
               for i in range(bot.num_people_per_callout)]

    call_out_count = bot.num_people_per_callout
    if len(fetchActiveUsers(bot)) < bot.num_people_per_callout:
      call_out_count = len(fetchActiveUsers(bot))

    for i in range(call_out_count):
      winner_announcement += str(winners[i].getUserHandle())
      if i == call_out_count - 2:
        winner_announcement += ", and "
      elif i == call_out_count - 1:
        winner_announcement += "!"
      else:
        winner_announcement += ", "

      winners[i].addExercise(exercise, exercise_reps)
      logExercise(bot, winners[i].getUserHandle(), exercise[
        "name"], exercise_reps, exercise["units"])

  # ELITES
  if random.random() < bot.elite_callout_chance:

    elite_reps = (random.randrange(
      exercise["minReps"], exercise["maxReps"]) * 2)

    winner_announcement += " & " + str(elite_reps) + " " + \
                           str(exercise["units"]) + " " + exercise["name"] + " GET SOME "

    winner_announcement += "@workoutmultiplier!"

    # log ELITES
    elite_ids = fetchEliteUsers(bot)

    for user_id in elite_ids:
      user = bot.user_cache[user_id]
      user.addExercise(exercise, elite_reps)

    logExercise(bot, "@workoutmultiplier", exercise[
      "name"], elite_reps, exercise["units"])

  # Announce the user
  if not bot.debug:
    response = postSlackMessage(bot, winner_announcement)
    print(curl.parse(response))
    print(response.text)
  print(winner_announcement)


def logExercise(bot, username, exercise, reps, units):
  filename = bot.csv_filename + "_DEBUG" if bot.debug else bot.csv_filename
  with open(filename, 'a') as f:
    writer = csv.writer(f)

    writer.writerow([str(datetime.datetime.now()), username,
                     exercise, reps, units, bot.debug])


def saveUsers(bot):
  # Write to the command console today's breakdown
  s = "```\n"
  # s += "Username\tAssigned\tComplete\tPercent
  s += "Username".ljust(15)
  for exercise in bot.exercises:
    s += exercise["name"] + "  "
  s += "\n------------------------------------------------------------------------------------------------------\n"

  for user_id in bot.user_cache:
    user = bot.user_cache[user_id]
    s += user.username.ljust(15)
    for exercise in bot.exercises:
      if exercise["id"] in user.exercises:
        s += str(user.exercises[exercise["id"]]
                 ).ljust(len(exercise["name"]) + 2)
      else:
        s += str(0).ljust(len(exercise["name"]) + 2)
    s += "\n"

    user.storeSession(str(datetime.datetime.now()))

  s += "```"

  if not bot.debug:
    response = postSlackMessage(bot, s)
    print(curl.parse(response))
    print(response.text)
  print(s)

  # write to file
  with open('user_cache.save', 'wb') as f:
    pickle.dump(bot.user_cache, f)


def isOfficeHours(bot):
  if not bot.office_hours_on:
    if bot.debug:
      print("not office hours")
    return True
  now = datetime.datetime.now()
  now_time = now.time()
  day_of_week = datetime.datetime.today().weekday()

  if now_time >= datetime.time(bot.office_hours_begin) and now_time <= datetime.time(bot.office_hours_end) and day_of_week < 5:
    if bot.debug:
      print("in office hours")
    return True
  else:
    if bot.debug:
      print("out office hours")
    return False


def main():
  # Handle a SIGTERM so that killing the bot via other methods (like "docker stop")
  # triggers the same functionality as Ctrl-C (KeyboardInterrupt)
  signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))

  bot = Bot()

  postSlackMessage(bot, "_rebooting..._")

  try:
    while True:
      if isOfficeHours(bot) and len(fetchActiveUsers(bot)) > 0:
        # Re-fetch config file if settings have changed
        bot.setConfiguration()

        # Get an exercise to do
        exercise = selectExerciseAndStartTime(bot)

        # Assign the exercise to someone
        assignExercise(bot, exercise)

      else:
        # Sleep the script and check again for office hours
        if not bot.debug:
          time.sleep(5 * 60)  # Sleep 5 minutes
        else:
          # If debugging, check again in 5 seconds
          time.sleep(5)

  except (KeyboardInterrupt, SystemExit):
    saveUsers(bot)


main()
