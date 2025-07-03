AI-Powered Healthcare Appointment Scheduling Bot

This project is a conversational AI assistant designed to help users schedule healthcare appointments using natural language. It leverages **Gemini 1.5 Pro**, **LangChain**, **Flask**, and **Google Sheets** integration.



Features

- LLM-driven conversation using **LangChain + Gemini**
- Responsive web-based chat UI
- Google Sheets appointment logging
- Input validation for time, date, email, and phone
- Conversational memory and error handling
- Modular, production-ready Flask API



Tech Stack

- Python 3.10+
- Flask + Flask-CORS
- LangChain
- Google Generative AI (Gemini)
- gspread + oauth2client (Google Sheets API)
- dotenv for environment management
- HTML/CSS/JS frontend (no frameworks)



To enable Google Sheets integration, you need to set up a Google service account:

Steps:
1.	Go to Google Cloud Console
  https://console.cloud.google.com/
2.	Create a Project (or use an existing one)
   
3.	Enable APIs
  o	Google Sheets API
  o	Google Drive API

4.	Create a Service Account
  o	Navigate to IAM & Admin → Service Accounts
  o	Create a new service account with basic editor access

5.	Generate a Key
  o	Select JSON format
  o	Download and save the file securely, e.g. service_account.json

6.	Share your Google Sheet
  o	Open your Google Sheet
  o	Click "Share"
  o	Grant "Editor" access to the service account email (e.g. my-bot@my-project.iam.gserviceaccount.com)

7.	Configure .env file
  Sample env
    GOOGLE_CREDENTIALS_PATH=path/to/service_account.json
    GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit

