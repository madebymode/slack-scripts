import datetime
import json
import os

import curl
import requests
from dotenv import load_dotenv

load_dotenv()

# Environment variables must be set with your tokens
BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')

# lazy
AUTH_HEADER = {'Authorization': 'Bearer {}'.format(BOT_TOKEN)}


class User:

  def __init__(self, user_id):
    # The Slack ID of the user
    self.id = user_id

    # The username (@username) and real name
    self.username, self.real_name = self.fetchNames()

    # A list of all exercises done by user
    self.exercise_history = []

    # A record of all exercise totals (quantity)
    self.exercises = {}

    # A record of exercise counts (# of times)
    self.exercise_counts = {}

    # A record of past runs
    self.past_workouts = {}

    print("New user: " + self.real_name + " (" + self.username + ")")

  def storeSession(self, run_name):
    try:
      self.past_workouts[run_name] = self.exercises
    except:
      self.past_workouts = {}

    self.past_workouts[run_name] = self.exercises
    self.exercises = {}
    self.exercise_counts = {}

  def fetchNames(self):
    params = {"user": self.id}
    response = requests.get("https://slack.com/api/users.info",
                            headers=AUTH_HEADER, params=params)

    print(curl.parse(response))
    print(response.text)

    user_obj = json.loads(response.text)["user"]

    username = user_obj["name"]
    real_name = user_obj["profile"]["real_name"]

    return username, real_name

  def getUserHandle(self):
    return ("@" + self.username)

  '''
    Returns true if a user is currently "active", else false
    '''

  def isActive(self):
    try:
      params = {"user": self.id}
      response = requests.get("https://slack.com/api/users.getPresence",
                              headers=AUTH_HEADER, params=params)

      print(curl.parse(response))
      print(response.text)

      status = json.loads(response.text)["presence"]

      return status == "active"
    except requests.exceptions.ConnectionError:
      print("Error fetching online status for " + self.getUserHandle())
      return False

  def addExercise(self, exercise, reps):
    # Add to total counts
    self.exercises[exercise["id"]] = self.exercises.get(
      exercise["id"], 0) + reps
    self.exercise_counts[exercise["id"]] = self.exercise_counts.get(exercise[
                                                                      "id"], 0) + 1

    # Add to exercise history record
    self.exercise_history.append([datetime.datetime.now().isoformat(), exercise[
      "id"], exercise["name"], reps, exercise["units"]])

  def hasDoneExercise(self, exercise):
    return exercise["id"] in self.exercise_counts
