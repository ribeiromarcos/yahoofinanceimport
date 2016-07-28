#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Module to import historical stock quotes from Yahoo Finance
'''

import csv
import datetime
import os

# URL for historical information
HISTORICAL_URL = 'http://real-chart.finance.yahoo.com/table.csv?' + \
    's={ss}&a={sm}&b={sd}&c={sy}&d={em}&e={ed}&f={ey}'

# Data directory
DATA_DIR = 'yahoo_data'
# Historical directory
HISTORICAL_DIR = DATA_DIR + os.sep + 'historical'
# Directories list
DIR_LIST = [DATA_DIR, HISTORICAL_DIR]

# Stock file
STOCK_FILE = DATA_DIR + os.sep + 'stocks.csv'
# Trades file
TRADE_FILE = DATA_DIR + os.sep + 'trade.csv'
# Volatility file
VOLATILITY_FILE = DATA_DIR + os.sep + 'volatility.csv'
# Transactions file
TRANSACTION_FILE = DATA_DIR + os.sep + 'transaction.csv'

# Number of retries to get an URL
URL_RETRY = 10

# Attribute names
SECTOR = 'sector'
INDUSTRY = 'industry'
SYMBOL = 'symbol'
NAME = 'name'
EXCHANGE = 'exchange'
COUNTRY = 'country'
TS = '_ts'
FLAG = '_flag'
DATE = 'date'
OPEN = 'open'
HIGH = 'high'
LOW = 'low'
CLOSE = 'close'
VOLUME = 'volume'
ADJ_CLOSE = 'adj close'
METHOD = 'method'
RATE = 'rate'
PRICE = 'price'

# Original file header of historical files
HISTORICAL_HEADER = [DATE, OPEN, HIGH, LOW, CLOSE, VOLUME, ADJ_CLOSE]

# Final file header of stock files
STOCK_HEADER = [TS, FLAG, SYMBOL, SECTOR, EXCHANGE, COUNTRY]
# File header for trade stream
TRADE_HEADER = [TS, SYMBOL, OPEN, CLOSE, VOLUME]
# File header for volatility stream
VOLATILITY_HEADER = [TS, SYMBOL, METHOD, RATE]
# File header for transactions stream
TRANSACTION_HEADER = [TS, SYMBOL, SECTOR, COUNTRY, PRICE, VOLUME, METHOD, RATE]

# Volatility ranges
VOLATILITY_COUNTS = [21, 60]


def read_url(url):
    '''
    Try to get an URL content
    '''
    import requests
    from time import sleep
    print 'Reading URL: ' + url
    try_count = 0
    while try_count < URL_RETRY:
        content = None
        try:
            content = requests.get(url)
        except Exception as exc:  # IGNORE:broad-except
            print '\n\n Error for ' + url
            print exc
            print 'Retry\n\n'
            sleep(1)
        # Try to read the URL content
        if content is not None:
            if content.status_code == 200:
                return content.text
            else:
                print '\n\nError for ' + url
                print 'Error code: ' + str(content.status_code)
                print 'Retry\n\n'
                sleep(1)
        try_count += 1
    # Return empty string when the URL could not be read
    return ''


def write_csv_file(rec_list, filename, att_list, mode='w'):
    '''
    Write stock records on file
    '''
    out_file = open(filename, mode)
    out_write = csv.DictWriter(out_file, att_list, dialect='table')
    if mode == 'w':
        out_write.writeheader()
    out_write.writerows(rec_list)
    out_file.close()


def read_csv_file(filename, att_list):
    '''
    Read stocks from file
    '''
    stock_list = []
    in_file = open(filename)
    in_reader = csv.DictReader(in_file, att_list, dialect='table')
    # Skip header
    try:
        in_reader.next()
    except StopIteration:
        return stock_list
    for rec in in_reader:
        stock_list.append(rec)
    in_file.close()
    return stock_list


def get_all_historical(stocks_list, start_date, end_date):
    '''
    Get historical data for a stock list
    '''
    for rec in stocks_list:
        symbol = rec[SYMBOL]
        print 'Getting historical data for ' + symbol
        filename = HISTORICAL_DIR + os.sep + symbol + '.csv'
        if not os.path.isfile(filename):
            get_historical_data(symbol, filename, start_date, end_date)
        else:
            print 'Using cached download for ' + symbol


def get_historical_data(symbol, filename, start_date, end_date):
    '''
    Get historical data from a stock list
    '''
    print 'Getting historical for ' + symbol
    hist_url = \
        HISTORICAL_URL.format(ss=symbol,
                              sy=start_date.year, sm=start_date.month,
                              sd=start_date.day,
                              ey=end_date.year, em=end_date.month,
                              ed=end_date.day)
    hist_content = read_url(hist_url)
    hist_content = hist_content.replace(',', '|').lower()
    out_file = open(filename, 'w')
    out_file.write(hist_content)
    print 'Historical size: ' + str(out_file.tell())
    out_file.close()


def create_directories():
    '''
    Create default directories if they do not exists
    '''
    for directory in DIR_LIST:
        if not os.path.exists(directory):
            os.mkdir(directory)


def get_date(string_date):
    '''
    Get date from string
    '''
    try:
        year, month, day = string_date.split('-')
        return datetime.date(int(year), int(month), int(day))
    except:  # IGNORE:bare-except
        print 'Invalid date: ' + string_date
        return None


def get_volatility(stock_list, count):
    '''
    Calculate volatility over last 'count' records of a list
    '''
    import math
    # Calculate difference between current and previous (CLOSE and OPEN)
    diff_list = [float(rec[CLOSE]) / float(rec[OPEN])
                 for rec in stock_list[-count:]]
    diff_list = [math.log(n) for n in diff_list]
    if len(diff_list):
        # Average of differences
        avg = sum(n for n in diff_list) / float(count)
        # Variance
        var = sum([(n - avg) * (n - avg)
                   for n in diff_list]) / float(count)
        # Standard deviation
        dev = math.sqrt(var)
        # Volatility
        return dev * math.sqrt(252)
    else:
        return None


def get_trade_stream(symbol, start_date, end_date):
    '''
    Get transactions stream for a stock symbol
    '''
    in_filename = HISTORICAL_DIR + os.sep + symbol + '.csv'
    hist_list = read_csv_file(in_filename, HISTORICAL_HEADER)
    # Sort records by date
    hist_list.sort(key=lambda k: k[DATE])
    trade_list = []
    previous_ts = 0
    # For each historical record
    for hist_rec in hist_list:
        # Skip record with zero volume and out of period
        # It is not possible to calculate the rate for these records
        rec_date = get_date(hist_rec[DATE])
        if int(hist_rec[VOLUME]) > 0 and start_date <= rec_date <= end_date:
            rec_ts = previous_ts + 1
            previous_ts = rec_ts
            t_rec = {TS: rec_ts, SYMBOL: symbol,
                     OPEN: hist_rec[OPEN], CLOSE: hist_rec[CLOSE],
                     VOLUME: hist_rec[VOLUME]}
            # Append record into transactions list
            trade_list.append(t_rec)
    return trade_list


def get_volatility_stream(symbol, trade_list):
    '''
    Get volatilities stream for a stock symbol
    '''
    volatolity_list = []
    # For each historical record
    for rec in trade_list:
        # For each count in volatility counts
        for count in VOLATILITY_COUNTS:
            # Calculate volatility for this count
            vol = get_volatility(trade_list, count)
            if vol is not None:
                # Create volatility record
                v_rec = {SYMBOL: symbol, TS: rec[TS],
                         METHOD: count, RATE: vol}
                # Append record to list
                volatolity_list.append(v_rec)
    return volatolity_list


def get_transaction_stream(stock_rec, trade_list, volatility_list):
    '''
    Join stock and transactions and volatilities
    '''
    full_list = []
    if not len(trade_list):
        return full_list
    for trade_rec in trade_list:
        for vol_rec in volatility_list:
            if vol_rec[TS] == trade_rec[TS]:
                rec = {}
                rec[METHOD] = vol_rec[METHOD]
                rec[RATE] = vol_rec[RATE]
                rec[TS] = trade_rec[TS]
                rec[SYMBOL] = stock_rec[SYMBOL]
                rec[SECTOR] = stock_rec[SECTOR]
                rec[COUNTRY] = stock_rec[COUNTRY]
                rec[PRICE] = trade_rec[CLOSE]
                rec[VOLUME] = trade_rec[VOLUME]
                rec[TS] = trade_rec[TS]
                full_list.append(rec)
    return full_list


def get_streams(stock_list, start_date, end_date):
    '''
    Get transactions and volatilities streams for a stock list
    '''
    if not len(stock_list):
        return
    # Get transaction and volatility streams
    if os.path.isfile(TRADE_FILE):
        os.remove(TRADE_FILE)
    if os.path.isfile(VOLATILITY_FILE):
        os.remove(VOLATILITY_FILE)
    # First symbol
    rec = stock_list[0]
    symbol = rec[SYMBOL]
    print 'Processing ' + symbol
    trade_list = get_trade_stream(symbol, start_date, end_date)
    volatility_list = get_volatility_stream(symbol, trade_list)
    transaction_list = get_transaction_stream(rec, trade_list, volatility_list)
    write_csv_file(trade_list, TRADE_FILE, TRADE_HEADER)
    write_csv_file(volatility_list, VOLATILITY_FILE, VOLATILITY_HEADER)
    write_csv_file(transaction_list, TRANSACTION_FILE, TRANSACTION_HEADER)
    for rec in stock_list[1:]:
        symbol = rec[SYMBOL]
        print 'Processing ' + symbol
        trade_list = get_trade_stream(symbol, start_date, end_date)
        volatility_list = get_volatility_stream(symbol, trade_list)
        transaction_list = get_transaction_stream(rec, trade_list,
                                                  volatility_list)
        write_csv_file(trade_list, TRADE_FILE,
                       TRADE_HEADER, 'a')
        write_csv_file(volatility_list, VOLATILITY_FILE,
                       VOLATILITY_HEADER, 'a')
        write_csv_file(transaction_list, TRANSACTION_FILE, TRANSACTION_HEADER,
                       'a')


def filter_by_exchange(symbol_list, exchange):
    '''
    Filter the stocks list
    '''
    new_list = []
    for rec in symbol_list:
        if rec[EXCHANGE] == exchange:
            new_list.append(rec)
    return new_list


def today():
    '''
    Return current date
    '''
    return datetime.date.today()


def get_arguments(print_help=False):
    '''
    Get arguments
    '''
    import argparse
    parser = argparse.ArgumentParser('yfimport')
    parser.add_argument('-s', '--start', action="store",
                        help='Start date yyyy-mm-dd' +
                        '(default: 365 days before end date)')
    parser.add_argument('-e', '--end', action="store",
                        help='End date yyyy-mm-dd' +
                        '(default: system current date)')
    parser.add_argument('-x', '--exchange', action="store",
                        help='Filter by an exchange')
    args = parser.parse_args()
    if print_help:
        parser.print_help()
    return args


def main():
    '''
    Main routine
    '''
    csv.register_dialect('table', delimiter='|', skipinitialspace=True)
    create_directories()
    args = get_arguments()
    end_date = today()
    if args.end:
        end_date = get_date(args.end)
        if end_date is None:
            return
    start_date = end_date - datetime.timedelta(days=365)
    if args.start:
        start_date = get_date(args.start)
        if start_date is None:
            return
    stock_list = read_csv_file(STOCK_FILE, STOCK_HEADER)
    if args.exchange:
        stock_list = filter_by_exchange(stock_list, args.exchange)
    get_all_historical(stock_list, start_date, end_date)
    get_streams(stock_list, start_date, end_date)
    print 'WARNING: The stream files must be sorted by timestamp'


if __name__ == '__main__':
    main()
