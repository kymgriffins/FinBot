FinBot
=====

Modern Flask app structure with app factory and blueprints.

Quick start
-----------

1. Create `.env`:

```
TELEGRAM_BOT_TOKEN=your_token
SYMBOLS=ES=F,NQ=F,YM=F,6E=F,CL=F,GC=F,SI=F
TIMEZONE=America/New_York
```

2. Install deps: `pip install -r requirements.txt`

3. Run: `python app.py`

Key endpoints
-------------

- `/` Home dashboard
- `/api/health` Health check
- `/data/generate-csv` Generate and send weekly CSVs
- `/telegram/test` Send test Telegram message

Project layout
--------------

```
finbot/
├── app.py
├── wsgi.py
├── requirements.txt
├── .env
├── render.yaml
├── README.md
├── src/
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── api.py
│   │   ├── data.py
│   │   ├── telegram.py
│   │   └── web.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── data_fetcher.py
│   │   └── telegram_bot.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── decorators.py
│   └── models/
│       ├── __init__.py
│       └── schemas.py
├── templates/
│   └── base.html
└── static/
    ├── css/
    ├── js/
    └── images/