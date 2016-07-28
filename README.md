YFImport
===

**Table of Contents**

- [Introduction](#introduction)
- [Command Line Usage](#command-line-usage)
- [File Structure](#file-structure)

# Introduction

YFImport is a tool for import historical data from Yahoo Finance and prepare for experiments with StreamPref DSMS

# Command Line Usage

The command line parameters are:
- -h/--help: Show help message
- -s/--start: Start date
- -e/--end: End date
- -x/--exchange: Filter by exchange

# File Structure

The tool creates the following file structure:
- imported
  - historical (directory for individual imported historical files)
  - stocks.csv (table of stocks)
  - trade.csv (stream of trades)
  - volatility.csv (stream of volatility rate)
  - transaction.csv (join of stocks, trades and volatility)
