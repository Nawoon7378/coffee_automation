import datetime

def _logging(prefix="", text=None):
    form = "{}[{}]".format(prefix, datetime.datetime.now().strftime("%y-%m-%d %h:%M:%S"))
    if text is not None:
        print("{} : {}".format(form, text))
    else:
        print("{} - Log Stamp -".format(form))

def log(text=None):
    _logging("[Log] ", text)

def err(text=None):
    _logging("[Error] ", text)

def info(text=None):
    _logging("[Info] ", text)

def warn(text=None):
    _logging("[Warning] ", text)