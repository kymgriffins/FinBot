# 🤖 FinBot - Real-Time Financial Data Monitor

A sophisticated Python bot that monitors stock market data in real-time, stores it in a database, and sends intelligent alerts via Telegram. Perfect for traders and investors who want automated market monitoring.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-green.svg)
![Render](https://img.shields.io/badge/Deployed-Render-purple.svg)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)

## ✨ Features

### 📊 Data Collection
- **Real-time 1-minute** stock data from Yahoo Finance
- **Multiple ticker** support (AAPL, MSFT, TSLA, etc.)
- **Automatic market hours** detection (9:30 AM - 4:00 PM EST)
- **Persistent storage** in PostgreSQL database

### 🔔 Smart Alerts
- **Hourly summaries** during trading hours
- **Market open/close** notifications
- **Custom price alerts** on demand
- **Beautiful formatted messages** with emojis

### 🚀 Deployment
- **Free hosting** on Render
- **Auto-scaling** web service
- **Scheduled tasks** for continuous operation
- **REST API** for data access

## 🛠 Quick Setup

### 1. Clone & Setup
```bash
git clone https://github.com/kymmgiffins/finbot.git
cd finbot
cp .env.example .env