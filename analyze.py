#!/usr/bin/env python3

# Author: Rajbir Bhattacharjee
# Email: rajbir.bhattacharjee@gmail.com

"""
This script helps analyze memory leaks
"""

import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import sys
import os
import argparse

class PoolEntries:
    def __init__(self):
        self.pool_entries = None
        
    def GetEncoding(self, filename:str) -> str:
        """
        Try to guess the encoding of a file

        Parameters
        ----------
        filename : str
            The filename for which the encoding is to be guessed.

        Returns
        -------
        str
            The encoding. If it fails to find an encoding, it returns utf-8.

        """
        with open(filename, mode="rb") as f:
            fbytes = f.read(64)
            BOMS = (
                (BOM_UTF8, "utf-8"),
                (BOM_UTF16, "utf-16"),
                (BOM_UTF32_BE, "utf-32be"),
                (BOM_UTF32_LE, "utf-32le"),
                (BOM_UTF16_BE, "utf-16be"),
                (BOM_UTF16_LE, "utf-16le"),
            )
            try:
                return [encoding for bom, encoding in BOMS \
                        if fbytes.startswith(bom)][0]
            except:
                return "utf-8"

    
    def add_csv_file(self, csv_file:str) -> None:
        """
        Read a CSV file and add all its entries to the pool

        Parameters
        ----------
        csv_file : str
            The CSV file to add to the list.

        Returns
        -------
        None
            No return.

        """
        

def main():
    parser = argparse.ArgumentParser("Analyze Poolmon")
    parser.add_argument(\
                        "-d",\
                        "--directory",\
                        help="The directory where the CSV files reside",\
                        required=True)
    args = parser.parse_args()
    
if "__main__" == __name__:
    main()