#!/usr/bin/env python3

# Author: Rajbir Bhattacharjee

"""
    Windows Kernel Memory Usage Visualizer
    Copyright (C) 2021, Rajbir Bhattacharjee

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""


"""
This script helps analyze memory leaks. It plots a graph for each tag.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import argparse
import glob
import dateutil
import codecs
from matplotlib.ticker import FormatStrFormatter
import seaborn as sns

class PoolEntries:
    VALID_COLUMNS = ['TotalUsedBytes', 'PagedDiff', 'NonPagedDiff',\
              'TotalDiff', 'PagedUsedBytes', 'NonPagedUsedBytes']
    VALID_TIME_COLUMNS = ['DateTime', 'DateTimeUTC']
        
    def __init__(self):
        self.individual_data_frames = list()
        self.pool_entries = None
        self.digest_called = False

    # ------------------------------------------------------------------------

    def get_encoding(self, filename:str) -> str:
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
            encoding=self.get_encoding(csv_file),\
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

        self.pool_entries['TotalDiff'] = \
            self.pool_entries['PagedDiff'] + self.pool_entries['NonPagedDiff']
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
            ignore_tags:list=[]) -> list:
        """
        Get the list of tags that have the highest usage        

        Parameters
        ----------
        n_tags : int
            Number of highest tags to get.
        by_col : str, optional
            Which column to calculate the highest usage by.
            The default is "TotalUsedBytes".
        ignore_tags : list, optional
            These columns will not be considered for efficiency.
            The default is [].
        Returns
        -------
        List(str)
            List of tags that have the highest usage.
        """
        if ignore_tags is None or not isinstance(ignore_tags, list):
            ignore_tags = []
        ignore_tags.append('TOTAL')
        reduced_df = \
            self.pool_entries[~self.pool_entries['Tag'].isin(ignore_tags)]
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
            ignore_tags:list=[]) -> list:
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
        ignore_tags : list, optional
            These columns will not be considered for efficiency.
            The default is [].
        Returns
        -------
        List(str)
            List of tags that have the highest usage.
        """

        def get_change(x):
            # This reports the percentage change in the tag
            (first, last) = tuple(x.to_numpy()[[0,-1]])
            return ((last - first)  * 100) / (last + 0.001)

        if ignore_tags is None or not isinstance(ignore_tags, list):
            ignore_tags = []
        ignore_tags.append('TOTAL')
        
        reduced_df = \
            self.pool_entries[~self.pool_entries['Tag'].isin(ignore_tags)]
        reduced_df = reduced_df[['Tag', by_col]]

        g = reduced_df[['Tag', by_col]]\
                .groupby(['Tag'])\
                .agg(get_change)\
                .sort_values([by_col], ascending=False)\
                .head(n_tags)

        return [row.name for _ , row in g.iterrows()]

    # ------------------------------------------------------------------------
    
    def get_tags_with_highest_average_usage(\
            self,\
            n_tags:int,\
            by_col:str="TotalUsedBytes",\
            ignore_tags:list=[]) -> list:
        """
        Get N tags with the highest average usage across the timeframe.

        Parameters
        ----------
        n_tags : int
            Number of tags to consider.
        by_col : str, optional
            Which column to calculate the highest usage by.
            The default is "TotalUsedBytes".. The default is "TotalUsedBytes".
        ignore_tags : list, optional
            These columns will not be considered for efficiency.
            The default is [].

        Returns
        -------
        List(str)
            List of tags that have the highest average usage.

        """
        
        if ignore_tags is None or not isinstance(ignore_tags, list):
            ignore_tags = []
        ignore_tags.append('TOTAL')
        
        reduced_df = \
            self.pool_entries[~self.pool_entries['Tag'].isin(ignore_tags)]
        reduced_df = reduced_df[['Tag', by_col]]

        g = reduced_df[['Tag', by_col]]\
                .groupby(['Tag'])\
                .mean()\
                .sort_values([by_col], ascending=False)\
                .head(n_tags)

        return [row.name for _ , row in g.iterrows()]
    
    # ------------------------------------------------------------------------
    def show_plot(\
            self,\
            tags: list,\
            timestamp_tag:str='DateTimeUTC',
            by_col:str='TotalUsedBytes',
            rcparams:dict=None) -> None:
        """
        Plot a set of tags and display

        Parameters
        ----------
        tags : list
            List of tags to plot
        timestamp_tag : str, optional
            Timestamp, localtime or UTC. The default is 'DateTimeUTC'.
            The other valid value is DateTime
        by_col : str, optional
            Which column to look at. The default is 'TotalUsedBytes'.
            Other possible values are:
                PagedDiff
                NonPagedDiff,
                TotalDiff,
                PagedUsedBytes,
                NonPagedUsedBytes,
                TotalUsedBytes
        rcparams : dict, optional
            rcParams for matplotlib. The default is None.

        Returns
        -------
        None
            DESCRIPTION.

        """
        if timestamp_tag not in PoolEntries.VALID_TIME_COLUMNS:
            raise Exception('Invalid timestamp tag')

        if by_col not in PoolEntries.VALID_COLUMNS:
            raise Exception('Invalid column name')

        if None is not rcparams: plt.rcParams.update(rcparams)

        title = by_col
        reduced_df = self.pool_entries[self.pool_entries['Tag'].isin(tags)]
        reduced_df = reduced_df[['Tag', by_col, 'DateTimeUTC']]
        yformatter = FormatStrFormatter('%d')

        if by_col.endswith('Bytes'):
            reduced_df = reduced_df.copy()
            reduced_df[[by_col]] = reduced_df[[by_col]].divide(1024 * 1024)
            title = f"{by_col} (MB)"
            yformatter = FormatStrFormatter('%.3f')
        else:
            title = f"{by_col} (n_allocs)"

        ax = reduced_df.pivot(\
                        index='DateTimeUTC',\
                        values=by_col,\
                        columns='Tag').plot(marker='.')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
        ax.yaxis.set_major_formatter(yformatter)
        ax.set_title(title)

        colorScheme = 'seaborn'
        plt.style.use([colorScheme])
        plt.style.context(colorScheme)

    # -----------------------------------------------------------------------
    def do_plot(\
            self,\
            by_col:str='TotalUsedBytes',\
            timestamp_tag:str='DateTimeUTC',\
            ignore_tags:list=None,\
            include_tags:list=None,\
            rcparams:dict=None,\
            n_most_changed:int=5,\
            n_highest:int=5,\
            n_highest_average:int=5) -> None:
        """
        Plot a column

        Parameters
        ----------
        by_col : str, optional
            The column to plot. The default is 'TotalUsedBytes'.
            Other possible values are:
                PagedDiff
                NonPagedDiff,
                TotalDiff,
                PagedUsedBytes,
                NonPagedUsedBytes,
                TotalUsedBytes
        timestamp_tag : str, optional
            Whether to use localtime or UTC. The default is 'DateTimeUTC'.
        ignore_tags : list, optional
            List of tags to ignore. The default is None.
        include_tags : list, optional
            List of tags to include. The default is None.
        rcparams : dict, optional
            rcParams for matplotlib configuration. The default is None.
        n_most_changed : int, optional
            Number of tags that show highest increase. The default is 5.
        n_highest : int, optional
            Number of tags that have highest peak usage. The default is 5.
        n_highest_average : int, optional
            Number of tags that have the highest average usage.
            The default is 5.

        Raises
        ------
        Exception
            DESCRIPTION.

        Returns
        -------
        None
            Does not return anything.

        """

        if timestamp_tag not in PoolEntries.VALID_TIME_COLUMNS:
            raise Exception('Invalid timestamp tag')

        if by_col not in PoolEntries.VALID_COLUMNS:
            raise Exception('Invalid column name')

        if None is include_tags or not isinstance(include_tags, list):
            include_tags = []

        if not self.digest_called: self.digest()

        all_tags = ['TOTAL']
        def select_tags(\
                    fn,\
                    n_tags:int,\
                    description:str):
            if n_tags > 0:
                taglist = fn(\
                            by_col=by_col,\
                            n_tags=n_tags,\
                            ignore_tags=ignore_tags)
                for t in taglist:
                    if t not in all_tags:
                        all_tags.append(t)
                print(f"tags with {description:25s}: {taglist}")
            
        
        select_tags(\
                    fn=self.get_most_changed_tags,
                    n_tags=n_most_changed,
                    description="GREATEST INCREASE")
        select_tags(\
                    fn=self.get_highest_tags,
                    n_tags=n_highest,
                    description="HIGHEST PEAK USAGE")    
        select_tags(\
                    fn=self.get_tags_with_highest_average_usage,
                    n_tags=n_highest_average,
                    description="HIGHEST AVERAGE USAGE")
        

        self.show_plot(\
                tags=all_tags,\
                timestamp_tag=timestamp_tag,\
                by_col=by_col,\
                rcparams=rcparams)
        plt.show()

    # -----------------------------------------------------------------------

# ---------------------------------------------------------------------------


def plot_files_in_directory(\
        dirname:str=".",\
        by_col:str=PoolEntries.VALID_COLUMNS[0],\
        time_col:str=PoolEntries.VALID_TIME_COLUMNS[0],\
        include_tags:list=[],\
        exclude_tags:list=[],\
        n_most_changed:int=5,\
        n_highest_usage:int=5,\
        n_highest_average_usage:int=5) -> None:
    """
    Read all files in a directory and plot the results

    Parameters
    ----------
    dirname : str, optional
        Directory where all the csv files are. The default is ".".
    by_col : str, optional
        The column to sort by. The default is PoolEntries.VALID_COLUMNS[0].
    time_col : str, optional
        Localtime or UTC. The default is PoolEntries.VALID_TIME_COLUMNS[0].
    include_tags : list, optional
        Must include these tags. The default is [].
    exclude_tags : list, optional
        Don't include these tags. The default is [].
    n_most_changed : int
        The number of tags to plot which have shown the most increase.
        The default is 5.
    n_highest_usage : int
        The number of tags to plot which have the highest peak usage.
        The default is 5.
    n_highest_average_usage : int
        The number of tags to plot which have the highest average usage.
        The default is 5.

    Returns
    -------
    None
        Does not return anything.

    """
    pe = PoolEntries()
    for fname in glob.glob(f"{dirname}/*pool.csv"):
        pe.add_csv_file(fname)
    pe.digest()
    pe.do_plot(\
        by_col=by_col,\
        timestamp_tag=time_col,\
        ignore_tags=exclude_tags,\
        include_tags=include_tags,\
        n_most_changed=n_most_changed,\
        n_highest=n_highest_usage,\
        n_highest_average=n_highest_average_usage,\
        )


def main():
    parser = argparse.ArgumentParser("visualize.py")
    parser.add_argument(\
                        "-d",\
                        "--directory",\
                        type=str,\
                        help="The directory where the CSV files reside",\
                        required=True)
    parser.add_argument(\
                        "-t",\
                        "--type",\
                        type=str,\
                        choices=PoolEntries.VALID_COLUMNS,\
                        help="Type of plot, valid values",\
                        required=True)
    parser.add_argument(\
                        "-ts",\
                        "--time-stamp",\
                        type=str,\
                        choices=PoolEntries.VALID_TIME_COLUMNS,\
                        help="Which timestamp to use",\
                        default=PoolEntries.VALID_TIME_COLUMNS[0],\
                        required=False)
    parser.add_argument(\
                        "-it",\
                        "--include-tags",\
                        type=str,\
                        nargs='+',\
                        help="List of tags that must be included",\
                        required=False)
    parser.add_argument(\
                        "-et",\
                        "--exclude-tags",\
                        type=str,\
                        nargs='+',\
                        help="List of tags that must be excluded",\
                        required=False)
    parser.add_argument(\
                        "-nmc",\
                        "--n-most-changed-tags",
                        type=int,
                        default=5,\
                        help="Number of tags that show highest growth",\
                        required=False)
    parser.add_argument(\
                        "-nh",\
                        "--n-highest-usage-tags",\
                        type=int,\
                        default=5,\
                        help="No of tags that have the highest peak usage",\
                        required=False)
    parser.add_argument(\
                        "-nha",\
                        "--n-highest-average-usage-tags",\
                        type=int,\
                        default=5,\
                        help="No of tags that have the highest average usage",\
                        required=False)
    args = parser.parse_args()
    args.include_tags = [] if None is args.include_tags else args.include_tags
    args.exclude_tags = [] if None is args.exclude_tags else args.exclude_tags
    plot_files_in_directory(\
                dirname=args.directory,\
                by_col=args.type,\
                time_col=args.time_stamp,\
                include_tags=args.include_tags,\
                exclude_tags=args.exclude_tags,\
                n_most_changed=args.n_most_changed_tags,\
                n_highest_usage=args.n_highest_usage_tags,\
                n_highest_average_usage=args.n_highest_average_usage_tags,\
                )


if "__main__" == __name__:
    main()
