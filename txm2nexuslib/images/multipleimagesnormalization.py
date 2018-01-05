#!/usr/bin/python

"""
(C) Copyright 2018 ALBA-CELLS
Author: Marc Rosanes Siscart
The program is distributed under the terms of the
GNU General Public License (or the Lesser GPL).

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import time
from joblib import Parallel, delayed
from tinydb import TinyDB, Query
from tinydb.storages import MemoryStorage

from util import create_subset_db
from txm2nexuslib.parser import get_file_paths
from txm2nexuslib.image.image_operate_lib import normalize_image


def normalize_images(file_index_fn, date=None, sample=None, energy=None,
                     create_subindex=False, cores=-1, average_ff=True):
    """Normalize images of one experiment.
    If date, sample and/or energy are indicated, only the corresponding
    images for the given date, sample and/or energy are normalized.
    The normalization of single images will be done in parallel.
    """

    if create_subindex:
        subset_file_index_fn = "index_proc.json"
        file_index_db = create_subset_db(file_index_fn, subset_file_index_fn,
                                         processed=True)
    else:
        file_index_db = TinyDB(file_index_fn)

    files_query = Query()
    if date or sample or energy:
        temp_db = TinyDB(storage=MemoryStorage)
        if date:
            records = file_index_db.search(files_query.date == date)
            temp_db.insert_multiple(records)
        if sample:
            if temp_db:
                records = temp_db.search(files_query.sample == sample)
                temp_db.purge()
                temp_db.insert_multiple(records)
            else:
                records = file_index_db.search(files_query.sample == sample)
                temp_db.insert_multiple(records)
        if energy:
            if temp_db:
                records = temp_db.search(files_query.energy == energy)
                temp_db.purge()
                temp_db.insert_multiple(records)
            else:
                records = file_index_db.search(files_query.energy == energy)
                temp_db.insert_multiple(records)
        file_index_db = temp_db

    root_path = os.path.dirname(os.path.abspath(file_index_fn))

    all_file_records = file_index_db.all()
    dates_samples_energies = []
    for record in all_file_records:
        dates_samples_energies.append((record["date"],
                                       record["sample"],
                                       record["energy"]))
    dates_samples_energies = list(set(dates_samples_energies))
    for date_sample_energie in dates_samples_energies:
        date = date_sample_energie[0]
        sample = date_sample_energie[1]
        energy = date_sample_energie[2]

        # Raw image records by given date, sample and energy
        query_cmd = ((files_query.date == date) &
                     (files_query.sample == sample) &
                     (files_query.energy == energy) &
                     (files_query.FF == False))
        h5_records = file_index_db.search(query_cmd)
        # FF records by given date, sample and energy
        query_cmd_ff = ((files_query.date == date) &
                        (files_query.sample == sample) &
                        (files_query.energy == energy) &
                        (files_query.FF == True))
        h5_ff_records = file_index_db.search(query_cmd_ff)
        files = get_file_paths(h5_records, root_path)
        files_ff = get_file_paths(h5_ff_records, root_path)

        if not files_ff:
            msg = "FlatFields are not present, images cannot be normalized"
            raise Exception(msg)

        if average_ff:
            # Average the FF files and use always the same average (for a
            # same date, sample and energy)
            # Normally the case of tomographies
            _, ff_norm_image = normalize_image(files[0],
                                               ff_img_filenames=files_ff)
            files.pop(0)
            start_time = time.time()
            if len(files):
                Parallel(n_jobs=cores, backend="multiprocessing")(
                    delayed(normalize_image)(
                        h5_file, average_normalized_ff_img=ff_norm_image
                    ) for h5_file in files)
            print("--- Normalize %d files took %s seconds ---" %
                  (len(files)+1, (time.time() - start_time)))
        else:
            # Same number of FF as sample data files
            # Normalize each single sample data image for a single FF image
            # Normally the case of spectrocopies
            # TODO
            pass

def main():
    #file_index = "/home/mrosanes/TOT/BEAMLINES/MISTRAL/DATA/" \
    #             "PARALLEL_IMAGING/image_operate_xrm_test_add/" \
    #             "tests4/xrm/index.json"

    file_index = "/home/mrosanes/TOT/BEAMLINES/MISTRAL/DATA/" \
                 "PARALLEL_IMAGING/PARALLEL_XRM2H5/tomo05/index.json"
    normalize_images(file_index, create_subindex=True, cores=-1)
    # sample="ols", energy=640, date=20161203)


if __name__ == "__main__":
    main()



