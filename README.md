# MondayVox

### A voice assistant for making changes in any board on Monday.com.

We have developed an AI voice assistant, that can be used seamlessly with Monday.com. \
Modern speech recognition technology is used by MondayVox to flawlessly and accurately comprehend your orders. Our voice assistant enables you to easily make real-time edits to your Monday.com boards while you're on the go, in a meeting, or just prefer a hands-free experience.\
It uses LLM to intelligently query the given prompt.\
MondayVox streamlines your workflow and improves cooperation by enabling you to create new items, assign them to team members, update their statuses, and delete completed tasks. Voice feedbacks are integrated to make it interactive.

------------------------------------------------

## How to build FrontEnd

1. Create a .env file. That file should have two lines:
  ```
  OPENAI_APIKEY=YOUR_OPENAI_KEY
  DO_NOT_USE_API=false
  ```
2. Run the following commands:
  ```
  npm i --save
  npm run dev
  ```

## How to run BackEnd
1. Add your Monday API Key at Line 19 of hosting_flask.py
2. Add your openai Key at line 22 of hosting_flask.py
3. Run the following command: 
  ```
  python3 hosting_flask.py
  ```

## Integrate BackEnd and FrontEnd using NGROK
1. Run:
  ```
  ngrok http 5000
  ```
2. Replace '6024' in line 230 of components/mainPage.jsx with first 4 characters of the url mentioned in front of Forwarding of ngrok.


## Acknowledgment
1. Thanks to openai for Whisper and GPT-3.5 Turbo
