from datetime import date, timedelta

HOLIDAYS_2026 = [
    "01-01",
    "02-17", "02-18", "02-19", "02-20", "02-21", "02-22",
    "04-04", "04-05", "04-06",
    "05-01", "05-02", "05-03", "05-04", "05-05",
    "06-19", "06-20", "06-21",
    "10-01", "10-02", "10-03", "10-04", "10-05", "10-06", "10-07",
    "10-08",
]

def is_weekend(d: date) -> bool:
    return d.weekday() >= 5

def is_holiday(d: date) -> bool:
    month_day = d.strftime("%m-%d")
    return month_day in HOLIDAYS_2026

def is_trading_day(d: date = None) -> bool:
    if d is None:
        d = date.today()
    
    if is_weekend(d):
        return False
    
    if is_holiday(d):
        return False
    
    return True

def get_next_trading_day(d: date = None) -> date:
    if d is None:
        d = date.today()
    
    if is_trading_day(d):
        return d
    
    current = d + timedelta(days=1)
    while not is_trading_day(current):
        current += timedelta(days=1)
    
    return current

def get_previous_trading_day(d: date = None) -> date:
    if d is None:
        d = date.today()
    
    if is_trading_day(d):
        return d
    
    current = d - timedelta(days=1)
    while not is_trading_day(current):
        current -= timedelta(days=1)
    
    return current