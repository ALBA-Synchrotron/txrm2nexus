#!/usr/bin/python

"""
(C) Copyright 2018 ALBA-CELLS
Author(s): Marc Rosanes Siscart, Carlos Falcon Torres,
Zbigniew Reszela, Carlos Pascual
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
import subprocess
import argparse
from argparse import RawTextHelpFormatter
from tinydb import TinyDB, Query
from tinydb.middlewares import CachingMiddleware

from txm2nexuslib.images.multiplexrm2h5 import multiple_xrm_2_hdf5
from txm2nexuslib.images.util import copy2proc_multiple
from txm2nexuslib.images.multiplecrop import crop_images
from txm2nexuslib.images.multiplenormalization import normalize_images
from txm2nexuslib.images.multiplealign import align_images
from txm2nexuslib.images.multipleaverage import average_image_groups
from txm2nexuslib.images.imagestostack import many_images_to_h5_stack
from txm2nexuslib.parser import create_db, get_db_path, get_db


def partial_preprocesing(db_filename, crop, query=None,
                         date=None, sample=None, energy=None,
                         stacks_zp=False, table_name="hdf5_proc"):

    #single_zp = True

    # Multiple xrm 2 hdf5 files: working with many single images files
    multiple_xrm_2_hdf5(db_filename, query=query)
    # Copy of multiple hdf5 raw data files to files for processing
    copy2proc_multiple(db_filename, query=query, purge=True)
    # Multiple files hdf5 images crop: working with single images files
    if crop:
        crop_images(db_filename, query=query)
    # Normalize multiple hdf5 files: working with many single images files
    normalize_images(db_filename,
                     date=date, sample=sample, energy=energy,
                     query=query)

    #file_records = db_filename.all()
    #many_zps = check_if_multiple_zps()

    if stacks_zp or not many_zps:
        many_images_to_h5_stack(db_filename, table_name="hdf5_proc",
                                type_struct="normalized", suffix="_stack")

    # Align multiple hdf5 files: working with many single images files
    align_images(db_filename, align_method='cv2.TM_SQDIFF_NORMED')

    # Average multiple hdf5 files: working with many single images files
    average_image_groups(db_filename)

    # Build up hdf5 stacks from individual images
    many_images_to_h5_stack(db_filename, table_name=table_name,
                            type_struct="normalized_multifocus",
                            suffix="_FS")
    return db_filename


def main():
    """
    - Convert from xrm to hdf5 individual image hdf5 files
    - Copy raw hdf5 to new files for processing
    - Crop borders
    - Normalize
    - Create stacks by date, sample, energy and zpz,
      with multiple angles in each stack
    """
    def str2bool(v):
        return v.lower() in ("yes", "true", "t", "1")

    description = "pre-processing for biological samples"
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=RawTextHelpFormatter)
    parser.register('type', 'bool', str2bool)

    parser.add_argument('txm_txt_script', type=str,
                        help=('TXM txt script containing the commands used ' +
                              'to perform the image acquisition by the ' +
                              'BL09 TXM microscope'))

    parser.add_argument('--crop', type='bool',
                        default='True',
                        help='- If True: Crop images\n'
                             '- If False: Do not crop images\n'
                             '(default: True)')

    parser.add_argument('--table_for_stack', type=str,
                        default='hdf5_averages',
                        help=("DB table of image files to create the stacks" +
                              "(default: hdf5_averages)"))

    parser.add_argument('-z', '--stacks_zp', type='bool',
                        default='True',
                        help="Create individual ZP stacks\n"
                             "(default: True)")

    parser.add_argument('-m', '--hdf_to_mrc', type='bool',
                        default='True',
                        help="Convert FS hdf5 to mrc")

    parser.add_argument('--db', type=str2bool, nargs='?',
                        const=True, default=False,
                        help='- If True: Create database\n'
                             '- If False: Do not create db\n'
                             '(default: False)')

    parser.add_argument('--id', type=int,
                        help='- ID of the record in DB\n')

    args = parser.parse_args()

    print("\nWorkflow with Extended Depth of Field:\n" +
          "xrm -> hdf5 -> crop -> normalize -> align for same angle and" +
          " variable zpz -> average all images with same angle ->" +
          " make normalized stacks")
    start_time = time.time()


    # Align and average by repetition
    # variable = "sample"

    db_filename = get_db_path(args.txm_txt_script)
    query = Query()

    if args.db:
        create_db(args.txm_txt_script)

    if args.id:
        db = get_db(args.txm_txt_script, use_existing_db=True)
        dbsample = db.get(doc_id=args.id)
        date = dbsample['date']
        energy = dbsample['energy']
        sample = dbsample['sample']
        query_impl = ((query.date == date) &
                      (query.sample == sample) &
                      (query.energy == energy))
        partial_preprocesing(db_filename, args.crop, query=query_impl,
                             date=date, sample=sample, energy=energy,
                             stacks_zp=args.stacks_zp,
                             table_name=args.table_for_stack)

    print("Execution took %d seconds\n" % (time.time() - start_time))


if __name__ == "__main__":
    main()

