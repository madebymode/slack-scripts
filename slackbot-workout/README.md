# slackbot-workout
A fun script that gets Slackbot to force your teammates to work out!

<img src = "https://cldup.com/iL-6xfp2Aa.thumb.png">

# Instructions

1. Clone the repo and navigate into the directory in your terminal.

2. Go to your slack home page [https://{yourgroup}.slack.com/home](http://my.slack.com/home) & click on **Integrations** on the left sidebar.

3. Scroll All the Way Down until you see **Slack API** and **Slackbot**. You'll need to access these two integrations.

4. In the **Slack API Page**, select **WebAPI** in the left side bar, scroll all the way down, and register yourself an auth token. You should see this. Take note of the token, e.g. `xoxp-2751727432-4028172038-5281317294-3c46b1`. This is your **User Auth Token**

5. In the **Slackbot** (Remote control page). Register an integration & you should see this. __Make sure you grab just the token out of the url__, e.g. `AizJbQ24l38ai4DlQD9yFELb`

6. Save your SLACK_USER_TOKEN_STRING and SLACK_URL_TOKEN_STRING as environmental variables in your terminal.

    `$ export SLACK_USER_TOKEN_STRING=YOURUSERTOKEN`

    `$ export SLACK_URL_TOKEN_STRING=YOURURLTOKEN`

    If you need help with this, try adapting the first 5 steps of the guide to [edit your .bash_profile](http://natelandau.com/my-mac-osx-bash_profile/)

7. Set up channel and customize configurations

    Open `default.json` and set `teamDomain` (ex: ctrlla) `channelName` (ex: general) and `channelId` (ex: B22D35YMS). Save the file as `config.json` in the same directory. Set any other configurations as you like.

    If you don't know the channel Id, fetch it using

    `$ python fetchChannelId.py channelname`

8. If you haven't set up pip for python, go in your terminal and run.
`$ sudo easy_install pip`

9. While in the project directory, run

    `$ sudo pip install -r requirements.txt`

    `$ python slackbotExercise.py`

Run the script to start the workouts and hit ctrl+c to stop the script. Hope you have fun with it!