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
import glob
import dateutil
import codecs
import typing
from typing import TypeVar

class PoolEntries:
    def __init__(self):
        self.individual_data_frames = list()
        self.pool_entries = None
        self.digest_called = False
    
    # ------------------------------------------------------------------------

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
                (codecs.BOM_UTF8, "utf-8"),
                (codecs.BOM_UTF16, "utf-16"),
                (codecs.BOM_UTF32_BE, "utf-32be"),
                (codecs.BOM_UTF32_LE, "utf-32le"),
                (codecs.BOM_UTF16_BE, "utf-16be"),
                (codecs.BOM_UTF16_LE, "utf-16le"),
            )
            try:
                return [encoding for bom, encoding in BOMS \
                        if fbytes.startswith(bom)][0]
            except:
                return "utf-8"

    # ------------------------------------------------------------------------
    
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
        df = pd.read_csv(\
            csv_file,\
            encoding=self.GetEncoding(csv_file),\
            parse_dates=True,\
            date_parser=dateutil.parser.parser)
        df['DateTime'] = pd.to_datetime(\
            df['DateTime'],\
            format=('%Y-%m-%dT%H:%M:%S'))
        df['DateTimeUTC'] = pd.to_datetime(\
            df['DateTimeUTC'],\
            format=('%Y-%m-%dT%H:%M:%S'))
        self.individual_data_frames.append(df)
    
    # ------------------------------------------------------------------------

    def add_totals_row(\
            self, \
            df:pd.DataFrame) -> pd.DataFrame:
        """
        Individual CSV files have all the tags at that moment, and each
        entry forms a tag. But there is no tag for all the tags combined.
        This function adds an entry for the total at any instance.

        Parameters
        ----------
        df : pd.DataFrame
            Input dataframe, this is one full CSV file equivalent at an
            instance
        templateDf : TYPE
            The template of the dataframe

        Returns
        -------
        pd.DataFrame
            The Dataframe with a total's row added

        """  
        column_types = {i:str(df.dtypes[i]) for i in df.columns}
        total_row_series = df.loc[0].copy()
        total_row_series["Tag"] = "TOTAL"
        for colname, coltype in column_types.items():
            if coltype.startswith('int'):
                total_row_series[colname] = df[colname].sum()
        df = df.append(total_row_series, ignore_index=True)
        return df

    # ------------------------------------------------------------------------

    def digest(self) -> pd.DataFrame:
        """
        Call this after adding all CSV files

        Returns
        -------
        pd.DataFrame
            Returns the DataFrame

        """

        if self.digest_called:
            raise Exception("digest() called again")
        self.digest_called = True

        all_dfs = []
        for df in self.individual_data_frames:
            df = self.add_totals_row(df)
            all_dfs.append(df)
        self.pool_entries = pd.concat(all_dfs)
        del(self.individual_data_frames)
        self.individual_data_frames = None

        # Sort by timestamp
        # First find the timestamp column name
        col_types = {i:str(self.pool_entries.dtypes[i]) for i in df.columns}
        date_col_name = None
        for colname, coltype in col_types.items():
            if coltype.startswith('datetime'): date_col_name = colname
        # Then sort by that column
        self.pool_entries.sort_values(\
            date_col_name,\
            ascending=True,\
            inplace=True,\
            ignore_index=True)
        return self.pool_entries
    
    # ------------------------------------------------------------------------

    def get_df(self) -> pd.DataFrame:
        """
        Get the dataframe

        Returns
        -------
        pd.DataFrame
            Returns the dataframe that is an aggregate of all time steps
            and includes TOTAL counts as well

        """
        if not self.digest_called: self.digest()
        return self.pool_entries
    
    # ------------------------------------------------------------------------

    def get_all_tags(self) -> list:
        """
        returns all tags that we've seen so far

        Returns
        -------
        List(str)
            All tags.

        """
        if not self.digest_called: self.digest()
        return [t for t in self.pool_entries['Tag'].unique()]
    
    # ------------------------------------------------------------------------

    def get_highest_tags(\
            self,\
            n_tags:int,\
            by_col:str="TotalUsedBytes",\
            ignore_columns:list=[]) -> list:
        """
        Get the list of tags that have the highest usage        

        Parameters
        ----------
        n_tags : int
            Number of highest tags to get.
        by_col : str, optional
            Which column to calculate the highest usage by.
            The default is "TotalUsedBytes".
        ignore_columns : list, optional
            These columns will not be considered for efficiency.
            The default is [].
        Returns
        -------
        List(str)
            List of tags that have the highest usage.
        """
        if ignore_columns is None or not isinstance(ignore_columns, list):
            ignore_columns = []
        ignore_columns.append('TOTAL')
        reduced_df = \
            self.pool_entries[~self.pool_entries['Tag'].isin(ignore_columns)]
        reduced_df = reduced_df[['Tag', by_col]]
        top_users = reduced_df.groupby(['Tag'])\
                                .max()\
                                .sort_values([by_col], ascending=False)\
                                .head(n_tags)
        return [row.name for _ , row in top_users.iterrows()]
    
    # ------------------------------------------------------------------------

    def get_most_changed_tags(\
            self,\
            n_tags:int,\
            by_col:str="TotalUsedBytes",\
            ignore_columns:list=[]) -> list:
        """
        Get the list of tags that see the highest change
        Highest change here is the difference between the first and the
        last entry

        Parameters
        ----------
        n_tags : int
            Number of highest tags to get.
        by_col : str, optional
            Which column to calculate the highest usage by.
            The default is "TotalUsedBytes".
        ignore_columns : list, optional
            These columns will not be considered for efficiency.
            The default is [].
        Returns
        -------
        List(str)
            List of tags that have the highest usage.
        """
        
        def get_change(x):
            (first, last) = tuple(x.to_numpy()[[0,-1]])
            return last - first
        
        if ignore_columns is None or not isinstance(ignore_columns, list):
            ignore_columns = []
        ignore_columns.append('TOTAL')
        reduced_df = \
            self.pool_entries[~self.pool_entries['Tag'].isin(ignore_columns)]
        reduced_df = reduced_df[['Tag', by_col]]
        
        g = reduced_df[['Tag', by_col]]\
                .groupby(['Tag'])\
                .agg(get_change)\
                .sort_values([by_col], ascending=False)\
                .head(n_tags)
                
        return [row.name for _ , row in g.iterrows()]
    
    # ------------------------------------------------------------------------
        
def read_directory(dirname:str) -> PoolEntries:
    """
    Reads a directory and returns all the items in a PoolEntry structure

    Parameters
    ----------
    dirname : str
        Name of the directory.

    Returns
    -------
    PoolEntries
        The entries from all the CSV files in the directory.

    """    
    pe = PoolEntries()
    for fname in glob.glob(f"{dirname}/*pool.csv"):
        pe.add_csv_file(fname)
    df = pe.get_df()
    print(pe.get_highest_tags(5, ignore_columns=['MmSt']))
    print(pe.get_most_changed_tags(5, ignore_columns=[]))
    alltags = pe.get_all_tags()
    return pe

def main():
    """
    parser = argparse.ArgumentParser("Analyze Poolmon")
    parser.add_argument(\
                        "-d",\
                        "--directory",\
                        help="The directory where the CSV files reside",\
                        required=True)
    args = parser.parse_args()
    """
    read_directory(".")


if "__main__" == __name__:
    main()
