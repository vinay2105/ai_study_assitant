# 📚 Study Assistant

**Study Assistant** is an **AI-powered Django web application** that helps students create **study notes and quizzes** automatically from uploaded PDFs or text files.  
It uses **Google Gemini API** to generate **summarized notes and MCQ quizzes**, making exam preparation faster and easier.  

🔗 **Live Demo:** [Deployed Link](https://study-assistant-6x0g.onrender.com) *(Replace with your Render URL)*

---

## ✨ Features

- **User Authentication**
  - Custom user model
  - Sign up, login, and logout
- **AI-Powered Notes Generation**
  - Upload PDFs or text files
  - Generates structured HTML notes
  - Notes automatically formatted for readability
- **AI-Generated Quizzes**
  - Creates 10 MCQs from uploaded notes
  - Displays options with **correct answers in green** and **wrong answers in red**
  - Tracks quiz scores per user
- **Session-Based Notes Handling**
  - Uploaded files are **not stored permanently**
  - Notes stored temporarily in session for security
- **PostgreSQL Database for Production**
  - Stores users and quiz results
- **Secure Environment Variables**
  - Secret keys, database credentials, and API keys stored in `.env`

---

## 🛠 Tech Stack

- **Backend:** Django 5.x (Python)
- **Frontend:** HTML, CSS, Bootstrap
- **Database:**
  - SQLite (Local Development)
  - PostgreSQL (Production via Render)
- **AI Integration:** Google Gemini 1.5 Flash API
- **Deployment:** Render

---

## 📂 Project Structure

