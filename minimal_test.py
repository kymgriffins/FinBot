#!/usr/bin/env python3
"""
Minimal test for Flask app
"""

from flask import Flask, render_template

app = Flask(__name__)

@app.route('/test')
def test():
    return "Hello World"

@app.route('/template')
def template_test():
    return render_template('test_simple.html')

if __name__ == '__main__':
    print("Starting minimal Flask app...")
    app.run(debug=True, port=5001)
