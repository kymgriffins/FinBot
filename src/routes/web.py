from flask import Blueprint, render_template
import os

web_bp = Blueprint('web', __name__)


@web_bp.route('/')
def home():
    symbols = os.getenv('SYMBOLS', 'ES=F,NQ=F,YM=F,6E=F,CL=F,GC=F,SI=F').split(',')
    return render_template('base.html', symbols=symbols)


