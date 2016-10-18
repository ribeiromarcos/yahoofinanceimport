#!/usr/bin/python -u
# -*- coding: utf-8 -*-
'''
Module for generation of environments for experiments over Yahoo finance data
using BEST and TOPK operators
'''


import csv
import os

from yfimport import TRANSACTION_FILE


# Experiment parameters
RAN = 'range'
SLI = 'slide'
OPE = 'operator'
TOPK = 'top'
BEST = 'best'
ALGORITHM = 'algorithm'

# Result fields
RUNTIME = 'runtime'
MEMORY = 'memory'

# List of ranges
RANGE_LIST = [2, 3, 4, 5, 6]
# Default range
RANGE_DEFAULT = 4

# List of slides
SLIDE_LIST = [1, 2, 3, 4]
# Default slide
SLIDE_DEFAULT = 1

# List of operator
OPERATOR_LIST = [BEST, TOPK]
# Default operator
OPERATOR_DEFAULT = BEST

# Top-k variation (-1 for best operator)
TOPK_LIST = [1, 35, 70, 140, 280]

# List of algorithms
ALGORITHM_LIST = ['inc_ancestors', 'inc_graph', 'inc_partition', 'partition']

# Directories
MAIN_DIR = 'streampref'
DATA_DIR = MAIN_DIR + os.sep + 'data'
DETAILS_DIR = MAIN_DIR + os.sep + 'details'
SUMMARY_DIR = MAIN_DIR + os.sep + 'summary'
RESULT_DIR = MAIN_DIR + os.sep + 'result'
QUERY_DIR = MAIN_DIR + os.sep + 'queries'
ENV_DIR = MAIN_DIR + os.sep + 'env'
DIR_LIST = [MAIN_DIR, DATA_DIR, DETAILS_DIR, SUMMARY_DIR, RESULT_DIR,
            QUERY_DIR, ENV_DIR]

# Yahoo imported file
DATA_FILE = DATA_DIR + os.sep + 'transaction.csv'

# Number or experiment runs
RUN_COUNT = 5

# Command for experiment run
RUN_COMMAND = \
    "streampref -r'|' -p {alg} -e {env} -d {det} -m {ite}"
# Command for calculation of confidence interval
CONFINTERVAL_COMMAND = \
    'confinterval.py -i {inf} -o {outf} -k {keyf}'
# Command for sort stream file download
SORT_COMMAND = \
    'cat ' + TRANSACTION_FILE + ' | sort -g > ' + DATA_FILE

# Default registration of tables and streams
REGISTER_DEFAULT = '''
REGISTER STREAM transactions (symbol STRING, sector STRING, country STRING,
             price FLOAT, volume INTEGER, method INTEGER, rate FLOAT)
INPUT '{dfile}';


REGISTER QUERY preferred_stocks
INPUT '{qdir}/{qfile}.cql'
;
'''

# Default query
QUERY_DEFAULT = '''
SELECT {topk} *
FROM transactions [RANGE {ran} SECOND, SLIDE {sli} SECOND]
ACCORDING TO PREFERENCES
IF sector = 'Basic Materials' THEN rate < 0.25 BETTER rate >= 0.25
[method, symbol, price]
AND
IF sector = 'Technology' THEN rate < 0.35 BETTER rate >= 0.35
[method, symbol, price]
AND
IF rate >= 0.35 THEN  country = 'Brazil' BETTER country = 'France'
[symbol, price]
AND
IF rate >= 0.35 THEN  volume > 1000 BETTER volume <= 1000
[symbol, price]
;
'''


def gen_env_file(experiment_conf):
    '''
    Generate environment file for range and slide
    '''
    exp_id = get_experiment_id(experiment_conf)
    text = REGISTER_DEFAULT.format(qdir=QUERY_DIR,
                                   qfile=exp_id,
                                   dfile=DATA_FILE)
    filename = ENV_DIR + os.sep + get_experiment_id(experiment_conf) + '.env'
    out_file = open(filename, 'w')
    out_file.write(text)
    out_file.close()


def gen_query_file(experiment_conf):
    '''
    Generate query file for range and slide
    '''
    topk_option = ''
    if experiment_conf[OPE] == TOPK:
        topk_option = 'TOPK(' + str(experiment_conf[TOPK]) + ')'
    text = QUERY_DEFAULT.format(topk=topk_option,
                                ran=experiment_conf[RAN],
                                sli=experiment_conf[SLI])
    filename = QUERY_DIR + os.sep + get_experiment_id(experiment_conf) + '.cql'
    out_file = open(filename, 'w')
    out_file.write(text)
    out_file.close()


def gen_files(experiment_list):
    '''
    Generate all files (queries and environments)
    '''
    # Copy imported data file and sort by timestamp
    os.system(SORT_COMMAND)
    if not os.path.isfile(DATA_FILE):
        print 'Error copying data file\n' + \
            'Make sure that import tool was executed'
    # Generate query files
    for exp_conf in experiment_list:
        gen_query_file(exp_conf)
    # Generate environment files
    for exp_conf in experiment_list:
        gen_env_file(exp_conf)


def get_experiment_id(experiment_conf):
    '''
    Return the ID of an experiment
    '''
    operation = 'best'
    if experiment_conf[OPE] == TOPK:
        operation = TOPK + str(experiment_conf[TOPK])
    return RAN + str(experiment_conf[RAN]) + \
        SLI + str(experiment_conf[SLI]) + operation


def get_detail_file(algorithm, experiment_id, count):
    '''
    Get filename for experiment details
    '''
    return DETAILS_DIR + os.sep + algorithm + '-' + \
        experiment_id + '.' + str(count) + '.csv'


def run(experiment_conf, count, algorithm, iterations):
    '''
    Run experiment for range and slide
    '''
    exp_id = get_experiment_id(experiment_conf)
    detail_file = get_detail_file(algorithm, exp_id, count)
    env_file = ENV_DIR + os.sep + exp_id + '.env'
    if not os.path.isfile(detail_file):
        command = RUN_COMMAND.format(alg=algorithm, env=env_file,
                                     det=detail_file, ite=iterations)
        print command
        os.system(command)


def get_max_iteration():
    '''
    Get maximum iteration of data file
    '''
    from yfimport import read_csv_file, TRANSACTION_HEADER, TS
    rec_list = read_csv_file(DATA_FILE, TRANSACTION_HEADER)
    last_rec = rec_list[-1]
    return int(last_rec[TS])


def run_experiments(experiment_list):
    '''
    Run all experiments
    '''
    iterations = get_max_iteration()
    for count in range(RUN_COUNT):
        for exp_conf in experiment_list:
            for alg in ALGORITHM_LIST:
                run(exp_conf, count + 1, alg, iterations)


def summarize_all():
    '''
    Summarize all results
    '''
    # Summarize experiments for BEST operator
    variation = {}
    variation[RAN] = RANGE_LIST
    variation[SLI] = SLIDE_LIST
    default_values = {RAN: RANGE_DEFAULT, SLI: SLIDE_DEFAULT, OPE: BEST}
    for parameter in variation:
        summarize(parameter, variation[parameter], default_values)
    # Summarize experiments for TOPK operator
    variation = {TOPK: TOPK_LIST}
    default_values = {RAN: RANGE_DEFAULT, SLI: SLIDE_DEFAULT, OPE: TOPK}
    for parameter in variation:
        summarize(parameter, variation[parameter], default_values)


def write_file(filename, record_list, key_field):
    '''
    Write record_list to file
    '''
    if len(record_list):
        field_list = [field for field in record_list[0].keys()
                      if field != key_field]
        field_list.sort()
        field_list.insert(0, key_field)
        output_file = open(filename, 'w')
        writer = csv.DictWriter(output_file, field_list)
        header = {field: field for field in field_list}
        writer.writerow(header)
        for rec in record_list:
            writer.writerow(rec)
        output_file.close()


def summarize(parameter, value_list, default_values):
    '''
    Summarize experiments about range variation
    '''
    time_list = []
    mem_list = []
    exp_conf = default_values.copy()
    for value in value_list:
        exp_conf[parameter] = value
        for rcount in range(RUN_COUNT):
            time_rec = {parameter: value}
            mem_rec = {parameter: value}
            for alg in ALGORITHM_LIST:
                dfile = get_detail_file(alg, get_experiment_id(exp_conf),
                                        rcount + 1)
                runtime, memory = get_summaries(dfile)
                time_rec[alg] = runtime
                mem_rec[alg] = memory
            time_list.append(time_rec)
            mem_list.append(mem_rec)
    fname = SUMMARY_DIR + os.sep + 'runtime_' + parameter + '.csv'
    write_file(fname, time_list, parameter)
    fname = SUMMARY_DIR + os.sep + 'memory_' + parameter + '.csv'
    write_file(fname, mem_list, parameter)


def get_summaries(detail_file):
    '''
    Import a result file to database
    '''
    if not os.path.isfile(detail_file):
        print 'File does not exists: ' + detail_file
        return (float('NaN'), float('NaN'))
    in_file = open(detail_file, 'r')
    reader = csv.DictReader(in_file, skipinitialspace=True)
    sum_time = 0.0
    sum_memory = 0.0
    count = 0
    for rec in reader:
        sum_time += float(rec[RUNTIME])
        sum_memory += float(rec[MEMORY])
        count += 1
    in_file.close()
    return (sum_time, sum_memory / count)


def create_directories():
    '''
    Create default directories if they do not exists
    '''
    for directory in DIR_LIST:
        if not os.path.exists(directory):
            os.mkdir(directory)


def add_experiment(experiment_list, experiment):
    '''
    Add an experiment into experiment list
    '''
    if experiment not in experiment_list:
        experiment_list.append(experiment.copy())


def gen_experiment_list():
    '''
    Generate the list of experiments
    '''
    exp_list = []
    # Default parameters configuration (for BEST operator)
    def_conf = {RAN: RANGE_DEFAULT, SLI: SLIDE_DEFAULT, OPE: BEST}
    # Attributes number variation (no deletions)
    for range_val in RANGE_LIST:
        conf = def_conf.copy()
        conf[RAN] = range_val
        add_experiment(exp_list, conf)
    for slide_val in SLIDE_LIST:
        conf = def_conf.copy()
        conf[SLI] = slide_val
        add_experiment(exp_list, conf)
    # Default parameters configuration (for TOPK operator)
    def_conf = {RAN: RANGE_DEFAULT, SLI: SLIDE_DEFAULT, OPE: TOPK}
    for topk_value in TOPK_LIST:
        conf = def_conf.copy()
        conf[TOPK] = topk_value
        add_experiment(exp_list, conf)
    return exp_list


def confidence_interval(parameter, in_file, out_file):
    '''
    Calculate final result with confidence interval
    '''
    if not os.path.isfile(in_file):
        print 'File does not exists: ' + in_file
        return
    command = CONFINTERVAL_COMMAND.format(inf=in_file, outf=out_file,
                                          keyf=parameter)
    print command
    os.system(command)
    if not os.path.isfile(out_file):
        print 'Output file not found: ' + out_file
        print "Check if 'confinterval.py' is in path"


def confidence_interval_all():
    '''
    Calculate confidence interval for all summarized results
    '''
    # Deletions and insertions
    par_list = [RAN, SLI, TOPK]
    for parameter in par_list:
        in_file = SUMMARY_DIR + os.sep + 'runtime_' + parameter + '.csv'
        out_file = RESULT_DIR + os.sep + 'runtime_' + parameter + '.csv'
        confidence_interval(parameter, in_file, out_file)
        in_file = SUMMARY_DIR + os.sep + 'memory_' + parameter + '.csv'
        out_file = RESULT_DIR + os.sep + 'memory_' + parameter + '.csv'
        confidence_interval(parameter, in_file, out_file)


def get_arguments(print_help=False):
    '''
    Get arguments
    '''
    import argparse
    parser = argparse.ArgumentParser('YFRun')
    parser.add_argument('-g', '--gen', action="store_true",
                        default=False,
                        help='Generate files')
    parser.add_argument('-r', '--run', action="store_true",
                        default=False,
                        help='Run experiments')
    parser.add_argument('-s', '--summarize', action="store_true",
                        default=False,
                        help='Summarize results')

    if print_help:
        parser.print_help()
    args = parser.parse_args()
    return args


def main():
    '''
    Main routine
    '''
    args = get_arguments()
    csv.register_dialect('table', delimiter='|', skipinitialspace=True)
    create_directories()
    exp_list = gen_experiment_list()
    if args.gen:
        print 'Generating files'
        gen_files(exp_list)
    elif args.run:
        print 'Running experiments'
        run_experiments(exp_list)
    elif args.summarize:
        print 'Summarizing results'
        summarize_all()
        print 'Calculating confidence intervals'
        confidence_interval_all()
    else:
        get_arguments(True)


if __name__ == '__main__':
    main()
