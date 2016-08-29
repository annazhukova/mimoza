# !/usr/bin/env python
# encoding: utf-8

from sbml_vis.mimoza_pipeline import process_sbml

__author__ = 'anna'

if __name__ == "__main__":

    # parameter parsing #
    import argparse

    parser = argparse.ArgumentParser(description="Generalizes and visualizes an SBML model.")
    parser.add_argument('--model', required=True, type=str, help="input model in SBML format")
    parser.add_argument('--verbose', action="store_true", help="print logging information")
    params = parser.parse_args()

    process_sbml(params.model, params.verbose, ub_ch_ids=None, web_page_prefix=None, generalize=True, log_file=None)
